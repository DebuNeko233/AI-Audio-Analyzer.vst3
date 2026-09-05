# AI Audio Analyzer Cherry Studio Skill

This Skill targets:

- Cherry Studio;
- AI Audio Analyzer VST3 1.2.0;
- AI Audio Analyzer MCP 1.2;
- optional FL Studio control MCP: https://github.com/rosasynthesiz/flstudio-mcp

Its purpose is to help an LLM call Analyzer MCP correctly, understand current project/runtime identity limits, interpret measurement validity, manage deterministic Analyzer bindings, choose only the required Analysis Profile, use transport-aware Song Memory, explainable section structure, Track Story, bounded section-aware relationships, and auditable Before/After verification around externally controlled DAW changes.

It does **not** prescribe a mixing style, LUFS target, EQ/compression/sidechain/stereo recipe, semantic section label, track role, key/harmony edit, or mastering chain.

## Current capability layers

```text
Project/runtime identity-scope disclosure
Signal State / runtime UUID
Identify -> FL Mixer Track/Slot deterministic mapping
Project Status / Mix Overview / Snapshot A-B
Adaptive Analysis + worker/FIFO telemetry
Analyzer-owned loopback Analysis Profile control + ACK
DAW Transport / instance-local playback epochs / Song Memory
Explainable section boundaries / neutral A-B-C recurrence families
Track Story across sections/families
Bounded Section-aware Mix Relationships
Temporal / Masking / Mid-Side / Stereo / Tonal evidence
Recent-window verification
Transport-anchored same-range verification
```

OSC analysis protocol remains append-only **1.2**, indexes `0..149` unchanged. Analyzer-owned Profile control remains separate local revision 1.

MCP 1.2 exposes **42 tools**.

## Recommended initialization

First inspect current identity guarantees:

```text
audio_project_identity_status()
```

Current expected result includes:

```text
stable_project_id = null
project_identity_confidence = UNRESOLVED
runtime_id scope = live_plugin_instance
runtime_id persistent = false
same-project reopen UUID stable = false
binding scope = mcp_session
cross-project retained-state isolation = not guaranteed
```

Therefore:

- reopening the same project recreates Analyzer runtime UUIDs;
- a new runtime UUID does not prove a different project was opened;
- retained MCP state may survive a DAW project switch while MCP keeps running;
- until exact project identity exists, do not silently reuse old Song Memory / Section Map / Snapshot / Relationship / Verification state after a switch/reopen;
- restart Analyzer MCP when changing/reopening projects if strict state isolation is required.

Then inspect current-session project readiness:

```text
audio_project_status()
```

If instances are unbound:

```text
real DAW-control MCP locates Mixer Track / Slot
-> toggle target Analyzer Identify
-> audio_last_identify()
-> audio_bind_last_identified(...)
-> audio_instance_map()
```

After binding, prefer selectors such as:

```text
mixer:<index>/slot:<slot>
```

Bindings are deterministic within the current MCP session but are not persistent track identity.

For whole-song/past-passage work:

```text
audio_song_status()
-> audio_section_map() when enough of the pass is retained
```

Then choose the smallest query:

```text
audio_track_story(...)           one track across sections
audio_section_profile(...)       many tracks inside one section
audio_section_relationships(...) bounded pair shortlist
audio_song_timeline(...)         raw DAW-time history only when needed
```

## Analysis Profile

