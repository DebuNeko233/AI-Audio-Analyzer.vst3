# AI Audio Analyzer Parameter Semantics Reference

This reference explains technical meaning, validity, and common misreadings. It does **not** prescribe a mixing, mastering, harmony, arrangement, tuning, or processing action.

## Signal / validity

### `signal_present`

Boolean indicating whether the Analyzer currently considers the input valid.

Approximate detector behavior:

```text
close   below -50 dBFS for ~0.4 s
reopen  above -48 dBFS
```

When false, content-dependent spectrum/stereo/temporal/semantic fields are unavailable.

### `detector_peak_db`

Current detector peak in dBFS. It is a gate-state measurement, not RMS, LUFS, or True Peak.

### `silence_seconds`

Continuous time accumulated below the gate's closing condition.

### `analysis_valid`

Whether a window/summary contains usable active frames for content analysis.

### `active_frames`

Number of valid active analysis frames in a requested window.

### `active_ratio`

Fraction of requested frames considered active. It is time coverage, not loudness or confidence.

### `null`

`null` means no valid/available measurement for that field. Never reinterpret it as numeric zero.

## Level / dynamics

### `peak_db`

Sample Peak in dBFS. It measures discrete sample amplitude and is not True Peak.

### `rms_db`

RMS level in dBFS. It is an energy statistic and is not LUFS.

### `crest_db`

Approximate peak-to-average relation:

```text
Crest ≈ Peak - RMS
```

It is descriptive, not a quality score.

### `true_peak_dbtp`

Current True Peak estimate in dBTP.

### `max_true_peak_dbtp`

Maximum True Peak observed since the current Analyzer session/reset state began. It is session cumulative.

## Loudness

### `lufs_s`

Short-Term LUFS, roughly a 3-second time scale. It may become unavailable after sustained silence.

### `lufs_i`

Integrated LUFS accumulated since the Analyzer loudness state was reset/prepared, using EBU R128 gating.

It does not automatically represent an entire song unless the entire program has been measured in that session. Snapshot A/B does not independently reset LUFS-I for each snapshot.

## Spectrum

### `bands_db`

32 log-spaced 20 Hz–20 kHz FFT-derived **Mid-spectrum** machine features in dB-like relative level units.

The underlying signal is:

```text
Mid = (L + R) / 2
```

Useful for spectral-shape comparison; not calibrated SPL.

### `spectral_regions`

Project-level broad-band summaries:

```text
sub_20_120_db
low_mid_120_500_db
mid_500_2000_db
presence_2000_5000_db
high_5000_20000_db
```

These are organizational labels, not automatic tonal-problem labels.

### `centroid_hz`

Frequency-weighted center of spectral magnitude. Higher/lower is descriptive, not inherently better/worse.

### `rolloff_hz`

Approximately 85% spectral rolloff: the frequency below which about 85% of spectral power is accumulated.

### `flatness`

Spectral Flatness describing concentrated/tonal versus distributed/noise-like spectral shape. It is not distortion or quality.

## Legacy stereo measurements

### `stereo_correlation`

Full-band L/R correlation:

```text
+1  highly similar L/R
 0  weak linear relation
-1  strongly anti-correlated
```

It is a statistical relation, not a good/bad score.

### `stereo_width`

Legacy ratio-style scalar:

```text
Side RMS / Mid RMS
```

It is clamped for historical continuity. Prefer V0.8 `side_to_mid_db` for explicit energy-ratio semantics.

### `band_stereo_correlation`

Eight L/R correlation regions:

```text
20–60 Hz
60–120 Hz
120–250 Hz
250–500 Hz
500 Hz–1 kHz
1–2 kHz
2–5 kHz
5–20 kHz
```

Very low-energy bands should not be overinterpreted.

## V0.6 temporal measurements

### `temporal_supported`

Whether the frame contains the V0.6 append-only temporal tail.

### `temporal_valid`

Whether temporal descriptors are valid, typically requiring active signal and nonzero temporal coverage.

### `temporal_window_seconds`

Internal analysis time represented by the current emitted temporal aggregate. Do not hard-code it as exactly 0.1 s.

### `spectral_flux_mean`

Mean positive change in normalized spectral distribution across adjacent internal FFT windows. It emphasizes spectral redistribution rather than simple gain scaling.

### `spectral_flux_peak`

Largest normalized spectral-flux value within the emitted aggregate. It is change evidence, not proof of a musical onset.

### `rms_rise_peak_db`

Largest positive adjacent-window RMS increase in dB. It is rapid level-rise evidence, not Crest Factor or attack time.

### `low_band_energy_db`

FFT-derived 40–160 Hz energy feature. It is not calibrated SPL and does not identify an instrument.

### `onset_candidate_frames`

Threshold-based change candidates returned by `audio_temporal_profile()`.

Current defaults:

```text
rms_rise_peak_db >= 3.0
OR
spectral_flux_peak >= 0.18
```

