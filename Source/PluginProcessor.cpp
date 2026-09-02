#include "PluginProcessor.h"
#include "PluginEditor.h"

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

    lastWorkerProfileIndex = static_cast<int>(aianalyzer::AnalysisProfile::Full);
    analysisWorker.setAnalysisProfile(aianalyzer::AnalysisProfile::Full);
    analysisWorker.setOscConfig(instanceId, oscHost, oscPort);
}

AIAnalyzerAudioProcessor::~AIAnalyzerAudioProcessor()
{
    analysisWorker.shutdown();
}

void AIAnalyzerAudioProcessor::prepareToPlay(double sampleRate, int)
{
    lastWorkerProfileIndex = getAnalysisProfileIndex();
    analysisWorker.setAnalysisProfile(
        static_cast<aianalyzer::AnalysisProfile>(lastWorkerProfileIndex));
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

    // Profile reads are cheap; notify the background worker only when the host
    // parameter actually changes. Normal realtime blocks do not signal/wake it.
    const auto currentProfileIndex = getAnalysisProfileIndex();
    if (currentProfileIndex != lastWorkerProfileIndex)
    {
        lastWorkerProfileIndex = currentProfileIndex;
        analysisWorker.setAnalysisProfile(
            static_cast<aianalyzer::AnalysisProfile>(currentProfileIndex));
    }

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
            analysisProfileParameter->setValueNotifyingHost(normalized);
        else
            analysisProfileParameter->setValue(normalized);
    }

    lastWorkerProfileIndex = profileIndex;
    analysisWorker.setAnalysisProfile(
        static_cast<aianalyzer::AnalysisProfile>(profileIndex));
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
