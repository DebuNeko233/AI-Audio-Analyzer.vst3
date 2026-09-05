---
name: ai-analyzer-flstudio
description: Technical usage skill for Cherry Studio + AI Audio Analyzer MCP. Teaches explicit project/runtime identity scope, deterministic Analyzer binding, adaptive Analysis Profile control, transport-aware Song Memory, explainable song structure, Track Story, bounded section-aware relationships, measurement validity, performance telemetry, recent-window verification, and transport-anchored same-range verification around externally controlled DAW changes. It does not prescribe a mixing style, LUFS target, EQ/compression/sidechain/stereo recipe, semantic section label, key change, harmony edit, or aesthetic decision.
---

# AI Audio Analyzer MCP Usage Skill

Use this Skill to:

1. call **AI Audio Analyzer MCP** correctly;
2. interpret its evidence without overstating it.

It is not a mixing/mastering style guide. Analyzer measurements do not imply a mandatory processor, parameter value, section name, track role, chord/key edit, stereo action, or aesthetic choice.

## 1. Start with project identity scope, then project status

At the beginning of a new Agent/MCP session, and whenever the user may have switched or reopened a DAW project, first inspect:

```text
audio_project_identity_status()
```

Current expected identity semantics are:

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
runtime_id scope                        live_plugin_instance
runtime_id persistent                   false
runtime_id serialized with project      false
same-project reopen UUID stable         false
binding scope                           mcp_session
cross-project retained-state isolation  not guaranteed
```

Critical rules:

- `runtime_id` identifies one live Analyzer plugin instance only;
- reopening the **same** project recreates Analyzer runtime UUIDs;
- a new runtime UUID does **not** prove that the project changed;
- MCP bindings are session-scoped, not persistent track identity;
- retained Song Memory, Section Maps, snapshots, relationships and verification sessions may remain in MCP RAM while the user switches/reopens projects;
- until exact external project identity is integrated, do not assume retained state belongs to the current project after a project switch/reopen;
- when strict isolation matters, ask/use the workflow that restarts Analyzer MCP before analyzing the newly opened/reopened project.

Do not invent a project ID from runtime UUIDs, tempo, track count, names, topology fingerprints, transport epochs, or Mixer indexes.

Then inspect project readiness:

```text
audio_project_status()
```

Use it to check Bridge/OSC health, live instances, deterministic bindings, stale streams, duplicate names, and current-session analysis readiness.

Only descend when needed:

```text
audio_bridge_status()
audio_list_tracks()
audio_instance_map()
```

For whole-song, past-passage, section, or latency-sensitive work next use:

```text
audio_song_status()
```

If enough of the intended pass has been captured, prefer structural compression:

```text
audio_section_map()
```

Then choose the smallest follow-up:

```text
audio_track_story(track, map_id)          # one track across sections
audio_section_profile(section_id, map_id) # many tracks inside one section
audio_section_relationships(map_id)       # bounded cross-track shortlist
```

Use `audio_song_timeline()` only when raw DAW-time evolution is still required.

Do not call all 42 tools mechanically.

## 2. Deterministic Analyzer ↔ FL Mixer mapping

Host-visible parameter:

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

Preferred discovery flow:

```text
locate real Mixer Track / Plugin Slot with the DAW-control MCP
-> read current Identify value
-> toggle Identify
-> audio_last_identify()
-> verify fresh + unconsumed event
-> audio_bind_last_identified(fl_track_index, fl_track_name, slot)
-> audio_instance_map()
```

Preferred selectors:

```text
mixer:<index>/slot:<slot>
-> unique FL Mixer track name
-> runtime UUID
-> unique Analyzer display name
```

Never guess instance mapping from spectrum, chroma, or musical role when Identify is available.

Runtime UUIDs and bindings are session-scoped. If a plugin instance is recreated or the project is reopened, rediscover the binding.

A deterministic current-session binding does **not** become persistent track identity.

## 3. Analysis Profile is a measurement-performance control

```text
Parameter ID: analysis_profile
Display name: Analysis Profile

0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

`Full` is the compatibility default.

Profiles change Analyzer computation only. They do not change the audio signal or artistic quality.

Minimum profile examples:

```text
Transport / signal / Peak-RMS-Crest   Eco
LUFS / True Peak                      Balanced
Spectrum / basic masking              Balanced
Deep Mid/Side / stereo                Balanced
Temporal                              Mix
Tonal / chroma / harmonic             Full
```

Analyzer-owned write tools:

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

These are the **only** Analyzer-owned write tools. Never expand this exception into EQ, compression, gain, pan, routing, synth, automation, or project-state writes.

Keep separate:

```text
control_acknowledged = target VST3 accepted/applied the Profile request
telemetry_confirmed  = a fresh measurement frame reports the Profile
```

