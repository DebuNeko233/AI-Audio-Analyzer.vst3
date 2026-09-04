---
name: ai-analyzer-flstudio
description: Technical usage skill for Cherry Studio + AI Audio Analyzer MCP. Teaches deterministic Analyzer discovery/binding, adaptive Analysis Profile selection, transport-aware whole-song memory, latency/data-quality handling, measurement validity, evidence semantics, performance telemetry, and controlled Before/After verification around externally controlled DAW changes. It does not prescribe a mixing style, LUFS target, EQ/compression/sidechain/stereo recipe, key change, harmony edit, or aesthetic decision.
---

# AI Audio Analyzer MCP Usage Skill

Use this Skill for two things only:

1. call **AI Audio Analyzer MCP** correctly;
2. interpret returned measurements/evidence without overstating them.

It is **not** a mixing, mastering, harmony, arrangement, tuning, or style guide. Measurements, transport memory, and Analysis Profiles do not imply a mandatory processor, parameter value, key change, chord edit, stereo action, or aesthetic choice.

## 1. Start with project state

For a project-level request, begin with:

```text
audio_project_status()
```

Use it to check Bridge/OSC health, live instances, deterministic bindings, active input, stale streams, duplicate names, and Master candidates.

Only descend when needed:

```text
audio_bridge_status()
audio_list_tracks()
audio_instance_map()
```

Do not call every tool mechanically.

If the task concerns a **whole song, a past passage, section-to-section evolution, or mixing/mastering work where LLM/tool latency matters**, next call:

```text
audio_song_status()
```

The Analyzer observes continuously; the LLM does not need to observe continuously.

If the request involves many Analyzer instances, CPU/load concerns, or a measurement family that may be disabled, also inspect:

```text
audio_project_performance()
audio_analysis_status(track)
```

## 2. Deterministic Analyzer ↔ FL Mixer mapping

The VST3 exposes:

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

When an Analyzer is unbound and the connected FL Studio control MCP can access plugin parameters:

```text
find the real Mixer Track / Plugin Slot
→ read current Identify value
→ toggle Identify
→ audio_last_identify()
→ verify fresh + unconsumed event
→ audio_bind_last_identified(fl_track_index, fl_track_name, slot)
→ audio_instance_map()
```

One Identify event may be consumed only once.

Preferred selector order:

```text
mixer:<index>/slot:<slot>
→ unique FL Mixer track name
→ runtime UUID
→ unique Analyzer display name
```

If multiple Analyzer instances exist on one Mixer Track, include `slot`.

Never guess mapping from track names, spectrum, chroma, or musical content when Identify is available.

## 3. Analysis Profile is a performance control

The VST3 exposes:

```text
Parameter ID: analysis_profile
Display name: Analysis Profile
Choices:
0 Eco
1 Balanced
2 Mix
3 Full
```

Profile groups:

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

`Full` is the default for backward compatibility.

Profiles change **Analyzer computation**, not the audio signal and not artistic quality.

### Minimum profile by evidence family

```text
Transport / Identify / signal / Peak-RMS-Crest   Eco
LUFS / True Peak                                  Balanced
Spectrum / basic masking                          Balanced
Deep Mid/Side / stereo                            Balanced
Temporal profile/compare                          Mix
Masking with temporal interaction                 Mix
Chroma / tonal / single-F0 evidence               Full
```

A stronger profile includes the lower groups.

### How to change a profile

Analyzer MCP does **not** write DAW parameters.

When a different profile is needed:

```text
audio_analysis_status(target)
→ remember current profile
→ use the actual FL Studio control MCP to inspect the real plugin parameters
→ change Analysis Profile through that control MCP
→ read the actual host parameter state back
→ audio_analysis_status(target)
→ verify the expected feature group is enabled
→ collect the required measurement window
→ call the needed Analyzer tool
→ restore the previous profile through the control MCP when appropriate
→ verify the restored Analyzer state
```

Do not invent FL Studio MCP tool names. Do not set every Analyzer to `Full` merely because one track needs tonal analysis.

Detailed rules:

```text
references/performance-evidence.md
```

## 4. Whole-song memory and LLM latency

Do **not** assume the newest Analyzer frame corresponds to the audio that the user hears at the instant the LLM reads it.

The chain can contain:

