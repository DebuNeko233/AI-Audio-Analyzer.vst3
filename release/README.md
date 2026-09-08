# Release packaging policy

User-facing Release packages are created by:

```text
.github/workflows/release.yml
```

The normal `build` workflow is for development validation/artifacts, not final user distribution.

Current P6a branch target:

```text
AI Audio Analyzer 1.2.0
MCP 1.2
OSC analysis protocol 1.2
Analyzer control protocol local revision 1
43 MCP tools
14 MCP guide resources
```

## Release audience

GitHub Release is designed for users with **no programming experience**.

Expected flow:

```text
download one platform ZIP
-> extract once
-> double-click installer
-> restart/rescan FL Studio if needed
-> add generated MCP config to the intended Agent
-> optionally import the packaged Skill when useful for that client
```

Do not require Python, pip, venv, source code, build tools, package managers, repository knowledge, or client-side Skill import for basic MCP use.

## Supported targets

```text
Windows x64
macOS Apple Silicon arm64
```

Intel/x86_64 macOS is not packaged.

## MCP runtime

Release MCP uses PyInstaller one-file mode:

```text
-F / --onefile
```

Stable source entrypoint:

```text
mcp/server.py
```

Runtime modules include:

```text
analyzer_core.py
self_description.py
project_tools.py
project_identity_tools.py
temporal_tools.py
masking_tools.py
stereo_tools.py
semantic_tools.py
performance_tools.py
control_tools.py
song_tools.py
section_tools.py
track_story_tools.py
section_relationship_tools.py
verification_tools.py
range_tools.py
range_verification_tools.py
dynamics_tools.py
```

Repository-only regressions include:

```text
mcp/ci_regression.py
mcp/relationship_regression.py
mcp/range_verification_regression.py
mcp/dynamics_regression.py
```

Regression/test Python files must never be shipped to ordinary users.

## MCP Self-Describing API

The Release MCP must remain understandable without requiring a client-imported Skill.

Required protocol-facing layers:

```text
Server instructions
non-empty description for every MCP Tool
14 discoverable aianalyzer://guide/* Resources
```

The packaged/repository `skills/ai-analyzer-flstudio/SKILL.md` and `references/*.md` remain the canonical long-form content source. MCP Resources read those same files on demand instead of maintaining a second long-form copy in Python.

Release rules:

- the physical `skill/` directory remains required in the complete user package because it supplies canonical Resource content and can also be imported by Skill-capable clients;
- importing the Skill into the client is optional for basic MCP use;
- clients with MCP Resources should read `aianalyzer://guide/index` and only the guides needed for the current task;
- clients without Resource support may import `skill/` to receive the same long-form guidance;
- if guide files are unavailable at runtime, Server instructions and Tool descriptions remain the minimum fallback, but the complete beginner Release must fail validation rather than ship without the guide files.

## User package layout

Windows:

```text
AI Audio Analyzer.vst3
mcp/ai-audio-analyzer-mcp.exe
skill/
Install.cmd
Install.ps1
START-HERE.md
MCP-SETUP.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
```

macOS Apple Silicon:

```text
AI Audio Analyzer.vst3
mcp/ai-audio-analyzer-mcp
skill/
Install.command
install.sh
START-HERE.md
MCP-SETUP.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
```

The following must **never** appear in a user Release:

```text
mcp/source/
*.py
requirements.txt
cherry-studio.example.json
venv/
_internal/
repository regression/test scripts
inner Release ZIP files
```

`MCP-SETUP.md`, `skill/`, and `LICENSE` are required.

## Single-compression rule

Platform jobs stage ordinary directories. The publish job creates each final user ZIP exactly once.

A final Release ZIP must not contain another `.zip` file. GitHub Actions artifacts are transport containers only.

## Required validation

Before publication verify at least:

