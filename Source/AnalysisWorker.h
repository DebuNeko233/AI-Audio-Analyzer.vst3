#pragma once

#include <JuceHeader.h>
#include <array>
#include <atomic>
#include <mutex>

#include <ebur128.h>

#include "AnalysisFrame.h"
#include "SpscStereoFifo.h"
#include "WorkerScheduling.h"

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
    void setAnalysisProfile(AnalysisProfile profile) noexcept;

    // Realtime path: atomic handoff only. Do not call Thread::notify(), take a
    // lock, allocate, or perform any analysis from the audio callback. The
    // worker polls requestedProfile before each FIFO wait/processing cycle.
    void setAnalysisProfileRealtimeSafe(AnalysisProfile profile) noexcept
    {
        requestedProfile.store(
            juce::jlimit(0, 3, static_cast<int>(profile)),
            std::memory_order_release);
    }

    AnalysisProfile getAnalysisProfile() const noexcept;

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
    void resetTemporalAccumulator() noexcept;
    void resetSemanticCache() noexcept;
    void applyProfileChangeIfNeeded();
    void updateSignalState();
    void processLoudnessHop();
    void processCoreWindow();
    void processWindow();
    void publishFrame(AnalysisFrame frame, bool temporalEnabled);
    void attachRuntimeMetadata(AnalysisFrame& frame) const noexcept;
    void updatePerformanceTelemetry(double busyMilliseconds, double nowMilliseconds) noexcept;
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
    std::atomic<int> requestedProfile { static_cast<int>(AnalysisProfile::Full) };
    AnalysisProfile activeProfile = AnalysisProfile::Full;

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
    std::array<float, kFftSize> sideMagnitudes {};

    // Temporal state. Spectral flux compares normalized successive spectra at
    // the internal FFT-hop rate when the active profile includes Temporal.
    std::array<float, kFftSize> previousMidMagnitudes {};
    bool hasPreviousTemporalFrame = false;
    float previousWindowRmsDb = -120.0f;
    double temporalAccumulatedSeconds = 0.0;
    double temporalSpectralFluxSum = 0.0;
    int temporalSpectralFluxCount = 0;
    float temporalSpectralFluxPeak = 0.0f;
    float temporalRmsRisePeakDb = 0.0f;
    double temporalLowBandPowerSum = 0.0;
    int temporalLowBandPowerCount = 0;

    // Semantic analysis is intentionally lower-rate than hop-level FFT work.
    std::array<float, kNumChromaBins> cachedChroma {};
    float cachedChromaEnergyRatio = 0.0f;
    float cachedSingleF0HarmonicEnergyRatio = 0.0f;
    float cachedHarmonicF0CandidateHz = 0.0f;
    double lastSemanticAnalysisMs = 0.0;

    ebur128_state* loudnessState = nullptr;
    float latestLufsShortTerm = -120.0f;
    float latestLufsIntegrated = -120.0f;
    float latestTruePeakDbtp = -120.0f;
    float maxTruePeakDbtp = -120.0f;
    double lastLoudnessMetricsMs = 0.0;

    bool signalPresent = false;
    float detectorPeakDb = -120.0f;
    double silenceSeconds = 0.0;

    // Performance/scheduling telemetry. Ratios are background-worker metrics,
    // not DAW audio-thread CPU measurements.
    double lastReducedAnalysisMs = 0.0;
    double performanceWindowStartMs = 0.0;
    double performanceBusyMs = 0.0;
    std::uint64_t fftRunsInWindow = 0;
    std::uint64_t semanticRunsInWindow = 0;
    float workerLoadRatio = 0.0f;
    float fftRunsPerSecond = 0.0f;
    float semanticRunsPerSecond = 0.0f;

    // Generated once per live VST3 instance and deliberately not serialized.
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
