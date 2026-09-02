#include "PluginProcessor.h"
#include "PluginEditor.h"

AIAnalyzerAudioProcessor::AIAnalyzerAudioProcessor()
    : AudioProcessor(BusesProperties()
                         .withInput("Input", juce::AudioChannelSet::stereo(), true)
                         .withOutput("Output", juce::AudioChannelSet::stereo(), true))
{
    auto* identify = new juce::AudioParameterBool(
        juce::ParameterID { "identify", 1 },
        "Identify",
        false);
    addParameter(identify);
    identifyParameter = identify;
    lastIdentifyState.store(identify->getValue() >= 0.5f, std::memory_order_release);

    analysisWorker.setOscConfig(instanceId, oscHost, oscPort);
}

AIAnalyzerAudioProcessor::~AIAnalyzerAudioProcessor()
{
    analysisWorker.shutdown();
}

void AIAnalyzerAudioProcessor::prepareToPlay(double sampleRate, int)
{
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

    if (identifyParameter != nullptr)
    {
        const auto currentIdentifyState = identifyParameter->getValue() >= 0.5f;
        const auto previousIdentifyState = lastIdentifyState.exchange(
            currentIdentifyState, std::memory_order_acq_rel);

        if (currentIdentifyState != previousIdentifyState)
            analysisWorker.requestIdentify();
    }

    const auto numInputChannels = getTotalNumInputChannels();
    if (numInputChannels <= 0 || buffer.getNumSamples() <= 0)
        return;

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
