#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>

namespace aianalyzer
{
class SpscStereoFifo
{
public:
    static constexpr std::size_t capacity = 131072;

    void reset() noexcept
    {
        readIndex.store(0, std::memory_order_release);
        writeIndex.store(0, std::memory_order_release);
        droppedBlocks.store(0, std::memory_order_relaxed);
    }

    // Consumer-only fast discard. Unlike reset(), this never rewinds the
    // producer index and intentionally preserves the cumulative drop counter.
    // It is used when the DAW transport jumps so queued audio from the previous
    // transport epoch cannot be analyzed as if it belonged to the new pass.
    void discardAllFromConsumer() noexcept
    {
        const auto w = writeIndex.load(std::memory_order_acquire);
        readIndex.store(w, std::memory_order_release);
    }

    bool push(const float* left, const float* right, int numSamples) noexcept
    {
        if (left == nullptr || numSamples <= 0)
            return false;

        const auto n = static_cast<std::uint64_t>(numSamples);
        const auto w = writeIndex.load(std::memory_order_relaxed);
        const auto r = readIndex.load(std::memory_order_acquire);

        if ((w - r) + n > capacity)
        {
            droppedBlocks.fetch_add(1, std::memory_order_relaxed);
            return false;
        }

        for (std::uint64_t i = 0; i < n; ++i)
        {
            const auto slot = static_cast<std::size_t>((w + i) % capacity);
            leftBuffer[slot] = left[i];
            rightBuffer[slot] = right != nullptr ? right[i] : left[i];
        }

        writeIndex.store(w + n, std::memory_order_release);
        return true;
    }

    std::size_t available() const noexcept
    {
        const auto w = writeIndex.load(std::memory_order_acquire);
        const auto r = readIndex.load(std::memory_order_relaxed);
        return static_cast<std::size_t>(w - r);
    }

    bool pop(float* left, float* right, std::size_t numSamples) noexcept
    {
        const auto r = readIndex.load(std::memory_order_relaxed);
        const auto w = writeIndex.load(std::memory_order_acquire);

        if (w - r < numSamples)
            return false;

        for (std::size_t i = 0; i < numSamples; ++i)
        {
            const auto slot = static_cast<std::size_t>((r + i) % capacity);
            left[i] = leftBuffer[slot];
            right[i] = rightBuffer[slot];
        }

        readIndex.store(r + numSamples, std::memory_order_release);
        return true;
    }

    std::uint64_t getDroppedBlocks() const noexcept
    {
        return droppedBlocks.load(std::memory_order_relaxed);
    }

private:
    alignas(64) std::array<float, capacity> leftBuffer {};
    alignas(64) std::array<float, capacity> rightBuffer {};
    alignas(64) std::atomic<std::uint64_t> readIndex { 0 };
    alignas(64) std::atomic<std::uint64_t> writeIndex { 0 };
    std::atomic<std::uint64_t> droppedBlocks { 0 };
};
} // namespace aianalyzer
