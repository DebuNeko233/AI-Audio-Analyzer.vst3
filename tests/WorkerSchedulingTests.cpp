#include "WorkerScheduling.h"

#include <ebur128.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <iostream>
#include <numbers>
#include <vector>

namespace
{
bool expect(bool condition, const char* message)
{
    if (!condition)
        std::cerr << "FAIL: " << message << '\n';
    return condition;
}

bool testIdleWait()
{
    bool ok = true;
    ok &= expect(aianalyzer::workerIdleWaitMilliseconds(1024, 1024, 48000.0) == 0,
                 "full hop must not wait");
    ok &= expect(aianalyzer::workerIdleWaitMilliseconds(1023, 1024, 48000.0) == 1,
                 "one missing sample must use the one-millisecond floor");
    ok &= expect(aianalyzer::workerIdleWaitMilliseconds(512, 1024, 48000.0) == 11,
                 "half hop at 48 kHz should wait about eleven milliseconds");
    ok &= expect(aianalyzer::workerIdleWaitMilliseconds(0, 1024, 48000.0) == 20,
                 "empty FIFO at 48 kHz must respect the twenty-millisecond cap");
    ok &= expect(aianalyzer::workerIdleWaitMilliseconds(0, 1024, 192000.0) == 6,
                 "high sample rates should wake sooner because one hop arrives sooner");
    ok &= expect(aianalyzer::workerIdleWaitMilliseconds(0, 1024, 0.0) == 20,
                 "invalid sample rate must remain bounded");
    return ok;
}

bool testLoudnessCadence()
{
    bool ok = true;
    ok &= expect(aianalyzer::loudnessMetricsIntervalSamples(48000.0) == 4800,
                 "one hundred milliseconds at 48 kHz must equal 4800 samples");
    ok &= expect(aianalyzer::loudnessMetricsIntervalSamples(44100.0) == 4410,
                 "one hundred milliseconds at 44.1 kHz must equal 4410 samples");
    ok &= expect(!aianalyzer::loudnessMetricsDue(4799, 48000.0),
                 "loudness metrics should not be polled before one hundred milliseconds of audio");
    ok &= expect(aianalyzer::loudnessMetricsDue(4800, 48000.0),
                 "loudness metrics should be due at one hundred milliseconds of audio");
    ok &= expect(aianalyzer::loudnessMetricsIntervalSamples(0.0) == 1,
                 "invalid sample rate must still produce a bounded positive interval");
    return ok;
}

bool testRunningTruePeakMatchesGlobal()
{
    constexpr unsigned long sampleRate = 48000;
    constexpr std::size_t blockSize = 1024;
    constexpr int blocks = 10;

    auto* state = ebur128_init(2, sampleRate, EBUR128_MODE_TRUE_PEAK);
    if (!expect(state != nullptr, "ebur128_init must succeed"))
        return false;

    std::vector<float> interleaved(blockSize * 2);
    const std::array<double, blocks> amplitudes {
        0.08, 0.16, 0.42, 0.91, 0.27, 0.63, 0.11, 0.74, 0.35, 0.19
    };

    double runningPeak = 0.0;
    std::size_t sampleOffset = 0;
    bool ok = true;

    for (int block = 0; block < blocks; ++block)
    {
        const auto amplitude = amplitudes[static_cast<std::size_t>(block)];
        for (std::size_t i = 0; i < blockSize; ++i)
        {
            const auto t = static_cast<double>(sampleOffset + i) / sampleRate;
            interleaved[i * 2] = static_cast<float>(
                amplitude * std::sin(2.0 * std::numbers::pi * 997.0 * t));
            interleaved[i * 2 + 1] = static_cast<float>(
                amplitude * 0.83 * std::sin(2.0 * std::numbers::pi * 1403.0 * t + 0.37));
        }
        sampleOffset += blockSize;

        ok &= expect(ebur128_add_frames_float(state, interleaved.data(), blockSize) == EBUR128_SUCCESS,
                     "ebur128_add_frames_float must succeed");

        double left = 0.0;
        double right = 0.0;
        ok &= expect(ebur128_prev_true_peak(state, 0, &left) == EBUR128_SUCCESS,
                     "left previous true peak must be readable");
        ok &= expect(ebur128_prev_true_peak(state, 1, &right) == EBUR128_SUCCESS,
                     "right previous true peak must be readable");
        runningPeak = std::max(runningPeak, std::max(left, right));
    }

    double globalLeft = 0.0;
    double globalRight = 0.0;
    ok &= expect(ebur128_true_peak(state, 0, &globalLeft) == EBUR128_SUCCESS,
                 "left global true peak must be readable");
    ok &= expect(ebur128_true_peak(state, 1, &globalRight) == EBUR128_SUCCESS,
                 "right global true peak must be readable");

    const auto globalPeak = std::max(globalLeft, globalRight);
    ok &= expect(std::abs(runningPeak - globalPeak) <= 1.0e-12,
                 "running max of prev_true_peak must equal global true peak");

    ebur128_destroy(&state);
    return ok;
}
} // namespace

int main()
{
    const bool ok = testIdleWait()
                 && testLoudnessCadence()
                 && testRunningTruePeakMatchesGlobal();
    if (ok)
        std::cout << "Worker scheduling regressions passed\n";
    return ok ? 0 : 1;
}
