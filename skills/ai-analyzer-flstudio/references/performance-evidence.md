# Adaptive Analysis and Performance Reference

This reference explains how to use AI Audio Analyzer's adaptive analysis controls without confusing performance configuration with artistic intent.

## Analysis Profile is a host parameter

The VST3 exposes:

```text
Parameter ID: analysis_profile
Display name: Analysis Profile
Choices:
0  Eco
1  Balanced
2  Mix
3  Full
```

AI Audio Analyzer MCP **does not write this parameter**. Use the actual DAW-control MCP to inspect the plugin's exposed parameters, change `Analysis Profile`, read back the host value, and then verify the Analyzer state with:

```text
audio_analysis_status(track)
```

Do not invent DAW-control MCP tool names. Use the tools and parameter model the connected DAW MCP actually exposes.

## Profiles

### Eco

Enabled feature groups:

```text
Core
```

Use for low-cost instance presence, signal detection, runtime identity, Identify mapping, and basic Peak/RMS/Crest state when deeper evidence is not currently required.

Disabled/unavailable:

```text
Loudness
Spectrum
Stereo
Temporal
Semantic
```

### Balanced

Enabled:

```text
Core
Loudness
Spectrum
Stereo
```

FFT analysis is reduced to approximately the OSC update rate instead of running at every internal hop. Use when stable level/loudness/spectrum/stereo evidence is needed but hop-level Temporal or tonal Semantic evidence is not.

### Mix

Enabled:

```text
Core
Loudness
Spectrum
Stereo
Temporal
```

Hop-level FFT is restored because Temporal evidence depends on adjacent internal FFT windows.

### Full

Enabled:

```text
Core
Loudness
Spectrum
Stereo
Temporal
Semantic
```

This preserves the pre-adaptive-analysis feature set. It is also the default so older projects do not silently lose measurement families after upgrading.

Semantic Chroma/single-F0 work is scheduled at a lower rate than hop-level FFT work.

## Evidence-family requirements

Use these minimum profiles when a request needs the corresponding measurements:

```text
Core / Identify / signal state       Eco
LUFS / True Peak                     Balanced
Spectrum / basic masking evidence    Balanced
Deep Mid/Side / stereo evidence      Balanced
Temporal profile/compare             Mix
Stronger masking with temporal data  Mix
Tonal / chroma / harmonic evidence   Full
```

A stronger profile includes the lower-profile groups, so `Full` can answer all existing measurement families. Do not switch profiles merely because a higher mode exists.

## Recommended temporary escalation

When many Analyzer instances are present, prefer targeted temporary escalation:

```text
1. audio_analysis_status(target)
2. remember current profile
3. determine minimum profile required by the requested evidence
4. if needed, use the real DAW-control MCP to change Analysis Profile
5. read back the actual host parameter value
6. call audio_analysis_status(target) until the requested feature group is reported enabled
7. play/capture a sufficient comparable measurement window
8. call the required Analyzer evidence tool
9. restore the previous Analysis Profile through the DAW-control MCP when appropriate
10. verify the restored Analyzer status
```

Do not change every Analyzer to `Full` by default for a single-track question.

## Runtime telemetry

`audio_analysis_status()` and `audio_project_performance()` expose:

```text
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
```

### `worker_load_ratio`

Approximate fraction of elapsed monitoring time spent inside the Analyzer **background analysis worker**.

It is **not**:

```text
DAW realtime audio-thread CPU
whole-plugin CPU percentage
system CPU percentage
audio dropout probability
```

### `fifo_fill_ratio`

Fraction of the preallocated Analyzer SPSC input FIFO currently queued.

A transient nonzero value is not automatically a problem. Sustained growth or consistently high fill is evidence that the background analyzer may be falling behind incoming audio, which can make measurement timing stale.

### `fft_runs_per_second`

Observed internal FFT executions per second. It is useful for verifying that profile scheduling is actually reducing work.

### `semantic_runs_per_second`

Observed Chroma/single-F0 semantic analysis executions per second. It should be zero when Semantic is disabled.

## Disabled fields are unavailable, not zero

The append-only OSC frame keeps older field positions for compatibility even when a feature family is disabled. The feature mask is authoritative.

Bridge parsing converts disabled measurements to `null`/invalid state before downstream interpretation. Therefore:

```text
Semantic disabled + chroma placeholder = unavailable
Temporal disabled + flux placeholder    = unavailable
Spectrum disabled + bands placeholder   = unavailable
```

Never reinterpret an unavailable field as numeric zero.

## Performance profiles are not artistic modes

Do not infer any of these:

```text
Eco = rough mix
Balanced = balanced sound
Mix = better for mixing aesthetics
Full = higher audio quality
```

Profiles change **analysis computation**, not the audio signal and not the user's artistic target.

## Relationship to closed-loop verification

Profile changes are real host state changes. If profile switching is part of a controlled workflow:

```text
DAW-control MCP writes Analysis Profile
→ DAW-control MCP reads it back
→ audio_analysis_status verifies Analyzer feature-mask state
```

For an artistic plugin-parameter A/B, avoid changing Analysis Profile between Before and After unless the measurement procedure explicitly accounts for it, because different enabled evidence families can make the two observation states non-equivalent.
