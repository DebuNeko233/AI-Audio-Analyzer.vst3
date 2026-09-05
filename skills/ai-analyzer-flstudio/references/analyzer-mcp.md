# AI Audio Analyzer MCP Reference

This reference describes the MCP tool surface, selector rules, Analysis Profile control/readback, Song Memory, structure, Track Story, section relationships, verification modes, validity and control boundaries.

Related references:

```text
parameters.md
performance-evidence.md
song-memory.md
section-structure.md
track-story.md
section-relationships.md
masking-evidence.md
stereo-evidence.md
tonal-evidence.md
verification-evidence.md
```

## Tool registry

MCP 1.2 exposes **41 tools**:

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
```

Do not call all 41 tools by default.

## Recommended hierarchy

```text
project readiness
-> audio_project_status()

whole-song / delayed Agent context
-> audio_song_status()
-> audio_song_overview()

structure / arrangement context
-> audio_section_map()
-> audio_track_story() for one track across sections
-> audio_section_profile() for many tracks inside one section
-> audio_section_relationships() for a bounded pair shortlist

raw historical timeline only when needed
-> audio_song_timeline()

performance / feature availability
-> audio_project_performance()
-> audio_analysis_status()

Analyzer-owned computation scope
-> audio_set_analysis_profile()
-> audio_set_project_analysis_profile()

external DAW change with known passage
-> audio_begin_range_verification()
-> external write + actual host readback
-> replay effective_range
-> audio_complete_range_verification()

external DAW change without practical explicit range
-> audio_begin_verification()
-> external write + actual host readback
-> replay comparable recent passage
-> audio_complete_verification()
```

## Deterministic Identify mapping

Host-visible parameter:

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

Recommended flow:

1. use the actual DAW-control MCP to locate Mixer Track / Plugin Slot;
2. toggle the target Analyzer's `Identify` parameter;
3. call `audio_last_identify()`;
4. verify a fresh unconsumed event;
5. call `audio_bind_last_identified(...)`;
6. repeat one instance at a time;
7. verify with `audio_instance_map()`.

Preferred selector order:

```text
mixer:<track_index>/slot:<slot>
-> unique FL Mixer track name
-> runtime UUID
-> unique Analyzer display name
```

Runtime UUIDs and bindings are session-scoped.

## Analysis Profile control/readback

```text
0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

Analyzer-owned write tools may change only `analysis_profile`. They do not grant permission to modify EQ, compression, gain, pan, routing, synth, automation, arrangement, or unrelated plugin state.

Keep separate:

```text
control_acknowledged
telemetry_confirmed
```

The ACK can succeed while playback is stopped. Fresh telemetry normally requires new frames.

`worker_load_ratio` is Analyzer background-worker load, not DAW realtime CPU.

## Signal / validity rules

Approximate signal gate:

```text
close threshold   -50 dBFS
reopen threshold  -48 dBFS
hold              ~0.4 s
```

Rules:

- `null` means unavailable, not zero;
- missing Song Memory coverage is not silence;
- stale streams are not current state;
- disabled/unmeasured feature families remain unavailable;
- current live Profile must not be used as proof of historical feature availability;
- retained range comparison uses fields actually present in selected retained evidence.

## Song Memory

Protocol 1.2 keeps bounded DAW-time evidence.

```text
canonical bin        1 second
coverage slot        100 ms
max bins             1200 / Analyzer instance
query resolutions    1 / 2 / 5 / 10 / 15 / 30 seconds
```

`transport_epoch` is an **instance-local continuous playback pass**. Cross-track retained reasoning aligns by DAW-time overlap, not equal epoch numbers.

Important data-quality fields:

```text
coverage_ratio
data_age_seconds
mean/max estimated_analysis_lag_ms
dropped_blocks_cumulative
```

Transport coordinates are not sample-accurate editing coordinates.

## Structure / Track Story / relationships

### `audio_section_map()`

Creates explainable section boundaries and neutral recurring families.

`boundary strength` is novelty evidence, not formal-boundary probability.

A/B/C families are recurrence classes only, not semantic Intro/Verse/Chorus/Drop labels.

### `audio_section_profile()`

Returns multi-track evidence within one section, including each track's selected local epoch and data quality.

### `audio_track_story()`

Summarizes one track across sections with per-section measurements, adjacent deltas, same-family per-dimension variation, coverage/lag/drop and relative extrema.

Do not infer track role or one overall quality/consistency score.

### `audio_section_relationships()`

Returns a bounded pair shortlist across sections/families.

`shortlist_priority` is inspection priority only, not masking probability, mix-problem probability, audibility probability, quality score, or processing instruction.

Detailed masking/stereo/temporal pair tools remain recent-window based.

## Recent-window verification

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

This mode compares recent measurement windows. Its active-ratio tolerance is a passage-comparability guard, not a quality threshold.

Do not call it exact same-range verification.

## Transport-anchored same-range verification

```text
audio_begin_range_verification(...)
audio_complete_range_verification(...)
audio_range_verification_status(...)
```

Use this mode when an explicit DAW-time passage is known.

Core behavior:

```text
requested range
-> normalize to effective one-second Song Memory range
-> choose best retained Before pass per Analyzer by coverage first
-> freeze receive-time fence
-> external DAW write + actual host readback
-> replay the same effective range
-> choose clean post-fence After pass per Analyzer
-> compare After - Before
```

Important invariants:

- fractional request boundaries remain visible;
- `effective_range` is the actual retained one-second range;
- each track can use a different local epoch;
- newer sparse passes do not outrank older complete passes;
- pre-change retained bins cannot silently become After;
- missing coverage is not silence;
- `active_ratio` is descriptive, not passage identity;
- historical feature availability comes from retained evidence, not current Profile;
- higher selected After dropped-block evidence blocks a controlled comparison;
- arbitrary-range LUFS-I delta is unavailable because retained `lufs_i_latest` is pass-cumulative, not isolated range-integrated loudness.

`controlled_comparison=true` means technical comparability only.

`closed_loop_complete=true` additionally requires caller-supplied actual host readback.

Neither means the artistic result is better.

Detailed semantics: `verification-evidence.md`.

## Control boundary

Analyzer MCP owns measurement, retained memory, derived structure/relationships/range resolution, comparison, verification conditions, deterministic binding evidence, and Analyzer Analysis Profile control only.

The external DAW-control layer owns exact project state and all non-Analyzer writes/readback.

Never invent write success, readback values, semantic section labels, track roles, or processing certainty.

## OSC compatibility

OSC analysis protocol remains append-only **1.2** with existing indexes `0..149` unchanged by Track Story, relationships or range verification.

Analyzer-owned Profile control remains a separate loopback-only control protocol, revision 1.
