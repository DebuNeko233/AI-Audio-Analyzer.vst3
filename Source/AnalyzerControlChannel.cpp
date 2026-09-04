#include "AnalyzerControlChannel.h"

#include <utility>

namespace aianalyzer
{
AnalyzerControlChannel::AnalyzerControlChannel(juce::String runtimeIdIn,
                                               ProfileRequestHandler handler)
    : runtimeId(std::move(runtimeIdIn)),
      profileRequestHandler(std::move(handler))
{
    const auto runtimeUtf8 = runtimeId.toStdString();
    for (const auto port : controlCandidatePorts(runtimeUtf8))
    {
        auto candidate = std::make_unique<juce::DatagramSocket>(false);
        if (!candidate->bindToPort(port, "127.0.0.1"))
            continue;

        controlSocket = std::move(candidate);
        boundPort = port;
        break;
    }

    if (controlSocket == nullptr)
        return;

    receiver.addListener(
        this,
        juce::OSCAddress(juce::String(kControlProfileAddress.data())));
    listenerAdded = true;
    receiverConnected = receiver.connectToSocket(*controlSocket);

    if (!receiverConnected)
    {
        receiver.removeListener(this);
        listenerAdded = false;
        controlSocket.reset();
        boundPort = -1;
    }
}

AnalyzerControlChannel::~AnalyzerControlChannel()
{
    if (receiverConnected)
        receiver.disconnect();
    if (listenerAdded)
        receiver.removeListener(this);
}

void AnalyzerControlChannel::oscMessageReceived(const juce::OSCMessage& message)
{
    if (message.size() < 4 || profileRequestHandler == nullptr)
        return;

    if (!message[0].isString()
        || !message[1].isInt32()
        || !message[2].isString()
        || !message[3].isInt32())
    {
        return;
    }

    const auto requestedRuntimeId = message[0].getString();
    const auto profileIndex = message[1].getInt32();
    const auto requestId = message[2].getString();
    const auto replyPort = message[3].getInt32();

    if (requestedRuntimeId != runtimeId
        || profileIndex < 0
        || profileIndex > 3
        || requestId.isEmpty()
        || replyPort < 1
        || replyPort > 65535)
    {
        return;
    }

    // This callback runs on JUCE's OSC network thread. Do not call the host or
    // mutate AudioProcessor parameters here. The processor callback only queues
    // a request and triggers an AsyncUpdater for the message thread.
    profileRequestHandler(profileIndex, requestId, replyPort);
}

void AnalyzerControlChannel::sendProfileAck(const juce::String& requestId,
                                            int profileIndex,
                                            int replyPort)
{
    if (requestId.isEmpty() || replyPort < 1 || replyPort > 65535)
        return;

    juce::OSCSender sender;
    if (!sender.connect("127.0.0.1", replyPort))
        return;

    juce::OSCMessage message(juce::String(kControlAckAddress.data()));
    message.addString(runtimeId);
    message.addString(requestId);
    message.addInt32(juce::jlimit(0, 3, profileIndex));
    message.addString(juce::String(kControlRevision.data()));
    sender.send(message);
}
} // namespace aianalyzer
