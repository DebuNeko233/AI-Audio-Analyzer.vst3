# AI Audio Analyzer Parameter Semantics Reference

This reference explains technical meaning, validity, and common misreadings. It does **not** prescribe a mixing style or processing action.

## Signal / validity

### `signal_present`

Boolean indicating whether the Analyzer currently considers the input valid.

Approximate detector behavior:

```text
close   below -50 dBFS for ~0.4 s
reopen  above -48 dBFS
```

When false, content-dependent spectrum/stereo fields are unavailable.

### `detector_peak_db`

Current detector peak in dBFS. It is a gate-state measurement, not RMS, LUFS, or True Peak.

### `silence_seconds`

Continuous time accumulated below the gate's closing condition.

### `analysis_valid`

Whether a window/summary contains usable active frames for content analysis.

### `active_frames`

Number of valid active analysis frames in a requested window.

### `active_ratio`

Fraction of requested frames considered active:

```text
0.0 → no valid input
1.0 → all frames active
```

It is time coverage, not loudness or confidence.

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

Maximum True Peak observed since the Analyzer's current session/reset state began. It is session cumulative.

## Loudness

### `lufs_s`

Short-Term LUFS, roughly a 3-second time scale. It may become unavailable after sustained silence.

### `lufs_i`

Integrated LUFS accumulated since the Analyzer's loudness state was reset/prepared, using EBU R128 gating.

It does not automatically represent an entire song unless the entire program has been measured in that session.

For short Snapshot A/B, LUFS-I is not independently reset for each snapshot.

## Spectrum

### `bands_db`

32 log-spaced 20 Hz–20 kHz FFT-derived **Mid-spectrum** machine features in dB-like relative level units.

The field predates explicit V0.8 Mid/Side naming, but the underlying implementation has historically used:

```text
Mid = (L + R) / 2
```

They are useful for spectral shape comparisons but are not calibrated SPL.

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

Spectral Centroid: a frequency-weighted center of spectral magnitude. Higher/lower is descriptive, not inherently better/worse.

### `rolloff_hz`

Current implementation uses approximately 85% spectral rolloff: the frequency below which about 85% of spectral power is accumulated.

### `flatness`

Spectral Flatness, describing whether a spectrum is more concentrated/tonal or more distributed/noise-like. It is not a distortion or quality score.

## Legacy stereo measurements

### `stereo_correlation`

Full-band L/R correlation, approximately:

```text
+1  highly similar L/R
 0  weak linear correlation
-1  strongly anti-correlated
```

It is a statistical relation, not a good/bad score.

### `stereo_width`

Legacy Mid/Side RMS ratio-style measurement:

```text
Side RMS / Mid RMS
```

The plugin clamps this legacy scalar to a bounded range for continuity. V0.8 `side_to_mid_db` is the clearer unambiguous energy-ratio representation for detailed analysis.

### `band_stereo_correlation`

Eight band-limited L/R correlation values:

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

## V0.8 Mid/Side and stereo measurements

Detailed interpretation notes are in `stereo-evidence.md`.

### `stereo_v08_supported`

Whether the current frame contains the append-only V0.8 stereo tail.

Older VST3 versions can still expose legacy correlation/width fields while this is false or absent.

### `stereo_v08_valid`

Whether the V0.8 fields are valid for the current frame. Active signal is required.

### `mid_rms_db`

RMS level of:

```text
Mid = (L + R) / 2
```

in Analyzer dBFS-like units.

### `side_rms_db`

RMS level of:

```text
Side = (L - R) / 2
```

Higher/lower Side RMS describes difference energy, not quality.

### `side_to_mid_db`

Side/Mid energy relation:

```text
10 * log10(Side power / Mid power)
```

Equivalent form:

```text
20 * log10(Side RMS / Mid RMS)
```

Interpretation:

```text
negative → Mid energy exceeds Side
0        → equal Mid and Side energy
positive → Side energy exceeds Mid
```

There is no universal target.

### `negative_cross_energy_ratio`

Range `0..1`.

