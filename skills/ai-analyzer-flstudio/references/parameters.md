# AI Audio Analyzer Parameter Semantics Reference

This reference explains technical meaning, validity, and common misreadings. It does **not** prescribe a mixing, mastering, harmony, arrangement, tuning, or processing action.

## Adaptive Analysis / performance

### `Analysis Profile` host parameter

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

This changes Analyzer computation only. It does not process the audio or define an artistic mode.

`Full` is the default for backward compatibility.

### `analysis_profile` / `analysis_profile_index`

Bridge-reported active profile name/index received from the VST3 telemetry tail. Use this to verify what the Analyzer instance is actually computing after the DAW-control MCP changes the host parameter.

### `analysis_feature_mask`

Bit mask describing enabled analysis groups:

```text
1   Core
2   Loudness
4   Spectrum
8   Stereo
16  Temporal
32  Semantic
```

The feature mask is authoritative for adaptive-analysis frames. Append-only OSC compatibility positions remain present even when a feature family is disabled; disabled values are converted to unavailable state by the Bridge.

### `analysis_features`

Decoded Boolean map of the feature mask:

```text
core
loudness
spectrum
stereo
temporal
semantic
```

### `worker_load_ratio`

Approximate fraction of elapsed monitoring time spent doing work inside the Analyzer **background analysis worker**.

It is not:

```text
DAW realtime audio-thread CPU
whole-plugin CPU percentage
system CPU percentage
dropout probability
```

Use as relative implementation telemetry, especially when comparing profiles on the same environment.

### `fifo_fill_ratio`

Fraction of the preallocated SPSC input FIFO currently queued.

A transient nonzero value is normal. Sustained growth or high fill indicates that the analysis worker may be falling behind incoming audio, so measurement timing can become stale.

### `fft_runs_per_second`

Observed number of internal FFT executions per second over the recent telemetry interval.

Expected scheduling character:

```text
Eco       approximately 0
Balanced  reduced, approximately network-update scale
Mix       hop-level FFT
Full      hop-level FFT
```

Actual rate also depends on sample rate, transport/audio flow, scheduling, and measurement state.

### `semantic_runs_per_second`

Observed Chroma/single-F0 semantic-analysis executions per second.

It should be approximately zero when Semantic is disabled. Full intentionally runs semantic work at a lower rate than hop-level FFT.

Detailed usage: `performance-evidence.md`.

## Signal / validity

### `signal_present`

Boolean indicating whether the Analyzer currently considers the input active.

Approximate detector behavior:

```text
close   below -50 dBFS for ~0.4 s
reopen  above -48 dBFS
```

### `detector_peak_db`

Current detector peak in dBFS. It is not RMS, LUFS, or True Peak.

### `silence_seconds`

Continuous time accumulated under the gate's silence condition.

### `analysis_valid`

Whether a returned window/summary contains usable active measurement data.

### `active_frames`

Number of active analysis frames in a requested window.

### `active_ratio`

Fraction of requested frames considered active. It is time coverage, not loudness or confidence.

### `null`

`null` means unavailable. Never reinterpret it as numeric zero.

Adaptive-profile rule: if the required feature group is disabled, its fields are unavailable even though append-only protocol positions physically exist.

## Level / dynamics

### `peak_db`

Sample Peak in dBFS. Not True Peak.

### `rms_db`

RMS level in dBFS. Not LUFS.

### `crest_db`

Approximate:

```text
Peak - RMS
```

Descriptive only; not a quality score.

## Loudness

Requires the Loudness feature group (`Balanced` or higher).

### `lufs_s`

Short-Term LUFS, approximately a 3-second time scale. May become unavailable after sustained silence.

### `lufs_i`

Integrated LUFS accumulated during the Analyzer loudness session using EBU R128 gating.

It does not automatically represent the whole song unless the whole program was measured in the relevant session. Snapshot/verification windows do not independently reset LUFS-I.

### `true_peak_dbtp`

Current True Peak estimate in dBTP.

### `max_true_peak_dbtp`

Maximum True Peak observed during the current Analyzer loudness session/reset state.

## Spectrum

Requires Spectrum (`Balanced` or higher).

### `bands_db`

32 log-spaced 20 Hz–20 kHz FFT-derived **Mid-spectrum** machine features.

