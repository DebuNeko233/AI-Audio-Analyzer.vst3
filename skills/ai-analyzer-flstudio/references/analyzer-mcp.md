# AI Audio Analyzer MCP Reference

This reference describes MCP tools, selector rules, adaptive Analysis Profile readback, call order, validity checks, controlled verification, and OSC compatibility.

Related semantics:

```text
parameters.md
performance-evidence.md
masking-evidence.md
stereo-evidence.md
tonal-evidence.md
verification-evidence.md
```

Current MCP 1.1 exposes **29 tools**:

```text
audio_bridge_status()
audio_list_tracks()
audio_last_identify(max_age_seconds=10)
audio_bind_last_identified(fl_track_index, fl_track_name, slot, max_age_seconds=5)
audio_instance_map()
audio_snapshot(track)
audio_average(track, seconds=5)
audio_stereo_bands(track)
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
audio_master_status(track="Master")
audio_project_status()
audio_mix_overview(seconds=10, max_tracks=32)
audio_capture_snapshot(name, seconds=5)
audio_list_snapshots()
audio_compare_snapshots(before, after)
audio_temporal_profile(track, seconds=5)
audio_temporal_compare(track_a, track_b, seconds=5, low_hz=40, high_hz=160, alignment_tolerance_ms=80)
audio_masking_evidence(track_a, track_b, seconds=5, alignment_tolerance_ms=80, max_regions=8)
audio_project_masking_scan(seconds=5, max_pairs=8, alignment_tolerance_ms=80)
audio_stereo_profile(track, seconds=5)
audio_stereo_compare(track_a, track_b, seconds=5)
audio_tonal_profile(track, seconds=8)
audio_tonal_compare(track_a, track_b, seconds=8)
audio_analysis_status(track)
audio_project_performance()
audio_begin_verification(label, seconds=5, target_selectors=None)
audio_complete_verification(verification_id, seconds=0, change_summary="", host_readback="")
audio_verification_status(verification_id="")
```

## Recommended hierarchy

Do not call all 29 tools by default.

```text
project readiness
→ audio_project_status()

many instances / performance concern
→ audio_project_performance()

one instance feature/profile check
→ audio_analysis_status()

project recent overview
→ audio_mix_overview()

stable single-track measurement
→ audio_average()

then choose only the needed evidence family:
→ temporal
→ masking
→ stereo
→ tonal

external DAW change + measured verification
→ audio_begin_verification()
→ external control MCP write + actual host readback
→ audio_complete_verification()
```

## Deterministic Identify mapping

Host-visible parameter:

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

Recommended flow:

1. use the real FL Studio control MCP to locate the Mixer Track / Plugin Slot;
2. inspect the actual plugin parameters and find `Identify`;
3. read current value;
4. toggle it;
5. immediately call `audio_last_identify()`;
6. verify the event is fresh and unconsumed;
7. call `audio_bind_last_identified(fl_track_index, fl_track_name, slot)`;
8. repeat one instance at a time;
9. verify with `audio_instance_map()`.

Do not assume FL Studio MCP tool names. Use the tools it actually exposes.

Runtime UUIDs, Identify events, and bindings are session-scoped.

## Selector rules

Preferred order:

```text
mixer:<track_index>/slot:<slot>
→ unique FL Mixer track name
→ runtime UUID
→ unique Analyzer display name
```

Examples:

```text
mixer:7
mixer:7/slot:9
fl:7
fl:7/slot:9
```

If multiple Analyzer instances exist on one Mixer Track, include `slot`.

## Analysis Profile control/readback

Host-visible parameter:

```text
Parameter ID: analysis_profile
Display name: Analysis Profile

0 Eco
1 Balanced
2 Mix
3 Full
```

Feature groups:

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

`Full` is the default for backward compatibility.

Analyzer MCP does not write this parameter. Use the actual DAW-control MCP to change the host parameter, read the host value back, then verify what the Analyzer is really computing with:

```text
audio_analysis_status(track)
```

Important returned fields:

```text
adaptive_analysis_supported
profile
profile_index
feature_mask
features
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
control_parameter
```

For project-wide profile/load inspection:

```text
audio_project_performance()
```

It returns instance/profile counts, max/mean worker load, max FIFO fill, per-instance status, and transparent backlog/load warnings.

`worker_load_ratio` is background Analyzer-worker busy time, not DAW realtime audio-thread CPU.

Detailed semantics: `performance-evidence.md`.

## Signal and validity

Approximate signal gate:

```text
close threshold   -50 dBFS
reopen threshold  -48 dBFS
hold              ~0.4 s
```

Rules:

- `null` means unavailable, not zero;
- inspect active/valid coverage for window tools;
- stale streams are not current state;
- when adaptive telemetry exists, `analysis_features` is authoritative about which feature families are actually enabled;
- append-only compatibility positions may exist in the OSC packet even when a profile disabled that family; Bridge parsing invalidates those values before interpretation.

Minimum profiles:

```text
LUFS / True Peak                 Balanced
Spectrum / basic masking         Balanced
Deep stereo                      Balanced
Temporal                         Mix
Tonal / chroma / harmonic        Full
```

## Core / project tools

### `audio_project_status()`

Use first for project readiness. Important fields include:

```text
project_ready
audio_ready
live_count
bound_count
unbound_count
active_count
stale_count
instances
warnings
```

### `audio_mix_overview()`

