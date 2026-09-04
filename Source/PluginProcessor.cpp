#include "PluginProcessor.h"
#include "PluginEditor.h"

#include <cmath>
#include <functional>
#include <utility>

namespace
{
class IdentifyParameter final : public juce::AudioParameterBool
{
public:
    explicit IdentifyParameter(std::function<void()> callback)
        : juce::AudioParameterBool(
              juce::ParameterID { "identify", 1 },
              "Identify",
              false),
          onChange(std::move(callback))
    {
    }

protected:
    void valueChanged(bool) override
    {
        if (onChange)
            onChange();
    }

private:
    std::function<void()> onChange;
};
} // namespace

AIAnalyzerAudioProcessor::AIAnalyzerAudioProcessor()
    : AudioProcessor(BusesProperties()
                         .withInput("Input", juce::AudioChannelSet::stereo(), true)
                         .withOutput("Output", juce::AudioChannelSet::stereo(), true))
{
    // Keep Identify first: it was historically the only host-visible parameter.
    // Stable IDs remain authoritative, but preserving its index reduces risk in
    // hosts that also retain parameter order/index information.
    addParameter(new IdentifyParameter([this]
    {
        analysisWorker.requestIdentify();
    }));

    analysisProfileParameter = new juce::AudioParameterChoice(
        juce::ParameterID { "analysis_profile", 1 },
        "Analysis Profile",
        juce::StringArray { "Eco", "Balanced", "Mix", "Full" },
        static_cast<int>(aianalyzer::AnalysisProfile::Full));
    addParameter(analysisProfileParameter);

    lastWorkerProfileIndex.store(
        static_cast<int>(aianalyzer::AnalysisProfile::Full),
        std::memory_order_relaxed);
    analysisWorker.setAnalysisProfile(aianalyzer::AnalysisProfile::Full);
    analysisWorker.setOscConfig(instanceId, oscHost, oscPort);

    // Analyzer-owned control is intentionally narrow: only the measurement
    // profile can be changed. The receiver listens on loopback only and routes
    // requests to this processor's message thread through AsyncUpdater.
    controlChannel = std::make_unique<aianalyzer::AnalyzerControlChannel>(
        analysisWorker.getRuntimeUuid(),
        [this](int profileIndex, juce::String requestId, int replyPort)
        {
            enqueueControlProfileRequest(profileIndex, std::move(requestId), replyPort);
        });
}

AIAnalyzerAudioProcessor::~AIAnalyzerAudioProcessor()
{
    cancelPendingUpdate();
    controlChannel.reset();
    analysisWorker.shutdown();
}

void AIAnalyzerAudioProcessor::prepareToPlay(double sampleRate, int)
{
    const auto currentProfileIndex = getAnalysisProfileIndex();
    lastWorkerProfileIndex.store(currentProfileIndex, std::memory_order_relaxed);
    analysisWorker.setAnalysisProfile(
        static_cast<aianalyzer::AnalysisProfile>(currentProfileIndex));

    previousTransportValid = false;
    previousTransportPlaying = false;
    previousTransportHadSamples = false;
    previousTransportSamplePosition = 0;
    previousTransportTimeSeconds = 0.0;
    previousTransportBlockSamples = 0;
    transportEpoch = 0;

    analysisWorker.prepare(sampleRate);

    juce::String currentInstance;
    juce::String currentHost;
    int currentPort = 9855;
    getAnalyzerConfig(currentInstance, currentHost, currentPort);
    analysisWorker.setOscConfig(currentInstance, currentHost, currentPort);
}

void AIAnalyzerAudioProcessor::releaseResources()
{
    analysisWorker.shutdown();
}

bool AIAnalyzerAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    const auto input = layouts.getMainInputChannelSet();
    const auto output = layouts.getMainOutputChannelSet();

    if (input != output)
        return false;

    return input == juce::AudioChannelSet::mono()
        || input == juce::AudioChannelSet::stereo();
}

void AIAnalyzerAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                             juce::MidiBuffer&)
{
    juce::ScopedNoDenormals noDenormals;

    const auto numInputChannels = getTotalNumInputChannels();
    if (numInputChannels <= 0 || buffer.getNumSamples() <= 0)
        return;

    // Profile reads are cheap; hand the change to the worker only when the host
    // parameter actually changes. The realtime-safe setter is atomic-only and
    // never signals a condition variable from the audio callback.
    const auto currentProfileIndex = getAnalysisProfileIndex();
    if (currentProfileIndex
        != lastWorkerProfileIndex.load(std::memory_order_relaxed))
    {
        lastWorkerProfileIndex.store(currentProfileIndex, std::memory_order_relaxed);
        analysisWorker.setAnalysisProfileRealtimeSafe(
            static_cast<aianalyzer::AnalysisProfile>(currentProfileIndex));
    }

    // Capture host transport while AudioPlayHead information is valid. No lock,
    // allocation, OSC, or worker wake occurs here. A transport epoch identifies
    // one continuous forward playback pass; starts, seeks and loop jumps split
    // the history so delayed LLM/tool calls cannot blend unrelated song ranges.
    bool transportSupported = false;
    float transportTimeSeconds = 0.0f;
    float transportPpqPosition = 0.0f;
    float transportBpm = 0.0f;
    int timeSignatureNumerator = 4;
    int timeSignatureDenominator = 4;
    bool isPlaying = false;
    bool isRecording = false;
    bool isLooping = false;
    float loopStartPpq = 0.0f;
    float loopEndPpq = 0.0f;
    bool hasSamplePosition = false;
    std::int64_t samplePosition = 0;
    double preciseTimeSeconds = 0.0;

    if (auto* playHead = getPlayHead())
    {
        if (auto position = playHead->getPosition())
        {
            isPlaying = position->getIsPlaying();
            isRecording = position->getIsRecording();
            isLooping = position->getIsLooping();

            if (const auto bpm = position->getBpm())
                transportBpm = static_cast<float>(*bpm);

            if (const auto timeSignature = position->getTimeSignature())
            {
                timeSignatureNumerator = std::max(1, timeSignature->numerator);
                timeSignatureDenominator = std::max(1, timeSignature->denominator);
            }

            if (const auto ppq = position->getPpqPosition())
                transportPpqPosition = static_cast<float>(*ppq);

            if (const auto loopPoints = position->getLoopPoints())
            {
                loopStartPpq = static_cast<float>(loopPoints->ppqStart);
                loopEndPpq = static_cast<float>(loopPoints->ppqEnd);
            }

            if (const auto samples = position->getTimeInSamples())
            {
                hasSamplePosition = true;
                samplePosition = *samples;
            }

            if (const auto seconds = position->getTimeInSeconds())
            {
                preciseTimeSeconds = *seconds;
                transportSupported = std::isfinite(preciseTimeSeconds);
            }
            else if (hasSamplePosition)
            {
                const auto currentSampleRate = std::max(1.0, getSampleRate());
                preciseTimeSeconds = static_cast<double>(samplePosition) / currentSampleRate;
                transportSupported = true;
            }

            if (transportSupported)
                transportTimeSeconds = static_cast<float>(std::max(0.0, preciseTimeSeconds));
        }
    }

    if (transportSupported)
    {
        bool newEpoch = false;
        if (isPlaying && (!previousTransportValid || !previousTransportPlaying))
        {
            newEpoch = true;
        }
        else if (isPlaying && previousTransportValid && previousTransportPlaying)
        {
            if (hasSamplePosition && previousTransportHadSamples)
            {
                const auto expected = previousTransportSamplePosition
                                    + static_cast<std::int64_t>(previousTransportBlockSamples);
                const auto delta = samplePosition >= expected
                    ? samplePosition - expected
                    : expected - samplePosition;
                const auto tolerance = static_cast<std::int64_t>(
                    std::max(2048, buffer.getNumSamples() * 4));
                if (delta > tolerance)
                    newEpoch = true;
            }
            else
            {
                const auto currentSampleRate = std::max(1.0, getSampleRate());
                const auto expectedSeconds = previousTransportTimeSeconds
                    + static_cast<double>(previousTransportBlockSamples) / currentSampleRate;
                const auto toleranceSeconds = std::max(
                    0.05,
                    static_cast<double>(buffer.getNumSamples() * 4) / currentSampleRate);
                if (std::abs(preciseTimeSeconds - expectedSeconds) > toleranceSeconds)
                    newEpoch = true;
            }
        }

        if (newEpoch)
            ++transportEpoch;

        previousTransportValid = true;
        previousTransportPlaying = isPlaying;
        previousTransportHadSamples = hasSamplePosition;
        previousTransportSamplePosition = samplePosition;
        previousTransportTimeSeconds = preciseTimeSeconds;
        previousTransportBlockSamples = buffer.getNumSamples();
    }
    else
    {
        previousTransportValid = false;
        previousTransportPlaying = false;
        previousTransportHadSamples = false;
        previousTransportBlockSamples = buffer.getNumSamples();
    }

    analysisWorker.setTransportStateRealtimeSafe(
        transportSupported,
        transportTimeSeconds,
        transportPpqPosition,
        transportBpm,
        timeSignatureNumerator,
        timeSignatureDenominator,
        isPlaying,
        isRecording,
        isLooping,
        loopStartPpq,
        loopEndPpq,
        transportEpoch,
        buffer.getNumSamples());

    const auto* left = buffer.getReadPointer(0);
    const auto* right = numInputChannels > 1 ? buffer.getReadPointer(1) : nullptr;
    analysisWorker.pushAudio(left, right, buffer.getNumSamples());
}

