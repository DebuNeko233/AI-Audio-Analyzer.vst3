#pragma once

#include <array>
#include <cstdint>
#include <string_view>

namespace aianalyzer
{
inline constexpr int kControlPortBase = 20000;
inline constexpr int kControlPortSpan = 40000;
inline constexpr int kControlCandidateCount = 16;
inline constexpr int kControlStepModulo = 997;
inline constexpr std::string_view kControlProfileAddress = "/aianalyzer/control/profile";
inline constexpr std::string_view kControlAckAddress = "/aianalyzer/control/ack";
inline constexpr std::string_view kControlRevision = "1";

constexpr std::uint32_t controlFnv1a(std::string_view text) noexcept
{
    std::uint32_t hash = 2166136261u;
    for (const auto ch : text)
    {
        hash ^= static_cast<std::uint8_t>(ch);
        hash *= 16777619u;
    }
    return hash;
}

constexpr std::array<int, kControlCandidateCount>
controlCandidatePorts(std::string_view runtimeId) noexcept
{
    std::array<int, kControlCandidateCount> ports {};
    const auto start = static_cast<int>(controlFnv1a(runtimeId) % kControlPortSpan);

    // Keep the step coprime with 40,000 (2^6 * 5^4), so the deterministic
    // probe sequence does not cycle through a small subset of the port range.
    std::uint32_t step = 1u + controlFnv1a(std::string_view {}) % kControlStepModulo;

    // controlFnv1a cannot directly concatenate at constexpr time. Derive a
    // second independent-enough stream by mixing the first hash before the
    // coprime adjustment. Python control_tools.py mirrors this exact operation.
    step = 1u + ((controlFnv1a(runtimeId) ^ 0x9e3779b9u) % kControlStepModulo);
    while ((step % 2u) == 0u || (step % 5u) == 0u)
        ++step;

    for (int i = 0; i < kControlCandidateCount; ++i)
    {
        const auto offset = (start + i * static_cast<int>(step)) % kControlPortSpan;
        ports[static_cast<std::size_t>(i)] = kControlPortBase + offset;
    }
    return ports;
}
} // namespace aianalyzer