No ACK means no confirmed change. Older VST3 builds may lack the local receiver.

## 4. Song Memory and transport epochs

Use:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
```

A `transport_epoch` is one **instance-local continuous playback pass**.

Playback start, seek, loop jump, or another detected discontinuity may create a new epoch.

Never require equal numeric epochs across independently loaded Analyzer instances. Cross-track retained analysis aligns by overlapping DAW-time coverage.

Song Memory:

```text
canonical bin size   1 second
coverage slot        100 ms
retained bins        up to 1200 / instance
scope                current MCP session
```

Song Memory is not yet partitioned by a stable project ID. After a project switch/reopen while MCP keeps running, retained state must be treated as potentially belonging to an earlier project until exact identity is available or the MCP session is restarted.

Keep data-quality concepts separate:

```text
estimated_analysis_lag_ms
  Analyzer FIFO + analysis-window estimate only.

data_age_seconds
  Wall-clock age of retained evidence.

dropped_blocks
  Cumulative Analyzer FIFO push failures.

coverage_ratio
  Fraction of the requested interval represented by retained coverage slots.
```

Missing coverage is not silence.

Transport coordinates are suitable for song/section/range reasoning, not sample-accurate editing or phase alignment.

## 5. Explainable structure

```text
audio_section_map(...)
```

The section detector combines available retained evidence such as activity, energy/loudness, spectral balance, chroma, stereo, crest and temporal change.

Returned `boundary strength` is structural novelty evidence, not a calibrated formal-boundary probability.

Neutral recurring families:

```text
S01 A
S02 B
S03 A
```

Never automatically translate them to Intro/Verse/Chorus/Drop.

Exact DAW markers, Playlist/arrangement labels, MIDI/project annotations, or explicit user structure are authoritative for exact names.

### Track Story

```text
audio_track_story(track, map_id)
```

Use it for one track across sections. It exposes:

```text
activity
RMS / LUFS-S / crest
spectral centroid / coarse regions
stereo correlation / width
temporal flux
chroma / strongest pitch classes
coverage / lag / drops
current-minus-previous deltas
same-family per-dimension variation
relative extrema
```

Rules:

```text
missing coverage != silence
low active_ratio != muted
low-frequency energy != Bass role
A/B/C != Intro/Verse/Chorus
descriptor delta != required processing move
```

Do not invent one overall track consistency/quality score.

### Section-aware relationships

```text
audio_section_relationships(...)
```

Use it to shortlist bounded track pairs across sections/families.

`shortlist_priority` is inspection priority only. It is not masking probability, audibility probability, mix-problem probability, quality score, or a processing recommendation.

Directional descriptors such as B-minus-A preserve numeric direction only; they do not say which track should be processed.

Detailed `audio_masking_evidence()`, `audio_stereo_compare()` and `audio_temporal_compare()` remain recent-window tools. Do not claim their current results describe a historical section unless the DAW is actually replaying/measuring that passage.

## 6. Validate evidence before interpreting it

Inspect relevant validity/coverage fields:

```text
signal_present
analysis_valid
active_ratio
analysis_features
coverage_ratio
data_age_seconds
estimated_analysis_lag_ms
dropped_blocks
warnings
```

The feature mask / retained field availability is authoritative. Disabled or unmeasured families are unavailable, not zero.

For historical range evidence, use what was actually retained in that pass. Do not use the **current** live Analysis Profile as proof of what was measured earlier.

Before reusing historical project-level evidence across a reopen/switch, inspect `audio_project_identity_status()` and require a trustworthy external project identity or a clean MCP session boundary.

## 7. Choose the smallest evidence tool

Recent stable single track:

```text
audio_average(track, seconds=5)
```

Current frame:

```text
audio_snapshot(track)
```

Temporal:

```text
audio_temporal_profile(...)
audio_temporal_compare(...)
```

Masking:

```text
audio_project_masking_scan(...)
audio_masking_evidence(...)
```

Stereo:

```text
audio_stereo_profile(...)
audio_stereo_compare(...)
```

Tonal:

```text
audio_tonal_profile(...)
audio_tonal_compare(...)
```

Master technical summary:

```text
audio_master_status(...)
```

These tools provide evidence, not automatic processing instructions.

## 8. Snapshot A/B

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

Use comparable passages and feature availability.

Snapshot deltas are `After - Before`.

Snapshots are MCP-session memory and are not currently tagged with a stable project identity. Do not compare a snapshot created before a project switch/reopen with a new snapshot unless an authoritative external project identity proves they belong together.

Snapshots are still recent-window evidence and are not a substitute for transport-anchored same-range verification when the exact DAW passage matters.

## 9. Closed-loop verification

When coordinating a real DAW/plugin modification through an external control MCP, **prefer same-range verification whenever an explicit passage is known**.

### 9.1 Transport-anchored same-range verification

```text
audio_begin_range_verification(
  label,
  start_seconds,
  end_seconds,
  target_selectors=None,
  minimum_coverage=...
)
-> inspect ready_for_external_change / baseline_blockers
-> external DAW-control MCP performs the real write
-> external DAW-control MCP reads actual host state back
-> replay the returned effective_range
-> audio_complete_range_verification(
     verification_id,
     change_summary="...",
     host_readback="..."
   )
