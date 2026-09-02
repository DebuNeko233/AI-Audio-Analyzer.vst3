#pragma once

#include <array>

namespace aianalyzer
{
constexpr int kFftOrder = 12;
constexpr int kFftSize = 1 << kFftOrder;
constexpr int kHopSize = 1024;
constexpr int kNumBands = 32;
constexpr int kNumStereoCorrelationBands = 8;
constexpr int kNumChromaBins = 12;

inline constexpr std::array<float, kNumStereoCorrelationBands + 1> kStereoCorrelationBandEdgesHz {
    20.0f, 60.0f, 120.0f, 250.0f, 500.0f, 1000.0f, 2000.0f, 5000.0f, 20000.0f
};

struct AnalysisFrame
{
    double sampleRate = 48000.0;
    double timestampSeconds = 0.0;

    // V0.3 signal-state metadata. The detector uses a -50 dBFS close threshold,
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

    // V0.6 temporal fields. These are descriptive machine measurements rather
    // than artistic quality scores. Network frames may aggregate several
    // internal FFT hops into one ~10 Hz OSC update.
    float temporalWindowSeconds = 0.0f;
    float spectralFluxMean = 0.0f;
    float spectralFluxPeak = 0.0f;
    float rmsRisePeakDb = 0.0f;
    float lowBandEnergyDb = -120.0f; // FFT-derived 40-160 Hz energy feature.

    // V0.8 Mid/Side and stereo evidence. These values deliberately separate
    // channel similarity, Side energy, and negative cross-spectrum evidence so
    // a wide/decorrelated signal is not conflated with a strongly phase-opposed
    // signal. They remain measurements/evidence, not quality scores.
    float midRmsDb = -120.0f;
    float sideRmsDb = -120.0f;
    float sideToMidDb = -120.0f;
    float negativeCrossEnergyRatio = 0.0f;
    float lowBandCorrelation = 1.0f;      // 20-120 Hz aggregate correlation.
    float lowBandSideToMidDb = -120.0f;  // 20-120 Hz Side/Mid power ratio in dB.

    // V0.9 music-semantic evidence. Chroma is a normalized 12-TET pitch-class
    // power distribution accumulated from the Mid spectrum over 80 Hz-5 kHz.
    // The harmonic ratio is deliberately a single-F0 alignment heuristic, not
    // a pitch-tracker confidence, source-separation result, or musical label.
    std::array<float, kNumChromaBins> chroma {};
    float chromaEnergyRatio = 0.0f;
    float singleF0HarmonicEnergyRatio = 0.0f;
    float harmonicF0CandidateHz = 0.0f;

    // Historical bandsDb is the Mid-spectrum feature used since V0.1.
    std::array<float, kNumBands> bandsDb {};
    std::array<float, kNumStereoCorrelationBands> bandStereoCorrelation {};

    // V0.8 adds an explicit Side spectrum plus integrated Side/Mid ratios over
    // the same eight frequency ranges used by bandStereoCorrelation.
    std::array<float, kNumBands> sideBandsDb {};
    std::array<float, kNumStereoCorrelationBands> bandSideToMidDb {};
};
} // namespace aianalyzer