```text
source MCP py_compile/self-test
MCP 1.2 exact 43-tool registry
non-empty Tool descriptions for all 43 tools
non-empty Server instructions
exact 14-guide Resource registry + descriptions
source/repository guide lookup
packaged/final-Release guide lookup with AI_ANALYZER_REQUIRE_GUIDES=1
project/runtime identity disclosure regression
Analyzer control revision 1 regression
historical evidence regressions
transport parser + Song Memory coverage/epoch regressions
section boundary/recurrence regressions
Track Story regression
Section Relationship regression
recent-window verification regressions
transport-range verification regression
P6a dynamics distribution regression
range normalization / coverage-first pass selection
post-baseline After freshness fence
cross-instance different-epoch same-range comparison
coverage-weighted P6a percentile determinism
low-coverage-bin rejection / missing-is-not-silence
LUFS-S-unavailable handling
standardized LRA / arbitrary-range Integrated LUFS / PLR remain unavailable in P6a
adaptive Full/Eco validity regressions
PyInstaller -F one-file build
packaged runtime native self-test
no _internal tree
Windows x64 VST3 build
macOS arm64 VST3 build/signature
Windows installer parse
macOS installer syntax
MCP-SETUP.md + Skill guides + LICENSE present
no MCP source/developer/test files
no nested ZIP
final checksums
Release draft/prerelease/public state matches workflow inputs
```

A successful source self-test alone does not prove PyInstaller, guide lookup, VST3, package assembly, or publication succeeded.

## Project/runtime identity note

Release and Skill docs must expose the current limitation instead of implying persistent project identity.

