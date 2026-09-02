#pragma once

#include <array>

namespace aianalyzer
{
constexpr int kFftOrder = 12;
constexpr int kFftSize = 1 << kFftOrder;
constexpr int kHopSize = 1024;
constexpr int kNumBands = 32;
constexpr int kNumStereoCorrelationBands = 8;

inline constexpr std::array<float, kNumStereoCorrelationBands + 1> kStereoCorrelationBandEdgesHz {
    20.0f, 60.0f, 120.0f, 250.0f, 500.0f, 1000.0f, 2000.0f, 5000.0f, 20000.0f
};

struct AnalysisFrame
{
    double sampleRate = 48000.0;
    double timestampSeconds = 0.0;

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

    std::array<float, kNumBands> bandsDb {};
    std::array<float, kNumStereoCorrelationBands> bandStereoCorrelation {};
};
} // namespace aianalyzer
