#include "AnalysisWorker.h"

#include <algorithm>
#include <cmath>
#include <numeric>

namespace aianalyzer
{
namespace
{
constexpr float kFloorDb = -120.0f;
constexpr float kMinFrequencyHz = 20.0f;
constexpr float kMaxFrequencyHz = 20000.0f;
constexpr float kRolloffFraction = 0.85f;
constexpr double kOscIntervalMs = 100.0; // 10 Hz network update rate

float bandCenterHz(int index)
{
    const auto t = (static_cast<float>(index) + 0.5f) / static_cast<float>(kNumBands);
    return kMinFrequencyHz * std::pow(kMaxFrequencyHz / kMinFrequencyHz, t);
}
} // namespace

AnalysisWorker::AnalysisWorker()
    : juce::Thread("AI Analyzer Analysis")
{
}

AnalysisWorker::~AnalysisWorker()
{
    shutdown();
}

void AnalysisWorker::prepare(double newSampleRate)
{
    sampleRate.store(newSampleRate > 0.0 ? newSampleRate : 48000.0, std::memory_order_release);
    fifo.reset();
    resetRequested.store(true, std::memory_order_release);

    if (!isThreadRunning())
        startThread();
}

void AnalysisWorker::shutdown()
{
    if (isThreadRunning())
    {
        signalThreadShouldExit();
        stopThread(1500);
    }

    oscSender.disconnect();
    oscConnected = false;
}

bool AnalysisWorker::pushAudio(const float* left, const float* right, int numSamples) noexcept
{
    return fifo.push(left, right, numSamples);
}

void AnalysisWorker::setOscConfig(juce::String instanceId, juce::String host, int port)
{
    instanceId = instanceId.trim();
    host = host.trim();

    if (instanceId.isEmpty())
        instanceId = "Track";
    if (host.isEmpty())
        host = "127.0.0.1";

    port = juce::jlimit(1, 65535, port);

    {
        const std::scoped_lock lock(configMutex);
        pendingConfig.instanceId = std::move(instanceId);
        pendingConfig.host = std::move(host);
        pendingConfig.port = port;
    }

    configDirty.store(true, std::memory_order_release);
}

bool AnalysisWorker::getLatestFrame(AnalysisFrame& destination) const
{
    const std::scoped_lock lock(latestMutex);
    if (!hasLatestFrame)
        return false;

    destination = latestFrame;
    return true;
}

void AnalysisWorker::resetAnalysisState()
{
    std::fill(windowLeft.begin(), windowLeft.end(), 0.0f);
    std::fill(windowRight.begin(), windowRight.end(), 0.0f);
    std::fill(fftData.begin(), fftData.end(), 0.0f);
    filledSamples = 0;
}

float AnalysisWorker::amplitudeToDb(float value) noexcept
{
    return juce::Decibels::gainToDecibels(std::max(value, 1.0e-9f), kFloorDb);
}

float AnalysisWorker::interpolateMagnitudeAtFrequency(const float* magnitudes,
                                                       int numBins,
                                                       double currentSampleRate,
                                                       float frequencyHz) noexcept
{
    const auto bin = static_cast<float>(frequencyHz * static_cast<float>(kFftSize) /
                                        static_cast<float>(currentSampleRate));
    const auto lower = juce::jlimit(0, numBins - 1, static_cast<int>(std::floor(bin)));
    const auto upper = juce::jlimit(0, numBins - 1, lower + 1);
    const auto fraction = juce::jlimit(0.0f, 1.0f, bin - static_cast<float>(lower));
    return magnitudes[lower] + fraction * (magnitudes[upper] - magnitudes[lower]);
}

void AnalysisWorker::processWindow()
{
    const auto currentSampleRate = sampleRate.load(std::memory_order_acquire);
    AnalysisFrame frame;
    frame.sampleRate = currentSampleRate;
    frame.timestampSeconds = juce::Time::getMillisecondCounterHiRes() / 1000.0;

    double sumSquares = 0.0;
    double sumLR = 0.0;
    double sumL2 = 0.0;
    double sumR2 = 0.0;
    double sumMid2 = 0.0;
    double sumSide2 = 0.0;
    float peak = 0.0f;

    for (int i = 0; i < kFftSize; ++i)
    {
        const auto l = windowLeft[static_cast<std::size_t>(i)];
        const auto r = windowRight[static_cast<std::size_t>(i)];
        const auto mid = 0.5f * (l + r);
        const auto side = 0.5f * (l - r);

        peak = std::max(peak, std::max(std::abs(l), std::abs(r)));
        sumSquares += static_cast<double>(l) * l + static_cast<double>(r) * r;
        sumLR += static_cast<double>(l) * r;
        sumL2 += static_cast<double>(l) * l;
        sumR2 += static_cast<double>(r) * r;
        sumMid2 += static_cast<double>(mid) * mid;
        sumSide2 += static_cast<double>(side) * side;

        fftData[static_cast<std::size_t>(i)] = mid;
    }

    std::fill(fftData.begin() + kFftSize, fftData.end(), 0.0f);
    windowFunction.multiplyWithWindowingTable(fftData.data(), kFftSize);
    fft.performFrequencyOnlyForwardTransform(fftData.data());

    const auto rms = static_cast<float>(std::sqrt(sumSquares / (2.0 * kFftSize)));
    frame.peakDb = amplitudeToDb(peak);
    frame.rmsDb = amplitudeToDb(rms);
    frame.crestDb = frame.peakDb - frame.rmsDb;

    const auto denom = std::sqrt(std::max(1.0e-20, sumL2 * sumR2));
    frame.stereoCorrelation = denom > 0.0
        ? juce::jlimit(-1.0f, 1.0f, static_cast<float>(sumLR / denom))
        : 1.0f;

    const auto midRms = std::sqrt(sumMid2 / kFftSize);
    const auto sideRms = std::sqrt(sumSide2 / kFftSize);
    frame.stereoWidth = juce::jlimit(0.0f, 4.0f,
                                     static_cast<float>(sideRms / std::max(midRms, 1.0e-12)));

    const int numBins = kFftSize / 2 + 1;
    const auto normalization = static_cast<float>(kFftSize) * 0.5f;

    double weightedFrequency = 0.0;
    double totalMagnitude = 0.0;
    double totalPower = 0.0;
    double arithmeticMagnitude = 0.0;
    double logMagnitude = 0.0;
    int flatnessBins = 0;

    const int firstBin = std::max(1, static_cast<int>(std::ceil(kMinFrequencyHz * kFftSize / currentSampleRate)));
    const int lastBin = std::min(numBins - 1,
                                 static_cast<int>(std::floor(std::min(kMaxFrequencyHz,
                                                                      static_cast<float>(currentSampleRate * 0.5))
                                                             * kFftSize / currentSampleRate)));

    for (int k = firstBin; k <= lastBin; ++k)
    {
        const auto magnitude = std::max(fftData[static_cast<std::size_t>(k)] / normalization, 1.0e-12f);
        const auto frequency = static_cast<double>(k) * currentSampleRate / kFftSize;
        const auto power = static_cast<double>(magnitude) * magnitude;

        weightedFrequency += frequency * magnitude;
        totalMagnitude += magnitude;
        totalPower += power;
        arithmeticMagnitude += magnitude;
        logMagnitude += std::log(static_cast<double>(magnitude));
        ++flatnessBins;
    }

    frame.spectralCentroidHz = totalMagnitude > 0.0
        ? static_cast<float>(weightedFrequency / totalMagnitude)
        : 0.0f;

    const auto targetPower = totalPower * kRolloffFraction;
    double runningPower = 0.0;
    frame.spectralRolloffHz = 0.0f;
    for (int k = firstBin; k <= lastBin; ++k)
    {
        const auto magnitude = fftData[static_cast<std::size_t>(k)] / normalization;
        runningPower += static_cast<double>(magnitude) * magnitude;
        if (runningPower >= targetPower)
        {
            frame.spectralRolloffHz = static_cast<float>(static_cast<double>(k) * currentSampleRate / kFftSize);
            break;
        }
    }

    if (flatnessBins > 0 && arithmeticMagnitude > 0.0)
    {
        const auto geometric = std::exp(logMagnitude / flatnessBins);
        const auto arithmetic = arithmeticMagnitude / flatnessBins;
        frame.spectralFlatness = juce::jlimit(0.0f, 1.0f,
                                              static_cast<float>(geometric / arithmetic));
    }

    for (int band = 0; band < kNumBands; ++band)
    {
        const auto frequency = std::min(bandCenterHz(band),
                                        static_cast<float>(currentSampleRate * 0.5));
        const auto magnitude = interpolateMagnitudeAtFrequency(fftData.data(),
                                                               numBins,
                                                               currentSampleRate,
                                                               frequency) / normalization;
        frame.bandsDb[static_cast<std::size_t>(band)] = amplitudeToDb(magnitude);
    }

    {
        const std::scoped_lock lock(latestMutex);
        latestFrame = frame;
        hasLatestFrame = true;
    }

    const auto nowMs = juce::Time::getMillisecondCounterHiRes();
    if (nowMs - lastOscSendMs >= kOscIntervalMs)
    {
        refreshOscConnectionIfNeeded();
        if (oscConnected)
            sendFrame(frame);
        lastOscSendMs = nowMs;
    }
}

void AnalysisWorker::refreshOscConnectionIfNeeded()
{
    if (!configDirty.exchange(false, std::memory_order_acq_rel))
        return;

    OscConfig newConfig;
    {
        const std::scoped_lock lock(configMutex);
        newConfig = pendingConfig;
    }

    oscSender.disconnect();
    oscConnected = oscSender.connect(newConfig.host, newConfig.port);
    activeConfig = std::move(newConfig);
}

void AnalysisWorker::sendFrame(const AnalysisFrame& frame)
{
    juce::OSCMessage message("/aianalyzer/frame");
    message.addString(activeConfig.instanceId);
    message.addFloat32(static_cast<float>(frame.sampleRate));
    message.addFloat32(static_cast<float>(frame.timestampSeconds));
    message.addFloat32(frame.peakDb);
    message.addFloat32(frame.rmsDb);
    message.addFloat32(frame.crestDb);
    message.addFloat32(frame.spectralCentroidHz);
    message.addFloat32(frame.spectralRolloffHz);
    message.addFloat32(frame.spectralFlatness);
    message.addFloat32(frame.stereoCorrelation);
    message.addFloat32(frame.stereoWidth);

    for (const auto bandDb : frame.bandsDb)
        message.addFloat32(bandDb);

    oscSender.send(message);
}

void AnalysisWorker::run()
{
    resetAnalysisState();

    while (!threadShouldExit())
    {
        if (resetRequested.exchange(false, std::memory_order_acq_rel))
            resetAnalysisState();

        if (fifo.available() < static_cast<std::size_t>(kHopSize))
        {
            wait(2);
            continue;
        }

        if (!fifo.pop(hopLeft.data(), hopRight.data(), kHopSize))
            continue;

        if (filledSamples < kFftSize)
        {
            const auto toCopy = std::min(kHopSize, kFftSize - filledSamples);
            std::copy_n(hopLeft.begin(), toCopy, windowLeft.begin() + filledSamples);
            std::copy_n(hopRight.begin(), toCopy, windowRight.begin() + filledSamples);
            filledSamples += toCopy;

            if (filledSamples < kFftSize)
                continue;
        }
        else
        {
            std::move(windowLeft.begin() + kHopSize, windowLeft.end(), windowLeft.begin());
            std::move(windowRight.begin() + kHopSize, windowRight.end(), windowRight.begin());
            std::copy(hopLeft.begin(), hopLeft.end(), windowLeft.end() - kHopSize);
            std::copy(hopRight.begin(), hopRight.end(), windowRight.end() - kHopSize);
        }

        processWindow();
    }
}
} // namespace aianalyzer
