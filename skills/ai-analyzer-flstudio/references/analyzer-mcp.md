# AI Audio Analyzer MCP Reference

This reference describes the MCP 1.2 tool surface, self-description layers, project/runtime identity scope, selector rules, Analysis Profile control/readback, Song Memory, structure, Track Story, section relationships, retained dynamics distributions, direct mono-fold compatibility, frozen session reference comparison, verification modes, validity and control boundaries.

Related references:

```text
parameters.md
performance-evidence.md
song-memory.md
section-structure.md
track-story.md
section-relationships.md
dynamics-evidence.md
mono-compatibility.md
reference-comparison.md
masking-evidence.md
stereo-evidence.md
tonal-evidence.md
verification-evidence.md
```

## Tool registry

MCP 1.2 exposes **47 tools**:

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
audio_project_identity_status()
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
audio_analysis_status(track)
audio_project_performance()
audio_set_analysis_profile(track, profile, timeout_seconds=1.0)
audio_set_project_analysis_profile(profile, tracks=None, timeout_seconds=1.0)
audio_song_status()
audio_song_timeline(track, resolution_seconds=5, transport_epoch=None, start_seconds=None, end_seconds=None, max_bins=240)
audio_song_overview(transport_epoch=None, max_tracks=32)
audio_section_map(reference_track=None, transport_epoch=None, min_section_seconds=8, sensitivity=0.55, family_similarity=0.78, max_sections=48, max_tracks=32)
audio_section_profile(section_id, map_id=None, max_tracks=32, max_related=8)
audio_track_story(track, map_id=None)
audio_section_relationships(map_id=None, max_pairs=12, max_tracks=32, include_master=False, min_activity_overlap=0.15, min_shortlist_priority=0.18)
audio_begin_verification(label, seconds=5, target_selectors=None)
audio_complete_verification(verification_id, seconds=0, change_summary="", host_readback="")
audio_verification_status(verification_id="")
audio_begin_range_verification(label, start_seconds, end_seconds, target_selectors=None, minimum_coverage=0.8)
audio_complete_range_verification(verification_id, change_summary="", host_readback="")
audio_range_verification_status(verification_id="")
audio_dynamics_distribution(track, transport_epoch=None, start_seconds=None, end_seconds=None, map_id=None, section_id=None, compare_section_id=None, minimum_range_coverage=0.8, minimum_bin_coverage=0.5)
audio_mono_compatibility(track, seconds=5.0)
audio_capture_reference(track, label="", seconds=10.0)
audio_list_references()
audio_compare_reference(reference_id, target, seconds=None)
```

Do not call all 47 tools by default.

## Self-describing API

The MCP remains minimally safe even without an imported client Skill:

```text
Server instructions
-> startup order + hard rules

Tool descriptions
-> purpose/intended use through tools/list

