#include "AnalysisWorker.h"

#include <algorithm>
#include <cmath>

namespace aianalyzer
{
namespace
{
constexpr float kFloorDb = -120.0f;
constexpr float kMinFrequencyHz = 20.0f;
constexpr float kMaxFrequencyHz = 20000.0f;
constexpr float kRolloffFraction = 0.85f;
constexpr double kOscIntervalMs = 100.0; // 10 Hz network update rate
constexpr float kTemporalLowBandMinHz = 40.0f;
constexpr float kTemporalLowBandMaxHz = 160.0f;
constexpr float kStereoLowBandMaxHz = 120.0f;

// Treat material below -50 dBFS as absent, but use hysteresis and a short hold
// to avoid chattering when a tail hovers around the threshold.
constexpr float kSignalCloseDb = -50.0f;
constexpr float kSignalOpenDb = -48.0f;
constexpr double kSignalHoldSeconds = 0.4;
constexpr double kShortTermInvalidSilenceSeconds = 3.0;

float bandCenterHz(int index)
{
    const auto t = (static_cast<float>(index) + 0.5f) / static_cast<float>(kNumBands);
    return kMinFrequencyHz * std::pow(kMaxFrequencyHz / kMinFrequencyHz, t);
}

int stereoBandForFrequency(float frequencyHz)
{
    for (int band = 0; band < kNumStereoCorrelationBands; ++band)
    {
        const auto lo = kStereoCorrelationBandEdgesHz[static_cast<std::size_t>(band)];
        const auto hi = kStereoCorrelationBandEdgesHz[static_cast<std::size_t>(band + 1)];
        if (frequencyHz >= lo && (frequencyHz < hi || band == kNumStereoCorrelationBands - 1))
            return band;
    }
    return -1;
}

float amplitudeRatioToDb(double numerator, double denominator) noexcept
{
    if (numerator <= 1.0e-20 && denominator <= 1.0e-20)
        return 0.0f;

    const auto ratio = std::max(numerator, 1.0e-20) / std::max(denominator, 1.0e-20);
    return juce::jlimit(-120.0f, 120.0f,
                        static_cast<float>(20.0 * std::log10(ratio)));
}

float powerRatioToDb(double numeratorPower, double denominatorPower) noexcept
{
    if (numeratorPower <= 1.0e-30 && denominatorPower <= 1.0e-30)
        return 0.0f;

    const auto ratio = std::max(numeratorPower, 1.0e-30) /
                       std::max(denominatorPower, 1.0e-30);
    return juce::jlimit(-120.0f, 120.0f,
                        static_cast<float>(10.0 * std::log10(ratio)));
}
} // namespace

AnalysisWorker::AnalysisWorker()
    : juce::Thread("AI Audio Analyzer Analysis"),
      runtimeUuid(juce::Uuid().toString())
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

    if (loudnessState != nullptr)
        ebur128_destroy(&loudnessState);

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
    notify();
}

bool AnalysisWorker::getLatestFrame(AnalysisFrame& destination) const
{
    const std::scoped_lock lock(latestMutex);
    if (!hasLatestFrame)
        return false;

    destination = latestFrame;
    return true;
}

void AnalysisWorker::resetLoudnessState()
{
    if (loudnessState != nullptr)
        ebur128_destroy(&loudnessState);

    latestLufsShortTerm = kFloorDb;
    latestLufsIntegrated = kFloorDb;
    latestTruePeakDbtp = kFloorDb;
    maxTruePeakDbtp = kFloorDb;

    const auto currentSampleRate = static_cast<unsigned long>(
        std::max(1.0, std::round(sampleRate.load(std::memory_order_acquire))));

    const int mode = EBUR128_MODE_S
                   | EBUR128_MODE_I
                   | EBUR128_MODE_TRUE_PEAK
                   | EBUR128_MODE_HISTOGRAM;

    loudnessState = ebur128_init(2, currentSampleRate, mode);
}