juce::AudioProcessorEditor* AIAnalyzerAudioProcessor::createEditor()
{
    return new AIAnalyzerAudioProcessorEditor(*this);
}

void AIAnalyzerAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    juce::String currentInstance;
    juce::String currentHost;
    int currentPort = 9855;
    getAnalyzerConfig(currentInstance, currentHost, currentPort);

    juce::XmlElement xml("AIAnalyzerState");
    xml.setAttribute("instanceId", currentInstance);
    xml.setAttribute("oscHost", currentHost);
    xml.setAttribute("oscPort", currentPort);
    xml.setAttribute("analysisProfile", getAnalysisProfileIndex());
    xml.setAttribute("uiLanguage", getUiLanguageIndex());
    copyXmlToBinary(xml, destData);
}

void AIAnalyzerAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    const auto xml = getXmlFromBinary(data, sizeInBytes);
    if (xml == nullptr || !xml->hasTagName("AIAnalyzerState"))
        return;

    setAnalyzerConfig(xml->getStringAttribute("instanceId", "Track"),
                      xml->getStringAttribute("oscHost", "127.0.0.1"),
                      xml->getIntAttribute("oscPort", 9855));

    // Older project state does not contain this attribute. Full preserves the
    // exact pre-adaptive-analysis behavior in that case.
    setAnalysisProfileIndex(
        xml->getIntAttribute("analysisProfile", static_cast<int>(aianalyzer::AnalysisProfile::Full)),
        false);

    // GUI language is a local preference, not a host automation parameter.
    // Older projects default to English for backwards-compatible presentation.
    setUiLanguageIndex(xml->getIntAttribute("uiLanguage", 0));
}

void AIAnalyzerAudioProcessor::setAnalyzerConfig(const juce::String& newInstanceId,
                                                  const juce::String& newHost,
                                                  int newPort)
{
    juce::String cleanInstance = newInstanceId.trim();
    juce::String cleanHost = newHost.trim();

    if (cleanInstance.isEmpty())
        cleanInstance = "Track";
    if (cleanHost.isEmpty())
        cleanHost = "127.0.0.1";

    newPort = juce::jlimit(1, 65535, newPort);

    {
        const std::scoped_lock lock(configMutex);
        instanceId = cleanInstance;
        oscHost = cleanHost;
        oscPort = newPort;
    }

    analysisWorker.setOscConfig(cleanInstance, cleanHost, newPort);
}

void AIAnalyzerAudioProcessor::getAnalyzerConfig(juce::String& outInstanceId,
                                                  juce::String& outHost,
                                                  int& outPort) const
{
    const std::scoped_lock lock(configMutex);
    outInstanceId = instanceId;
    outHost = oscHost;
    outPort = oscPort;
}

