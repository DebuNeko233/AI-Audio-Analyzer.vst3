#pragma once

#include <JuceHeader.h>
#include <array>
#include <atomic>
#include <mutex>

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
    void processWindow();
    void refreshOscConnectionIfNeeded();
    void sendFrame(const AnalysisFrame& frame);

    static float amplitudeToDb(float value) noexcept;
    static float interpolateMagnitudeAtFrequency(const float* magnitudes,
                                                 int numBins,
                                                 double sampleRate,
                                                 float frequencyHz) noexcept;

    SpscStereoFifo fifo;

    std::atomic<double> sampleRate { 48000.0 };
    std::atomic<bool> resetRequested { true };

    std::array<float, kHopSize> hopLeft {};
    std::array<float, kHopSize> hopRight {};
    std::array<float, kFftSize> windowLeft {};
    std::array<float, kFftSize> windowRight {};
    int filledSamples = 0;

    juce::dsp::FFT fft { kFftOrder };
    juce::dsp::WindowingFunction<float> windowFunction {
        static_cast<std::size_t>(kFftSize),
        juce::dsp::WindowingFunction<float>::hann,
        false
    };
    std::array<float, kFftSize * 2> fftData {};

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
