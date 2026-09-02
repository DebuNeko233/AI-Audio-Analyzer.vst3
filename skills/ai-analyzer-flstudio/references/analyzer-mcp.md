# AI Audio Analyzer MCP Reference

This file describes MCP tools, selector rules, call order, validity checks, verification flow, and OSC compatibility. Measurement semantics are documented in `parameters.md`; V0.7 masking evidence in `masking-evidence.md`; V0.8 stereo evidence in `stereo-evidence.md`; V0.9 tonal evidence in `tonal-evidence.md`; V1.0 closed-loop verification in `verification-evidence.md`.

Current MCP 1.0 exposes **27 tools**:

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
audio_begin_verification(label, seconds=5, target_selectors=None)
audio_complete_verification(verification_id, seconds=0, change_summary="", host_readback="")
audio_verification_status(verification_id="")
```

## Recommended hierarchy

Do not call all 27 tools by default.

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

single-track audio tonal evidence
→ audio_tonal_profile()

two-track basic spectrum
→ audio_compare_tracks()

two-track detailed masking evidence
→ audio_masking_evidence()

custom-band temporal relation
→ audio_temporal_compare()

two-track stereo measurement comparison
→ audio_stereo_compare()

two-track pitch-class distribution comparison
→ audio_tonal_compare()

manual Before/After snapshots
→ audio_capture_snapshot() / audio_compare_snapshots()

externally controlled DAW change with auditable A/B
→ audio_begin_verification()
→ external control MCP write + host readback
→ audio_complete_verification()
→ audio_verification_status()
```

Use the highest-level tool that answers the request, then drill down only when more detail is useful.

For exact symbolic note/key/chord facts, use actual DAW/MIDI/project data when available. V0.9 is audio-domain inference evidence.

## V1.0 closed-loop verification

V1.0 adds Bridge-side orchestration only. It does **not** add VST3/OSC fields and does not control FL Studio.

Use it when the agent coordinates a DAW change through an external control MCP and wants auditable Before/After measurement evidence.

Canonical order:

```text
audio_project_status()
→ deterministic Identify mapping if needed
→ play intended comparison passage
→ audio_begin_verification(...)
→ check ready_for_external_change / baseline_blockers
→ external DAW-control MCP performs actual write
→ external DAW-control MCP reads actual host state back
→ replay same intended passage
→ audio_complete_verification(..., change_summary=..., host_readback=...)
→ inspect controlled_comparison / comparability
→ specialized Analyzer tools only when deeper evidence is needed
```

### `audio_begin_verification()`

```text
audio_begin_verification(
  label,
  seconds=5,
  target_selectors=None
)
```

`label` is a short factual description for the current verification session.

`target_selectors` may be omitted or may contain deterministic selectors such as:

```text
["mixer:4/slot:9", "mixer:7/slot:9"]
```

Main output:

```text
verification_id
status = "awaiting_external_change"
ready_for_external_change
baseline_blockers
target_selectors
baseline.captured_at
baseline.window_seconds
baseline.track_count
baseline.valid_track_count
baseline.topology_fingerprint
baseline.tracks[]
recommended_next_step
```

Do not make the DAW write first and then pretend this result is a Before baseline.

If `ready_for_external_change=false`, resolve `baseline_blockers` and begin a new verification before changing the DAW.

### `audio_complete_verification()`

```text
audio_complete_verification(
  verification_id,
  seconds=0,
  change_summary="",
  host_readback=""
)
```

When `seconds <= 0`, the After capture reuses the Before measurement-window duration.

`change_summary` should factually describe the actual control change attempted.

`host_readback` should be the actual post-write host state returned by the external DAW-control MCP. It is caller-supplied audit evidence; Analyzer stores it but does not independently validate it against FL Studio.

Main output includes:

```text
status = "completed"
result.before
result.after
result.comparison.controlled_comparison
result.comparison.comparability.same_window_seconds
result.comparison.comparability.topology_unchanged
result.comparison.comparability.active_ratio_tolerance
result.comparison.comparability.missing_targets
result.comparison.comparability.invalid_targets
result.comparison.comparability.coverage_mismatch_targets
result.comparison.comparability.warnings
result.comparison.topology
result.comparison.targets[].delta
result.external_change.change_summary
result.external_change.host_readback
result.external_change.readback_supplied
result.audit
```