```text
Analyzer worker backlog
OSC/MCP transport
LLM reasoning
external control tool calls
human/host interaction
```

Protocol 1.2 addresses this by attaching DAW transport context and keeping bounded song-time memory.

Use:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(track, resolution_seconds=5, ...)
```

### Recommended whole-song flow

```text
audio_project_status()
→ fix mapping/readiness if necessary
→ audio_song_status()
→ play the song or target passage
→ allow Analyzer to keep collecting while the Agent reasons/works
→ audio_song_overview()
→ audio_song_timeline() only for tracks/time regions requiring detail
→ drill into Temporal / Masking / Stereo / Tonal evidence only as needed
```

Do not repeatedly poll all Analyzer tools during playback just to avoid missing an event.

### Transport epoch

`transport_epoch` means one **instance-local continuous playback pass**.

A new epoch can begin on:

```text
stopped → playing
seek / playhead jump
loop jump
other detected transport discontinuity
```

The worker discards queued pre-jump FIFO audio and resets pass-dependent Loudness/Temporal/Semantic state before measuring the new epoch.

Never assume equal epoch numbers from two independently loaded Analyzer instances are a permanent project-wide pass identity. Inspect:

```text
epoch_counters_consistent
selected_transport_epochs
DAW-time spans
warnings
```

### Data-quality fields

Keep these distinct:

```text
estimated_analysis_lag_ms
  Analyzer FIFO + FFT-window estimate only.
  Not network latency and not LLM latency.

data_age_seconds
  Wall-clock age of retained MCP evidence.
  Old evidence can still be exactly the requested historical song range.

dropped_blocks
  Cumulative Analyzer FIFO push failures.
  Non-zero means some input audio was not measured.

coverage_ratio
  How much of a requested/coarse interval is represented by retained timeline bins.
```

Transport coordinates are useful for song/section reasoning, not sample-accurate edits, transient placement, or phase alignment.

### Choose compact timeline resolution

Current query resolutions:

```text
1 2 5 10 15 30 seconds
```

Prefer the coarsest resolution that answers the question. Do not feed hundreds of one-second bins to the LLM when a 10-second or whole-pass summary is enough.

Automatic Verse/Chorus/Bridge labeling is **not currently implemented**. Do not invent section names from `audio_song_overview()`.

Detailed rules:

```text
references/song-memory.md
```

## 5. Validate data before interpretation

For content-related measurements inspect:

```text
signal_present
analysis_valid
active_ratio
analysis_features   # when adaptive telemetry is available
```

Signal gate is approximately:

```text
close   below -50 dBFS for ~0.4 s
reopen  above -48 dBFS
```

`null` means **unavailable**, not numeric zero.

Feature-specific validity:

```text
Temporal:
  temporal_supported
  temporal_valid
  temporal_window_seconds

Deep stereo:
  stereo_v08_supported
  stereo_v08_valid
  stereo_frames

Tonal / semantic:
  semantic_v09_supported
  semantic_v09_valid
  valid_frames
  evidence_quality.mean_chroma_energy_ratio
  evidence_quality.normalized_pitch_class_entropy
  evidence_quality.tonal_center_top2_margin
  evidence_quality.valid_frame_ratio

Transport/song memory:
  transport_v12_supported
  transport_epoch
  estimated_analysis_lag_ms
  dropped_blocks
  data_quality.coverage_ratio
```

A newer append-only frame may still physically contain older field positions while a profile has disabled that feature family. The **feature mask is authoritative**; disabled measurements must be treated as unavailable.

## 6. Performance telemetry

Use:

```text
audio_analysis_status(track)
audio_project_performance()
```

Important fields:

```text
analysis_profile
analysis_features
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
```

Interpretation:

- `worker_load_ratio` = approximate busy-time ratio of the Analyzer **background analysis worker**;
- it is not DAW realtime audio-thread CPU, total plugin CPU, or system CPU;
- `fifo_fill_ratio` = fraction of Analyzer input FIFO currently queued;
- transient FIFO fill is not automatically a problem;
- sustained growth/high fill can indicate the background worker is falling behind;
- `fft_runs_per_second` verifies actual FFT scheduling rate;
- `semantic_runs_per_second` verifies actual Chroma/single-F0 scheduling rate and should be zero when Semantic is disabled.

Do not convert these telemetry values into audio-quality judgments.

## 7. Choose the smallest tool that answers the question

### Project readiness

```text
audio_project_status()
```

### Whole-song / latency-resilient context

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
```

