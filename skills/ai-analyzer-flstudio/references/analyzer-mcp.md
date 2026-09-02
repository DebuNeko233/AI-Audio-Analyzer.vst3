# AI Audio Analyzer MCP Reference

This file describes MCP tools, selector rules, call order, and validity checks. Measurement semantics are documented in `parameters.md`; V0.7 masking-evidence details are documented in `masking-evidence.md`; V0.8 stereo evidence is documented in `stereo-evidence.md`.

Current MCP 0.8 exposes **22 tools**:

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
```

## Recommended hierarchy

Do not call all 22 tools by default.

```text
project readiness
→ audio_project_status()

project recent overview
→ audio_mix_overview()

project masking-evidence ranking
→ audio_project_masking_scan()

stable single track
→ audio_average()

single-track temporal change
→ audio_temporal_profile()

single-track deep stereo / Mid-Side
→ audio_stereo_profile()

two-track basic spectrum
→ audio_compare_tracks()

two-track detailed masking evidence
→ audio_masking_evidence()

custom-band temporal relation
→ audio_temporal_compare()

two-track stereo measurement comparison
→ audio_stereo_compare()

Before/After verification
→ audio_capture_snapshot() / audio_compare_snapshots()
```

Use the highest-level tool that answers the request, then drill down only when more detail is useful.

## V0.4 Identify: FL Studio ↔ Analyzer mapping

AI Audio Analyzer exposes a host-visible parameter:

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

Every Boolean transition emits `/aianalyzer/identify`. Recommended flow:

1. use the FL Studio control MCP to locate the real Mixer Track / Plugin Slot;
2. inspect the plugin's real exposed parameters and locate `Identify`;
3. read its current value;
4. set the opposite value;
5. immediately call `audio_last_identify()`;
6. verify the event is fresh and not consumed;
7. immediately call `audio_bind_last_identified(fl_track_index, fl_track_name, slot)`;
8. repeat for the next instance;
9. call `audio_instance_map()` and verify `discovery_complete`.

Do not assume FL Studio MCP tool names. Use the tools and parameter names it actually exposes.

Identify events, runtime UUIDs, and bindings are session-scoped.

## Selector rules

Preferred order:

```text
mixer:<track_index>/slot:<slot>
→ unique FL Mixer track name
→ runtime UUID
→ unique Analyzer display name
```

Supported selector forms:

```text
mixer:7
mixer:7/slot:9
fl:7
fl:7/slot:9
```

If multiple Analyzer instances exist on one Mixer Track, include `slot`.

## Signal / validity

V0.3 gate semantics:

```text
close threshold   ≈ -50 dBFS
reopen threshold  ≈ -48 dBFS
hold              ≈ 0.4 s
```

Rules:

- do not infer spectrum/stereo content from `signal_present=false` frames;
- `null` means unavailable, not zero;
- inspect `active_frames`, `active_ratio`, and `analysis_valid` for window tools;
- stale streams are not current real-time state.

For temporal tools also inspect:

```text
temporal_supported
temporal_valid
temporal_window_seconds
```

For V0.8 deep stereo tools inspect:

```text
stereo_v08_supported
stereo_v08_valid
stereo_frames
active_ratio
```

## `audio_project_status()`

Use first for project readiness.

Important fields:

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

If instances are unbound, perform Identify before project-wide interpretation.

## `audio_mix_overview()`

Returns recent project-level track summaries and:

```text
potential_spectral_conflicts
```

These are coarse relative-spectrum candidates, not proof of audible masking.

## `audio_project_masking_scan()` — V0.7

```text
audio_project_masking_scan(
  seconds=5,
  max_pairs=8,
  alignment_tolerance_ms=80
)
```

It starts from project spectral-conflict candidates and evaluates them with the V0.7 ERB-rebinned spectral/relative-level/temporal evidence model.

Use it for project-level ranking, not as a universal list of problems.

Important fields:

```text
candidate_pair_count
pairs[].masking_evidence_score
pairs[].top_region
pairs[].alignment
```

## `audio_snapshot()` / `audio_average()`

```text
audio_snapshot(track)
```

Latest frame; useful for current-state/connection checks.

```text
audio_average(track, seconds)
```

Stable recent window; preferred when describing several seconds of content. Content-dependent averages use active frames only.

## `audio_stereo_bands()` — legacy stereo correlation view

Returns the existing eight correlation bands. Use it when the legacy band view is sufficient.

For Mid/Side energy, Side spectrum, low-band Side/Mid, or negative-cross evidence, use `audio_stereo_profile()` instead.

## `audio_stereo_profile()` — V0.8

```text
audio_stereo_profile(track, seconds=5)
```

Returns a windowed profile with:

```text
full_band.mid_rms_db
full_band.side_rms_db
full_band.side_to_mid_db
full_band.stereo_correlation_mean
full_band.stereo_correlation_min
full_band.decorrelation_proxy_mean
full_band.negative_cross_energy_ratio_mean
full_band.negative_cross_energy_ratio_max

