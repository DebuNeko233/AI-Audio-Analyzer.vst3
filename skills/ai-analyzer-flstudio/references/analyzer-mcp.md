# AI Audio Analyzer MCP Reference

This document describes MCP tools, selectors, calling order, and data-validity rules. See `parameters.md` for technical parameter semantics.

AI Audio Analyzer MCP 0.6 currently exposes 18 tools:

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
```

## Recommended call hierarchy

Do not call all 18 tools automatically. Use the highest-level tool that already contains enough information, then drill down only when needed.

```text
Project readiness
→ audio_project_status()

Project recent window
→ audio_mix_overview()

Stable single-track window
→ audio_average()

Single-track temporal behavior
→ audio_temporal_profile()

Two-track spectral relationship
→ audio_compare_tracks()

Two-track temporal relationship
→ audio_temporal_compare()

Before/After measurement
→ audio_capture_snapshot() / audio_compare_snapshots()
```

## V0.4 FL Studio ↔ Analyzer Identify

AI Audio Analyzer exposes this host parameter:

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

Every boolean transition emits `/aianalyzer/identify`. Recommended flow:

1. use the FL Studio control MCP to find the real Mixer Track and Plugin Slot;
2. inspect the plugin's real exposed parameters and locate `Identify`;
3. read its current value;
4. set it to the opposite value;
5. immediately call `audio_last_identify()`;
6. verify the event is fresh and unconsumed;
7. immediately call `audio_bind_last_identified(fl_track_index, fl_track_name, slot)`;
8. repeat for the next instance;
9. finish with `audio_instance_map()` and inspect `discovery_complete`.

Do not invent FL Studio MCP tool names. Use the tools and parameters that the connected control MCP actually exposes.

Each Identify event may be consumed only once. Bindings and runtime UUIDs are session-scoped.

## Selectors

Preferred order:

```text
mixer:<track_index>/slot:<slot>
→ unique FL Mixer Track name
→ runtime UUID
→ unique human-readable Analyzer name
```

Supported selector forms include:

```text
mixer:7
mixer:7/slot:9
fl:7
fl:7/slot:9
```

If one Mixer Track contains multiple Analyzer instances, the selector must include `slot`.

## Signal / validity

V0.3 signal gate:

```text
close threshold   ≈ -50 dBFS
reopen threshold  ≈ -48 dBFS
hold              ≈ 0.4 s
```

Rules:

- do not infer spectral/stereo content when `signal_present=false`;
- `null` means unavailable, not zero;
- interpret `audio_average()` together with `active_frames`, `active_ratio`, and `analysis_valid`;
- do not describe stale streams as current real-time state.

## `audio_project_status()`

Use this first for project-level readiness. Important fields include:

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

If instances are unbound, run deterministic Identify mapping instead of guessing from names or musical content.

## `audio_mix_overview()`

Use this to read recent-window state across multiple Analyzer instances. It returns project tracks, Master candidates, and `potential_spectral_conflicts`.

`potential_spectral_conflicts` is heuristic relative spectral overlap intended to identify areas worth further inspection. It does not prove audible masking.

If the question is whether two tracks occupy a region **at the same time**, continue with `audio_temporal_compare()` rather than relying on overview overlap alone.

## `audio_snapshot()` and `audio_average()`

```text
audio_snapshot(track)
```

Reads the latest frame. Use it for current-state inspection or connection troubleshooting.

```text
audio_average(track, seconds)
```

Reads a stable recent window. Spectrum, stereo, and other content-related statistics use active frames only.

## `audio_compare_tracks()` / `audio_detect_masking()`

`audio_compare_tracks()` compares relative spectral shapes between two active Analyzer instances.

`audio_detect_masking()` currently remains a spectral-overlap candidate tool, not a complete Bark/ERB psychoacoustic masking model. Do not describe its output as proof that audible masking has occurred.

## V0.6 `audio_temporal_profile()`

Summarizes recent temporal behavior for one Analyzer:

```text
spectral_flux_mean
spectral_flux_peak
rms_rise_peak_db
low_band_40_160_energy_db
low_band_40_160_min_db
low_band_40_160_max_db
onset_candidate_frames
onset_candidate_density_hz
```

Requirements: the VST3 must support the V0.6 temporal tail, and the requested window must contain temporally valid active frames.

`onset_candidate_*` fields are thresholded change candidates, not ground-truth onset labels. Actual thresholds are returned under `onset_candidate_thresholds`.

## V0.6 `audio_temporal_compare()`

Compares time-aligned band envelopes from two Analyzer instances:

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
temporal_descriptor_pairs
onset_candidate_frames_a
onset_candidate_frames_b
coincident_onset_candidate_frames
candidate_coincidence_ratio
```

Interpretation:

```text
band_envelope_correlation
→ whether the selected-band envelopes tend to vary in the same direction

normalized_band_temporal_overlap
→ how often both tracks are simultaneously strong relative to their own selected-band peaks

candidate_coincidence_ratio
→ how often V0.6 change/onset candidates occur in the same aligned OSC frames
```

These are timing-relationship measurements/heuristics. They are not processing instructions and not a complete masking probability.

If `mean_abs_alignment_offset_ms` approaches the allowed alignment tolerance, reduce confidence in correlation/overlap interpretation.

## Snapshot / A-B

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

Snapshots exist only in the current Bridge session.

For comparability:

- use the same musical passage when practical;
- use similar window lengths;
- compare `active_ratio`;
- delta is defined as `After - Before`;
- LUFS-I is session-integrated and should not be treated as two independently reset short-window measurements.

## Multiple instances and OSC

All VST3 instances send OSC to the same default destination:

```text
127.0.0.1:9855
```

Only the Bridge binds UDP 9855. VST3 instances are senders, so each Analyzer does not need a separate port.

## V0.6 append-only OSC tail

`/aianalyzer/frame` preserves fields `0..58` unchanged and appends these after the runtime UUID:

```text
59  temporal_window_seconds
60  spectral_flux_mean
61  spectral_flux_peak
62  rms_rise_peak_db
63  low_band_energy_db      # FFT-derived 40-160 Hz
64  frame_schema_version    # "0.6"
```

Older Bridges may ignore these trailing fields. The 0.6 compatibility layer first runs the stable parser and then attaches the V0.6 tail.