### Project performance / adaptive profiles

```text
audio_project_performance()
audio_analysis_status(track)
```

### Project recent overview

```text
audio_mix_overview(seconds=10, max_tracks=32)
```

`potential_spectral_conflicts` are coarse candidates only.

### Stable recent single-track window

```text
audio_average(track, seconds=5)
```

Prefer this to a single frame when several recent seconds should be represented. Prefer song memory instead when the requested passage may already have passed.

### Current single frame

```text
audio_snapshot(track)
```

Use for connection/current-state inspection, not stable-window or historical song analysis.

### Temporal evidence

Requires Temporal (`Mix` or `Full`):

```text
audio_temporal_profile(track, seconds=5)

audio_temporal_compare(
  track_a,
  track_b,
  seconds=5,
  low_hz=40,
  high_hz=160,
  alignment_tolerance_ms=80
)
```

Spectral Flux and RMS Rise are change evidence, not ground-truth onset labels.

### Masking evidence

Spectrum requires `Balanced` or higher. Temporal interaction requires `Mix` or `Full`.

```text
audio_project_masking_scan(...)
audio_masking_evidence(...)
```

The model uses existing Analyzer spectrum → 16 equal-ERB-rate regions → relative-level weighting → temporal overlap when available.

ERB handling is re-binning, not a gammatone/cochlear filterbank. Scores are heuristic evidence, not audible-masking probabilities.

Older spectrum-only paths remain:

```text
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
```

### Deep stereo evidence

Requires Stereo (`Balanced` or higher):

```text
audio_stereo_profile(track, seconds=5)
audio_stereo_compare(track_a, track_b, seconds=5)
```

Keep independent:

```text
signed L/R correlation
Side/Mid energy
1 - abs(correlation) decorrelation proxy
negative-cross evidence
frequency-dependent stereo relation
```

Do not collapse them into a stereo-quality score.

Legacy eight correlation bands:

```text
audio_stereo_bands(track)
```

### Tonal / music-semantic evidence

Requires Semantic (`Full`):

```text
audio_tonal_profile(track, seconds=8)
audio_tonal_compare(track_a, track_b, seconds=8)
```

Important axes:

```text
12-bin normalized chroma C..B
chroma analysis energy coverage
pitch-class entropy
24 major/minor template correlations
top-2 tonal-center separation
single-F0 harmonic-alignment ratio
single-F0 candidate stability
```

Do not use audio inference to replace exact symbolic project data. If DAW/MIDI tooling provides exact note events, key metadata, chord data, or tuning metadata and the request asks for those facts, prefer the exact source.

### Master technical summary

```text
audio_master_status(track="Master")
```

It summarizes measurements; it does not define universal mastering targets.

## 8. Snapshot A/B

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

Use comparable passages, similar windows, comparable `active_ratio`, and the same relevant Analysis Profile/feature availability.

Deltas are `After - Before`.

Snapshot tools do not independently reset Loudness.

For protocol-1.2 instances:

```text
LUFS-I / pass-max True Peak accumulate inside the current transport epoch.
Playback start / seek / loop discontinuity creates a new epoch and Loudness state.
```

Legacy pre-1.2 instances retain historical reset/prepare-scoped LUFS-I behavior.

## 9. Controlled external-change verification

Use this when the agent coordinates a real DAW modification through an external control MCP and the user wants measured verification.

Begin **before** the artistic/technical write:

```text
audio_begin_verification(
  label="short factual label",
  seconds=5,
  target_selectors=["mixer:4/slot:9"]
)
```

Inspect:

```text
ready_for_external_change
baseline_blockers
verification_id
```

If ready:

```text
external FL Studio control MCP makes the intended change
→ external control MCP reads actual host state back
→ replay the same intended passage
→ audio_complete_verification(...)
```

`host_readback` must represent actual state returned by the external control MCP, not the intended value.

`controlled_comparison=true` is a technical comparability gate only.

`closed_loop_complete=true` additionally requires supplied host readback.

Neither means:

```text
After is better
change should be kept
processor setting is correct
mix is more professional
```

