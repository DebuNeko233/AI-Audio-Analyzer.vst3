# Adaptive Analysis and Performance Reference

This reference explains how to use AI Audio Analyzer's adaptive analysis controls without confusing performance configuration with artistic intent.

## Analysis Profile is an Analyzer-owned host parameter

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

Current Analyzer builds can change this **Analyzer-owned measurement-performance parameter** through:

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

These tools do not write EQ, compression, gain, pan, synth, routing, automation, or other artistic/project parameters. Those remain the responsibility of the actual DAW-control MCP.

The control path is deliberately local and narrow:

```text
Analyzer MCP
→ loopback-only OSC control request
→ target VST3 runtime UUID
→ JUCE message thread
→ host-visible Analysis Profile parameter
→ loopback ACK
```

The existing `/aianalyzer/frame` measurement protocol remains OSC 1.2 and keeps indexes `0..149` unchanged. Analyzer-owned control uses a separate local control revision.

## Control acknowledgement, change state, and telemetry confirmation

`audio_set_analysis_profile()` keeps three ideas separate:

```text
control_acknowledged
  The target live VST3 accepted the request on its local control path and
  processed the host-visible Analysis Profile request on the JUCE message thread.

changed
  When supplied by the current VST3 ACK, this reports whether the real
  host-visible Analysis Profile differed immediately before that request.
  It is not inferred from retained Analyzer telemetry.

telemetry_confirmed
  A measurement frame newer than the pre-request frame also reports the
  requested profile.
```

The MCP always requires a live control ACK, even when retained telemetry already shows the requested profile. Retained telemetry can be stale while transport is stopped or after another host-side profile write, so it is observation evidence rather than authority for the current host parameter.

The control ACK does **not** require DAW playback. Telemetry confirmation normally requires new audio processing, so it may remain false while transport is stopped.

Never claim a successful change when:

```text
ok = false
control_acknowledged = false
```

A successful ACK with `changed=false` means the live VST3 confirmed that the requested profile was already the current host-visible value when it processed the request.

Older revision-1 ACKs that predate the appended `changed` field remain readable; in that case `changed` may be `null`. Older VST3 builds with no local control receiver time out cleanly and must not be treated as successful. If the connected DAW-control MCP can write the historical `analysis_profile` host parameter, it may be used as a compatibility fallback, followed by Analyzer telemetry verification.

## Profiles

### Eco

Enabled feature groups:

```text
Core
```

Use for low-cost instance presence, signal detection, runtime identity, Identify mapping, transport context, and basic Peak/RMS/Crest state when deeper evidence is not currently required.

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
Core / Identify / transport / signal state  Eco
LUFS / True Peak                            Balanced
Spectrum / basic masking evidence           Balanced
Deep Mid/Side / stereo evidence             Balanced
Temporal profile/compare                    Mix
Stronger masking with temporal data         Mix
Tonal / chroma / harmonic evidence          Full
```

A stronger profile includes the lower-profile groups, so `Full` can answer all existing measurement families. Do not switch profiles merely because a higher mode exists.

## Recommended temporary escalation

When many Analyzer instances are present, prefer targeted temporary escalation:

```text
1. audio_analysis_status(target)
2. remember the current profile
3. determine the minimum profile required by the requested evidence
4. audio_set_analysis_profile(target, required_profile)
5. require control_acknowledged=true when a control request was sent
6. inspect changed only as live host-state evidence from that ACK
7. when new frames are available, verify audio_analysis_status(target)
8. play/capture a sufficient comparable measurement window/pass
9. call the required Analyzer evidence tool
10. restore the previous profile with audio_set_analysis_profile() when appropriate
11. verify the restored Analyzer state when new telemetry is available
```

For many intended targets, use:

```text
audio_set_project_analysis_profile(profile, tracks=[...])
```

Omit `tracks` only when the task really intends to change every currently live Analyzer instance.

Do not set every Analyzer to `Full` by default for a single-track tonal question.

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

Changing Analysis Profile is an Analyzer configuration action, not an artistic Before/After intervention. Keep it separate from the user's sound-changing verification ledger.

For an artistic plugin-parameter A/B, avoid changing Analysis Profile between Before and After unless the measurement procedure explicitly accounts for it, because different enabled evidence families can make the two observation states non-equivalent.

The Analyzer-owned control ACK confirms that its own profile request was processed by the live VST3. It does not replace actual host readback requirements for unrelated external DAW/plugin changes.