low_band_20_120_hz.correlation_mean
low_band_20_120_hz.correlation_min
low_band_20_120_hz.side_to_mid_db
low_band_20_120_hz.side_to_mid_db_max

mid_spectrum_db[32]
side_spectrum_db[32]
frequency_dependent_stereo[8]
```

Each `frequency_dependent_stereo` entry contains the range plus:

```text
correlation
side_to_mid_db
```

Do not collapse correlation, Side/Mid, decorrelation proxy, and negative-cross evidence into one stereo-quality score.

## `audio_stereo_compare()` — V0.8

```text
audio_stereo_compare(track_a, track_b, seconds=5)
```

Returns measurement deltas using:

```text
B - A
```

Important fields:

```text
deltas_b_minus_a.mid_rms_db
deltas_b_minus_a.side_rms_db
deltas_b_minus_a.side_to_mid_db
deltas_b_minus_a.stereo_correlation_mean
deltas_b_minus_a.decorrelation_proxy_mean
deltas_b_minus_a.negative_cross_energy_ratio_mean
deltas_b_minus_a.low_band_20_120_correlation
deltas_b_minus_a.low_band_20_120_side_to_mid_db
frequency_dependent_deltas[]
```

Positive/negative deltas are not automatically better/worse.

## `audio_compare_tracks()` / `audio_detect_masking()`

These are older spectrum-only comparison paths.

`audio_detect_masking()` should still be understood as a heuristic spectral-overlap candidate tool. It is not a Bark/ERB psychoacoustic proof of masking.

For stronger current evidence use `audio_masking_evidence()`.

## `audio_temporal_profile()` — V0.6

Returns recent temporal descriptors such as:

```text
spectral_flux_mean
spectral_flux_peak
rms_rise_peak_db
low_band_40_160_energy_db
onset_candidate_frames
onset_candidate_density_hz
```

Onset/change candidates are threshold-based heuristics. The active thresholds are returned explicitly in `onset_candidate_thresholds`.

## `audio_temporal_compare()` — V0.6

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

Important fields:

```text
aligned_pairs
usable_band_pairs
mean_abs_alignment_offset_ms
coactive_ratio
band_envelope_correlation
normalized_band_temporal_overlap
candidate_coincidence_ratio
```

Use it when a user asks whether two sources actually co-occupy or co-vary in a custom frequency range over time.

## `audio_masking_evidence()` — V0.7

```text
audio_masking_evidence(
  track_a,
  track_b,
  seconds=5,
  alignment_tolerance_ms=80,
  max_regions=8
)
```

The current model:

```text
32 Analyzer spectrum features
→ 16 equal ERB-rate regions
→ local relative spectral overlap
→ directional relative-level weighting
→ V0.6 temporal overlap when available
```

Important output:

```text
auditory_band_model
alignment
masking_evidence_score
strongest_regions[]
evidence_formula
```

The model is deliberately transparent. `auditory_band_model.filterbank=false` because the implementation re-bins existing 32-band features rather than running a gammatone/cochlear filterbank.

Do not report `masking_evidence_score` as an audible-masking probability.

## Snapshot / A-B

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

For comparability:

- use the same musical passage when possible;
- use similar window lengths;
- inspect `active_ratio`;
- remember delta = `After - Before`;
- LUFS-I is session cumulative, not independently reset for each snapshot.

## Multiple instances and OSC

All VST3 instances normally send to:

```text
127.0.0.1:9855
```

Only the Bridge binds UDP port 9855. VST3 instances are senders, so multiple Analyzer instances do not need separate ports.

## OSC compatibility

V0.8 keeps the frame append-only. Existing indexes `0..64` are unchanged:

```text
0..58    V0.1–V0.4-compatible prefix
59       temporal_window_seconds
60       spectral_flux_mean
61       spectral_flux_peak
62       rms_rise_peak_db
63       low_band_energy_db
64       V0.6 schema marker = "0.6"
65       mid_rms_db
66       side_rms_db
67       side_to_mid_db
68       negative_cross_energy_ratio
69       low_band_20_120_correlation
70       low_band_20_120_side_to_mid_db
71..102  32 Side-spectrum bands
103..110 8 Side/Mid band ratios
111      V0.8 schema marker = "0.8"
```

The historical `bands_db` at indexes `11..42` is the Mid spectrum. V0.8 appends the Side spectrum rather than changing those existing fields.