Underlying signal:

```text
Mid = (L + R) / 2
```

Useful for spectral-shape comparison; not calibrated SPL.

### `spectral_regions`

Project-level broad groups such as sub/low-mid/mid/presence/high. These are organizational summaries, not automatic problem labels.

### `centroid_hz`

Frequency-weighted center of spectral magnitude. Descriptive, not better/worse.

### `rolloff_hz`

Approximately the frequency below which ~85% of measured spectral power accumulates.

### `flatness`

Spectral Flatness describing concentrated/tonal versus distributed/noise-like shape. Not distortion or quality.

## Stereo / Mid-Side

Requires Stereo (`Balanced` or higher).

### `stereo_correlation`

Full-band L/R correlation:

```text
+1  highly similar
 0  weak linear relation
-1  strongly anti-correlated
```

Not a quality score and not a Side-energy measurement.

### `stereo_width`

Historical ratio-style scalar based on Side RMS / Mid RMS, retained for compatibility. Prefer explicit `side_to_mid_db` for energy-ratio semantics.

### `band_stereo_correlation`

Eight correlation regions:

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

### `mid_rms_db` / `side_rms_db`

RMS of:

```text
Mid  = (L + R) / 2
Side = (L - R) / 2
```

### `side_to_mid_db`

```text
10 * log10(Side power / Mid power)
```

Equivalent to `20 * log10(Side RMS / Mid RMS)`.

No universal target is defined.

### `negative_cross_energy_ratio`

Range approximately `0..1`. Weighted fraction of bilateral FFT evidence whose real L/R cross-spectrum is negative.

It is phase-opposition evidence, not:

```text
phase-angle histogram
sample-sign ratio
mono-cancellation percentage
audibility probability
quality score
```

### `low_band_20_120_correlation`

Signed L/R correlation over approximately 20–120 Hz.

### `low_band_20_120_side_to_mid_db`

Integrated Side/Mid power relation over approximately 20–120 Hz. Not a mono-compatibility pass/fail result.

### `side_bands_db`

32 log-spaced Side-spectrum machine features using the same centers as `bands_db`.

### `band_side_to_mid_db`

Eight integrated Side/Mid power ratios over the same regions as band correlation.

### `decorrelation_proxy_mean`

Derived by stereo profile:

```text
1 - abs(stereo_correlation)
```

Both `+1` and `-1` correlation produce a value near zero. Read it with the correlation sign. It is not perceptual spaciousness.

## Temporal

Requires Temporal (`Mix` or `Full`).

### `temporal_supported`

Whether the plugin/frame supports the temporal append-only fields.

### `temporal_valid`

Whether temporal evidence is usable in the current frame/window. A supported feature can still be invalid due to profile state, silence, or insufficient data.

### `temporal_window_seconds`

Internal analysis time represented by the current temporal aggregate. Do not assume it is always exactly 0.1 s.

### `spectral_flux_mean`

Mean positive redistribution in normalized spectral shape across adjacent internal FFT windows. It emphasizes spectral change rather than simple gain scaling.

### `spectral_flux_peak`

Largest normalized spectral-flux value in the aggregate. Change evidence, not proof of a musical onset.

### `rms_rise_peak_db`

Largest positive adjacent-window RMS increase in dB. Not Crest Factor or attack time.

### `low_band_energy_db`

FFT-derived approximately 40–160 Hz energy feature. Not calibrated SPL and does not identify an instrument.

### Onset/change candidates

Current temporal profile derives heuristic candidates using thresholds such as RMS rise or spectral flux. They are not annotated onset ground truth, BPM, or note density.

### `band_envelope_correlation`

Pearson correlation of aligned selected-band energy envelopes. Describes co-variation, not which source should be changed.

### `normalized_band_temporal_overlap`

Relative simultaneous occupancy after each source's selected-band envelope is normalized. Not a masking probability.

### `alignment_tolerance_ms` / `mean_abs_alignment_offset_ms`

Requested timestamp-alignment tolerance and actual mean mismatch. Large offsets weaken timing conclusions.

## Masking evidence

Spectrum is required; Temporal strengthens the interaction evidence when enabled.

Detailed model: `masking-evidence.md`.

### `auditory_band_model.type`

Current model:

```text
equal-erb-rate-rebinning
```

