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
constexpr double kReducedAnalysisIntervalMs = 100.0;
constexpr double kSemanticAnalysisIntervalMs = 200.0;
constexpr double kPerformanceWindowMs = 1000.0;
constexpr float kTemporalLowBandMinHz = 40.0f;
constexpr float kTemporalLowBandMaxHz = 160.0f;
constexpr float kStereoLowBandMaxHz = 120.0f;
constexpr float kChromaMinFrequencyHz = 80.0f;
constexpr float kChromaMaxFrequencyHz = 5000.0f;
constexpr float kHarmonicFundamentalMinHz = 55.0f;
constexpr float kHarmonicFundamentalMaxHz = 1000.0f;
constexpr int kMaxSemanticHarmonics = 8;
constexpr int kHarmonicToleranceBins = 1;

// Treat material below -50 dBFS as absent, but use hysteresis and a short hold
// to avoid chattering when a tail hovers around the threshold.
constexpr float kSignalCloseDb = -50.0f;
constexpr float kSignalOpenDb = -48.0f;
constexpr double kSignalHoldSeconds = 0.4;
constexpr double kShortTermInvalidSilenceSeconds = 3.0;

AnalysisProfile profileFromInt(int value) noexcept
{
    return static_cast<AnalysisProfile>(juce::jlimit(0, 3, value));
}

bool hasFeature(AnalysisProfile profile, AnalysisFeature feature) noexcept
{
    return (analysisFeatureMask(profile) & static_cast<std::uint32_t>(feature)) != 0u;
}

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

