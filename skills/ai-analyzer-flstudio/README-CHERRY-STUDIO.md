# AI Audio Analyzer Cherry Studio Skill

This Skill targets:

- Cherry Studio;
- AI Audio Analyzer VST3 1.2.0;
- AI Audio Analyzer MCP 1.2;
- optional FL Studio control MCP: https://github.com/rosasynthesiz/flstudio-mcp

Its purpose is to help an LLM call Analyzer MCP correctly, understand current project/runtime identity limits, interpret measurement validity, manage deterministic Analyzer bindings, choose only the required Analysis Profile, use transport-aware Song Memory, explainable song structure, Track Story, bounded section-aware relationships, coverage-aware retained dynamics distributions, direct energy-aware mono-fold compatibility evidence, and auditable Before/After verification around externally controlled DAW changes.

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
Coverage-aware retained Dynamics Distribution
Direct recent-window Mono-fold RMS / energy-aware compatibility evidence
Temporal / Masking / Mid-Side / Stereo / Tonal evidence
Recent-window verification
Transport-anchored same-range verification
```

OSC analysis protocol remains append-only **1.2**, indexes `0..149` unchanged. Analyzer-owned Profile control remains separate local revision 1.

MCP 1.2 exposes **44 tools** and **15 Guide Resources** on the stacked P7a branch.

## MCP self-description and Skill relationship

The MCP server is designed to remain understandable even when the client has **not imported this Skill**.

The protocol-facing layers are:

```text
Server instructions
-> short global startup order and hard semantic/control rules

Tool descriptions
-> purpose and critical limitation for every one of the 44 tools

