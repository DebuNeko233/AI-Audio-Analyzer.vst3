# AI Audio Analyzer Parameter Semantics Reference

This document explains the technical meaning, validity, and common misinterpretations of Analyzer measurements. It does not provide style-specific mixing guidance or processing recipes.

## Signal / validity

### `signal_present`

Boolean indicating whether the Analyzer currently detects valid input.

Current detector behavior is approximately:

```text
close   < -50 dBFS for about 0.4 s
reopen  > -48 dBFS
```

When false, the Bridge may set content-dependent measurements to `null`.

### `detector_peak_db`

Current detector peak used by the signal gate, in dBFS.

It is a detector-state value, not LUFS, RMS, or True Peak.

### `silence_seconds`

Accumulated time for which input has remained below the signal-gate closing condition.

### `analysis_valid`

Indicates whether a windowed/summary result contains valid frames for content analysis.

### `active_frames`

Number of analysis frames in the requested window that were treated as valid input.

### `active_ratio`

Fraction of the requested window containing active frames:

```text
0.0 → no valid input
1.0 → all sampled frames were active
```

This describes temporal coverage. It is not a loudness value or confidence score.

## Level / dynamics

### `peak_db`

Sample Peak in dBFS. Describes the largest discrete sample amplitude in the measurement window.

It is not True Peak.

### `rms_db`

RMS level in dBFS. Describes root-mean-square signal energy over the measurement window.

It is not LUFS.

### `crest_db`

Approximate difference between peak and average energy:

```text
Crest ≈ Peak - RMS
```

The value is descriptive and is not inherently good or bad.

### `true_peak_dbtp`

Current True Peak estimate in dBTP, including inter-sample peak estimation.

### `max_true_peak_dbtp`

Maximum True Peak observed since the current Analyzer session was last reset/prepared.

This is session state, not a value limited to the most recent `audio_average()` window.

## Loudness

### `lufs_s`

Short-Term LUFS, using approximately a three-second time scale.

After sustained invalid/no input, this field may become `null`.

### `lufs_i`

Integrated LUFS accumulated since the Analyzer's most recent reset/prepare, using EBU R128 gating.

If only part of a song has been played, `lufs_i` describes only what has accumulated in the current session and must not automatically be treated as full-program integrated loudness.

For short A/B comparisons, before/after LUFS-I values are not independent reset windows.

## Spectrum

### `bands_db`

32 logarithmically distributed FFT features covering roughly 20 Hz–20 kHz.

They are intended for machine comparison of spectral shape and relative energy distribution. They are not calibrated SPL measurements.

When `signal_present=false`, this field is normally `null` through the Bridge.

### `spectral_regions`

V0.5 project tools summarize the 32-band spectrum into broad regions:

```text
sub_20_120_db
low_mid_120_500_db
mid_500_2000_db
presence_2000_5000_db
high_5000_20000_db
```

These names are frequency-range labels for organizing data. They do not imply that a region is problematic or corresponds to a fixed tonal judgment.

### `centroid_hz`

Spectral Centroid: the weighted center of the spectral magnitude distribution.

A higher or lower value describes a shift in spectral center of mass; it is not a quality score.

### `rolloff_hz`

Approximately the 85% Spectral Rolloff frequency in the current implementation: the frequency below which about 85% of accumulated spectral energy is contained.

### `flatness`

Spectral Flatness. Describes whether the spectrum is more concentrated/narrowband or more broadband/noise-like.

It is not a distortion, clarity, or sound-quality score.

## Stereo

### `stereo_correlation`

Full-band left/right correlation, typically interpreted over approximately:

```text
+1  highly similar left/right signals
 0  weak linear correlation
-1  strongly anti-correlated left/right signals
```

This is a statistical relationship, not a universal width-quality score or automatic processing trigger.

Interpret it together with valid signal state and the energy present in the relevant frequency range.

### `stereo_width`

Analyzer Mid/Side width ratio describing the relative side-energy relationship formed by the stereo signal.

It is a relative measurement, not a fixed percentage-style width score.

### `band_stereo_correlation`

Eight band-limited stereo-correlation values:

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

If a band contains very little energy, its correlation should not be overinterpreted. When Signal State is invalid, the Bridge returns these values as unavailable/null.

## V0.6 Temporal

V0.6 temporal descriptors are computed from 1024-sample analysis hops inside the VST3 and aggregated into the roughly 10 Hz OSC stream. They describe **change and temporal coexistence**, not sound quality.

### `temporal_supported`

Indicates whether the current frame came from a plugin version that supports the V0.6 temporal tail.

Older Analyzer versions can still provide legacy measurements, but temporal features must not be invented when this field is false or absent.

### `temporal_valid`

Indicates whether the current V0.6 temporal descriptors are valid for active input. This normally requires:

```text
signal_present = true
and temporal_window_seconds > 0
```

### `temporal_window_seconds`

Internal analysis duration represented by the temporal aggregate carried in the current OSC frame.

It is usually close to the network-update interval but should not be hard-coded as exactly 0.1 seconds.

### `spectral_flux_mean`

Mean normalized positive spectral change across adjacent FFT windows within the current temporal aggregate.

Approximate interpretation:

```text
near 0 → little redistribution of normalized spectral shape
higher → stronger spectral-shape change
```

The normalization intentionally reduces sensitivity to simple overall gain changes, so this metric does not replace RMS level change.