For each FFT bin, the plugin computes the real L/R cross-spectrum. Bins with a negative real cross term contribute to the numerator, weighted by bilateral L/R spectral energy.

This is **phase-opposition evidence**. It is not:

- a phase-angle histogram;
- a sample-sign ratio;
- a mono-cancellation percentage;
- an audibility probability;
- a quality score.

### `low_band_20_120_correlation`

Aggregate L/R correlation over approximately `20-120 Hz` FFT content.

It describes signed low-frequency channel relation. Very low-energy low bands should not be overinterpreted.

### `low_band_20_120_side_to_mid_db`

Integrated Side/Mid power relation over approximately `20-120 Hz`.

It is low-frequency difference/common energy evidence, not an automatic mono-compatibility pass/fail score.

### `side_bands_db`

32 log-spaced Side-spectrum features using the same center frequencies as `bands_db`.

They represent:

```text
Side = (L - R) / 2
```

and are FFT-derived machine features, not calibrated SPL.

### `band_side_to_mid_db`

Eight integrated Side/Mid power ratios using the same frequency regions as `band_stereo_correlation`.

Read each ratio together with the corresponding signed correlation; they answer different questions.

### `decorrelation_proxy_mean`

Returned by `audio_stereo_profile()` as the transparent derived quantity:

```text
1 - abs(stereo_correlation)
```

Range is approximately `0..1`.

Important: both correlation `+1` and `-1` produce a proxy near `0`. Therefore this field must be read with correlation **sign** and negative-cross evidence.

It is a mathematical proxy, not perceptual spaciousness.

### `mid_spectrum_db` / `side_spectrum_db`

Window-averaged spectrum arrays returned by `audio_stereo_profile()`.

`mid_spectrum_db` is derived from historical `bands_db`; `side_spectrum_db` is derived from V0.8 `side_bands_db`.

### `frequency_dependent_stereo`

V0.8 profile output with eight regions. Each region contains:

```text
range
correlation
side_to_mid_db
```

Correlation describes signed L/R relation. Side/Mid dB describes difference/common energy distribution.

## V0.6 temporal measurements

V0.6 computes temporal descriptors at the internal 1024-sample analysis hop and aggregates them into the ~10 Hz OSC stream.

### `temporal_supported`

Whether the current Analyzer frame includes the V0.6 temporal tail.

### `temporal_valid`

Whether temporal descriptors are valid for the current frame, typically requiring active signal and nonzero temporal coverage.

### `temporal_window_seconds`

Internal analysis time represented by the current emitted temporal aggregate. Do not hard-code it as exactly 0.1 seconds.

### `spectral_flux_mean`

Mean positive change in normalized spectral distribution across adjacent internal FFT windows.

Near zero means less redistribution; higher values mean stronger spectral change. Because spectra are normalized, this is deliberately less sensitive to pure gain scaling than RMS change.

### `spectral_flux_peak`

Largest normalized spectral-flux value within the current emitted aggregate.

It is change evidence, not proof of a ground-truth musical onset.

### `rms_rise_peak_db`

Largest positive adjacent-window RMS increase inside the current temporal aggregate, in dB.

It is rapid level-rise evidence, not Crest Factor and not attack-time estimation.

### `low_band_energy_db`

VST3 temporal-tail feature representing FFT-derived 40–160 Hz energy. It is not calibrated SPL and does not identify a specific instrument.

### `onset_candidate_frames`

Threshold-based change candidates in `audio_temporal_profile()`.

Current default rule:

```text
rms_rise_peak_db >= 3.0
OR
spectral_flux_peak >= 0.18
```

The thresholds are returned with the result. These are not annotated onset ground truth.

### `onset_candidate_density_hz`

Candidate frame count divided by temporally valid observed seconds. It is not BPM or note density.

### `band_envelope_correlation`

Pearson correlation of two time-aligned selected-band energy envelopes:

```text
+1 → tend to move together
 0 → weak linear co-variation
-1 → tend to move oppositely
```

It does not say which source should be changed.

### `normalized_band_temporal_overlap`