```

Key rules:

```text
requested fractional range != fake sub-second precision
effective range = normalized one-second Song Memory bins
pass selection = coverage first, recency second
epoch IDs remain instance-local
After must be first-observed after the frozen receive-time fence
pre-change retained bins cannot silently become After
missing coverage != silence
active_ratio is descriptive, not passage identity
```

Historical feature comparability is based on measurement fields actually retained in Before and After, not the current live Profile.

A higher cumulative dropped-block count in the selected After evidence is a data-quality regression and blocks a controlled comparison.

Do **not** report arbitrary-range LUFS-I delta. Current retained `lufs_i_latest` is pass-cumulative, not an isolated integrated loudness for the requested sub-range.

A same-range verification session is not proof of persistent project identity. Do not carry it across a suspected project switch/reopen unless external project identity is authoritative.

### 9.2 Recent-window verification

Fallback when explicit retained range anchoring is unavailable/unnecessary:

```text
audio_begin_verification(...)
-> external write + actual host readback
-> replay a comparable passage
-> audio_complete_verification(...)
```

This older mode uses recent windows and an active-ratio comparability guard. Do not describe it as exact same-range verification.

### Shared interpretation

`host_readback` must be actual state returned by the external DAW-control MCP, not the intended setting.

```text
controlled_comparison=true
```

means technical comparability only.

```text
closed_loop_complete=true
```

additionally requires supplied host readback.

Neither means After is better or should be kept.

Detailed rules: `references/verification-evidence.md`.

## 10. Critical distinctions

Always keep these distinct:

- runtime UUID != persistent project ID.
- runtime UUID != persistent track ID.
- a new runtime UUID != proof of a different project.
- same project reopened != same runtime UUID.
- current-session Mixer/Slot binding != persistent track identity.
- MCP session memory != project-isolated persistent memory.
- Sample Peak != True Peak.
- RMS != LUFS.
- LUFS-S != LUFS-I.
- pass-cumulative LUFS-I != arbitrary-range LUFS-I.
- spectrum dB != calibrated SPL.
- stereo correlation != Side/Mid energy.
- low correlation != anti-correlation.
- overlap/masking heuristics != audible-masking probability.
- chroma != MIDI note probability.
- tonal-center correlation != key probability.
- harmonic F0 candidate != certain musical note.
- `transport_epoch` != persistent project identity.
- `data_age_seconds` != invalid historical evidence.
- section family != semantic section name.
- Track Story activity != mute/role state.
- relationship shortlist != confirmed mix problem.
- coverage gap != silence.
- topology fingerprint != DAW project hash.
- `host_readback` != Analyzer-verified host state.
- `controlled_comparison` != artistic quality.
- `worker_load_ratio` != DAW realtime CPU.
- Analysis Profile != audio quality.
- Analyzer Profile ACK != fresh measurement telemetry.
- `null` != zero.

## 11. Boundary with FL Studio control MCP

AI Audio Analyzer MCP owns:

```text
measure
read Analyzer state
disclose current project/runtime identity guarantees
remember transport-aligned evidence
infer explainable structural boundaries / neutral recurrence families
summarize Track Story
shortlist bounded section-aware relationships
compare measurements
resolve retained DAW-time ranges
verify Before/After measurement conditions
control Analyzer Analysis Profile only
```

The DAW-control MCP owns:

```text
DAW topology / exact project data
stable project identity when available
markers / Playlist / arrangement metadata when exposed
plugin access
all non-Analyzer artistic/technical writes
actual host-state readback for those writes
transaction / rollback when implemented by that layer
```

Never invent project identity, control tools, write success, readback values, track roles, semantic section labels, or processing certainty.

## 12. Output discipline

When using Analyzer evidence, include enough provenance to audit the claim:

```text
project identity confidence when cross-session/reopen continuity matters
selector / runtime context
DAW-time range + selected local epoch when retained evidence is used
section_id / family_id / map_id when structure is used
coverage / data age / lag / drops when relevant
Analysis Profile / available feature group when relevant
measurement window/resolution
verification requested/effective range and freshness when relevant
external host-readback status when relevant
measurement value / delta
what the metric can and cannot establish
```

All LLM-facing Skill/reference content remains English-only.