### `spectral_flux_peak`

Maximum normalized spectral flux within the current temporal aggregate.

It emphasizes short change peaks more than `spectral_flux_mean`, but it is not absolute proof of a true musical onset.

### `rms_rise_peak_db`

Largest **positive** RMS increase between adjacent internal analysis windows inside the current temporal aggregate, in dB.

It describes rapid level-rise evidence. It is not Crest Factor and not an attack-time constant.

### `low_band_energy_db` / `low_band_40_160_energy_db`

The VST3 temporal tail's `low_band_energy_db` is an FFT-derived **40–160 Hz** energy feature. `audio_temporal_profile()` summarizes recent valid frames as `low_band_40_160_energy_db`, plus minimum and maximum values.

It is useful for building a low-frequency energy envelope. It is not calibrated SPL and does not imply that a specific instrument is present.

### `onset_candidate_frames`

`audio_temporal_profile()` uses explicit thresholds to mark OSC frames as onset/change candidates. Current defaults are returned with the result:

```text
rms_rise_peak_db >= 3.0
OR
spectral_flux_peak >= 0.18
```

This is a compressed heuristic event candidate, not onset ground truth validated against manual annotations.

### `onset_candidate_density_hz`

Candidate-frame count divided by valid temporal coverage in seconds.

It describes the density of change candidates. It is not BPM, beat density, or note density.

### `band_envelope_correlation`

`audio_temporal_compare()` time-aligns the selected-band energy envelopes from two Analyzer instances and computes Pearson correlation:

```text
near +1 → envelopes tend to move in the same direction
near  0 → weak linear covariation
near -1 → envelopes tend to move in opposite directions
```

This describes covariation. It does not identify which track should change.

### `normalized_band_temporal_overlap`

Each track's selected-band envelope is normalized relative to its own peak in the comparison window. At every aligned point, the implementation takes `min()` between the two normalized values and then averages those minima.

The result is normally about 0–1:

```text
higher → both tracks are more often simultaneously strong in that band relative to their own peaks
lower  → strong selected-band energy occurs together less often
```

This is a temporal-occupancy heuristic, not a complete audible-masking probability.

### `coactive_ratio`

Fraction of aligned frame pairs where both Analyzer instances report `signal_present=true`.

### `candidate_coincidence_ratio`

Summary of how often threshold-based onset/change candidates from both tracks occur in the same aligned OSC frames.

It depends on the candidate thresholds and OSC time resolution and must not be interpreted as sample-accurate transient synchronization.

### `alignment_tolerance_ms` / `mean_abs_alignment_offset_ms`

`audio_temporal_compare()` aligns two independent Analyzer streams within an allowed tolerance. These fields report the requested tolerance and actual average absolute alignment offset.

When alignment quality is weak, temporal correlation/overlap should be interpreted more cautiously.

## Track comparison

### `spectral_overlap_score`

Heuristic score describing overlap between two tracks' **relative spectral shapes**.

It is not a complete psychoacoustic masking measurement and does not encode full timing, arrangement, perception thresholds, or source roles.

Therefore:

```text
high overlap → spectral shapes share substantial relative energy regions
```

but it does not prove audible masking.

V0.6 `audio_temporal_compare()` can add evidence about whether those regions are active or changing at the same time, but neither class of measurement is a final perceptual conclusion.

### `audio_detect_masking()`

Despite the tool name, the current implementation should be understood as potential spectral-overlap candidate detection. Do not describe the result as masking proven by a full psychoacoustic model.

## Identity / topology

### `id` / `runtime_id`

Runtime UUID for a live VST3 instance. It allows the Bridge to distinguish Analyzer instances that share the same human-readable name.

It is session-scoped and should not be treated as a permanent cross-session project ID.

### `track` / `analyzer_name`

Human-readable Analyzer instance name. It may be duplicated and is therefore not a guaranteed unique identifier.

### `binding`

V0.4 host relationship established through Identify, containing fields such as:

```text
fl_track_index
fl_track_name
slot
runtime_id
```

### `selector`

After binding, the preferred machine selector is:

```text
mixer:<track_index>/slot:<slot>
```

It is more deterministic than the Analyzer display name.

## Freshness / connection

### `age_seconds`

Time since the Bridge last received an OSC frame from the instance.

### `stale`

Indicates that the instance's data is older than the Bridge freshness threshold. Stale data should not be described as current real-time state.

### `duplicate_name`

Indicates another live Analyzer instance has the same display name. Use a binding selector or runtime UUID when names are duplicated.

## Snapshot A/B

### `audio_capture_snapshot(name, seconds)`

Stores a project-level window summary in the current Bridge session. Snapshots are not written into the FL Studio project and do not survive Bridge restart.

### `audio_compare_snapshots(before, after)`

Delta is defined as:

```text
Delta = After - Before
```

For dB-like fields:

```text
positive → After is numerically higher
negative → After is numerically lower
```

For Stereo Correlation delta:

```text
positive → After moved toward more positive correlation
negative → After moved toward lower/negative correlation
```

Before comparing, check that both snapshots represent comparable musical passages, window lengths, and `active_ratio`.

## Unified `null` rule

Whenever a field is `null`, interpret it as:

```text
no valid/available measurement for this field at this time
```

Do not replace `null` with zero and do not infer audio content from an unavailable value.
