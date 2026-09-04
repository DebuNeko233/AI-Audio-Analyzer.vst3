#pragma once

#include <JuceHeader.h>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <memory>
#include <mutex>

#include "AnalysisFrame.h"
#include "AnalysisWorker.h"
#include "AnalyzerControlChannel.h"

class AIAnalyzerAudioProcessor final : public juce::AudioProcessor,
                                       private juce::AsyncUpdater
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

    int getUiLanguageIndex() const noexcept;
    void setUiLanguageIndex(int languageIndex) noexcept;

    bool getLatestAnalysis(aianalyzer::AnalysisFrame& frame) const;
    std::uint64_t getDroppedBlocks() const noexcept;

private:
    struct ControlProfileRequest
    {
        int profileIndex = 3;
        juce::String requestId;
        int replyPort = 0;
    };

    static constexpr std::size_t kMaxPendingControlRequests = 64;

    void enqueueControlProfileRequest(int profileIndex,
                                      juce::String requestId,
                                      int replyPort);
    void handleAsyncUpdate() override;

    mutable std::mutex configMutex;
    juce::String instanceId { "Track" };
    juce::String oscHost { "127.0.0.1" };
    int oscPort = 9855;

    juce::AudioParameterChoice* analysisProfileParameter = nullptr;
    std::atomic<int> lastWorkerProfileIndex {
        static_cast<int>(aianalyzer::AnalysisProfile::Full)
    };
    std::atomic<int> uiLanguageIndex { 0 };

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
    std::unique_ptr<aianalyzer::AnalyzerControlChannel> controlChannel;

    // OSC control arrives on JUCE's network thread. Queue it here and use
    // AsyncUpdater so host-visible parameter mutation always happens on the
    // message thread, never on the network or audio thread. The queue is
    // intentionally bounded and duplicate retries are coalesced before enqueue.
    std::mutex controlRequestMutex;
    std::deque<ControlProfileRequest> pendingControlRequests;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(AIAnalyzerAudioProcessor)
};