int pitchClassForFrequency(double frequencyHz) noexcept
{
    if (!(frequencyHz > 0.0) || !std::isfinite(frequencyHz))
        return 0;

    const auto midi = 69.0 + 12.0 * std::log2(frequencyHz / 440.0);
    auto pitchClass = static_cast<int>(std::lround(midi)) % kNumChromaBins;
    if (pitchClass < 0)
        pitchClass += kNumChromaBins;
    return pitchClass;
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

void AnalysisWorker::setAnalysisProfile(AnalysisProfile profile) noexcept
{
    requestedProfile.store(juce::jlimit(0, 3, static_cast<int>(profile)), std::memory_order_release);
    notify();
}

AnalysisProfile AnalysisWorker::getAnalysisProfile() const noexcept
{
    return profileFromInt(requestedProfile.load(std::memory_order_acquire));
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
    lastLoudnessMetricsMs = 0.0;

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

void AnalysisWorker::resetSemanticCache() noexcept
{
    cachedChroma.fill(0.0f);
    cachedChromaEnergyRatio = 0.0f;
    cachedSingleF0HarmonicEnergyRatio = 0.0f;
    cachedHarmonicF0CandidateHz = 0.0f;
    lastSemanticAnalysisMs = 0.0;
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

    activeProfile = profileFromInt(requestedProfile.load(std::memory_order_acquire));
    hasPreviousTemporalFrame = false;
    previousWindowRmsDb = kFloorDb;
    resetTemporalAccumulator();
    resetSemanticCache();

    if (hasFeature(activeProfile, FeatureLoudness))
    {
        resetLoudnessState();
    }
    else
    {
        if (loudnessState != nullptr)
            ebur128_destroy(&loudnessState);
        latestLufsShortTerm = kFloorDb;
        latestLufsIntegrated = kFloorDb;
        latestTruePeakDbtp = kFloorDb;
        maxTruePeakDbtp = kFloorDb;
        lastLoudnessMetricsMs = 0.0;
    }

    lastReducedAnalysisMs = 0.0;
    performanceWindowStartMs = juce::Time::getMillisecondCounterHiRes();
    performanceBusyMs = 0.0;
    fftRunsInWindow = 0;
    semanticRunsInWindow = 0;
    workerLoadRatio = 0.0f;
    fftRunsPerSecond = 0.0f;
    semanticRunsPerSecond = 0.0f;
}

void AnalysisWorker::applyProfileChangeIfNeeded()
{
    const auto next = profileFromInt(requestedProfile.load(std::memory_order_acquire));
    if (next == activeProfile)
        return;

    const auto oldMask = analysisFeatureMask(activeProfile);
    const auto newMask = analysisFeatureMask(next);

    const bool oldLoudness = (oldMask & FeatureLoudness) != 0u;
    const bool newLoudness = (newMask & FeatureLoudness) != 0u;
    if (oldLoudness != newLoudness)
    {
        if (newLoudness)
            resetLoudnessState();
        else if (loudnessState != nullptr)
            ebur128_destroy(&loudnessState);

        if (!newLoudness)
            lastLoudnessMetricsMs = 0.0;
    }

    const bool oldTemporal = (oldMask & FeatureTemporal) != 0u;
    const bool newTemporal = (newMask & FeatureTemporal) != 0u;
    if (oldTemporal != newTemporal)
    {
        resetTemporalAccumulator();
        hasPreviousTemporalFrame = false;
        previousWindowRmsDb = kFloorDb;
        std::fill(previousMidMagnitudes.begin(), previousMidMagnitudes.end(), 0.0f);
    }

    const bool oldSemantic = (oldMask & FeatureSemantic) != 0u;
    const bool newSemantic = (newMask & FeatureSemantic) != 0u;
    if (oldSemantic != newSemantic)
        resetSemanticCache();

    activeProfile = next;
    lastReducedAnalysisMs = 0.0;
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

    // libebur128 performs the true-peak oversampling while frames are added.
    // Read the most recent block every hop so short transients are never missed,
    // and maintain the session maximum locally. This is equivalent to querying
    // ebur128_true_peak() every hop but avoids repeatedly asking for the global
    // accumulator value.
    double leftPeak = 0.0;
    double rightPeak = 0.0;
    if (ebur128_prev_true_peak(loudnessState, 0, &leftPeak) == EBUR128_SUCCESS
        && ebur128_prev_true_peak(loudnessState, 1, &rightPeak) == EBUR128_SUCCESS)
    {
        latestTruePeakDbtp = amplitudeToDb(static_cast<float>(std::max(leftPeak, rightPeak)));
        maxTruePeakDbtp = std::max(maxTruePeakDbtp, latestTruePeakDbtp);
    }

    // Audio still enters libebur128 on every hop, but LUFS-S/I are exposed at
    // network/GUI timescales. Polling those aggregate metrics faster than the
    // 10 Hz OSC cadence only repeats expensive work without adding evidence.
    const auto nowMs = juce::Time::getMillisecondCounterHiRes();
    if (!loudnessMetricsDue(lastLoudnessMetricsMs, nowMs))
        return;

    double value = 0.0;
    if (ebur128_loudness_shortterm(loudnessState, &value) == EBUR128_SUCCESS)
        latestLufsShortTerm = sanitizeLoudness(value);

    if (ebur128_loudness_global(loudnessState, &value) == EBUR128_SUCCESS)
        latestLufsIntegrated = sanitizeLoudness(value);

    lastLoudnessMetricsMs = nowMs;
}

void AnalysisWorker::attachRuntimeMetadata(AnalysisFrame& frame) const noexcept
{
    frame.analysisProfile = static_cast<int>(activeProfile);
    frame.analysisFeatureMask = analysisFeatureMask(activeProfile);
    frame.workerLoadRatio = workerLoadRatio;
    frame.fifoFillRatio = juce::jlimit(
        0.0f,
        1.0f,
        static_cast<float>(fifo.available()) / static_cast<float>(SpscStereoFifo::capacity));
    frame.fftRunsPerSecond = fftRunsPerSecond;
    frame.semanticRunsPerSecond = semanticRunsPerSecond;
}

void AnalysisWorker::updatePerformanceTelemetry(double busyMilliseconds,
                                                double nowMilliseconds) noexcept
{
    if (performanceWindowStartMs <= 0.0)
        performanceWindowStartMs = nowMilliseconds;

    performanceBusyMs += std::max(0.0, busyMilliseconds);
    const auto elapsed = nowMilliseconds - performanceWindowStartMs;
    if (elapsed < kPerformanceWindowMs)
        return;

    workerLoadRatio = juce::jlimit(
        0.0f,
        1.0f,
        static_cast<float>(performanceBusyMs / std::max(1.0, elapsed)));
    fftRunsPerSecond = static_cast<float>(
        static_cast<double>(fftRunsInWindow) * 1000.0 / std::max(1.0, elapsed));
    semanticRunsPerSecond = static_cast<float>(
        static_cast<double>(semanticRunsInWindow) * 1000.0 / std::max(1.0, elapsed));

    performanceWindowStartMs = nowMilliseconds;
    performanceBusyMs = 0.0;
    fftRunsInWindow = 0;
    semanticRunsInWindow = 0;
}

void AnalysisWorker::processCoreWindow()
{
    AnalysisFrame frame;
    frame.sampleRate = sampleRate.load(std::memory_order_acquire);
    frame.timestampSeconds = juce::Time::getMillisecondCounterHiRes() / 1000.0;
    frame.signalPresent = signalPresent;
    frame.detectorPeakDb = detectorPeakDb;
    frame.silenceSeconds = static_cast<float>(silenceSeconds);

    double sumSquares = 0.0;
    float peak = 0.0f;
    for (int i = 0; i < kFftSize; ++i)
    {
        const auto l = windowLeft[static_cast<std::size_t>(i)];
        const auto r = windowRight[static_cast<std::size_t>(i)];
        peak = std::max(peak, std::max(std::abs(l), std::abs(r)));
        sumSquares += static_cast<double>(l) * l + static_cast<double>(r) * r;
    }

    const auto rms = static_cast<float>(std::sqrt(sumSquares / (2.0 * kFftSize)));
    frame.peakDb = amplitudeToDb(peak);
    frame.rmsDb = amplitudeToDb(rms);
    frame.crestDb = frame.peakDb - frame.rmsDb;
    frame.lufsShortTerm = kFloorDb;
    frame.lufsIntegrated = kFloorDb;
    frame.truePeakDbtp = kFloorDb;
    frame.maxTruePeakDbtp = kFloorDb;
    frame.stereoCorrelation = 0.0f;
    frame.stereoWidth = 0.0f;
    frame.midRmsDb = kFloorDb;
    frame.sideRmsDb = kFloorDb;
    frame.sideToMidDb = 0.0f;
    frame.lowBandEnergyDb = kFloorDb;
    frame.lowBandSideToMidDb = 0.0f;
    frame.bandsDb.fill(kFloorDb);
    frame.sideBandsDb.fill(kFloorDb);
    frame.bandStereoCorrelation.fill(0.0f);
    frame.bandSideToMidDb.fill(0.0f);

    publishFrame(frame, false);
}

void AnalysisWorker::publishFrame(AnalysisFrame frame, bool temporalEnabled)
{
    attachRuntimeMetadata(frame);

    {
        const std::scoped_lock lock(latestMutex);
        latestFrame = frame;
        hasLatestFrame = true;
    }

    const auto nowMs = juce::Time::getMillisecondCounterHiRes();
    if (nowMs - lastOscSendMs < kOscIntervalMs)
        return;

    AnalysisFrame outgoing = frame;
    if (temporalEnabled && signalPresent && temporalSpectralFluxCount > 0)
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

    attachRuntimeMetadata(outgoing);
    refreshOscConnectionIfNeeded();
    if (oscConnected)
        sendFrame(outgoing);

    if (temporalEnabled)
        resetTemporalAccumulator();
    lastOscSendMs = nowMs;
}

void AnalysisWorker::processWindow()
{
    const auto currentSampleRate = sampleRate.load(std::memory_order_acquire);
    const auto hopSeconds = static_cast<double>(kHopSize) / std::max(1.0, currentSampleRate);
    const bool loudnessEnabled = hasFeature(activeProfile, FeatureLoudness);
    const bool temporalEnabled = hasFeature(activeProfile, FeatureTemporal);
    const bool semanticEnabled = hasFeature(activeProfile, FeatureSemantic);
    const auto nowMs = juce::Time::getMillisecondCounterHiRes();
    const bool semanticDue = semanticEnabled
        && signalPresent
        && (lastSemanticAnalysisMs <= 0.0
            || nowMs - lastSemanticAnalysisMs >= kSemanticAnalysisIntervalMs);

    AnalysisFrame frame;
    frame.sampleRate = currentSampleRate;
    frame.timestampSeconds = nowMs / 1000.0;
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
    ++fftRunsInWindow;

    const auto rms = static_cast<float>(std::sqrt(sumSquares / (2.0 * kFftSize)));
    frame.peakDb = amplitudeToDb(peak);
    frame.rmsDb = amplitudeToDb(rms);
    frame.crestDb = frame.peakDb - frame.rmsDb;
    frame.lufsShortTerm = loudnessEnabled
        ? ((!signalPresent && silenceSeconds >= kShortTermInvalidSilenceSeconds)
            ? kFloorDb
            : latestLufsShortTerm)
        : kFloorDb;
    frame.lufsIntegrated = loudnessEnabled ? latestLufsIntegrated : kFloorDb;
    frame.truePeakDbtp = loudnessEnabled ? latestTruePeakDbtp : kFloorDb;
    frame.maxTruePeakDbtp = loudnessEnabled ? maxTruePeakDbtp : kFloorDb;

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
    std::array<double, kNumChromaBins> chromaPower {};

    double negativeCrossWeight = 0.0;
    double totalCrossWeight = 0.0;
    double lowBandCross = 0.0;
    double lowBandLeftPower = 0.0;
    double lowBandRightPower = 0.0;
    double lowBandMidPower = 0.0;
    double lowBandSidePower = 0.0;
    double chromaPowerTotal = 0.0;

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

    if (temporalEnabled)
    {
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
    }
    else
    {
        frame.temporalWindowSeconds = 0.0f;
        frame.spectralFluxMean = 0.0f;
        frame.spectralFluxPeak = 0.0f;
        frame.rmsRisePeakDb = 0.0f;
        frame.lowBandEnergyDb = kFloorDb;
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

        if (semanticDue && frequency >= kChromaMinFrequencyHz && frequency <= kChromaMaxFrequencyHz)
        {
            const auto pitchClass = pitchClassForFrequency(frequency);
            chromaPower[static_cast<std::size_t>(pitchClass)] += power;
            chromaPowerTotal += power;
        }

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

    if (semanticDue)
    {
        std::array<float, kNumChromaBins> nextChroma {};
        if (chromaPowerTotal > 1.0e-18)
        {
            for (int pitchClass = 0; pitchClass < kNumChromaBins; ++pitchClass)
            {
                nextChroma[static_cast<std::size_t>(pitchClass)] = juce::jlimit(
                    0.0f,
                    1.0f,
                    static_cast<float>(chromaPower[static_cast<std::size_t>(pitchClass)] / chromaPowerTotal));
            }
        }

        float nextChromaEnergyRatio = totalPower > 1.0e-18
            ? juce::jlimit(0.0f, 1.0f, static_cast<float>(chromaPowerTotal / totalPower))
            : 0.0f;
        float nextHarmonicRatio = 0.0f;
        float nextF0Hz = 0.0f;

        const auto semanticMaxHz = std::min(
            static_cast<double>(kChromaMaxFrequencyHz),
            currentSampleRate * 0.5);
        const int semanticFirstBin = std::max(
            firstBin,
            static_cast<int>(std::ceil(kChromaMinFrequencyHz * kFftSize / currentSampleRate)));
        const int semanticLastBin = std::min(
            lastBin,
            static_cast<int>(std::floor(semanticMaxHz * kFftSize / currentSampleRate)));
        const int firstF0Bin = std::max(
            1,
            static_cast<int>(std::ceil(kHarmonicFundamentalMinHz * kFftSize / currentSampleRate)));
        const int lastF0Bin = std::min(
            numBins - 1,
            static_cast<int>(std::floor(std::min(
                static_cast<double>(kHarmonicFundamentalMaxHz),
                semanticMaxHz * 0.5) * kFftSize / currentSampleRate)));

        double bestHarmonicScore = 0.0;
        int bestF0Bin = 0;
        for (int candidateBin = firstF0Bin; candidateBin <= lastF0Bin; ++candidateBin)
        {
            const auto f0Hz = static_cast<double>(candidateBin) * currentSampleRate / kFftSize;
            double weightedPeakPower = 0.0;
            double totalWeight = 0.0;
            int harmonicCount = 0;

            for (int harmonic = 1; harmonic <= kMaxSemanticHarmonics; ++harmonic)
            {
                const auto targetHz = f0Hz * harmonic;
                if (targetHz > semanticMaxHz)
                    break;
                if (targetHz < kChromaMinFrequencyHz)
                    continue;

                const auto targetBin = static_cast<int>(std::lround(targetHz * kFftSize / currentSampleRate));
                double localPeakPower = 0.0;
                for (int delta = -kHarmonicToleranceBins; delta <= kHarmonicToleranceBins; ++delta)
                {
                    const auto bin = targetBin + delta;
                    if (bin < semanticFirstBin || bin > semanticLastBin)
                        continue;
                    const auto value = static_cast<double>(midMagnitudes[static_cast<std::size_t>(bin)]);
                    localPeakPower = std::max(localPeakPower, value * value);
                }

                const auto weight = 1.0 / static_cast<double>(harmonic);
                weightedPeakPower += localPeakPower * weight;
                totalWeight += weight;
                ++harmonicCount;
            }

            if (harmonicCount < 2 || totalWeight <= 0.0)
                continue;

            const auto score = weightedPeakPower / totalWeight;
            if (score > bestHarmonicScore)
            {
                bestHarmonicScore = score;
                bestF0Bin = candidateBin;
            }
        }

        if (bestF0Bin > 0 && chromaPowerTotal > 1.0e-18)
        {
            const auto f0Hz = static_cast<double>(bestF0Bin) * currentSampleRate / kFftSize;
            double matchedHarmonicPower = 0.0;

            for (int harmonic = 1; harmonic <= kMaxSemanticHarmonics; ++harmonic)
            {
                const auto targetHz = f0Hz * harmonic;
                if (targetHz > semanticMaxHz)
                    break;
                if (targetHz < kChromaMinFrequencyHz)
                    continue;

                const auto targetBin = static_cast<int>(std::lround(targetHz * kFftSize / currentSampleRate));
                for (int delta = -kHarmonicToleranceBins; delta <= kHarmonicToleranceBins; ++delta)
                {
                    const auto bin = targetBin + delta;
                    if (bin < semanticFirstBin || bin > semanticLastBin)
                        continue;
                    const auto value = static_cast<double>(midMagnitudes[static_cast<std::size_t>(bin)]);
                    matchedHarmonicPower += value * value;
                }
            }

            nextHarmonicRatio = juce::jlimit(
                0.0f,
                1.0f,
                static_cast<float>(matchedHarmonicPower / chromaPowerTotal));
            nextF0Hz = static_cast<float>(f0Hz);
        }

        cachedChroma = nextChroma;
        cachedChromaEnergyRatio = nextChromaEnergyRatio;
        cachedSingleF0HarmonicEnergyRatio = nextHarmonicRatio;
        cachedHarmonicF0CandidateHz = nextF0Hz;
        lastSemanticAnalysisMs = nowMs;
        ++semanticRunsInWindow;
    }

    if (semanticEnabled)
    {
        frame.chroma = cachedChroma;
        frame.chromaEnergyRatio = cachedChromaEnergyRatio;
        frame.singleF0HarmonicEnergyRatio = cachedSingleF0HarmonicEnergyRatio;
        frame.harmonicF0CandidateHz = cachedHarmonicF0CandidateHz;
    }
    else
    {
        frame.chroma.fill(0.0f);
        frame.chromaEnergyRatio = 0.0f;
        frame.singleF0HarmonicEnergyRatio = 0.0f;
        frame.harmonicF0CandidateHz = 0.0f;
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

    // Once the signal gate has closed, content-dependent values are explicitly
    // invalid rather than leaving random near-noise values in the stream.
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
        frame.chroma.fill(0.0f);
        frame.chromaEnergyRatio = 0.0f;
        frame.singleF0HarmonicEnergyRatio = 0.0f;
        frame.harmonicF0CandidateHz = 0.0f;
        frame.bandsDb.fill(kFloorDb);
        frame.bandStereoCorrelation.fill(0.0f);
        frame.sideBandsDb.fill(kFloorDb);
        frame.bandSideToMidDb.fill(0.0f);
        if (semanticEnabled)
            resetSemanticCache();
    }

    publishFrame(frame, temporalEnabled);
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

    // Preserve the historical prefix. bandsDb remains the Mid spectrum.
    for (const auto bandDb : frame.bandsDb)
        message.addFloat32(bandDb);

    message.addFloat32(frame.lufsShortTerm);
    message.addFloat32(frame.lufsIntegrated);
    message.addFloat32(frame.truePeakDbtp);
    message.addFloat32(frame.maxTruePeakDbtp);

    for (const auto correlation : frame.bandStereoCorrelation)
        message.addFloat32(correlation);

    message.addInt32(frame.signalPresent ? 1 : 0);
    message.addFloat32(frame.detectorPeakDb);
    message.addFloat32(frame.silenceSeconds);
    message.addString(runtimeUuid);

    message.addFloat32(frame.temporalWindowSeconds);
    message.addFloat32(frame.spectralFluxMean);
    message.addFloat32(frame.spectralFluxPeak);
    message.addFloat32(frame.rmsRisePeakDb);
    message.addFloat32(frame.lowBandEnergyDb);
    message.addString("0.6");

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

    for (const auto chromaValue : frame.chroma)
        message.addFloat32(chromaValue);
    message.addFloat32(frame.chromaEnergyRatio);
    message.addFloat32(frame.singleF0HarmonicEnergyRatio);
    message.addFloat32(frame.harmonicF0CandidateHz);
    message.addString("0.9");

    // Adaptive-analysis/runtime telemetry. Existing indexes 0..127 remain
    // unchanged. The feature mask tells the Bridge which older fields are
    // intentionally disabled rather than merely numerically zero.
    message.addInt32(frame.analysisProfile);
    message.addInt32(static_cast<juce::int32>(frame.analysisFeatureMask));
    message.addFloat32(frame.workerLoadRatio);
    message.addFloat32(frame.fifoFillRatio);
    message.addFloat32(frame.fftRunsPerSecond);
    message.addFloat32(frame.semanticRunsPerSecond);
    message.addString("1.1");

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

        applyProfileChangeIfNeeded();

        // Identify must work even while the transport is stopped and no audio
        // is reaching the plugin. Keep the request pending until OSC is ready.
        refreshOscConnectionIfNeeded();
        if (identifyRequested.load(std::memory_order_acquire) && oscConnected)
        {
            if (identifyRequested.exchange(false, std::memory_order_acq_rel))
                sendIdentify();
        }

        const auto availableSamples = fifo.available();
        if (availableSamples < static_cast<std::size_t>(kHopSize))
        {
            const auto waitMs = workerIdleWaitMilliseconds(
                availableSamples,
                static_cast<std::size_t>(kHopSize),
                sampleRate.load(std::memory_order_acquire));
            wait(waitMs);
            continue;
        }

        const auto busyStartMs = juce::Time::getMillisecondCounterHiRes();

        if (!fifo.pop(hopLeft.data(), hopRight.data(), kHopSize))
            continue;

        updateSignalState();
        if (hasFeature(activeProfile, FeatureLoudness))
            processLoudnessHop();

        bool windowReady = true;
        if (filledSamples < kFftSize)
        {
            const auto toCopy = std::min(kHopSize, kFftSize - filledSamples);
            std::copy_n(hopLeft.begin(), toCopy, windowLeft.begin() + filledSamples);
            std::copy_n(hopRight.begin(), toCopy, windowRight.begin() + filledSamples);
            filledSamples += toCopy;
            windowReady = filledSamples >= kFftSize;
        }
        else
        {
            std::move(windowLeft.begin() + kHopSize, windowLeft.end(), windowLeft.begin());
            std::move(windowRight.begin() + kHopSize, windowRight.end(), windowRight.begin());
            std::copy(hopLeft.begin(), hopLeft.end(), windowLeft.end() - kHopSize);
            std::copy(hopRight.begin(), hopRight.end(), windowRight.end() - kHopSize);
        }

        if (windowReady)
        {
            const auto nowMs = juce::Time::getMillisecondCounterHiRes();
            if (activeProfile == AnalysisProfile::Eco)
            {
                if (lastReducedAnalysisMs <= 0.0
                    || nowMs - lastReducedAnalysisMs >= kReducedAnalysisIntervalMs)
                {
                    processCoreWindow();
                    lastReducedAnalysisMs = nowMs;
                }
            }
            else if (activeProfile == AnalysisProfile::Balanced)
            {
                if (lastReducedAnalysisMs <= 0.0
                    || nowMs - lastReducedAnalysisMs >= kReducedAnalysisIntervalMs)
                {
                    processWindow();
                    lastReducedAnalysisMs = nowMs;
                }
            }
            else
            {
                // Mix/Full preserve hop-level FFT because Temporal evidence
                // depends on adjacent internal windows. Full adds lower-rate
                // Semantic analysis inside processWindow().
                processWindow();
            }
        }

        const auto busyEndMs = juce::Time::getMillisecondCounterHiRes();
        updatePerformanceTelemetry(busyEndMs - busyStartMs, busyEndMs);
    }
}
} // namespace aianalyzer