These are not annotated onset ground truth.

### `onset_candidate_density_hz`

Candidate count divided by temporally valid observed seconds. It is not BPM or note density.

### `band_envelope_correlation`

Pearson correlation of aligned selected-band energy envelopes. It describes co-variation, not which source should be changed.

### `normalized_band_temporal_overlap`

Average relative simultaneous occupancy after each source's selected-band envelope is normalized to its own peak. It is not a masking probability.

### `coactive_ratio`

Fraction of aligned frames where both sources report active signal.

### `alignment_tolerance_ms` / `mean_abs_alignment_offset_ms`

Alignment tolerance and actual mean timestamp mismatch. Large offsets weaken timing conclusions.

## V0.7 masking-evidence measurements

Detailed model notes are in `masking-evidence.md`.

### `auditory_band_model.type`

Current value:

```text
equal-erb-rate-rebinning
```

Existing 32 Analyzer spectrum features are re-binned into 16 equal ERB-rate regions.

### `auditory_band_model.filterbank`

Current value:

```text
false
```

This is not a gammatone/cochlear filterbank.

### `source_feature_count`

Number of original spectrum feature centers contributing to the ERB region.

### `a_db` / `b_db`

Power-domain mean of source Analyzer spectral features in the ERB region. Machine-feature levels, not SPL.

### `level_delta_a_minus_b_db`

```text
a_db - b_db
```

Positive means A is stronger in that region; negative means B is stronger.

### `relative_spectral_overlap`

Each source is normalized to its own strongest ERB-region power; regional overlap uses the minimum. It describes relative spectral coexistence, not audibility.

### `level_direction_weight_a_over_b` / `...b_over_a`

Bounded logistic descriptors from regional relative level. They are not probabilities or hearing thresholds.

### `spectral_level_evidence_*`

Transparent combination of relative spectral overlap and directional level weighting.

### `combined_evidence_*`

When temporal overlap exists, spectral/level evidence is weighted by temporal co-occupancy. This is still heuristic evidence.

### `dominant_direction`

Which direction currently has stronger measured evidence. It is not a processing instruction.

### `masking_evidence_score`

Compact candidate-ranking summary. It is not audible-masking probability, universal pass/fail, or mix-quality score.

### `evidence_formula`

Machine-readable description of the heuristic formula so downstream interpretation remains auditable.

### `spectral_overlap_score` / `audio_detect_masking()`

Older spectrum-only heuristics. Prefer `audio_masking_evidence()` for stronger current evidence, but neither is an audible-masking probability.

## V0.8 Mid/Side and stereo measurements

Detailed notes are in `stereo-evidence.md`.

### `stereo_v08_supported`

Whether the current frame contains the V0.8 append-only stereo tail.

### `stereo_v08_valid`

Whether V0.8 fields are valid for the current frame. Active signal is required.

### `mid_rms_db`

RMS of:

```text
Mid = (L + R) / 2
```

### `side_rms_db`

RMS of:

```text
Side = (L - R) / 2
```

### `side_to_mid_db`

```text
10 * log10(Side power / Mid power)
```

Equivalent to `20 * log10(Side RMS / Mid RMS)`.

```text
negative → Mid power exceeds Side
0        → equal Mid and Side power
positive → Side power exceeds Mid
```

No universal target is defined.

### `negative_cross_energy_ratio`

Range `0..1`. Weighted fraction of bilateral FFT-bin evidence whose real L/R cross-spectrum is negative.

This is phase-opposition evidence, not phase-angle histogram, sample-sign ratio, mono-cancellation percentage, audibility probability, or quality score.

### `low_band_20_120_correlation`

Signed L/R correlation over approximately 20–120 Hz.

### `low_band_20_120_side_to_mid_db`

Integrated Side/Mid power relation over approximately 20–120 Hz. Not a mono-compatibility pass/fail score.

### `side_bands_db`

32 log-spaced Side-spectrum machine features using the same centers as `bands_db`.

### `band_side_to_mid_db`

Eight integrated Side/Mid power ratios using the same regions as band stereo correlation.

### `decorrelation_proxy_mean`

Derived by `audio_stereo_profile()`:

```text
1 - abs(stereo_correlation)
```

Both `+1` and `-1` correlation yield a value near zero. Read it with correlation sign. It is not perceptual spaciousness.

### `mid_spectrum_db` / `side_spectrum_db`

Window-averaged Mid/Side spectral feature arrays.

### `frequency_dependent_stereo`

Eight regions, each containing `range`, `correlation`, and `side_to_mid_db`. Correlation and Side/Mid answer different questions.

## V0.9 tonal / music-semantic measurements

Detailed interpretation is in `tonal-evidence.md`.

### `semantic_v09_supported`

Whether the current frame contains the append-only V0.9 music-semantic tail.

Older plugins can still provide all previous measurements while this is false/absent.

### `semantic_v09_valid`