void AnalysisWorker::resetTemporalAccumulator() noexcept
{
    temporalAccumulatedSeconds = 0.0;
    temporalSpectralFluxSum = 0.0;
    temporalSpectralFluxCount = 0;
    temporalSpectralFluxPeak = 0.0f;
    temporalRmsRisePeakDb = 0.0f;
    temporalLowBandPowerSum = 0.0;
    temporalLowBandPowerCount = 0;
}

void AnalysisWorker::resetAnalysisState()
{
    std::fill(windowLeft.begin(), windowLeft.end(), 0.0f);
    std::fill(windowRight.begin(), windowRight.end(), 0.0f);
    std::fill(fftLeftData.begin(), fftLeftData.end(), 0.0f);
    std::fill(fftRightData.begin(), fftRightData.end(), 0.0f);
    std::fill(midMagnitudes.begin(), midMagnitudes.end(), 0.0f);
    std::fill(sideMagnitudes.begin(), sideMagnitudes.end(), 0.0f);
    std::fill(previousMidMagnitudes.begin(), previousMidMagnitudes.end(), 0.0f);
    filledSamples = 0;

    signalPresent = false;
    detectorPeakDb = kFloorDb;
    silenceSeconds = 0.0;

    hasPreviousTemporalFrame = false;
    previousWindowRmsDb = kFloorDb;
    resetTemporalAccumulator();
    resetLoudnessState();
}

float AnalysisWorker::amplitudeToDb(float value) noexcept
{
    return juce::Decibels::gainToDecibels(std::max(value, 1.0e-9f), kFloorDb);
}

float AnalysisWorker::sanitizeLoudness(double value) noexcept
{
    if (!std::isfinite(value))
        return kFloorDb;
    return juce::jlimit(kFloorDb, 24.0f, static_cast<float>(value));
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
    return magnitudes[static_cast<std::size_t>(lower)]
         + fraction * (magnitudes[static_cast<std::size_t>(upper)]
                     - magnitudes[static_cast<std::size_t>(lower)]);
}

void AnalysisWorker::updateSignalState()
{
    float peak = 0.0f;
    for (int i = 0; i < kHopSize; ++i)
    {
        peak = std::max(peak,
                        std::max(std::abs(hopLeft[static_cast<std::size_t>(i)]),
                                 std::abs(hopRight[static_cast<std::size_t>(i)])));
    }

    detectorPeakDb = amplitudeToDb(peak);

    const auto currentSampleRate = std::max(1.0, sampleRate.load(std::memory_order_acquire));
    const auto hopSeconds = static_cast<double>(kHopSize) / currentSampleRate;

    if (signalPresent)
    {
        if (detectorPeakDb >= kSignalCloseDb)
        {
            silenceSeconds = 0.0;
        }
        else
        {
            silenceSeconds += hopSeconds;
            if (silenceSeconds >= kSignalHoldSeconds)
                signalPresent = false;
        }
    }
    else
    {
        if (detectorPeakDb > kSignalOpenDb)
        {
            signalPresent = true;
            silenceSeconds = 0.0;
        }
        else
        {
            silenceSeconds += hopSeconds;
        }
    }
}

void AnalysisWorker::processLoudnessHop()
{
    if (loudnessState == nullptr)
        return;

    for (int i = 0; i < kHopSize; ++i)
    {
        interleavedHop[static_cast<std::size_t>(i * 2)] = hopLeft[static_cast<std::size_t>(i)];
        interleavedHop[static_cast<std::size_t>(i * 2 + 1)] = hopRight[static_cast<std::size_t>(i)];
    }

    if (ebur128_add_frames_float(loudnessState, interleavedHop.data(), kHopSize) != EBUR128_SUCCESS)
        return;

    double value = 0.0;
    if (ebur128_loudness_shortterm(loudnessState, &value) == EBUR128_SUCCESS)
        latestLufsShortTerm = sanitizeLoudness(value);

    if (ebur128_loudness_global(loudnessState, &value) == EBUR128_SUCCESS)
        latestLufsIntegrated = sanitizeLoudness(value);

    double leftPeak = 0.0;
    double rightPeak = 0.0;
    if (ebur128_prev_true_peak(loudnessState, 0, &leftPeak) == EBUR128_SUCCESS
        && ebur128_prev_true_peak(loudnessState, 1, &rightPeak) == EBUR128_SUCCESS)
    {
        latestTruePeakDbtp = amplitudeToDb(static_cast<float>(std::max(leftPeak, rightPeak)));
    }

    double leftMax = 0.0;
    double rightMax = 0.0;
    if (ebur128_true_peak(loudnessState, 0, &leftMax) == EBUR128_SUCCESS
        && ebur128_true_peak(loudnessState, 1, &rightMax) == EBUR128_SUCCESS)
    {
        maxTruePeakDbtp = amplitudeToDb(static_cast<float>(std::max(leftMax, rightMax)));
    }
}

