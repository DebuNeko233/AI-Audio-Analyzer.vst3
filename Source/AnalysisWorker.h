#pragma once

#include <JuceHeader.h>
#include <array>
#include <atomic>
#include <mutex>

#include <ebur128.h>

#include "AnalysisFrame.h"
#include "SpscStereoFifo.h"

namespace aianalyzer
{
class AnalysisWorker final : public juce::Thread
{
public:
    AnalysisWorker();
    ~AnalysisWorker() override;

    void prepare(double newSampleRate);
    void shutdown();

    bool pushAudio(const float* left, const float* right, int numSamples) noexcept;

    void setOscConfig(juce::String instanceId, juce::String host, int port);
    void requestIdentify() noexcept
    {
        identifyRequested.store(true, std::memory_order_release);
        notify();
    }

    bool getLatestFrame(AnalysisFrame& destination) const;
    std::uint64_t getDroppedBlocks() const noexcept { return fifo.getDroppedBlocks(); }

    void run() override;

private:
    struct OscConfig
    {
        juce::String instanceId { "Track" };
        juce::String host { "127.0.0.1" };
        int port = 9855;
    };

    void resetAnalysisState();
    void resetLoudnessState();
    void updateSignalState();
    void processLoudnessHop();
    void processWindow();
    void refreshOscConnectionIfNeeded();
    void sendFrame(const AnalysisFrame& frame);
    void sendIdentify();

    static float amplitudeToDb(float value) noexcept;
    static float sanitizeLoudness(double value) noexcept;
    static float interpolateMagnitudeAtFrequency(const float* magnitudes,
                                                 int numBins,
                                                 double sampleRate,
                                                 float frequencyHz) noexcept;

    SpscStereoFifo fifo;

    std::atomic<double> sampleRate { 48000.0 };
    std::atomic<bool> resetRequested { true };
    std::atomic<bool> identifyRequested { false };

    std::array<float, kHopSize> hopLeft {};
    std::array<float, kHopSize> hopRight {};
    std::array<float, kHopSize * 2> interleavedHop {};
    std::array<float, kFftSize> windowLeft {};
    std::array<float, kFftSize> windowRight {};
    int filledSamples = 0;

    juce::dsp::FFT fft { kFftOrder };
    juce::dsp::WindowingFunction<float> windowFunction {
        static_cast<std::size_t>(kFftSize),
        juce::dsp::WindowingFunction<float>::hann,
        false
    };
    std::array<float, kFftSize * 2> fftLeftData {};
    std::array<float, kFftSize * 2> fftRightData {};
    std::array<float, kFftSize> midMagnitudes {};

    ebur128_state* loudnessState = nullptr;
    float latestLufsShortTerm = -120.0f;
    float latestLufsIntegrated = -120.0f;
    float latestTruePeakDbtp = -120.0f;
    float maxTruePeakDbtp = -120.0f;

    bool signalPresent = false;
    float detectorPeakDb = -120.0f;
    double silenceSeconds = 0.0;

    // Generated once per live VST3 instance and deliberately not serialized.
    // Duplicating a mixer track therefore creates a fresh identity even when
    // the user-visible instance name is copied.
    juce::String runtimeUuid;

    mutable std::mutex latestMutex;
    AnalysisFrame latestFrame;
    bool hasLatestFrame = false;

    mutable std::mutex configMutex;
    OscConfig pendingConfig;
    OscConfig activeConfig;
    std::atomic<bool> configDirty { true };

    juce::OSCSender oscSender;
    bool oscConnected = false;
    double lastOscSendMs = 0.0;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(AnalysisWorker)
};
} // namespace aianalyzer