int AIAnalyzerAudioProcessor::getAnalysisProfileIndex() const noexcept
{
    if (analysisProfileParameter == nullptr)
        return static_cast<int>(aianalyzer::AnalysisProfile::Full);
    return juce::jlimit(0, 3, analysisProfileParameter->getIndex());
}

void AIAnalyzerAudioProcessor::setAnalysisProfileIndex(int profileIndex, bool notifyHost)
{
    profileIndex = juce::jlimit(0, 3, profileIndex);
    if (analysisProfileParameter != nullptr)
    {
        const auto normalized = analysisProfileParameter->convertTo0to1(
            static_cast<float>(profileIndex));
        if (notifyHost)
        {
            analysisProfileParameter->setValueNotifyingHost(normalized);
        }
        else
        {
            // AudioParameterChoice narrows setValue() to private in JUCE 8.
            // Call through the public AudioProcessorParameter interface so state
            // restoration updates the parameter without emitting a host change.
            static_cast<juce::AudioProcessorParameter*>(analysisProfileParameter)
                ->setValue(normalized);
        }
    }

    lastWorkerProfileIndex.store(profileIndex, std::memory_order_relaxed);
    analysisWorker.setAnalysisProfile(
        static_cast<aianalyzer::AnalysisProfile>(profileIndex));
}

void AIAnalyzerAudioProcessor::enqueueControlProfileRequest(int profileIndex,
                                                            juce::String requestId,
                                                            int replyPort)
{
    if (profileIndex < 0
        || profileIndex > 3
        || requestId.isEmpty()
        || replyPort < 1
        || replyPort > 65535)
    {
        return;
    }

    {
        const std::scoped_lock lock(controlRequestMutex);

        // MCP deliberately retransmits one request while waiting for its ACK.
        // Coalesce exact retries so a temporarily busy message thread cannot
        // turn one logical request into an unbounded queue of host mutations.
        for (const auto& pending : pendingControlRequests)
        {
            if (pending.profileIndex == profileIndex
                && pending.requestId == requestId
                && pending.replyPort == replyPort)
            {
                return;
            }
        }

        // Local loopback is still an external input boundary. Keep memory use
        // bounded even if another local process floods valid-looking requests.
        // Dropping the oldest request is safe because MCP retries until timeout.
        if (pendingControlRequests.size() >= kMaxPendingControlRequests)
            pendingControlRequests.pop_front();

        pendingControlRequests.push_back({ profileIndex, std::move(requestId), replyPort });
    }
    triggerAsyncUpdate();
}

void AIAnalyzerAudioProcessor::handleAsyncUpdate()
{
    std::deque<ControlProfileRequest> requests;
    {
        const std::scoped_lock lock(controlRequestMutex);
        requests.swap(pendingControlRequests);
    }

    for (const auto& request : requests)
    {
        const auto previousProfileIndex = getAnalysisProfileIndex();
        const bool changed = previousProfileIndex != request.profileIndex;

        if (changed)
            setAnalysisProfileIndex(request.profileIndex, true);

        if (controlChannel != nullptr)
        {
            controlChannel->sendProfileAck(
                request.requestId,
                request.profileIndex,
                request.replyPort,
                changed);
        }
    }
}

int AIAnalyzerAudioProcessor::getUiLanguageIndex() const noexcept
{
    return juce::jlimit(0, 1, uiLanguageIndex.load(std::memory_order_relaxed));
}

void AIAnalyzerAudioProcessor::setUiLanguageIndex(int languageIndex) noexcept
{
    uiLanguageIndex.store(juce::jlimit(0, 1, languageIndex), std::memory_order_relaxed);
}

bool AIAnalyzerAudioProcessor::getLatestAnalysis(aianalyzer::AnalysisFrame& frame) const
{
    return analysisWorker.getLatestFrame(frame);
}

std::uint64_t AIAnalyzerAudioProcessor::getDroppedBlocks() const noexcept
{
    return analysisWorker.getDroppedBlocks();
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new AIAnalyzerAudioProcessor();
}
