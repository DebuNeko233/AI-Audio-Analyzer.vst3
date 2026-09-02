#pragma once

#include <array>

namespace aianalyzer
{
constexpr int kFftOrder = 12;
constexpr int kFftSize = 1 << kFftOrder;
constexpr int kHopSize = 1024;
constexpr int kNumBands = 32;

struct AnalysisFrame
{
    double sampleRate = 48000.0;
    double timestampSeconds = 0.0;

    float peakDb = -120.0f;
    float rmsDb = -120.0f;
    float crestDb = 0.0f;

    float spectralCentroidHz = 0.0f;
    float spectralRolloffHz = 0.0f;
    float spectralFlatness = 0.0f;

    float stereoCorrelation = 1.0f;
    float stereoWidth = 0.0f;

    std::array<float, kNumBands> bandsDb {};
};
} // namespace aianalyzer
