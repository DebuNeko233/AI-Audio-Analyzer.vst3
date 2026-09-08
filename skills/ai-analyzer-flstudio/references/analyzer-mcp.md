# AI Audio Analyzer MCP Reference

This reference describes the MCP tool surface, self-description layers, project/runtime identity scope, selector rules, Analysis Profile control/readback, Song Memory, structure, Track Story, section relationships, retained dynamics distributions, verification modes, validity and control boundaries.

Related references:

```text
parameters.md
performance-evidence.md
song-memory.md
section-structure.md
track-story.md
section-relationships.md
dynamics-evidence.md
masking-evidence.md
stereo-evidence.md
tonal-evidence.md
verification-evidence.md
```

## Tool registry

MCP 1.2 exposes **43 tools** on the P6a branch:

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
```

Do not call all 43 tools by default.

## Self-describing API layers

The MCP server is intended to remain minimally safe and understandable even when an external Skill has not been imported by the client.

The contract is intentionally layered:

```text
Server instructions
  -> short cross-cutting startup order and hard rules

Tool descriptions
  -> purpose/intended use surfaced through tools/list

MCP Resources
  -> long-form Skill/reference guidance read on demand

External Skill
  -> canonical long-form content for clients that support Skills
```

Long-form content must not be duplicated into the server handshake. `skills/ai-analyzer-flstudio/SKILL.md` and `references/*.md` remain the canonical Markdown source. The MCP Resources load those same files from the source repository, development component package, installed beginner package, or an explicit `AI_ANALYZER_SKILL_DIR` override.

Self-description schema:

```text
schema_version = 1
guide URI prefix = aianalyzer://guide/
```

Static guide resources on the P6a branch:

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
aianalyzer://guide/masking-evidence
aianalyzer://guide/stereo-evidence
aianalyzer://guide/tonal-evidence
aianalyzer://guide/verification-evidence
```

Read only the guide needed for the current task. If the external Skill is already in context, avoid redundantly reading `aianalyzer://guide/core`, because it is the same `SKILL.md` content.

The runtime is allowed to keep operating when the long-form guide files are absent: Server instructions and Tool descriptions remain the fallback. Official beginner packages, however, include the canonical `skill/` folder and CI requires the assembled package to make those guide files available.

CI/self-test invariants:

- exact guide Resource URI registry;
- every registered Tool has a non-empty description;
- every registered Guide Resource has a non-empty description;
- Server instructions contain the required identity, coverage, dynamics, verification and control-boundary rules;
- official assembled packages can locate the canonical Skill/reference files.

No MCP Prompt is required for this initial self-description layer. Prompts should only be added later for a concrete user-invoked workflow that cannot be expressed cleanly by Server instructions, Tool descriptions and Resources.

## Recommended hierarchy

```text
project/runtime identity scope
-> audio_project_identity_status()

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

retained dynamics when needed
-> audio_dynamics_distribution() for selected pass span / explicit range / cached section

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

## Project/runtime identity scope

Use:

```text
audio_project_identity_status()
```

at the beginning of a new MCP/Agent session and whenever the user may have switched or reopened a DAW project.

Current machine-readable contract:

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
retained_state.automatically_partitioned_by_stable_project_id  false
retained_state.cross_project_isolation_guaranteed              false
```

Interpretation:

- `runtime_id` identifies one live Analyzer plugin instance only;
- reopening the same project recreates Analyzer runtime UUIDs;
- therefore a new runtime UUID does not prove that the DAW project changed;
- Mixer/Slot bindings are deterministic for the current session but are not persistent track identity;
- MCP retained state can outlive an FL Studio project switch while the MCP process stays running;
- Song Memory, Section Maps, snapshots, relationship/verification state are not yet automatically partitioned by stable project ID;
- until exact project identity is provided by the external DAW-control layer, callers must not silently carry retained project-level state across a switch/reopen;
- if strict isolation is required before P3/P5 identity integration, restart Analyzer MCP when changing/reopening projects.

Never manufacture a project ID from runtime UUID, tempo, track count, Mixer indexes, names, topology fingerprints, epoch numbers, or an audio fingerprint unless a future explicit project-identity contract defines it.

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

Runtime UUIDs and bindings are session-scoped. Reopening/recreating an Analyzer requires rediscovery. A current-session binding is not persistent track identity.

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
- retained range comparison uses fields actually present in selected retained evidence;
- current fresh telemetry does not prove retained project-level state belongs to the same DAW project after a switch/reopen.

## Song Memory

Protocol 1.2 keeps bounded DAW-time evidence.

```text
canonical bin        1 second
coverage slot        100 ms
max bins             1200 / Analyzer instance
query resolutions    1 / 2 / 5 / 10 / 15 / 30 seconds
```

`transport_epoch` is an **instance-local continuous playback pass**. Cross-track retained reasoning aligns by DAW-time overlap, not equal epoch numbers.

Song Memory is MCP-session state and is not yet tagged/partitioned by a stable project ID. Treat it as potentially belonging to an earlier project after a switch/reopen unless a clean MCP session boundary or authoritative external identity establishes otherwise.

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

## Coverage-aware retained dynamics distributions

### `audio_dynamics_distribution()`

This P6a tool is MCP-side and reuses one-second Song Memory plus the common transport-range resolver. It adds no realtime DSP and no OSC fields.

Supported scopes:

```text
selected retained transport-pass span
explicit DAW-time range
cached Section Map section
optional compare_section_id for section-to-section deltas
```

Coverage policy:

```text
minimum per-bin coverage floor
+
covered-seconds weighting for accepted bins
```

The result exposes coverage/provenance such as effective range, selected instance-local epoch, range coverage, accepted bin count, rejected low-coverage bin count, missing bin count and weighting policy. Missing bins are never inserted as silence or zero.

Descriptive distributions currently include:

```text
RMS dBFS
LUFS-S
Crest dB
observed per-bin Sample Peak maxima
observed per-bin True Peak maxima
```

Where available they report min/max, P10/P25/P50/P75/P90, IQR, P90-P10 spread and a covered-seconds weighted arithmetic mean. RMS additionally exposes a separately named covered-seconds power-domain mean.

Important boundaries:

- `lufs_s_interpercentile_range_lu` is P90(LUFS-S) - P10(LUFS-S), not standardized EBU LRA;
- standardized EBU LRA is explicitly unavailable in P6a;
- arbitrary-range Integrated LUFS is explicitly unavailable because current retained `lufs_i_latest` is pass-cumulative;
- arbitrary-range PLR is explicitly unavailable without scope-compatible peak and integrated loudness;
- observed per-bin peak distributions are not a reconstructed sample stream;
- section deltas are descriptive only and do not create a dynamics/mastering quality score;
- no fixed LUFS/LRA/PLR/crest target belongs in Analyzer MCP core logic.

Detailed semantics: `dynamics-evidence.md`.

## Recent-window verification

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

This mode compares recent measurement windows. Its active-ratio tolerance is a passage-comparability guard, not a quality threshold.

Do not call it exact same-range verification.

Verification sessions are MCP-session state, not persistent project identity. Do not carry a verification across a suspected project switch/reopen without authoritative project identity.

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

Neither means the artistic result is better, and neither establishes persistent DAW project identity.

Detailed semantics: `verification-evidence.md`.

## Control boundary

Analyzer MCP owns measurement, retained memory, project/runtime identity-scope disclosure, derived structure/relationships/range resolution, coverage-aware retained dynamics distributions, comparison, verification conditions, deterministic binding evidence, and Analyzer Analysis Profile control only.

The external DAW-control layer owns exact project state, future authoritative stable project identity, and all non-Analyzer writes/readback.

Never invent project identity, write success, readback values, semantic section labels, track roles, or processing certainty.

## OSC compatibility

OSC analysis protocol remains append-only **1.2** with existing indexes `0..149` unchanged by Track Story, relationships, range verification, identity-scope disclosure, MCP self-description, or P6a retained dynamics distributions.

Analyzer-owned Profile control remains a separate loopback-only control protocol, revision 1.