Current verification remains recent-window based. Do not claim it is already transport-anchored to an exact DAW-time range.

Detailed semantics:

```text
references/verification-evidence.md
```

## 10. Critical metric distinctions

Always keep these distinctions:

- Sample Peak ≠ True Peak.
- RMS ≠ LUFS.
- LUFS-S ≠ LUFS-I.
- Protocol-1.2 LUFS-I pass scope ≠ permanent project loudness history.
- Analyzer spectrum dB is not calibrated SPL.
- Centroid/Rolloff/Flatness are descriptive, not quality scores.
- Stereo Correlation ≠ Side/Mid energy.
- Low correlation ≠ anti-correlation.
- High Side energy ≠ proof of phase opposition.
- `1 - abs(correlation)` is a decorrelation proxy, not perceptual spaciousness.
- Negative-cross evidence is not an audible mono-cancellation percentage.
- Spectral Flux is normalized spectral redistribution, not simple gain change.
- RMS Rise is rapid level-increase evidence, not Crest Factor or attack time.
- Spectral overlap, temporal overlap, and masking evidence are not probabilities of audible masking.
- Chroma is not note probability or MIDI transcription.
- Tonal-center profile correlation is not key probability.
- Tonal-center top-2 margin is not calibrated confidence.
- Pitch-class entropy is not musical quality.
- Single-F0 harmonic ratio is not probability of harmonic content.
- Harmonic F0 candidate is not a detected musical note.
- Chroma similarity is not harmonic compatibility.
- `transport_epoch` is instance-local pass identity, not a persistent project hash.
- `estimated_analysis_lag_ms` is Analyzer backlog/window latency, not total Agent latency.
- `data_age_seconds` is not the same thing as invalid historical evidence.
- Topology fingerprint is not a persistent DAW-project hash.
- `host_readback` is caller-supplied control-MCP evidence, not Analyzer-verified host state.
- `controlled_comparison` is technical comparability, not artistic quality.
- `worker_load_ratio` is background Analyzer-worker load, not realtime DAW CPU.
- Analysis Profile is computation scope, not audio quality.
- `null` is unavailable, not zero.

Detailed references:

```text
references/parameters.md
references/performance-evidence.md
references/song-memory.md
references/masking-evidence.md
references/stereo-evidence.md
references/tonal-evidence.md
references/verification-evidence.md
references/analyzer-mcp.md
```

## 11. Boundary with FL Studio control MCP

AI Audio Analyzer MCP owns:

```text
measure
read Analyzer state
remember transport-aligned evidence
compare
identity/binding evidence
performance/profile readback
verification measurement conditions
```

FL Studio control MCP owns:

```text
DAW topology / project data
plugin access
Analysis Profile writes
artistic/technical parameter writes
actual host state readback
```

Never invent control tools, controls, notes, write success, profile state, section labels, or readback values.

If the connected control MCP cannot expose/write the required `Analysis Profile` parameter, report that requirement instead of pretending the profile changed.

## 12. Output discipline

When citing Analyzer evidence, include enough context to make it auditable:

```text
instance / selector
DAW-time range / transport epoch when song memory is used
Analysis Profile / enabled feature group when relevant
measurement window or timeline resolution
signal validity / active ratio
data age / estimated Analyzer lag / dropped blocks / coverage when relevant
evidence-quality fields
frequency / stereo band / ERB region / pitch-class context when relevant
alignment quality for temporal evidence
verification topology / coverage / readback context when relevant
measurement/evidence value
what the metric can and cannot establish
```

Do not present these as Analyzer-measured facts:

- a sound should be warmer/brighter/wider/louder/narrower;
- a genre must hit a fixed LUFS number;
- a frequency must be cut/boosted by a specific amount;
- masking evidence automatically requires EQ/sidechain;
- stereo evidence automatically requires mono/narrowing/widening/phase rotation;
- the top tonal-center candidate is certainly the song key;
- an F0 candidate is certainly the played note;
- `audio_song_overview()` has identified Verse/Chorus/Bridge when no exact structure source exists;
- `controlled_comparison=true` means After is better;
- `Full` means higher audio quality than `Eco`;
- `worker_load_ratio` is the DAW audio-thread CPU percentage.

Those are artistic, symbolic, processing, or external-host-state judgments outside the measurement scope of this MCP and Skill.
