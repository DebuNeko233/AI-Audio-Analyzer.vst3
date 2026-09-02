---
name: ai-analyzer-flstudio
description: Technical usage skill for Cherry Studio + AI Audio Analyzer MCP. Teaches deterministic Analyzer discovery/binding, adaptive Analysis Profile selection, tool selection, measurement validity, evidence semantics, performance telemetry, and controlled Before/After verification around externally controlled DAW changes. It does not prescribe a mixing style, LUFS target, EQ/compression/sidechain/stereo recipe, key change, harmony edit, or aesthetic decision.
---

# AI Audio Analyzer MCP Usage Skill

Use this Skill for two things only:

1. call **AI Audio Analyzer MCP** correctly;
2. interpret returned measurements/evidence without overstating them.

It is **not** a mixing, mastering, harmony, arrangement, tuning, or style guide. Measurements and Analysis Profiles do not imply a mandatory processor, parameter value, key change, chord edit, stereo action, or aesthetic choice.

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

The VST3 also exposes:

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
Identify / signal / Peak-RMS-Crest       Eco
LUFS / True Peak                         Balanced
Spectrum / basic masking                 Balanced
Deep Mid/Side / stereo                   Balanced
Temporal profile/compare                 Mix
Masking with temporal interaction        Mix
Chroma / tonal / single-F0 evidence      Full
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

## 4. Validate data before interpretation

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
```

A newer append-only frame may still physically contain older field positions while a profile has disabled that feature family. The **feature mask is authoritative**; disabled measurements must be treated as unavailable.

## 5. Performance telemetry

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
- sustained growth/high fill can indicate the background worker is falling behind and measurements may become stale;
- `fft_runs_per_second` verifies actual FFT scheduling rate;
- `semantic_runs_per_second` verifies actual Chroma/single-F0 scheduling rate and should be zero when Semantic is disabled.

Do not convert these telemetry values into audio-quality judgments.

## 6. Choose the smallest tool that answers the question

### Project readiness

```text
audio_project_status()
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

### Stable single-track window

```text
audio_average(track, seconds=5)
```

Prefer this to a single frame when several seconds should be represented.

### Current single frame

```text
audio_snapshot(track)
```

Use for connection/current-state inspection, not stable-window analysis.

### Temporal evidence

Requires the Temporal feature group (`Mix` or `Full`):

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
audio_project_masking_scan(
  seconds=5,
  max_pairs=8,
  alignment_tolerance_ms=80
)

audio_masking_evidence(
  track_a,
  track_b,
  seconds=5,
  alignment_tolerance_ms=80,
  max_regions=8
)
```

The model uses existing Analyzer spectrum → 16 equal-ERB-rate regions → relative-level weighting → temporal overlap when available.

ERB handling is re-binning, not a gammatone/cochlear filterbank. Scores are heuristic evidence, not audible-masking probabilities.

Older spectrum-only paths remain:

```text
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
```

Do not describe `audio_detect_masking()` as validated psychoacoustic masking.

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

Do not use audio inference to replace exact symbolic project data. If the DAW/MIDI tooling provides exact note events, key metadata, chord data, or tuning metadata and the request asks for those facts, prefer the exact source.

### Master technical summary

```text
audio_master_status(track="Master")
```

It summarizes measurements; it does not define universal mastering targets.

## 7. Snapshot A/B

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

Use comparable passages, similar windows, comparable `active_ratio`, and the same relevant Analysis Profile/feature availability.

Deltas are `After - Before`.

LUFS-I is session cumulative and is not independently reset for each snapshot.

## 8. Controlled external-change verification

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
→ audio_complete_verification(
     verification_id,
     seconds=0,
     change_summary="factual change actually attempted",
     host_readback="actual host state reported after the write"
   )
```

`seconds=0` reuses the baseline measurement duration.

Then inspect:

```text
result.comparison.controlled_comparison
result.closed_loop_complete
result.comparison.comparability
result.external_change.readback_supplied
result.comparison.targets[].delta
```

Use:

```text
audio_verification_status()
audio_verification_status(verification_id)
```

for current-session recovery/listing.

### Verification semantics

`ready_for_external_change` means the baseline measurement workflow passed current checks. It does not mean the proposed change is appropriate.

`host_readback` must represent actual state returned by the external control MCP, not the intended value. Analyzer stores caller-supplied readback but does not independently query/validate FL Studio state.

`controlled_comparison=true` requires the current transparent measurement guardrails, including baseline readiness, same window duration, unchanged live Analyzer topology, requested target presence, valid active analysis, and active-ratio difference within the current tolerance (`0.15` absolute).

`closed_loop_complete=true` additionally requires supplied host readback.

Neither Boolean means:

```text
After is better
change should be kept
processor setting is correct
mix is more professional
```

Verification sessions are Bridge-session memory only.

Detailed semantics:

```text
references/verification-evidence.md
```

## 9. Critical metric distinctions

Always keep these distinctions:

- Sample Peak ≠ True Peak.
- RMS ≠ LUFS.
- LUFS-S ≠ cumulative LUFS-I.
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
- Chroma energy coverage is not correctness probability.
- Single-F0 harmonic ratio is not probability of harmonic content.
- Harmonic F0 candidate is not a detected musical note.
- Chroma similarity is not harmonic compatibility.
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
references/masking-evidence.md
references/stereo-evidence.md
references/tonal-evidence.md
references/verification-evidence.md
references/analyzer-mcp.md
```

## 10. Boundary with FL Studio control MCP

AI Audio Analyzer MCP owns:

```text
measure
read Analyzer state
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

Never invent control tools, controls, notes, write success, profile state, or readback values.

If the connected control MCP cannot expose/write the required `Analysis Profile` parameter, report that requirement instead of pretending the profile changed.

## 11. Output discipline

When citing Analyzer evidence, include enough context to make it auditable:

```text
instance / selector
Analysis Profile / enabled feature group when relevant
measurement window
signal validity / active ratio
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
- chroma similarity proves harmonic compatibility;
- `controlled_comparison=true` means After is better;
- `Full` means higher audio quality than `Eco`;
- `worker_load_ratio` is the DAW audio-thread CPU percentage.

Those are artistic, symbolic, processing, or external-host-state judgments outside the measurement scope of this MCP and Skill.
