---
name: ai-analyzer-flstudio
description: Technical usage skill for Cherry Studio + AI Audio Analyzer MCP. Teaches deterministic Analyzer discovery/binding, tool selection, measurement validity, level/loudness/spectrum/stereo/temporal semantics, project overview, Snapshot A/B, and MCP 0.7 masking-evidence interpretation. It does not prescribe a mixing style, LUFS target, EQ/compression/sidechain recipe, or aesthetic decision.
---

# AI Audio Analyzer MCP Usage Skill

This Skill has two responsibilities only:

1. help the model call **AI Audio Analyzer MCP** correctly;
2. help the model interpret returned measurements and evidence without overstating them.

It is **not a mixing-style guide**. Do not infer a mandatory EQ, compressor, limiter, sidechain, panning, stereo, or mastering action merely because a measurement is high, low, overlapping, correlated, or temporally coincident. Artistic decisions come from the user's goal, musical context, references, DAW state, and the model's own reasoning—not from this Skill.

## 1. Start at project level

For a project-level request, begin with:

```text
audio_project_status()
```

Use it to check Bridge/OSC health, live Analyzer count, deterministic bindings, active input, stale streams, duplicate names, and Master candidates.

Only descend when needed:

```text
audio_bridge_status()
audio_list_tracks()
audio_instance_map()
```

Do not call all tools mechanically. Prefer the highest-level tool that answers the question, then drill down.

## 2. Deterministic multi-instance mapping

AI Audio Analyzer v0.4+ exposes a host-visible Boolean parameter:

```text
Parameter ID: identify
Display name: Identify
```

When an Analyzer is unbound and an FL Studio control MCP can access plugin parameters:

```text
find real Mixer Track / Plugin Slot
→ read current Identify value
→ toggle Identify
→ audio_last_identify()
→ verify fresh + unconsumed event
→ audio_bind_last_identified(fl_track_index, fl_track_name, slot)
→ audio_instance_map()
```

One Identify event may be consumed only once.

Preferred selector order after discovery:

```text
mixer:<index>/slot:<slot>
→ unique FL Mixer track name
→ runtime UUID
→ unique Analyzer display name
```

If multiple Analyzers exist on one Mixer Track, include `slot`.

Do not guess mapping from names, spectrum shape, or musical content when Identify is available.

## 3. Validate data before interpreting it

For content-related measurements check:

```text
signal_present
analysis_valid
active_ratio
```

Signal gate semantics are approximately:

```text
close   below -50 dBFS for ~0.4 s
reopen  above -48 dBFS
```

`null` means **unavailable**, not numeric zero.

For V0.6 temporal measurements also inspect:

```text
temporal_supported
temporal_valid
temporal_window_seconds
```

A legacy Analyzer may still provide level/spectrum data while lacking V0.6 temporal evidence.

## 4. Tool selection

### Project readiness

```text
audio_project_status()
```

### Project-wide recent overview

```text
audio_mix_overview(seconds=10, max_tracks=32)
```

Its `potential_spectral_conflicts` are coarse spectral candidates only.

### Project-wide stronger masking candidates — V0.7

```text
audio_project_masking_scan(seconds=5, max_pairs=8, alignment_tolerance_ms=80)
```

Use this when the user wants likely interaction candidates across the project. It starts from project spectral candidates and ranks them with the V0.7 auditory-band/relative-level/temporal evidence model.

It is still a **candidate ranking**, not an automatic list of mix problems.

### Stable single-track window

```text
audio_average(track, seconds)
```

Prefer this to a single frame for observations that should represent several seconds.

### Current single frame

```text
audio_snapshot(track)
```

Use for current-state/connection inspection, not as a substitute for a stable measurement window.

### Single-track temporal profile — V0.6

```text
audio_temporal_profile(track, seconds=5)
```

Use for normalized spectral flux, RMS-rise evidence, low-band temporal energy, and threshold-based onset/change candidate density.

### Two-track spectral comparison

```text
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
```

`audio_detect_masking()` is the older spectral-overlap heuristic. Do not describe it as a validated psychoacoustic masking result.

### Two-track temporal comparison — V0.6

```text
audio_temporal_compare(
  track_a,
  track_b,
  seconds=5,
  low_hz=40,
  high_hz=160,
  alignment_tolerance_ms=80
)
```

Use when the question depends on whether energy in a selected frequency range actually co-occurs or co-varies over time.

### Two-track masking evidence — V0.7

```text
audio_masking_evidence(
  track_a,
  track_b,
  seconds=5,
  alignment_tolerance_ms=80,
  max_regions=8
)
```

Use this for the most detailed current masking-related evidence. It combines:

```text
existing 32-band Analyzer spectrum
→ 16 equal ERB-rate regions
→ relative spectral occupancy
→ directional relative-level weighting
→ V0.6 selected-band temporal overlap
```