MCP Resources
-> on-demand long-form guides under aianalyzer://guide/*
```

The packaged/repository `SKILL.md` and `references/*.md` remain the **canonical long-form content source**. MCP Resources read those same files on demand; they are not a second hand-maintained copy.

Therefore:

- importing this Skill into Cherry Studio is an optional client-side enhancement, not a prerequisite for basic correct MCP use;
- a client that supports MCP Resources can read `aianalyzer://guide/index` and then only the guide relevant to the current task;
- P6a dynamics details are available from `aianalyzer://guide/dynamics-evidence`;
- P7a direct mono-fold details are available from `aianalyzer://guide/mono-compatibility`;
- do not load every guide mechanically;
- if the client does not expose MCP Resources, importing this Skill remains the preferred way to provide the full long-form guidance;
- if the physical packaged `skill` directory is missing, Server instructions and Tool descriptions still provide the minimum self-description, but detailed guide Resources are unavailable.

The normal Release still includes `skill/` because it serves both optional client-side Skill import and the canonical Markdown source for MCP guide Resources.

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
audio_dynamics_distribution(...) retained pass/range/section dynamics
audio_mono_compatibility(...)    recent direct mono-fold RMS / band-center energy evidence
audio_song_timeline(...)         raw DAW-time history only when needed
```

## Analysis Profile

```text
0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

Use the minimum profile that provides required evidence. P7a mono-fold energy evidence requires the existing stereo/spectrum family, so `Balanced` or above is sufficient.

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
- P7a mono compatibility is also recent-window based and must not be relabelled as historical/Section 32-band evidence;
- Song Memory is MCP-session state and is not yet partitioned by a stable Project ID.

Exact DAW/project metadata wins for exact markers, labels, routing, plugin state and symbolic information when available.

## Coverage-aware retained dynamics

Use:

```text
audio_dynamics_distribution(...)
```

for a selected retained transport-pass span, explicit DAW-time range or cached Section Map section. `compare_section_id` can request a descriptive section-to-section distribution shift.

P6a uses a minimum per-bin coverage floor and covered-seconds weighting. The result exposes accepted, rejected-low-coverage and missing bin counts; missing bins are not inserted as silence or zero.

Current descriptive groups include:

```text
RMS
LUFS-S
Crest
observed per-bin Sample Peak maxima
observed per-bin True Peak maxima
```

Keep these boundaries explicit:

- `lufs_s_interpercentile_range_lu` is P90(LUFS-S) - P10(LUFS-S), not standardized EBU Loudness Range;
- standardized EBU LRA is not implemented in P6a;
- arbitrary-range Integrated LUFS is unavailable because retained `lufs_i_latest` is pass-cumulative;
- arbitrary-range PLR is unavailable without scope-compatible integrated loudness and peak evidence;
- dB percentiles are not power-domain means;
- observed per-bin peak maxima are not a reconstructed sample stream;
- section deltas are descriptive evidence, not a mastering quality score or processing instruction;
- do not impose a fixed genre LUFS/LRA/PLR/Crest target.

See `references/dynamics-evidence.md`.

## Direct energy-aware mono-fold compatibility

Use:

```text
audio_mono_compatibility(track, seconds=5.0)
```

The Analyzer already defines:

```text
M = 0.5 * (L + R)
S = 0.5 * (L - R)
(L_power + R_power)/2 = M_power + S_power
```

so P7a adds no realtime DSP or OSC fields. Existing Mid RMS is the RMS of the standard `(L+R)/2` mono fold.

The current tool reports direct recent-window full-band RMS fold-down evidence and energy-aware 32 band-center evidence. It keeps direct fold-down energy separate from existing L/R correlation, Side/Mid, negative-cross and low-band stereo descriptors.

Key fields include:

```text
mono_fold_rms_db
mono_fold_rms_delta_db
mono_fold_delta_db per band center
energy_loss_fraction
relative_band_energy
inspection_priority
floor_censored
```

`inspection_priority` is only a shortlist aid. It is not a quality score, audibility probability, phase-problem probability, pass/fail threshold, or processing instruction.

If Mid reaches the Analyzer's `-120 dB` measurement floor, `floor_censored=true`; do not claim exact cancellation depth below the measurement floor.

Current P7a deliberately does **not** provide:

```text
arbitrary historical/Section 32-band mono-fold evidence
mono-fold Sample Peak
mono-fold True Peak
```

Do not infer mono peak/True Peak from stereo Peak, True Peak, RMS, correlation or Side/Mid. Direct peak/true-peak fold-down belongs to optional P7b.

Do not impose fixed rules such as `correlation < 0 = bad`, `all lows must be mono`, or `mono_fold_delta < X = fail`.

See `references/mono-compatibility.md`.

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
accepted / rejected / missing distribution bins
P7a recent window / floor_censored when mono evidence is used
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
Use AI Audio Analyzer MCP's own Server instructions and Tool descriptions as the minimum operating contract. When detailed semantics are needed, read the relevant aianalyzer://guide/* MCP Resource if the client exposes Resources; importing the ai-analyzer-flstudio Skill is an optional client-side way to provide the same long-form guidance.
At the start of a session and whenever the user may have switched or reopened a DAW project, call audio_project_identity_status before assuming any retained-state continuity. runtime_id is a live plugin-instance identifier only, reopening the same project recreates runtime UUIDs, and a new UUID does not prove the project changed. Until exact external project identity is available, do not reuse old project-level retained state across a switch/reopen; restart Analyzer MCP when strict isolation is required.
Then call audio_project_status and establish deterministic Identify bindings when needed.
For whole-song or historical work, use audio_song_status and then audio_section_map when enough Song Memory exists. Use Track Story for one track across sections, Section Profile for many tracks inside one section, and Section Relationships only as a bounded inspection shortlist. Use audio_dynamics_distribution only when retained dynamics distributions are needed; treat its LUFS-S interpercentile spread as descriptive evidence, not EBU LRA, and do not fabricate arbitrary-range Integrated LUFS or PLR.
Use audio_mono_compatibility only when recent direct mono-fold translation evidence is needed. Keep its fold-down energy separate from correlation/Side-Mid/negative-cross evidence; inspection_priority is not a quality score. Do not present recent P7a evidence as an arbitrary historical Section analysis, and do not infer mono-fold Sample Peak or True Peak because P7a does not measure them directly.
Treat A/B/C as neutral recurrence labels, missing coverage as missing evidence, and transport_epoch as instance-local.
When verifying a real DAW change over a known passage, prefer audio_begin_range_verification / audio_complete_range_verification and replay the returned effective_range after the external write/readback. Do not reuse pre-change retained evidence as After, do not fabricate arbitrary-range LUFS-I, and do not treat controlled_comparison as artistic success or persistent project identity.
Use recent-window verification only when explicit retained DAW-time anchoring is impractical.
Analyzer MCP may write only its own Analysis Profile; all sound/project writes and actual host readback belong to the real DAW-control layer.
```