Whether V0.9 chroma evidence is valid for the current frame. Current requirements include active input plus nonzero usable chroma-range energy.

### `chroma`

Twelve normalized Mid-spectrum pitch-class power bins in fixed order:

```text
C C# D D# E F F# G G# A A# B
```

Analysis range is approximately:

```text
80 Hz – 5 kHz
```

FFT-bin frequencies are mapped to the nearest 12-TET pitch class and accumulated in the power domain; octave identity is collapsed.

It is **not** note probability, MIDI transcription, note count, chord-membership probability, or note confidence.

### `chroma_pitch_class_order`

Explicit pitch-class order accompanying the vector. Do not assume a different ordering.

### `chroma_energy_ratio`

Per-frame fraction of Analyzer Mid-spectrum power represented inside the chroma analysis range relative to the wider spectral analysis power.

Use as coverage context. It is not probability that the chroma is correct.

Windowed `audio_tonal_profile()` exposes:

```text
evidence_quality.mean_chroma_energy_ratio
```

### `chroma.normalized_entropy` / `normalized_pitch_class_entropy`

Normalized Shannon entropy of the 12-bin distribution:

```text
approximately 0 → more concentrated pitch-class power
approximately 1 → more uniformly distributed pitch-class power
```

It is not quality, consonance, complexity, or confidence by itself.

### `tonal_center_evidence.method`

Current method:

```text
Krumhansl-Kessler major/minor profile Pearson correlation
```

The aggregated chroma is compared with 24 templates: 12 tonics × major/minor.

### `profile_correlation`

Pearson correlation between aggregated chroma shape and one tonal template. This is template similarity, not probability.

Do not report a value such as `0.82` as “82% probability”.

### `tonal_center_evidence.top_candidates`

Highest-ranking major/minor template correlations. The first candidate is the strongest current template match, **not a ground-truth key label**.

Short, modal, chromatic, changing, sparse, percussion-heavy, atonal, or mixed-source passages can be ambiguous.

### `tonal_center_evidence.top2_margin` / `tonal_center_top2_margin`

```text
best profile correlation - second-best profile correlation
```

Larger means stronger separation between the two top candidates within this 24-template set. It is not calibrated confidence probability and has no universal threshold.

### `single_f0_harmonic_energy_ratio`

Single-F0 spectral harmonic-alignment heuristic. The plugin searches a candidate fundamental approximately within `55–1000 Hz` and evaluates spectral energy near up to eight integer harmonics.

It is not:

- probability that the source is harmonic;
- calibrated harmonic-to-noise ratio;
- harmonic/percussive source separation;
- pitch-tracker confidence;
- note/chord confidence;
- quality score.

### `harmonic_f0_candidate_hz`

Candidate fundamental used by the single-F0 heuristic.

It can octave/subharmonic-jump or reflect a common divisor in polyphonic material. Do not convert it directly to a note label and claim that note was detected.

Windowed outputs expose median/min/max candidate Hz to show stability over time.

### `pitch_class_comparison.cosine_similarity`

Cosine similarity between two normalized chroma vectors. Higher means more similar pitch-class distribution; it does not prove harmonic compatibility or consonance.

### `pitch_class_comparison.jensen_shannon_divergence`

Symmetric distribution divergence, implementation-bounded approximately to `0..1`. Lower means more similar distributions; higher means more different. Not music-theory correctness.

### `pitch_class_comparison.normalized_power_delta_b_minus_a`

Twelve pitch-class deltas:

```text
B - A
```

They describe normalized distribution differences only and do not imply note/harmony/tuning/arrangement edits.

### Exact symbolic data rule

If exact note events, key metadata, chords, or tuning data are available through DAW/MIDI/project tools, prefer those sources for exact symbolic claims. V0.9 remains an audio-domain inference layer.

## Identity / topology

### `id` / `runtime_id`

Live plugin-instance UUID. Session-scoped, not a permanent project identifier.

### `track` / `analyzer_name`

Human-readable Analyzer name. It can be duplicated and is not guaranteed unique.

### `binding`

V0.4 deterministic runtime UUID ↔ FL Studio host location relation:

```text
fl_track_index
fl_track_name
slot
runtime_id
```

### `selector`

Preferred deterministic selector after binding:

```text
mixer:<track_index>/slot:<slot>
```

## Freshness

### `age_seconds`

Time since the Bridge received the latest frame from that instance.

### `stale`

Whether data exceeds the Bridge freshness threshold. Stale values are not current state.

### `duplicate_name`

Another live Analyzer shares the display name. Use deterministic binding selector or runtime UUID.

## Snapshot A/B

### `audio_capture_snapshot(name, seconds)`

Stores a project-level recent measurement state in the current Bridge session only.

### `audio_compare_snapshots(before, after)`

Delta convention:

```text
Delta = After - Before
```

Check passage comparability, window length, and `active_ratio` before interpretation.