The ERB stage is **re-binning**, not a gammatone/cochlear filterbank. The score is **heuristic evidence**, not an audible-masking probability.

### Stereo bands

```text
audio_stereo_bands(track)
```

### Master technical summary

```text
audio_master_status(track="Master")
```

It summarizes measurements; it does not define a universal mastering target.

### Snapshot A/B

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

Use comparable musical passages, similar window lengths, and comparable `active_ratio`. Snapshot deltas are `After - Before`. LUFS-I is session cumulative, not a reset per snapshot.

## 5. How to read V0.7 masking evidence

`audio_masking_evidence()` reports multiple transparent components instead of one opaque conclusion.

### `relative_spectral_overlap`

Each track's ERB-region powers are normalized to that track's own strongest ERB region. The score uses the minimum relative power of the two tracks.

It describes local spectral coexistence, not audibility or importance.

### `level_delta_a_minus_b_db`

```text
positive → A is stronger in that ERB region
negative → B is stronger in that ERB region
```

This is a relative Analyzer level difference, not an auditory masking threshold.

### `level_direction_weight_a_over_b` / `...b_over_a`

A bounded logistic weighting derived from the regional level difference. It only indicates which direction is more supported by relative level. It is not a probability.

### `spectral_level_evidence_*`

Combines relative spectral overlap with the directional level weight.

### `normalized_band_temporal_overlap`

Comes from aligned V0.6 band-energy envelopes. Higher values mean the two sources more often occupy strong states in that same region at the same time.

### `combined_evidence_*`

Combines spectral/level evidence with temporal overlap when temporal data is available.

Do not compare these values to an undocumented universal threshold. Prefer relative ranking across regions/pairs within the same measurement context.

### `masking_evidence_score`

A compact summary of the strongest returned regions. Use it to rank candidates, not to label a pair as objectively "bad".

## 6. Evidence quality matters

When interpreting V0.6/V0.7 pair evidence, report or inspect:

```text
window_seconds
active_ratio_a / active_ratio_b
alignment.aligned_pairs
alignment.tolerance_ms
alignment.mean_abs_offset_ms
temporal_usable_pairs
ERB region low_hz / high_hz
```

Sparse, stale, mostly silent, or poorly aligned data should reduce confidence in the interpretation.

## 7. Relationship between old and new masking tools

Use the tools progressively:

```text
audio_mix_overview()
    coarse project spectral candidates
        ↓
audio_project_masking_scan()
    project ranking with V0.7 evidence
        ↓
audio_masking_evidence(a, b)
    detailed ERB-region evidence
        ↓
audio_temporal_compare(a, b, custom band)
    custom-frequency temporal drill-down when needed
```

Do not mechanically call every layer if the user's question is already answered.

## 8. Parameter interpretation rules

Detailed semantics:

```text
references/parameters.md
references/masking-evidence.md
```

Tool/selector details:

```text
references/analyzer-mcp.md
```

Always keep these distinctions:

- Sample Peak ≠ True Peak.
- RMS ≠ LUFS.
- LUFS-S ≠ cumulative LUFS-I.
- Analyzer spectrum dB is not calibrated SPL.
- Centroid/Rolloff/Flatness are descriptive statistics, not quality scores.
- Stereo Correlation/Width are measurements, not good/bad scores.
- Spectral Flux is normalized spectral redistribution, not simple gain change.
- RMS Rise is rapid level-increase evidence, not Crest Factor or attack time.
- Spectral overlap, temporal overlap, and V0.7 masking evidence are not probabilities of audible masking.
- Onset candidates are threshold-based change candidates, not ground-truth labels.
- `null` is unavailable, not zero.

## 9. Boundary with FL Studio control MCP

AI Audio Analyzer MCP is responsible for:

```text
measure / read / compare / verify
```

FL Studio control MCP is responsible for:

```text
DAW topology / plugin access / host changes
```

This Skill may guide deterministic Identify mapping and measurement readback after an external DAW change. It must **not** prescribe what parameter to change, by how much, or which artistic style to follow.

If the user asks to modify the project, first read the actual DAW tracks/slots/plugins/parameters, do not invent controls, read back the host state after changes, and use Analyzer measurements only as technical evidence.

## 10. Output discipline

When citing Analyzer evidence, include enough context to make it auditable:

```text
instance / selector
measurement window
signal validity / active ratio
frequency or ERB region when relevant
alignment quality for temporal evidence
measurement/evidence value
what the metric can and cannot establish
```

Do not present these as Analyzer-measured facts:

- a sound "should" be warmer, brighter, wider, louder, or more modern;
- a genre must hit a fixed LUFS number;
- a frequency must be cut/boosted by a specific amount;
- spectral or V0.7 masking evidence automatically requires EQ or sidechain;
- one correlation/evidence score is inherently good or bad.

Those are artistic or processing judgments, outside the measurement scope of this MCP and Skill.
