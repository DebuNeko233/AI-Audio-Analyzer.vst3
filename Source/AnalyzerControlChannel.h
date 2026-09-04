#pragma once

#include <JuceHeader.h>

#include <functional>
#include <memory>

#include "ControlProtocol.h"

namespace aianalyzer
{
class AnalyzerControlChannel final
    : private juce::OSCReceiver::ListenerWithOSCAddress<juce::OSCReceiver::RealtimeCallback>
{
public:
    using ProfileRequestHandler = std::function<void(int, juce::String, int)>;

    AnalyzerControlChannel(juce::String runtimeId, ProfileRequestHandler handler);
    ~AnalyzerControlChannel() override;

    bool isAvailable() const noexcept { return receiverConnected; }
    int getBoundPort() const noexcept { return boundPort; }

    // Called on the processor/message thread after the host-visible parameter
    // request has been accepted. The ACK is sent to a temporary loopback port
    // supplied by the MCP caller, so stopped transport does not prevent control
    // confirmation.
    void sendProfileAck(const juce::String& requestId,
                        int profileIndex,
                        int replyPort);

private:
    void oscMessageReceived(const juce::OSCMessage& message) override;

    juce::String runtimeId;
    ProfileRequestHandler profileRequestHandler;
    std::unique_ptr<juce::DatagramSocket> controlSocket;
    juce::OSCReceiver receiver { "AI Audio Analyzer Control" };
    bool listenerAdded = false;
    bool receiverConnected = false;
    int boundPort = -1;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(AnalyzerControlChannel)
};
} // namespace aianalyzer
