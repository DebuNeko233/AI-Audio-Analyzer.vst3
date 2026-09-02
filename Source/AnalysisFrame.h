#pragma once

#include <array>
#include <cstdint>

namespace aianalyzer
{
constexpr int kFftOrder = 12;
constexpr int kFftSize = 1 << kFftOrder;
constexpr int kHopSize = 1024;
constexpr int kNumBands = 32;
constexpr int kNumStereoCorrelationBands = 8;
constexpr int kNumChromaBins = 12;

enum class AnalysisProfile : int
{
    Eco = 0,
    Balanced = 1,
    Mix = 2,
    Full = 3,
};

enum AnalysisFeature : std::uint32_t
{
    FeatureCore = 1u << 0,
    FeatureLoudness = 1u << 1,
    FeatureSpectrum = 1u << 2,
    FeatureStereo = 1u << 3,
    FeatureTemporal = 1u << 4,
    FeatureSemantic = 1u << 5,
};

constexpr std::uint32_t analysisFeatureMaskForProfile(AnalysisProfile profile) noexcept
{
    switch (profile)
    {
        case AnalysisProfile::Eco:
            return FeatureCore;
        case AnalysisProfile::Balanced:
            return FeatureCore | FeatureLoudness | FeatureSpectrum | FeatureStereo;
        case AnalysisProfile::Mix:
            return FeatureCore | FeatureLoudness | FeatureSpectrum | FeatureStereo | FeatureTemporal;
        case AnalysisProfile::Full:
        default:
            return FeatureCore | FeatureLoudness | FeatureSpectrum | FeatureStereo | FeatureTemporal | FeatureSemantic;
    }
}

inline constexpr std::array<float, kNumStereoCorrelationBands + 1> kStereoCorrelationBandEdgesHz {
    20.0f, 60.0f, 120.0f, 250.0f, 500.0f, 1000.0f, 2000.0f, 5000.0f, 20000.0f
};

struct AnalysisFrame
{
    double sampleRate = 48000.0;
    double timestampSeconds = 0.0;

    // Signal-state metadata. The detector uses a -50 dBFS close threshold,
    // -48 dBFS reopen threshold and a short hold so near-threshold material does
    // not chatter between active/silent states.
    bool signalPresent = false;
    float detectorPeakDb = -120.0f;
    float silenceSeconds = 0.0f;

    float peakDb = -120.0f;
    float rmsDb = -120.0f;
    float crestDb = 0.0f;

    float lufsShortTerm = -120.0f;
    float lufsIntegrated = -120.0f;
    float truePeakDbtp = -120.0f;
    float maxTruePeakDbtp = -120.0f;

    float spectralCentroidHz = 0.0f;
    float spectralRolloffHz = 0.0f;
    float spectralFlatness = 0.0f;

    float stereoCorrelation = 1.0f;
    float stereoWidth = 0.0f;

    // Temporal fields. These are descriptive machine measurements rather than
    // artistic quality scores. Network frames may aggregate several internal
    // FFT hops into one ~10 Hz OSC update.
    float temporalWindowSeconds = 0.0f;
    float spectralFluxMean = 0.0f;
    float spectralFluxPeak = 0.0f;
    float rmsRisePeakDb = 0.0f;
    float lowBandEnergyDb = -120.0f; // FFT-derived 40-160 Hz energy feature.

    // Mid/Side and stereo evidence. These values deliberately separate channel
    // similarity, Side energy, and negative cross-spectrum evidence so a
    // wide/decorrelated signal is not conflated with strong phase opposition.
    float midRmsDb = -120.0f;
    float sideRmsDb = -120.0f;
    float sideToMidDb = -120.0f;
    float negativeCrossEnergyRatio = 0.0f;
    float lowBandCorrelation = 1.0f;      // 20-120 Hz aggregate correlation.
    float lowBandSideToMidDb = -120.0f;  // 20-120 Hz Side/Mid power ratio in dB.

    // Music-semantic evidence. Chroma is a normalized 12-TET pitch-class power
    // distribution accumulated from the Mid spectrum over 80 Hz-5 kHz. The
    // harmonic ratio is a single-F0 alignment heuristic, not pitch confidence.
    std::array<float, kNumChromaBins> chroma {};
    float chromaEnergyRatio = 0.0f;
    float singleF0HarmonicEnergyRatio = 0.0f;
    float harmonicF0CandidateHz = 0.0f;

    // Historical bandsDb is the Mid-spectrum feature used since V0.1.
    std::array<float, kNumBands> bandsDb {};
    std::array<float, kNumStereoCorrelationBands> bandStereoCorrelation {};

    // Explicit Side spectrum plus integrated Side/Mid ratios over the same
    // eight frequency ranges used by bandStereoCorrelation.
    std::array<float, kNumBands> sideBandsDb {};
    std::array<float, kNumStereoCorrelationBands> bandSideToMidDb {};

    // Adaptive-analysis/runtime telemetry. These fields are appended to OSC and
    // never repurpose older indexes. They describe what this instance is
    // actually computing and whether its background worker is keeping up.
    int analysisProfile = static_cast<int>(AnalysisProfile::Full);
    std::uint32_t analysisFeatureMask = analysisFeatureMaskForProfile(AnalysisProfile::Full);
    float workerLoadRatio = 0.0f;
    float fifoFillRatio = 0.0f;
    float fftRunsPerSecond = 0.0f;
    float semanticRunsPerSecond = 0.0f;
};
} // namespace aianalyzer