MCP Resources
-> canonical long-form Skill/reference Markdown on demand
```

Self-description schema:

```text
schema_version = 1
guide URI prefix = aianalyzer://guide/
```

Current Resource registry contains **16 Resources**:

```text
aianalyzer://guide/index
aianalyzer://guide/core
aianalyzer://guide/analyzer-mcp
aianalyzer://guide/parameters
aianalyzer://guide/performance-evidence
aianalyzer://guide/song-memory
aianalyzer://guide/section-structure
aianalyzer://guide/track-story
aianalyzer://guide/section-relationships
aianalyzer://guide/dynamics-evidence
aianalyzer://guide/mono-compatibility
aianalyzer://guide/reference-comparison
aianalyzer://guide/masking-evidence
aianalyzer://guide/stereo-evidence
aianalyzer://guide/tonal-evidence
aianalyzer://guide/verification-evidence
```

Read only the guide needed for the current task. `skills/ai-analyzer-flstudio/SKILL.md` and `references/*.md` remain the canonical long-form source.

## Recommended hierarchy

```text
project/runtime identity scope
-> audio_project_identity_status()

project readiness
-> audio_project_status()

whole-song / delayed context
-> audio_song_status()
-> audio_song_overview()

structure
-> audio_section_map()
-> audio_track_story()
-> audio_section_profile()
-> audio_section_relationships()

retained dynamics
-> audio_dynamics_distribution()

recent mono translation
-> audio_mono_compatibility()

reference direction
-> audio_capture_reference()
-> audio_list_references()
-> audio_compare_reference()

raw historical timeline only when needed
-> audio_song_timeline()

performance / feature availability
-> audio_project_performance()
-> audio_analysis_status()

Analyzer-owned measurement scope
-> audio_set_analysis_profile()
-> audio_set_project_analysis_profile()

known-passage external DAW change
-> audio_begin_range_verification()
-> external write + actual host readback
-> replay effective range
-> audio_complete_range_verification()
```

## Project/runtime identity scope

Use `audio_project_identity_status()` at new MCP sessions and after a possible project switch/reopen.

Current contract:

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
project_switch_detection                not_available
runtime_id.scope                        live_plugin_instance
runtime_id.persistent                   false
runtime_id.serialized_with_project      false
runtime_id.stable_when_same_project_is_reopened  false
binding.scope                           mcp_session
binding.persistent                      false
retained_state.scope                    mcp_session
retained_state.cross_project_isolation_guaranteed  false
```

Do not manufacture project identity from runtime UUID, tempo, names, topology, Mixer indexes or transport epochs. Restart Analyzer MCP after a switch/reopen when strict isolation is required and authoritative identity is unavailable.

## Deterministic Identify mapping

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

Recommended flow:

```text
locate actual Mixer Track / Slot with DAW-control MCP
-> toggle Identify
-> audio_last_identify()
-> audio_bind_last_identified(...)
-> audio_instance_map()
```

Preferred selector order:

```text
mixer:<track_index>/slot:<slot>
-> unique FL Mixer track name
-> runtime UUID
-> unique Analyzer display name
```

Bindings are current-session location, not persistent track identity.

## Analysis Profile

```text
0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

Analyzer-owned write tools may change only `analysis_profile`. Keep `control_acknowledged` distinct from `telemetry_confirmed`.

`worker_load_ratio` is Analyzer background-worker load, not DAW realtime CPU.

## Validity rules

- `null` means unavailable, not zero;
- missing Song Memory coverage is not silence;
- stale streams are not current state;
- disabled/unmeasured families remain unavailable;
- current live Profile is not proof of historical feature availability;
- retained comparisons use fields actually retained in selected evidence;
- current fresh telemetry does not prove retained state belongs to the same project after a switch/reopen.

## Song Memory

```text
canonical bin        1 second
coverage slot        100 ms
max bins             1200 / Analyzer instance
query resolutions    1 / 2 / 5 / 10 / 15 / 30 seconds
```

`transport_epoch` is instance-local. Cross-track retained reasoning aligns by DAW-time overlap, not equal epoch numbers.

Song Memory is MCP-session state and not yet partitioned by a stable Project ID.

## Structure / Track Story / relationships

`audio_section_map()` creates explainable boundaries and neutral recurring families. Boundary strength is novelty evidence, not a formal-boundary probability.

`audio_section_profile()` returns multi-track evidence within one section.

`audio_track_story()` summarizes one track across sections and families without inventing role or one overall quality score.

`audio_section_relationships()` returns a bounded pair shortlist. `shortlist_priority` is inspection priority only, not masking/audibility/problem probability, quality score or processing instruction.

Detailed masking/stereo/temporal pair tools remain recent-window based.

## P6a retained dynamics

`audio_dynamics_distribution()` reuses one-second Song Memory and the common range resolver. It adds no realtime DSP or OSC fields.

Supported scopes: selected pass span, explicit DAW-time range, cached Section, and optional Section-to-Section deltas.

Coverage policy is a per-bin floor plus covered-seconds weighting.

Important boundaries:

- descriptive LUFS-S P90-P10 != standardized EBU LRA;
- arbitrary-range Integrated LUFS is unavailable while retained LUFS-I is pass-cumulative;
- arbitrary-range PLR is unavailable without compatible scope;
- observed peak distributions are not reconstructed sample streams;
- section deltas do not create a quality score.

See `dynamics-evidence.md`.

## P7a direct mono compatibility

`audio_mono_compatibility()` reuses existing recent Mid/Side evidence:

```text
M = 0.5 * (L + R)
S = 0.5 * (L - R)
(L_power + R_power)/2 = M_power + S_power
```

It returns direct full-band fold-down RMS and 32 band-center sampled energy evidence.

`inspection_priority` is an energy-weighted shortlist aid only. When Mid reaches `-120 dB`, results are floor-censored rather than claiming exact deeper cancellation.

Historical arbitrary Section 32-band mono evidence and direct mono Sample Peak/True Peak are unavailable in P7a.

See `mono-compatibility.md`.

## P8a session reference comparison

### Capture

```text
audio_capture_reference(track, label="", seconds=10.0)
```

Freezes a compact recent-window measurement profile in MCP memory. It stores no source audio.

Current scope:

```text
session-scoped
frozen at capture time
recent receive-time
not persistent
not whole-song truth
```

### List

```text
audio_list_references()
```

Returns compact provenance instead of full profile payloads.

### Compare

```text
audio_compare_reference(reference_id, target, seconds=None)
```

Returns independent descriptive groups:

```text
comparability
energy
spectrum
stereo
mono_compatibility
provenance
interpretation_boundary
```

Absolute direction is always `target - reference`.

The spectral result also provides an explicit RMS-level-normalized view:

```text
target_gain_to_reference_db = reference_rms - target_rms
normalized_delta = (target_band + target_gain_to_reference_db) - reference_band
```

This is only a comparison view. It does not change the target or reference.

Do not turn a spectral delta into a direct inverse-EQ recipe. Do not assume wider/narrower/louder/brighter than the reference is automatically wrong. Do not silently equate Section labels across unrelated songs.

P8a emits no automatic EQ/master match, quality score or processing recommendation.

Current limitations:

```text
persistent reference library                  unavailable
historical arbitrary Section 32-band capture  unavailable
whole-song completeness claim                 unavailable
external-file faster-than-realtime scan       unavailable
```

See `reference-comparison.md`.

## Verification

### Same-range

```text
audio_begin_range_verification(...)
-> external write + actual host readback
-> replay effective_range
audio_complete_range_verification(...)
```

The requested range is normalized to one-second retained bins. Per-track local epochs are selected coverage-first. After evidence must be newer than the frozen pre-change fence.

`active_ratio` is descriptive in same-range mode, not passage identity.

Do not report arbitrary-range LUFS-I delta from pass-cumulative retained LUFS-I.

### Recent-window fallback

```text
audio_begin_verification(...)
audio_complete_verification(...)
```

`controlled_comparison=true` means technical comparability only. `closed_loop_complete=true` additionally requires actual external host readback. Neither means After is artistically better.

## Control boundary

Analyzer MCP may:

```text
measure
read Analyzer state
disclose identity guarantees
remember transport-aligned evidence
infer explainable structure
summarize Track Story
shortlist relationships
compute retained dynamics distributions
compute recent mono compatibility
freeze/compare session reference measurement profiles
compare measurements
resolve retained ranges
verify Before/After conditions
control Analyzer Analysis Profile only
```

The DAW-control MCP owns exact DAW/project inspection, plugin access, all artistic/technical writes, actual host readback, and transaction/rollback when implemented.

Never invent project identity, control success, host readback, track roles, semantic Section labels, reference-match prescriptions, or processing certainty.