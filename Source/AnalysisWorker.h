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

    // DAW transport is sampled in processBlock(), where AudioPlayHead state is
    // valid, and handed to the worker using atomics only. Floats are deliberate:
    // they are lock-free on supported targets and match OSC float32 precision.
    // Store epoch last so a newly observed epoch publishes the preceding fields.
    void setTransportStateRealtimeSafe(bool supported,
                                       float timeSeconds,
                                       float ppqPosition,
                                       float bpm,
                                       int timeSignatureNumerator,
                                       int timeSignatureDenominator,
                                       bool isPlaying,
                                       bool isRecording,
                                       bool isLooping,
                                       float loopStartPpq,
                                       float loopEndPpq,
                                       std::uint32_t epoch,
                                       int blockSamples) noexcept
    {
        transportSupported.store(supported, std::memory_order_relaxed);
        transportTimeSeconds.store(timeSeconds, std::memory_order_relaxed);
        transportPpqPosition.store(ppqPosition, std::memory_order_relaxed);
        transportBpm.store(bpm, std::memory_order_relaxed);
        transportTimeSignatureNumerator.store(timeSignatureNumerator, std::memory_order_relaxed);
        transportTimeSignatureDenominator.store(timeSignatureDenominator, std::memory_order_relaxed);
        transportIsPlaying.store(isPlaying, std::memory_order_relaxed);
        transportIsRecording.store(isRecording, std::memory_order_relaxed);
        transportIsLooping.store(isLooping, std::memory_order_relaxed);
        transportLoopStartPpq.store(loopStartPpq, std::memory_order_relaxed);
        transportLoopEndPpq.store(loopEndPpq, std::memory_order_relaxed);
        transportBlockSamples.store(std::max(0, blockSamples), std::memory_order_relaxed);
        requestedTransportEpoch.store(epoch, std::memory_order_release);
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
    void applyTransportEpochChangeIfNeeded();
    void updateSignalState();
    void processLoudnessHop();
    bool loudnessMetricsDue(double lastMetricsMs, double nowMs) noexcept
    {
        if (lastMetricsMs <= 0.0)
        {
            loudnessSamplesSinceMetrics = 0;
            return true;
        }

        loudnessSamplesSinceMetrics += static_cast<std::uint64_t>(kHopSize);
        const auto elapsedMs = std::max(0.0, nowMs - lastMetricsMs);
        if (!aianalyzer::loudnessMetricsDue(
                loudnessSamplesSinceMetrics,
                sampleRate.load(std::memory_order_acquire),
                elapsedMs))
        {
            return false;
        }

        loudnessSamplesSinceMetrics = 0;
        return true;
    }
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

    // Realtime transport handoff. Epoch is incremented by the processor on a
    // playback start or discontinuity. The worker drops queued pre-jump audio
    // and resets pass-dependent state before accepting the new epoch.
    std::atomic<bool> transportSupported { false };
    std::atomic<float> transportTimeSeconds { 0.0f };
    std::atomic<float> transportPpqPosition { 0.0f };
    std::atomic<float> transportBpm { 0.0f };
    std::atomic<int> transportTimeSignatureNumerator { 4 };
    std::atomic<int> transportTimeSignatureDenominator { 4 };
    std::atomic<bool> transportIsPlaying { false };
    std::atomic<bool> transportIsRecording { false };
    std::atomic<bool> transportIsLooping { false };
    std::atomic<float> transportLoopStartPpq { 0.0f };
    std::atomic<float> transportLoopEndPpq { 0.0f };
    std::atomic<int> transportBlockSamples { 0 };
    std::atomic<std::uint32_t> requestedTransportEpoch { 0 };
    std::uint32_t activeTransportEpoch = 0;

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
    std::uint64_t loudnessSamplesSinceMetrics = 0;

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