Existing 32 Analyzer spectrum features are re-binned into 16 equal ERB-rate regions.

### `auditory_band_model.filterbank`

```text
false
```

This is not a gammatone/cochlear filterbank.

### `relative_spectral_overlap`

Relative coexistence after normalizing each source to its own strongest region. Not audible probability.

### `level_delta_a_minus_b_db`

```text
a_db - b_db
```

Positive means A is numerically stronger in that region.

### Directional / combined evidence

Directional level weights and temporal overlap are combined transparently for candidate ranking. They remain heuristic evidence, not automatic EQ/sidechain instructions.

### `masking_evidence_score`

Compact ranking summary. Not a probability of audible masking, pass/fail result, or mix-quality score.

## Tonal / music-semantic evidence

Requires Semantic (`Full`). Detailed interpretation: `tonal-evidence.md`.

### `chroma`

Twelve normalized Mid-spectrum pitch-class power bins:

```text
C C# D D# E F F# G G# A A# B
```

Approximate analysis band:

```text
80 Hz–5 kHz
```

FFT frequencies map to nearest 12-TET pitch class and octave information is collapsed.

Chroma is not note probability, MIDI transcription, note count, or chord-membership probability.

### `chroma_energy_ratio`

Fraction/context describing how much measured Mid-spectrum power lies in the chroma-analysis range. Not correctness probability.

### `normalized_pitch_class_entropy`

Approximate distribution concentration:

```text
0  more concentrated
1  more uniform
```

Not quality, consonance, complexity, or confidence by itself.

### Tonal-center candidates

Aggregated chroma is compared against 24 major/minor Krumhansl-Kessler templates using Pearson correlation.

`profile_correlation` is template similarity, not key probability.

### `top2_margin`

```text
best profile correlation - second-best profile correlation
```

Candidate separation within the template set, not calibrated confidence.

### `single_f0_harmonic_energy_ratio`

Single-F0 spectral harmonic-alignment heuristic. Not probability that the source is harmonic, source separation, pitch confidence, note confidence, or quality.

### `harmonic_f0_candidate_hz`

Candidate fundamental used by the heuristic. It can octave/subharmonic-jump, especially for polyphonic/noisy/inharmonic material. Do not directly convert it to a note and claim note detection.

### Pitch-class comparison

Cosine similarity / Jensen-Shannon divergence describe distribution similarity/difference, not harmonic compatibility, consonance, correctness, or required editing.

When exact DAW/MIDI note/key/chord/tuning data exists, prefer it for exact symbolic claims.

## Identity / topology

### `runtime_id`

Live plugin-instance UUID. Session-scoped, not a permanent project identifier.

### Analyzer name

Human-readable name. It may be duplicated and is not guaranteed unique.

### `binding`

Deterministic runtime UUID ↔ FL Studio host-location relation:

```text
fl_track_index
fl_track_name
slot
runtime_id
```

### Preferred selector

```text
mixer:<track_index>/slot:<slot>
```

### `age_seconds` / stale state

Time/freshness of the latest Bridge frame. Stale values are not current state.

## Snapshot A/B

### `audio_capture_snapshot(name, seconds)`

Stores a project-level recent measurement state in the current Bridge session.

### `audio_compare_snapshots(before, after)`

Delta convention:

```text
After - Before
```

Check passage, window, active coverage, and relevant Analysis Profile/feature availability before strong interpretation.

## Controlled verification

Detailed semantics: `verification-evidence.md`.

### `ready_for_external_change`

Whether the Before baseline passed current workflow checks. Not a statement that the planned change is artistically appropriate.

### `baseline_blockers`

Reasons a Before baseline should be corrected/restarted before an externally controlled change.

### topology fingerprint

Live Analyzer identity/binding consistency marker. Not a complete persistent DAW-project hash.

### `controlled_comparison`

Technical comparability gate. Current guardrails include baseline readiness, same window duration, stable live Analyzer topology, requested target presence/validity, and active-ratio comparability.

It does not mean After is better/correct/preferred.

### `closed_loop_complete`

True only when the measurement comparison is controlled **and** caller-supplied actual host readback is present.

Still not an artistic quality judgment.

### `host_readback`

Text supplied from the external DAW-control MCP's actual post-write readback. Analyzer stores it but does not independently validate the host state.