`audio_project_identity_status()` reports the machine-readable contract:

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
project_switch_detection                not_available
runtime_id scope                        live_plugin_instance
runtime_id persistent                   false
same-project reopen UUID stable         false
binding scope                           mcp_session
cross-project retained-state isolation  not guaranteed
```

User-facing claims must preserve:

- reopening the same project recreates Analyzer runtime UUIDs;
- a new runtime UUID does not prove that the DAW project changed;
- current Mixer/Slot bindings are deterministic session locations, not persistent track identity;
- MCP session memory can remain after a DAW project switch/reopen while MCP keeps running;
- retained Song Memory, Section Maps, snapshots, relationships and verification sessions are not yet partitioned by a stable project ID;
- until exact external project identity is integrated, restart Analyzer MCP after changing/reopening projects when strict state isolation is required;
- never manufacture a Project ID from runtime UUID, BPM, names, track count, topology fingerprint, Mixer index or transport epoch.

This disclosure does not claim automatic project-switch detection or automatic cache clearing.

## Analysis Profile note

Release notes may explain `Eco / Balanced / Mix / Full` as Analyzer measurement-performance profiles only.

`audio_set_analysis_profile()` and `audio_set_project_analysis_profile()` may change only Analyzer's own `analysis_profile` parameter through loopback-only local control with explicit ACK.

Keep `control_acknowledged` distinct from `telemetry_confirmed`.

Do not market `worker_load_ratio` as DAW realtime audio-thread CPU or claim fixed CPU reduction percentages.

This Profile control is the only Analyzer MCP write exception. All sound/project writes remain external.

## Song Memory / structure / relationship note

MCP/OSC 1.2 provides transport-aware retained evidence:

```text
audio_song_status
audio_song_overview
audio_song_timeline
audio_section_map
audio_section_profile
audio_track_story
audio_section_relationships
```

User-facing claims must preserve:

- Song Memory is bounded and MCP-session scoped;
- Song Memory is not yet partitioned by stable Project ID;
- transport epochs are instance-local;
- transport coordinates are not sample-accurate;
- missing coverage is not silence;
- A/B/C recurrence families are not automatic Verse/Chorus/Drop names;
- Track Story does not infer Bass/Vocal/Drums roles or prescribe processing;
- relationship `shortlist_priority` is an inspection heuristic, not masking/mix-problem probability or quality;
- detailed masking/stereo/temporal pair tools remain recent-window based.

## P6a dynamics-distribution note

MCP 1.2 P6a adds:

```text
audio_dynamics_distribution(...)
aianalyzer://guide/dynamics-evidence
```

It is MCP-side and reuses retained one-second Song Memory plus the existing transport-range resolver. No realtime VST3 DSP field or OSC schema change is required.

User-facing claims must preserve:

- supported scopes are selected retained pass span, explicit DAW-time range, and cached Section Map section;
- accepted bins must pass a per-bin coverage floor and are weighted by observed covered seconds;
- missing bins remain missing, never silence/zero;
- RMS / LUFS-S / Crest / observed per-bin Sample Peak / observed per-bin True Peak distributions are descriptive retained-observation statistics;
- dB percentiles and arithmetic dB means are not the same as power-domain means;
- `lufs_s_interpercentile_range_lu` is descriptive P90-P10 LUFS-S spread, not EBU Loudness Range;
- standardized EBU LRA is unavailable in P6a;
- arbitrary-range Integrated LUFS is unavailable because retained `lufs_i_latest` is pass-cumulative;
- arbitrary-range PLR is unavailable without scope-compatible peak and integrated-loudness evidence;
- section-to-section deltas are descriptive only;
- no fixed LUFS/LRA/PLR/Crest target or universal mastering quality score is provided.

## Closed-loop verification note

MCP 1.2 contains **two** verification paths.

Recent-window compatibility path:

```text
audio_begin_verification
audio_complete_verification
audio_verification_status
```

Transport-anchored same-range path:

```text
audio_begin_range_verification
audio_complete_range_verification
audio_range_verification_status
```

For a known musical passage, Release/Skill docs should prefer the same-range path.

Same-range public semantics:

- requested fractional boundaries remain visible;
- actual `effective_range` is normalized to one-second Song Memory bins;
- each Analyzer selects its own best retained epoch by coverage first, then recency;
- equal epoch numbers across tracks are not required;
- After must come from a clean retained pass first observed after the frozen receive-time fence;
- old Before memory cannot silently become After;
- historical feature comparability uses retained field availability rather than the current live Profile;
- higher selected After dropped-block evidence blocks a controlled comparison;
- `active_ratio` is descriptive and not used as passage identity in same-range mode;
- arbitrary-range LUFS-I delta is intentionally unavailable because current retained `lufs_i_latest` is pass-cumulative, not isolated range-integrated loudness;
- actual external host readback is still required for `closed_loop_complete=true`;
- neither verification mode establishes persistent project identity.

Never market `controlled_comparison=true` as “the change is better”. It means technical comparability only.

Never market `closed_loop_complete=true` as artistic success. It additionally means caller-supplied actual host readback was present.

## Analyzer control protocol compatibility

Analyzer Profile control is separate from `/aianalyzer/frame`.

```text
transport       UDP loopback only
revision        1
scope           Analysis Profile only
identity        live runtime UUID
ACK             explicit request-scoped acknowledgement
```

OSC analysis frame remains append-only 1.2 with existing indexes `0..149` unchanged by Track Story, relationships, range verification, identity disclosure, MCP self-description, or P6a retained dynamics distributions.

## Draft / prerelease semantics

`draft=true` means the Release is a Draft and is not public/Latest.

When rerunning an existing tag, assets, notes, draft state and prerelease state must be synchronized with workflow inputs.

## macOS signing

Current macOS builds are ad-hoc signed and are **not Apple Developer ID notarized**. Do not claim notarization until the workflow performs and verifies it.

## Documentation rule

When Release layout, metadata, installation behavior, tool count, guide-resource contract or public capability changes, review together:

```text
release/common/START-HERE.md
release/common/MCP-SETUP.md
release/common/INSTALL.en.md
release/common/INSTALL.zh-CN.md
release/windows/Install.ps1
release/macos/install.sh
README.md
README.zh-CN.md
AGENT.md
skills/ai-analyzer-flstudio/*
```

Not every file needs modification. User-facing Release docs should explain what users need to click/use, not internal build complexity.