Each track's selected-band envelope is normalized relative to its own peak over the compared history; aligned points use the minimum relative power and are averaged.

Higher values mean stronger simultaneous relative occupancy. It is not a masking probability.

### `coactive_ratio`

Fraction of aligned frames in which both tracks report active signal.

### `alignment_tolerance_ms`

Maximum allowed timestamp separation when aligning independent Analyzer streams.

### `mean_abs_alignment_offset_ms`

Mean absolute timestamp mismatch of aligned frame pairs. Large offsets reduce the strength of timing conclusions.

## V0.7 masking-evidence measurements

Detailed model notes are in `masking-evidence.md`.

### `auditory_band_model.type`

Current value:

```text
equal-erb-rate-rebinning
```

The Bridge re-bins existing 32 Analyzer spectrum features into 16 equal ERB-rate regions.

### `auditory_band_model.filterbank`

Current value:

```text
false
```

The implementation is **not** a gammatone/cochlear filterbank.

### `source_feature_count`

Number of original 32-band Analyzer feature centers that contributed to the ERB region.

### `a_db` / `b_db`

Power-domain mean of the original Analyzer spectral features assigned to that ERB region.

These are machine-feature levels, not SPL.

### `level_delta_a_minus_b_db`

```text
a_db - b_db
```

Positive means A is stronger in the region; negative means B is stronger.

### `relative_spectral_overlap`

Both tracks are independently normalized to their own strongest ERB-region power, then the regional minimum is used.

It describes whether the region is relatively important to both sources.

### `level_direction_weight_a_over_b`

Bounded logistic weighting from the regional A-minus-B level difference using a 6 dB scale.

It is a directional descriptor, not a masking probability or hearing threshold.

### `level_direction_weight_b_over_a`

Complementary directional weight for B over A.

### `spectral_level_evidence_a_over_b` / `...b_over_a`

Conceptually:

```text
relative_spectral_overlap * level_direction_weight
```

These are transparent heuristic components.

### `combined_evidence_a_over_b` / `...b_over_a`

When V0.6 temporal overlap is available:

```text
spectral_level_evidence * (0.25 + 0.75 * normalized_band_temporal_overlap)
```

If temporal overlap is unavailable, these may be `null`; inspect the spectral/level evidence instead.

### `dominant_direction`

Either:

```text
a_over_b
b_over_a
```

This means the current evidence is stronger in that direction. It is not a processing instruction.

### `masking_evidence_score`

Compact summary across the strongest returned regions. Intended for relative candidate ranking within a comparable project/window.

It is **not**:

- an audible-masking probability;
- a universal pass/fail score;
- a mix-quality score.

### `evidence_formula`

Machine-readable description of the current heuristic formula. Use it to keep LLM interpretation auditable if scoring logic evolves.

## Older masking fields

### `spectral_overlap_score`

Older relative spectral-shape overlap heuristic. It does not include a calibrated auditory filterbank or complete temporal/perceptual model.

### `audio_detect_masking()`

Despite its historical name, treat it as spectrum-only candidate detection. For stronger current evidence use `audio_masking_evidence()`.

## Identity / topology

### `id` / `runtime_id`

Live plugin-instance UUID. Session-scoped, not a permanent project identifier.

### `track` / `analyzer_name`

Human-readable Analyzer name. It may be duplicated and must not be assumed unique.

### `binding`

V0.4 deterministic relationship between runtime UUID and FL Studio host location:

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

Whether data exceeds the Bridge freshness threshold. Stale values are not current real-time state.

### `duplicate_name`

Another live Analyzer shares the same display name. Use binding selector or runtime UUID.

## Snapshot A/B

### `audio_capture_snapshot(name, seconds)`

Stores a project-level recent measurement state in the current Bridge session only.

### `audio_compare_snapshots(before, after)`

Delta convention:

```text
Delta = After - Before
```

Check passage comparability, window length, and `active_ratio` before interpreting changes.

## Unified `null` rule

Whenever a field is `null`, interpret it as:

```text
no valid / available measurement for this field
```

Do not silently replace `null` with zero or infer content from it.
