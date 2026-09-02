# V0.7 Masking Evidence Reference

This document explains the current V0.7 evidence model. It is intentionally technical and neutral. It does not prescribe EQ, compression, sidechain, gain, panning, stereo processing, or any other artistic decision.

## Scope

V0.7 does **not** claim to implement a validated psychoacoustic masking detector.

It combines already available Analyzer measurements into a more structured pairwise evidence model:

```text
32 log-spaced Analyzer spectrum features
→ equal ERB-rate re-binning
→ relative spectral occupancy
→ directional relative-level weighting
→ V0.6 temporal overlap
→ transparent region-level evidence
```

The output should be described as:

```text
masking-related evidence
interaction evidence
candidate region
relative ranking
```

Avoid calling it:

```text
audible masking probability
psychoacoustic ground truth
critical-band threshold proof
```

## Auditory-band model

The Bridge constructs **16 equal ERB-rate regions** between approximately 20 Hz and 20 kHz using the Glasberg/Moore ERB-rate scale:

```text
ERB-rate(f) = 21.4 * log10(1 + 0.00437 * f)
```

The existing 32 Analyzer spectrum feature centers are assigned to those regions and averaged in the power domain.

Important limitation:

```text
auditory_band_model.filterbank = false
```

This is feature re-binning. It is **not** a gammatone filterbank, cochlear filterbank, spreading-function model, or calibrated hearing-threshold model.

## Regional spectrum normalization

For each track independently, ERB-region power is normalized relative to that track's strongest region.

For a region:

```text
relative_a = power_a / strongest_region_power_a
relative_b = power_b / strongest_region_power_b
relative_spectral_overlap = min(relative_a, relative_b)
```

The result emphasizes whether the same region is important to both sources relative to their own spectral shapes.

It does not describe absolute SPL or listener audibility.

## Relative level direction

The regional level difference is:

```text
level_delta_a_minus_b_db = a_db - b_db
```

Interpretation:

```text
positive → A is stronger in this region
negative → B is stronger in this region
```

V0.7 maps this difference through a logistic function with a 6 dB scale to produce directional weights:

```text
level_direction_weight_a_over_b
level_direction_weight_b_over_a
```

These weights answer only:

> Which direction is more supported by the measured regional level difference?

They are **not** masking probabilities and are not based on a calibrated hearing threshold.

## Spectral + level evidence

The directional spectral/level components are:

```text
spectral_level_evidence_a_over_b
spectral_level_evidence_b_over_a
```

Conceptually:

```text
relative_spectral_overlap * directional_level_weight
```

They remain heuristic evidence.

## Temporal contribution

When enough V0.6 history exists, the same ERB region is measured across aligned Analyzer frames.

V0.7 uses:

```text
coactive_ratio
band_envelope_correlation
normalized_band_temporal_overlap
```

`normalized_band_temporal_overlap` indicates whether both tracks frequently occupy relatively strong states in the same region at aligned times.

The combined directional evidence is:

```text
spectral_level_evidence * (0.25 + 0.75 * temporal_overlap)
```

This formula deliberately leaves some spectral/level evidence when temporal overlap is low while giving greater weight to real co-occurrence.

The formula is an engineering heuristic and is returned explicitly in `evidence_formula` so the model can audit it.

If temporal overlap is unavailable, combined evidence may be `null`; use the spectral/level components instead and state that temporal support was unavailable.

## `dominant_direction`

A region may return:

```text
a_over_b
b_over_a
```

This means the current measured evidence is stronger in that direction.

It does **not** mean the dominant track is wrong, should be reduced, or should be processed.

## `masking_evidence_score`

This is a compact summary derived from the strongest returned regions.

Use it to:

- rank candidate track pairs within the same project/window;
- choose which pair deserves a detailed query;
- compare evidence before/after under controlled conditions.

Do not use it as:

- a universal pass/fail threshold;
- an audible-masking probability;
- a mix-quality score.

## Alignment quality

Pairwise temporal evidence depends on independent OSC streams being aligned.

Inspect:

```text
alignment.tolerance_ms
alignment.aligned_pairs
alignment.mean_abs_offset_ms
temporal_usable_pairs
```

Sparse or poorly aligned data should reduce confidence.

## Active coverage

Also inspect:

```text
active_ratio_a
active_ratio_b
```

A five-second request with low active coverage does not represent five seconds of continuous interaction.

## Relationship to older tools

### `audio_detect_masking()`

Older spectrum-only heuristic. Useful for quick compatibility and coarse candidate detection.

### `audio_temporal_compare()`

V0.6 custom-band temporal relation. Useful when the user wants a specific frequency range or more direct envelope/correlation evidence.

### `audio_masking_evidence()`

V0.7 detailed two-track region model. Preferred for current masking-related pair evidence.

### `audio_project_masking_scan()`

V0.7 project-level ranking. Preferred for discovering which pairs deserve deeper inspection.

## Recommended wording

Good:

> In the 180–310 Hz ERB region, the two tracks have relatively strong spectral coexistence and high temporal overlap; the current directional evidence is stronger from A toward B. This is a candidate interaction region, not proof of audible masking.

Avoid:

> A is definitely masking B, so cut A by 3 dB.

The second statement adds a certainty and processing prescription that the Analyzer did not measure.