Basic deltas use:

```text
After - Before
```

Calling `audio_complete_verification()` again for an already completed session returns the stored completed result instead of silently replacing the After capture.

### `controlled_comparison`

Current V1.0 requires all of the following:

```text
one or more compared targets
same Before/After window duration
unchanged Analyzer topology fingerprint / identity set
no requested target missing
valid active analysis in Before and After for each compared requested target
absolute active_ratio difference <= 0.15 for each compared requested target
```

The `0.15` active-ratio tolerance is a transparent passage-coverage guardrail, not an audible threshold or mix-quality threshold.

`controlled_comparison=true` means the A/B measurement conditions satisfy the listed technical guardrails. It does **not** mean After is better, correct, more professional, or should be kept.

### `audio_verification_status()`

```text
audio_verification_status()
```

lists recent Bridge-session verification records.

```text
audio_verification_status(verification_id)
```

retrieves one session and its completed result when available.

Verification records are in-memory and disappear when the Analyzer MCP Bridge exits.

Detailed semantics are in `verification-evidence.md`.

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
9. call `audio_instance_map()` and verify discovery.

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

- do not infer spectrum/stereo/semantic content from `signal_present=false` frames;
- `null` means unavailable, not zero;
- inspect active/valid frame coverage for window tools;
- stale streams are not current real-time state.

For V0.6 temporal tools inspect:

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

For V0.9 tonal tools inspect:

```text
semantic_v09_supported
semantic_v09_valid
valid_frames
active_ratio
evidence_quality.mean_chroma_energy_ratio
evidence_quality.normalized_pitch_class_entropy
evidence_quality.tonal_center_top2_margin
evidence_quality.valid_frame_ratio
```

For V1.0 verification inspect:

```text
ready_for_external_change
baseline_blockers
controlled_comparison
same_window_seconds
topology_unchanged
missing_targets
invalid_targets
coverage_mismatch_targets
active_ratio_tolerance
```

## `audio_project_status()`

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

If instances are unbound, perform Identify before project-wide interpretation or V1.0 verification.

## `audio_mix_overview()`

Returns recent project-level summaries and `potential_spectral_conflicts`. Those are coarse relative-spectrum candidates, not proof of audible masking.

## `audio_project_masking_scan()` — V0.7

```text
audio_project_masking_scan(
  seconds=5,
  max_pairs=8,
  alignment_tolerance_ms=80
)
```

It ranks project spectral candidates with the V0.7 ERB-rebinned spectral/relative-level/temporal evidence model. Use it for candidate ranking, not a universal problem list.

## `audio_snapshot()` / `audio_average()`

```text
audio_snapshot(track)
```

Latest frame; useful for current-state/connection checks.

```text
audio_average(track, seconds)
```

Stable recent window; preferred for several seconds of content. Content-dependent averages use active frames only.

## `audio_stereo_bands()`

Returns the legacy eight correlation bands. Use `audio_stereo_profile()` when Mid/Side energy, Side spectrum, low-band Side/Mid, or negative-cross evidence is needed.

## `audio_stereo_profile()` — V0.8

```text
audio_stereo_profile(track, seconds=5)
```

Main output:

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
low_band_20_120_hz.side_to_mid_db

mid_spectrum_db[32]
side_spectrum_db[32]
frequency_dependent_stereo[8]
```

Do not collapse correlation, Side/Mid, decorrelation proxy, and negative-cross evidence into one stereo-quality score.

## `audio_stereo_compare()` — V0.8

```text
audio_stereo_compare(track_a, track_b, seconds=5)
```

Deltas use `B - A`. Positive/negative is not automatically better/worse.

## `audio_tonal_profile()` — V0.9

```text
audio_tonal_profile(track, seconds=8)
```

Use for audio-domain music-semantic evidence over a stable recent window.

Main output:

```text
chroma.pitch_class_order[12]
chroma.normalized_power[12]
chroma.top_pitch_classes
chroma.normalized_entropy
chroma.analysis_range_hz

