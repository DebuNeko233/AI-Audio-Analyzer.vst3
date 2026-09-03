#pragma once

#include <JuceHeader.h>
#include <atomic>
#include <cstdint>
#include <mutex>

#include "AnalysisFrame.h"
#include "AnalysisWorker.h"

class AIAnalyzerAudioProcessor final : public juce::AudioProcessor
{
public:
    AIAnalyzerAudioProcessor();
    ~AIAnalyzerAudioProcessor() override;

    void prepareToPlay(double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;
    bool isBusesLayoutSupported(const BusesLayout& layouts) const override;
    void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }

    const juce::String getName() const override { return JucePlugin_Name; }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0.0; }

    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return {}; }
    void changeProgramName(int, const juce::String&) override {}

    void getStateInformation(juce::MemoryBlock& destData) override;
    void setStateInformation(const void* data, int sizeInBytes) override;

    void setAnalyzerConfig(const juce::String& instanceId,
                           const juce::String& host,
                           int port);
    void getAnalyzerConfig(juce::String& instanceId,
                           juce::String& host,
                           int& port) const;

    int getAnalysisProfileIndex() const noexcept;
    void setAnalysisProfileIndex(int profileIndex, bool notifyHost = true);

    bool getLatestAnalysis(aianalyzer::AnalysisFrame& frame) const;
    std::uint64_t getDroppedBlocks() const noexcept;

private:
    mutable std::mutex configMutex;
    juce::String instanceId { "Track" };
    juce::String oscHost { "127.0.0.1" };
    int oscPort = 9855;

    juce::AudioParameterChoice* analysisProfileParameter = nullptr;
    std::atomic<int> lastWorkerProfileIndex {
        static_cast<int>(aianalyzer::AnalysisProfile::Full)
    };

    // Audio-thread-only transport continuity state. None of this is serialized:
    // reopening a project starts a fresh Analyzer/MCP observation session.
    bool previousTransportValid = false;
    bool previousTransportPlaying = false;
    bool previousTransportHadSamples = false;
    std::int64_t previousTransportSamplePosition = 0;
    double previousTransportTimeSeconds = 0.0;
    int previousTransportBlockSamples = 0;
    std::uint32_t transportEpoch = 0;

    aianalyzer::AnalysisWorker analysisWorker;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(AIAnalyzerAudioProcessor)
};
