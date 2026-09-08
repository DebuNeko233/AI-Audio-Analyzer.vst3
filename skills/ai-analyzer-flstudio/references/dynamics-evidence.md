# Dynamics Distribution Evidence

Use `audio_dynamics_distribution(...)` when the task needs retained, coverage-aware dynamics evidence over a selected playback pass, an explicit DAW-time range, or a cached Section Map section.

This is P6a descriptive evidence. It does **not** implement standardized EBU Loudness Range, arbitrary-range integrated LUFS, or a scope-compatible PLR metric.

## Recommended use

For an explicit passage:

```text
audio_dynamics_distribution(
  track,
  start_seconds=...,
  end_seconds=...
)
```

For one cached structural section:

```text
audio_dynamics_distribution(
  track,
  map_id=...,
  section_id="S02"
)
```

For a descriptive section-to-section comparison:

```text
audio_dynamics_distribution(
  track,
  map_id=...,
  section_id="S02",
  compare_section_id="S04"
)
```

If no range or section is supplied, the tool analyzes the span represented by one retained instance-local transport pass. A caller may provide `transport_epoch` explicitly; otherwise the latest retained pass is used for this pass-span mode. For explicit ranges and sections, the shared P4 range resolver chooses the overlapping pass by coverage first unless an epoch is explicitly supplied.

## Coverage policy

Song Memory uses one-second retained bins with 100 ms coverage slots.

P6a uses two independent coverage controls:

```text
minimum_range_coverage
minimum_bin_coverage
```

The default per-bin floor is 0.5. A one-second bin below that floor is rejected from the distribution. Accepted observations are weighted by their observed covered seconds.

Always inspect:

```text
range_coverage_ratio
covered_seconds
accepted_bin_count
accepted_covered_seconds
rejected_low_coverage_bin_count
missing_bin_count
weighting_policy
```

Missing coverage is not silence and is never inserted as a zero-valued observation.

## Percentile semantics

The tool exposes descriptive retained distributions such as:

```text
min / max
P10 / P25 / P50 / P75 / P90
IQR = P75 - P25
P90 - P10
weighted arithmetic mean
```

Percentiles operate on the retained dB-like observations themselves and use covered seconds only as statistical weights.

For RMS, `covered_seconds_power_mean_db` is also returned as a separate energy-domain mean. Do not confuse that power-domain mean with a dB percentile or with the weighted arithmetic mean of dB values.

## LUFS-S spread is not LRA

The tool may return:

```text
lufs_s_interpercentile_range_lu
```

Its definition is explicitly:

```text
P90(LUFS-S) - P10(LUFS-S)
```

This is a descriptive interpercentile spread over retained short-term loudness observations.

It is **not** EBU Loudness Range and must never be relabeled as `LRA`.

The standardized field remains unavailable in P6a:

```text
standardized_metrics.ebu_lra_lu.available = false
standardized_metrics.ebu_lra_lu.value = null
```

## Integrated loudness and PLR boundary

Protocol 1.2 retained `LUFS-I` is transport-pass cumulative. It is not the integrated loudness of an arbitrary historical section/range.

Therefore P6a intentionally reports these as unavailable for arbitrary retained-range analysis:

```text
standardized_metrics.range_integrated_lufs
standardized_metrics.plr_db
```

Do not substitute LUFS-S for integrated loudness and call the result PLR.

## Scope/completeness

`scope.completeness` is descriptive:

```text
full_pass_coverage
partial_pass_coverage
section_range_only
explicit_range_only
```

`full_pass_coverage` means the retained **selected-pass span** satisfies the requested range-coverage threshold. It does not prove that the pass is the complete musical song.

Until authoritative project/timeline boundaries exist:

```text
scope.whole_song_claim_allowed = false
```

Do not turn a partial replay or retained section into a "whole-song dynamics" claim.

## Section comparison

When `compare_section_id` is supplied, deltas use:

```text
comparison - primary
```

Possible descriptive deltas include:

```text
median RMS
median LUFS-S
crest P50 / P90
sample-peak P50
RMS P90-P10 spread
LUFS-S P90-P10 spread
```

Positive or negative values are not a universal dynamics quality score and are not processing recommendations.

## Interpretation boundary

P6a provides evidence, not mastering targets.

Do not hard-code rules such as:

```text
all masters must be -14 LUFS
crest factor below X is always bad
P90-P10 spread must equal Y
one genre must have one fixed dynamics range
```

Interpret dynamics in musical context, section function, reference context, arrangement, and user intent.

## Realtime boundary

P6a runs in MCP over bounded retained summaries.

No percentile computation is added to the VST3 audio callback, and P6a does not change OSC protocol 1.2 or indexes `0..149`.

P6b is the separate future path for authoritative standardized loudness metrics if exact library/state semantics, reset behavior, performance cost, and regression vectors are verified.
