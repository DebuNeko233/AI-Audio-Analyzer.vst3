#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>

namespace aianalyzer
{
inline constexpr int kMaxWorkerIdleWaitMs = 20;
inline constexpr double kLoudnessMetricsIntervalMs = 100.0;

// The audio callback deliberately does not notify the worker. Estimate when the
// missing samples for one analysis hop should have arrived, but cap the sleep so
// transport restarts and low-block-size hosts cannot leave measurements stale
// for an unbounded interval.
inline int workerIdleWaitMilliseconds(std::size_t availableSamples,
                                      std::size_t hopSamples,
                                      double sampleRate) noexcept
{
    if (hopSamples == 0 || availableSamples >= hopSamples)
        return 0;

    const auto safeRate = sampleRate > 1.0 ? sampleRate : 1.0;
    const auto missingSamples = hopSamples - availableSamples;
    const auto estimatedMs = static_cast<int>(std::ceil(
        static_cast<double>(missingSamples) * 1000.0 / safeRate));

    return std::clamp(estimatedMs, 1, kMaxWorkerIdleWaitMs);
}

inline bool loudnessMetricsDue(double lastMetricsMs, double nowMs) noexcept
{
    return lastMetricsMs <= 0.0
        || nowMs - lastMetricsMs >= kLoudnessMetricsIntervalMs;
}
} // namespace aianalyzer