Returns recent project-level summaries and coarse `potential_spectral_conflicts`. These are candidates, not proof of audible masking.

### `audio_snapshot()`

Latest frame/current state. Do not substitute it for a stable multi-second observation.

### `audio_average()`

Recent stable window. Content-dependent averages use active frames.

### `audio_master_status()`

Technical summary only; no universal mastering target is defined.

## Temporal tools

Requires Temporal (`Mix` or `Full`).

```text
audio_temporal_profile(track, seconds=5)
audio_temporal_compare(track_a, track_b, seconds=5, low_hz=40, high_hz=160, alignment_tolerance_ms=80)
```

Typical evidence:

```text
spectral_flux_mean
spectral_flux_peak
rms_rise_peak_db
low_band_40_160_energy_db
onset/change candidates
aligned pairs
band-envelope correlation
normalized band temporal overlap
alignment offset
```

Change candidates are heuristic, not annotated onset ground truth.

## Masking tools

Spectrum requires `Balanced` or higher; temporal interaction evidence requires `Mix`/`Full`.

```text
audio_masking_evidence(...)
audio_project_masking_scan(...)
```

Current model:

```text
32 Analyzer Mid-spectrum features
→ 16 equal ERB-rate regions
→ relative spectral occupancy
→ directional relative-level weighting
→ temporal overlap when available
```

`auditory_band_model.filterbank=false`: this is re-binning, not a gammatone/cochlear filterbank.

`masking_evidence_score` is not an audible-masking probability.

Legacy spectrum-only tools remain:

```text
audio_compare_tracks()
audio_detect_masking()
```

## Stereo tools

Requires Stereo (`Balanced` or higher).

```text
audio_stereo_profile(track, seconds=5)
audio_stereo_compare(track_a, track_b, seconds=5)
```

Keep these independent:

```text
signed L/R correlation
Mid/Side energy
Side/Mid dB
1 - abs(correlation) decorrelation proxy
negative-cross evidence
20–120 Hz stereo relation
frequency-dependent stereo relation
```

Deltas from `audio_stereo_compare()` are `B - A`, not better/worse labels.

Legacy eight correlation bands:

```text
audio_stereo_bands(track)
```

## Tonal / semantic tools

Requires Semantic (`Full`).

```text
audio_tonal_profile(track, seconds=8)
audio_tonal_compare(track_a, track_b, seconds=8)
```

Main groups:

```text
chroma.normalized_power[12]
chroma.normalized_entropy
tonal_center_evidence.top_candidates[]
tonal_center_evidence.top2_margin
harmonic_alignment
evidence_quality
```

Chroma order:

```text
C C# D D# E F F# G G# A A# B
```

Tonal-center candidates are Krumhansl-Kessler major/minor profile correlations, not key probabilities.

Single-F0 fields are spectral-alignment evidence, not note transcription or pitch-confidence probability.

When exact MIDI/DAW notes, key, chords, or tuning metadata are available, use the exact project data for exact symbolic facts.

## Snapshot A/B

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

Use comparable passages, windows, active coverage, and relevant Analysis Profile/feature availability.

Delta convention:

```text
After - Before
```

LUFS-I remains session cumulative.

## Controlled verification

For a DAW modification that should be measured before/after:

```text
audio_begin_verification(
  label,
  seconds=5,
  target_selectors=[...]
)
```

Call it **before** the external artistic/technical write.

Inspect:

```text
ready_for_external_change
baseline_blockers
verification_id
```

Then:

```text
external DAW-control MCP performs the real write
→ external DAW-control MCP reads actual host state back
→ replay comparable passage
→ audio_complete_verification(
     verification_id,
     seconds=0,
     change_summary="factual attempted change",
     host_readback="actual returned host state"
   )
```

`seconds=0` reuses the baseline duration.

Important outputs:

```text
result.comparison.controlled_comparison
result.closed_loop_complete
result.comparison.comparability
result.external_change.readback_supplied
result.comparison.targets[].delta
```

`controlled_comparison` = measurement comparability guardrail only.

`closed_loop_complete` = controlled comparison plus supplied actual host readback.

Neither means the artistic change is better/correct/preferred.

Verification sessions are Bridge-session memory only.

## OSC compatibility

Analysis address:

```text
/aianalyzer/frame
```

Identify address:

```text
/aianalyzer/identify
```

The frame remains append-only:

```text
0..58      historical core / loudness / stereo / identity prefix
59..64     Temporal fields + "0.6" marker
65..111    Mid/Side + deeper stereo fields + "0.8" marker
112..123   12 chroma bins C..B
124        chroma_energy_ratio
125        single_f0_harmonic_energy_ratio
126        harmonic_f0_candidate_hz
127        "0.9" marker
128        analysis_profile index
129        analysis_feature_mask
130        worker_load_ratio
131        fifo_fill_ratio
132        fft_runs_per_second
133        semantic_runs_per_second
134        "1.1" marker
```

Existing indexes `0..127` are unchanged.

Feature-mask bits:

```text
1   Core
2   Loudness
4   Spectrum
8   Stereo
16  Temporal
32  Semantic
```

Historical `bands_db` remains the 32-band Mid spectrum.

## Multiple instances and OSC

All VST3 instances normally send to:

```text
127.0.0.1:9855
```

Only the Bridge binds UDP 9855. VST3 instances are senders, so multiple Analyzer instances do not require separate UDP ports.