tonal_center_evidence.method
tonal_center_evidence.top_candidates[]
tonal_center_evidence.top2_margin
tonal_center_evidence.probability = false

harmonic_alignment.single_f0_harmonic_energy_ratio_mean
harmonic_alignment.single_f0_harmonic_energy_ratio_max
harmonic_alignment.f0_candidate_hz_median
harmonic_alignment.f0_candidate_hz_min
harmonic_alignment.f0_candidate_hz_max

evidence_quality.mean_chroma_energy_ratio
evidence_quality.normalized_pitch_class_entropy
evidence_quality.tonal_center_top2_margin
evidence_quality.valid_frame_ratio
evidence_quality.active_ratio
```

The chroma order is:

```text
C C# D D# E F F# G G# A A# B
```

Tonal-center candidates are Pearson correlations against Krumhansl-Kessler major/minor templates. They are **not ground-truth key labels or probabilities**.

The harmonic fields are a single-F0 spectral-alignment heuristic. They are not pitch transcription, note detection, harmonic/percussive source separation, or probability of harmonic content.

If exact notes/key/chords are available from MIDI/project metadata, prefer those for exact symbolic questions.

## `audio_tonal_compare()` — V0.9

```text
audio_tonal_compare(track_a, track_b, seconds=8)
```

Main output:

```text
pitch_class_comparison.cosine_similarity
pitch_class_comparison.jensen_shannon_divergence
pitch_class_comparison.pitch_class_order
pitch_class_comparison.normalized_power_delta_b_minus_a[12]
harmonic_alignment_delta_b_minus_a
evidence_quality.track_a
evidence_quality.track_b
```

The deltas are `B - A`. Chroma similarity/divergence does not establish harmonic compatibility, consonance, correctness, or a required musical action.

## `audio_compare_tracks()` / `audio_detect_masking()`

These are older spectrum-only comparison paths. `audio_detect_masking()` is a heuristic spectral-overlap candidate tool. For stronger current evidence use `audio_masking_evidence()`.

## `audio_temporal_profile()` — V0.6

Returns descriptors such as:

```text
spectral_flux_mean
spectral_flux_peak
rms_rise_peak_db
low_band_40_160_energy_db
onset_candidate_frames
onset_candidate_density_hz
```

Onset/change candidates are threshold-based heuristics, not ground-truth musical onset labels.

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

Important fields include aligned pairs, band-envelope correlation, normalized band temporal overlap, candidate coincidence, and alignment offset.

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

Current model:

```text
32 Analyzer spectrum features
→ 16 equal ERB-rate regions
→ local relative spectral overlap
→ directional relative-level weighting
→ V0.6 temporal overlap when available
```

`auditory_band_model.filterbank=false`; this is re-binning, not a cochlear/gammatone filterbank. `masking_evidence_score` is not an audible-masking probability.

## Snapshot / A-B

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

Use comparable passages/windows and inspect active coverage. Delta convention is `After - Before`. LUFS-I remains session cumulative.

For agent-coordinated external DAW changes, V1.0 verification is preferred because it also records baseline blockers, topology consistency, target validity, active-coverage comparability, external change summary, and host readback.

## Multiple instances and OSC

All VST3 instances normally send to:

```text
127.0.0.1:9855
```

Only the Bridge binds UDP 9855. VST3 instances are senders, so multiple instances do not need separate ports.

## OSC compatibility

**MCP 1.0 still uses OSC protocol 0.9.** V1.0 adds no VST3 frame fields.

The OSC frame remains append-only through index `127`:

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
112..123 12 chroma bins: C..B
124      chroma_energy_ratio
125      single_f0_harmonic_energy_ratio
126      harmonic_f0_candidate_hz
127      V0.9 schema marker = "0.9"
```

Historical `bands_db` at indexes `11..42` remains the Mid spectrum. V0.8 and V0.9 only append fields; they do not repurpose existing indexes. V1.0 operates entirely in the Bridge verification layer.