void AnalysisWorker::processWindow()
{
    const auto currentSampleRate = sampleRate.load(std::memory_order_acquire);
    const auto hopSeconds = static_cast<double>(kHopSize) / std::max(1.0, currentSampleRate);

    AnalysisFrame frame;
    frame.sampleRate = currentSampleRate;
    frame.timestampSeconds = juce::Time::getMillisecondCounterHiRes() / 1000.0;
    frame.signalPresent = signalPresent;
    frame.detectorPeakDb = detectorPeakDb;
    frame.silenceSeconds = static_cast<float>(silenceSeconds);

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

        fftLeftData[static_cast<std::size_t>(i)] = l;
        fftRightData[static_cast<std::size_t>(i)] = r;
    }

    std::fill(fftLeftData.begin() + kFftSize, fftLeftData.end(), 0.0f);
    std::fill(fftRightData.begin() + kFftSize, fftRightData.end(), 0.0f);
    windowFunction.multiplyWithWindowingTable(fftLeftData.data(), kFftSize);
    windowFunction.multiplyWithWindowingTable(fftRightData.data(), kFftSize);
    fft.performRealOnlyForwardTransform(fftLeftData.data());
    fft.performRealOnlyForwardTransform(fftRightData.data());

    const auto rms = static_cast<float>(std::sqrt(sumSquares / (2.0 * kFftSize)));
    frame.peakDb = amplitudeToDb(peak);
    frame.rmsDb = amplitudeToDb(rms);
    frame.crestDb = frame.peakDb - frame.rmsDb;
    frame.lufsShortTerm = (!signalPresent && silenceSeconds >= kShortTermInvalidSilenceSeconds)
        ? kFloorDb
        : latestLufsShortTerm;
    frame.lufsIntegrated = latestLufsIntegrated;
    frame.truePeakDbtp = latestTruePeakDbtp;
    frame.maxTruePeakDbtp = maxTruePeakDbtp;

    const auto denom = std::sqrt(std::max(1.0e-20, sumL2 * sumR2));
    frame.stereoCorrelation = denom > 0.0
        ? juce::jlimit(-1.0f, 1.0f, static_cast<float>(sumLR / denom))
        : 1.0f;

    const auto midRms = std::sqrt(sumMid2 / kFftSize);
    const auto sideRms = std::sqrt(sumSide2 / kFftSize);
    frame.stereoWidth = juce::jlimit(0.0f, 4.0f,
                                     static_cast<float>(sideRms / std::max(midRms, 1.0e-12)));
    frame.midRmsDb = amplitudeToDb(static_cast<float>(midRms));
    frame.sideRmsDb = amplitudeToDb(static_cast<float>(sideRms));
    frame.sideToMidDb = amplitudeRatioToDb(sideRms, midRms);

    const int numBins = kFftSize / 2 + 1;
    const auto normalization = static_cast<float>(kFftSize) * 0.5f;

    double weightedFrequency = 0.0;
    double totalMagnitude = 0.0;
    double totalPower = 0.0;
    double arithmeticMagnitude = 0.0;
    double logMagnitude = 0.0;
    int flatnessBins = 0;

    std::array<double, kNumStereoCorrelationBands> bandCross {};
    std::array<double, kNumStereoCorrelationBands> bandLeftPower {};
    std::array<double, kNumStereoCorrelationBands> bandRightPower {};
    std::array<double, kNumStereoCorrelationBands> bandMidPower {};
    std::array<double, kNumStereoCorrelationBands> bandSidePower {};

    double negativeCrossWeight = 0.0;
    double totalCrossWeight = 0.0;
    double lowBandCross = 0.0;
    double lowBandLeftPower = 0.0;
    double lowBandRightPower = 0.0;
    double lowBandMidPower = 0.0;
    double lowBandSidePower = 0.0;

    const int firstBin = std::max(1, static_cast<int>(std::ceil(kMinFrequencyHz * kFftSize / currentSampleRate)));
    const int lastBin = std::min(numBins - 1,
                                 static_cast<int>(std::floor(std::min(kMaxFrequencyHz,
                                                                      static_cast<float>(currentSampleRate * 0.5))
                                                             * kFftSize / currentSampleRate)));

    for (int k = 0; k < numBins; ++k)
    {
        const auto index = static_cast<std::size_t>(k * 2);
        const auto lRe = fftLeftData[index];
        const auto lIm = fftLeftData[index + 1];
        const auto rRe = fftRightData[index];
        const auto rIm = fftRightData[index + 1];
        const auto midRe = 0.5f * (lRe + rRe);
        const auto midIm = 0.5f * (lIm + rIm);
        const auto sideRe = 0.5f * (lRe - rRe);
        const auto sideIm = 0.5f * (lIm - rIm);
        midMagnitudes[static_cast<std::size_t>(k)] =
            std::sqrt(midRe * midRe + midIm * midIm) / normalization;
        sideMagnitudes[static_cast<std::size_t>(k)] =
            std::sqrt(sideRe * sideRe + sideIm * sideIm) / normalization;
    }

    const bool hadPreviousTemporalFrame = hasPreviousTemporalFrame;
    double currentMagnitudeSum = 0.0;
    double previousMagnitudeSum = 0.0;
    double lowBandPower = 0.0;
    int lowBandBins = 0;

    for (int k = firstBin; k <= lastBin; ++k)
    {
        const auto magnitude = std::max(0.0f, midMagnitudes[static_cast<std::size_t>(k)]);
        currentMagnitudeSum += magnitude;
        if (hadPreviousTemporalFrame)
            previousMagnitudeSum += std::max(0.0f, previousMidMagnitudes[static_cast<std::size_t>(k)]);

        const auto frequency = static_cast<float>(static_cast<double>(k) * currentSampleRate / kFftSize);
        if (frequency >= kTemporalLowBandMinHz && frequency < kTemporalLowBandMaxHz)
        {
            lowBandPower += static_cast<double>(magnitude) * magnitude;
            ++lowBandBins;
        }
    }

    float spectralFlux = 0.0f;
    if (hadPreviousTemporalFrame && currentMagnitudeSum > 1.0e-12 && previousMagnitudeSum > 1.0e-12)
    {
        double positiveDifference = 0.0;
        for (int k = firstBin; k <= lastBin; ++k)
        {
            const auto currentNormalized =
                static_cast<double>(midMagnitudes[static_cast<std::size_t>(k)]) / currentMagnitudeSum;
            const auto previousNormalized =
                static_cast<double>(previousMidMagnitudes[static_cast<std::size_t>(k)]) / previousMagnitudeSum;
            positiveDifference += std::max(0.0, currentNormalized - previousNormalized);
        }
        spectralFlux = juce::jlimit(0.0f, 1.0f, static_cast<float>(positiveDifference));
    }

    const auto rmsRiseDb = hadPreviousTemporalFrame
        ? std::max(0.0f, frame.rmsDb - previousWindowRmsDb)
        : 0.0f;
    const auto lowBandEnergyDb = lowBandBins > 0
        ? amplitudeToDb(static_cast<float>(std::sqrt(lowBandPower / lowBandBins)))
        : kFloorDb;

    frame.temporalWindowSeconds = static_cast<float>(hopSeconds);
    frame.spectralFluxMean = spectralFlux;
    frame.spectralFluxPeak = spectralFlux;
    frame.rmsRisePeakDb = rmsRiseDb;
    frame.lowBandEnergyDb = lowBandEnergyDb;

    std::copy_n(midMagnitudes.begin(), numBins, previousMidMagnitudes.begin());
    hasPreviousTemporalFrame = true;
    previousWindowRmsDb = frame.rmsDb;

    if (signalPresent)
    {
        temporalAccumulatedSeconds += hopSeconds;
        temporalSpectralFluxSum += spectralFlux;
        ++temporalSpectralFluxCount;
        temporalSpectralFluxPeak = std::max(temporalSpectralFluxPeak, spectralFlux);
        temporalRmsRisePeakDb = std::max(temporalRmsRisePeakDb, rmsRiseDb);
        if (lowBandBins > 0)
        {
            temporalLowBandPowerSum += lowBandPower / lowBandBins;
            ++temporalLowBandPowerCount;
        }
    }
    else
    {
        resetTemporalAccumulator();
    }

    for (int k = firstBin; k <= lastBin; ++k)
    {
        const auto magnitude = std::max(midMagnitudes[static_cast<std::size_t>(k)], 1.0e-12f);
        const auto frequency = static_cast<double>(k) * currentSampleRate / kFftSize;
        const auto power = static_cast<double>(magnitude) * magnitude;
        const auto index = static_cast<std::size_t>(k * 2);
        const auto lRe = static_cast<double>(fftLeftData[index]);
        const auto lIm = static_cast<double>(fftLeftData[index + 1]);
        const auto rRe = static_cast<double>(fftRightData[index]);
        const auto rIm = static_cast<double>(fftRightData[index + 1]);
        const auto midRe = 0.5 * (lRe + rRe);
        const auto midIm = 0.5 * (lIm + rIm);
        const auto sideRe = 0.5 * (lRe - rRe);
        const auto sideIm = 0.5 * (lIm - rIm);
        const auto leftPower = lRe * lRe + lIm * lIm;
        const auto rightPower = rRe * rRe + rIm * rIm;
        const auto cross = lRe * rRe + lIm * rIm;
        const auto midPower = midRe * midRe + midIm * midIm;
        const auto sidePower = sideRe * sideRe + sideIm * sideIm;
        const auto bilateralWeight = std::sqrt(std::max(0.0, leftPower * rightPower));

        weightedFrequency += frequency * magnitude;
        totalMagnitude += magnitude;
        totalPower += power;
        arithmeticMagnitude += magnitude;
        logMagnitude += std::log(static_cast<double>(magnitude));
        ++flatnessBins;

        totalCrossWeight += bilateralWeight;
        if (cross < 0.0)
            negativeCrossWeight += bilateralWeight;

        if (frequency >= kMinFrequencyHz && frequency < kStereoLowBandMaxHz)
        {
            lowBandCross += cross;
            lowBandLeftPower += leftPower;
            lowBandRightPower += rightPower;
            lowBandMidPower += midPower;
            lowBandSidePower += sidePower;
        }

        const auto band = stereoBandForFrequency(static_cast<float>(frequency));
        if (band >= 0)
        {
            const auto b = static_cast<std::size_t>(band);
            bandCross[b] += cross;
            bandLeftPower[b] += leftPower;
            bandRightPower[b] += rightPower;
            bandMidPower[b] += midPower;
            bandSidePower[b] += sidePower;
        }
    }

    frame.negativeCrossEnergyRatio = totalCrossWeight > 1.0e-18
        ? juce::jlimit(0.0f, 1.0f,
                       static_cast<float>(negativeCrossWeight / totalCrossWeight))
        : 0.0f;

    const auto lowBandDenom = std::sqrt(std::max(0.0, lowBandLeftPower * lowBandRightPower));
    frame.lowBandCorrelation = lowBandDenom > 1.0e-18
        ? juce::jlimit(-1.0f, 1.0f,
                       static_cast<float>(lowBandCross / lowBandDenom))
        : 0.0f;
    frame.lowBandSideToMidDb = powerRatioToDb(lowBandSidePower, lowBandMidPower);

    frame.spectralCentroidHz = totalMagnitude > 0.0
        ? static_cast<float>(weightedFrequency / totalMagnitude)
        : 0.0f;

    const auto targetPower = totalPower * kRolloffFraction;
    double runningPower = 0.0;
    frame.spectralRolloffHz = 0.0f;
    for (int k = firstBin; k <= lastBin; ++k)
    {
        const auto magnitude = midMagnitudes[static_cast<std::size_t>(k)];
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
        const auto midMagnitude = interpolateMagnitudeAtFrequency(midMagnitudes.data(),
                                                                  numBins,
                                                                  currentSampleRate,
                                                                  frequency);
        const auto sideMagnitude = interpolateMagnitudeAtFrequency(sideMagnitudes.data(),
                                                                   numBins,
                                                                   currentSampleRate,
                                                                   frequency);
        frame.bandsDb[static_cast<std::size_t>(band)] = amplitudeToDb(midMagnitude);
        frame.sideBandsDb[static_cast<std::size_t>(band)] = amplitudeToDb(sideMagnitude);
    }

    for (int band = 0; band < kNumStereoCorrelationBands; ++band)
    {
        const auto b = static_cast<std::size_t>(band);
        const auto bandDenom = std::sqrt(std::max(0.0, bandLeftPower[b] * bandRightPower[b]));
        frame.bandStereoCorrelation[b] = bandDenom > 1.0e-18
            ? juce::jlimit(-1.0f, 1.0f, static_cast<float>(bandCross[b] / bandDenom))
            : 0.0f;
        frame.bandSideToMidDb[b] = powerRatioToDb(bandSidePower[b], bandMidPower[b]);
    }

    // Once the signal gate has closed, spectral/stereo/temporal values are
    // explicitly treated as invalid machine features instead of leaving random
    // near-noise values in the stream. Peak/RMS, LUFS-I and session max TP are
    // retained because they still describe detector/session state.
    if (!signalPresent)
    {
        frame.spectralCentroidHz = 0.0f;
        frame.spectralRolloffHz = 0.0f;
        frame.spectralFlatness = 0.0f;
        frame.stereoCorrelation = 0.0f;
        frame.stereoWidth = 0.0f;
        frame.temporalWindowSeconds = 0.0f;
        frame.spectralFluxMean = 0.0f;
        frame.spectralFluxPeak = 0.0f;
        frame.rmsRisePeakDb = 0.0f;
        frame.lowBandEnergyDb = kFloorDb;
        frame.midRmsDb = kFloorDb;
        frame.sideRmsDb = kFloorDb;
        frame.sideToMidDb = 0.0f;
        frame.negativeCrossEnergyRatio = 0.0f;
        frame.lowBandCorrelation = 0.0f;
        frame.lowBandSideToMidDb = 0.0f;
        frame.bandsDb.fill(kFloorDb);
        frame.bandStereoCorrelation.fill(0.0f);
        frame.sideBandsDb.fill(kFloorDb);
        frame.bandSideToMidDb.fill(0.0f);
    }

    {
        const std::scoped_lock lock(latestMutex);
        latestFrame = frame;
        hasLatestFrame = true;
    }

    const auto nowMs = juce::Time::getMillisecondCounterHiRes();
    if (nowMs - lastOscSendMs >= kOscIntervalMs)
    {
        AnalysisFrame outgoing = frame;
        if (signalPresent && temporalSpectralFluxCount > 0)
        {
            outgoing.temporalWindowSeconds = static_cast<float>(temporalAccumulatedSeconds);
            outgoing.spectralFluxMean = static_cast<float>(
                temporalSpectralFluxSum / temporalSpectralFluxCount);
            outgoing.spectralFluxPeak = temporalSpectralFluxPeak;
            outgoing.rmsRisePeakDb = temporalRmsRisePeakDb;
            outgoing.lowBandEnergyDb = temporalLowBandPowerCount > 0
                ? amplitudeToDb(static_cast<float>(std::sqrt(
                    temporalLowBandPowerSum / temporalLowBandPowerCount)))
                : kFloorDb;
        }
        else
        {
            outgoing.temporalWindowSeconds = 0.0f;
            outgoing.spectralFluxMean = 0.0f;
            outgoing.spectralFluxPeak = 0.0f;
            outgoing.rmsRisePeakDb = 0.0f;
            outgoing.lowBandEnergyDb = kFloorDb;
        }

        refreshOscConnectionIfNeeded();
        if (oscConnected)
            sendFrame(outgoing);

        resetTemporalAccumulator();
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

    // Preserve the V0.1 prefix so older bridges can still read the first
    // 11 scalar fields plus 32 spectrum bands. Historical bandsDb is the Mid
    // spectrum; V0.8 appends the Side spectrum separately.
    for (const auto bandDb : frame.bandsDb)
        message.addFloat32(bandDb);

    // V0.2 extras.
    message.addFloat32(frame.lufsShortTerm);
    message.addFloat32(frame.lufsIntegrated);
    message.addFloat32(frame.truePeakDbtp);
    message.addFloat32(frame.maxTruePeakDbtp);

    for (const auto correlation : frame.bandStereoCorrelation)
        message.addFloat32(correlation);

    // V0.3 extras. Keep these appended so V0.1/V0.2 bridges can ignore them.
    message.addInt32(frame.signalPresent ? 1 : 0);
    message.addFloat32(frame.detectorPeakDb);
    message.addFloat32(frame.silenceSeconds);
    message.addString(runtimeUuid);

    // V0.6 temporal extras. The schema remains append-only so older bridges can
    // safely ignore these fields. Flux is normalized spectral redistribution;
    // RMS rise is the largest positive window-to-window rise during this OSC
    // aggregate; low-band energy is an FFT-derived 40-160 Hz feature.
    message.addFloat32(frame.temporalWindowSeconds);
    message.addFloat32(frame.spectralFluxMean);
    message.addFloat32(frame.spectralFluxPeak);
    message.addFloat32(frame.rmsRisePeakDb);
    message.addFloat32(frame.lowBandEnergyDb);
    message.addString("0.6");

    // V0.8 Mid/Side + stereo extras. Indices 0..64 are untouched. These fields
    // separate Side energy and negative cross-spectrum evidence from ordinary
    // correlation so downstream models can distinguish decorrelation from
    // strong phase opposition without relying on a single width number.
    message.addFloat32(frame.midRmsDb);
    message.addFloat32(frame.sideRmsDb);
    message.addFloat32(frame.sideToMidDb);
    message.addFloat32(frame.negativeCrossEnergyRatio);
    message.addFloat32(frame.lowBandCorrelation);
    message.addFloat32(frame.lowBandSideToMidDb);
    for (const auto sideBandDb : frame.sideBandsDb)
        message.addFloat32(sideBandDb);
    for (const auto sideToMidDb : frame.bandSideToMidDb)
        message.addFloat32(sideToMidDb);
    message.addString("0.8");

    oscSender.send(message);
}

void AnalysisWorker::sendIdentify()
{
    juce::OSCMessage message("/aianalyzer/identify");
    message.addString(runtimeUuid);
    message.addString(activeConfig.instanceId);
    message.addFloat32(static_cast<float>(juce::Time::getMillisecondCounterHiRes() / 1000.0));
    message.addString("0.4");
    oscSender.send(message);
}

void AnalysisWorker::run()
{
    resetAnalysisState();
    resetRequested.store(false, std::memory_order_release);

    while (!threadShouldExit())
    {
        if (resetRequested.exchange(false, std::memory_order_acq_rel))
            resetAnalysisState();

        // Identify must work even while the transport is stopped and no audio
        // is reaching the plugin. Keep the request pending until OSC is ready.
        refreshOscConnectionIfNeeded();
        if (identifyRequested.load(std::memory_order_acquire) && oscConnected)
        {
            if (identifyRequested.exchange(false, std::memory_order_acq_rel))
                sendIdentify();
        }

        if (fifo.available() < static_cast<std::size_t>(kHopSize))
        {
            wait(2);
            continue;
        }

        if (!fifo.pop(hopLeft.data(), hopRight.data(), kHopSize))
            continue;

        updateSignalState();
        processLoudnessHop();

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