```text
0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

Use the minimum profile that provides required evidence.

```text
audio_set_analysis_profile(...)
audio_set_project_analysis_profile(...)
```

These are the only Analyzer-owned write tools. They change measurement computation only, not audio.

Keep separate:

```text
control_acknowledged
telemetry_confirmed
```

All EQ, compression, gain, pan, routing, synth, automation, arrangement and other project/sound writes remain external.

## Song Memory / structure semantics

- `transport_epoch` is an instance-local continuous playback pass;
- cross-track retained analysis aligns by DAW-time overlap, not equal epoch numbers;
- missing coverage is not silence;
- `estimated_analysis_lag_ms` is Analyzer-side lag, not total Agent/network latency;
- transport coordinates are not sample-accurate editing coordinates;
- A/B/C families are neutral recurrence labels, not automatic Intro/Verse/Chorus/Drop;
- Track Story does not infer Bass/Vocal/Drums roles or one overall quality score;
- relationship `shortlist_priority` is inspection priority, not masking/mix-problem probability or processing advice;
- detailed masking/stereo/temporal pair tools remain recent-window based;
- Song Memory is MCP-session state and is not yet partitioned by a stable Project ID.

Exact DAW/project metadata wins for exact markers, labels, routing, plugin state and symbolic information when available.

## Verification

Use verification when the Agent coordinates a real DAW/plugin change through an external control MCP.

### Prefer same-range verification for a known passage

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
-> audio_complete_range_verification(..., host_readback="...")
```

Important behavior:

- fractional requests are normalized explicitly to one-second retained Song Memory bins;
- pass selection is coverage-first, recency second;
- different Analyzer instances may select different local epoch numbers;
- After must come from a clean retained pass first observed after the baseline receive-time fence;
- pre-change Song Memory cannot silently become After;
- retained field availability, not current live Profile, determines historical feature comparability;
- higher selected After dropped-block evidence blocks a controlled comparison;
- arbitrary-range LUFS-I is not fabricated from pass-cumulative `lufs_i_latest`.

A same-range verification is not persistent project identity. Do not continue an old verification across a suspected project switch/reopen without authoritative external project identity.

### Recent-window fallback

```text
audio_begin_verification(...)
-> external write + actual host readback
-> replay a comparable recent passage
-> audio_complete_verification(...)
```

Do not describe this older path as exact DAW-time same-range verification.

For both modes:

```text
controlled_comparison=true
```

means technical comparability only.

```text
closed_loop_complete=true
```

additionally requires caller-supplied actual host readback.

Neither means After sounds better or should be kept, and neither establishes persistent project identity.

See `references/verification-evidence.md`.

## Validity checklist

When relevant inspect:

```text
project_identity_confidence
runtime identity scope
signal_present
analysis_valid
active_ratio
analysis_features
coverage_ratio
data_age_seconds
estimated_analysis_lag_ms
dropped_blocks
section/map warnings
selected transport epoch
verification requested/effective range
verification freshness/comparability fields
```

`null` means unavailable, not zero.

Historical feature availability comes from retained evidence, not whatever Analysis Profile happens to be active now.

## Suggested Agent instruction

```text
Use the ai-analyzer-flstudio Skill only as a technical MCP usage and evidence-semantics reference.
At the start of a session and whenever the user may have switched or reopened a DAW project, call audio_project_identity_status before assuming any retained-state continuity. runtime_id is a live plugin-instance identifier only, reopening the same project recreates runtime UUIDs, and a new UUID does not prove the project changed. Until exact external project identity is available, do not reuse old project-level retained state across a switch/reopen; restart Analyzer MCP when strict isolation is required.
Then call audio_project_status and establish deterministic Identify bindings when needed.
For whole-song or historical work, use audio_song_status and then audio_section_map when enough Song Memory exists. Use Track Story for one track across sections, Section Profile for many tracks inside one section, and Section Relationships only as a bounded inspection shortlist.
Treat A/B/C as neutral recurrence labels, missing coverage as missing evidence, and transport_epoch as instance-local.
When verifying a real DAW change over a known passage, prefer audio_begin_range_verification / audio_complete_range_verification and replay the returned effective_range after the external write/readback. Do not reuse pre-change retained evidence as After, do not fabricate arbitrary-range LUFS-I, and do not treat controlled_comparison as artistic success or persistent project identity.
Use recent-window verification only when explicit retained DAW-time anchoring is impractical.
Analyzer MCP may write only its own Analysis Profile; all sound/project writes and actual host readback belong to the real DAW-control layer.
```