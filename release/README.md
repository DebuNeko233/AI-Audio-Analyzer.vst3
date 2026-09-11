# Release packaging policy

User-facing Release packages are created by `.github/workflows/release.yml`. The normal `build` workflow is for development validation/artifacts, not final user distribution.

Current P4b PR #36 target:

```text
AI Audio Analyzer 1.2.0
MCP 1.2
OSC analysis protocol 1.2
Analyzer control protocol local revision 1
48 MCP tools
16 MCP guide resources
```

## Audience and package rule

GitHub Release is designed for users with **no programming experience**.

Expected flow:

```text
download one platform ZIP
-> extract once
-> run installer
-> restart/rescan FL Studio if needed
-> add generated MCP config to the Agent
-> optionally import packaged Skill
```

Do not require Python, pip, venv, source code, build tools, package managers or repository knowledge for normal use.

Supported targets:

```text
Windows x64
macOS Apple Silicon arm64
```

Intel/x86_64 macOS is not packaged.

## Runtime packaging

Release MCP uses PyInstaller one-file mode:

```text
-F / --onefile
```

Stable source entrypoint:

```text
mcp/server.py
```

Current runtime modules include:

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
historical_detail_store.py
historical_detail_profile.py
historical_detail_pair.py
historical_detail_tools.py
section_tools.py
track_story_tools.py
section_relationship_tools.py
verification_tools.py
range_tools.py
range_verification_tools.py
dynamics_tools.py
mono_compatibility_tools.py
reference_tools.py
```

Repository-only regressions include:

```text
mcp/ci_regression.py
mcp/relationship_regression.py
mcp/range_verification_regression.py
mcp/p4b_regression.py
mcp/dynamics_regression.py
mcp/mono_compatibility_regression.py
mcp/reference_regression.py
```

Regression/test Python files must never ship in beginner Releases.

## Self-describing MCP

The Release MCP must remain understandable without client-side Skill import.

Required protocol-facing layers:

```text
Server instructions
non-empty descriptions for all 48 MCP Tools
16 discoverable aianalyzer://guide/* Resources
```

The packaged `skill/` directory remains the canonical long-form Markdown source used by Resources and must be present in the final package.

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

Never include:

```text
mcp/source/
*.py
requirements.txt
cherry-studio.example.json
venv/
_internal/
repository regression/test scripts
nested Release ZIP files
```

`MCP-SETUP.md`, `skill/` and `LICENSE` are required.

## Required validation

Before publication verify at least:

```text
source py_compile + MCP self-test
exact 48-tool registry
non-empty Tool descriptions
non-empty Server instructions
exact 16-guide Resource registry + descriptions
source/package Guide lookup
project/runtime identity regression
Analyzer control revision 1 regression
transport/Song Memory coverage regressions
Section Map / Track Story / Relationships regressions
recent verification regression
same-range verification regression
P4b historical detail regression
P6a dynamics regression
P7a mono compatibility regression
P8a reference regression
adaptive Full/Eco validity regressions
PyInstaller -F build + packaged self-test
no _internal tree
Windows x64 VST3 build
macOS arm64 VST3 build/signature
installer syntax
no user-facing source/test files
no nested ZIP
final checksums
```

A successful source self-test alone does not prove the final user package is correct.

## Identity note

Release docs must preserve:

- `runtime_id` is live plugin-instance identity, not persistent project/track identity;
- reopening the same project creates new runtime UUIDs;
- a new UUID does not prove another project opened;
- Mixer/Slot bindings are session locations, not persistent identity;
- retained MCP state can outlive a project switch/reopen;
- retained state is not partitioned by a stable Project ID;
- restart Analyzer MCP when strict isolation is required and authoritative project identity is unavailable.

## Analysis Profile note

`Eco / Balanced / Mix / Full` are measurement-performance profiles only.

Analyzer profile tools may change only Analyzer's own `analysis_profile`. Keep `control_acknowledged` distinct from `telemetry_confirmed`.

## Song Memory / P4b note

Song Memory is bounded and MCP-session scoped:

```text
canonical bin       1 second
coverage slot       100 ms
max bins            1200 / instance
```

P4b adds `audio_historical_detail(...)` on top of the same memory and common P4 range resolver. It stores no raw audio and adds no OSC fields.

User-facing claims must preserve:

- transport epochs are instance-local;
- equal epoch numbers are not required across tracks;
- transport coordinates are not sample-accurate;
- missing coverage/detail is not silence;
- A/B/C families are not semantic Verse/Chorus/Drop labels;
- historical deep detail is one-second resolution;
- subsecond historical alignment is unsupported;
- dedicated masking/stereo/temporal tools remain recent-window APIs with finer current-frame context;
- historical mono Sample Peak / True Peak remain unavailable;
- no P4b quality score or processing recommendation exists.

Current CI memory guard reports a shallow Python container/array estimate around 1918 B/detail-bin, about 2.20 MiB at 1200 detail bins/track. This is not exact process RSS.

## P6a dynamics note

P6a is descriptive retained evidence. LUFS-S P90-P10 is not standardized EBU LRA. Arbitrary-range Integrated LUFS and PLR remain unavailable.

## P7 mono note

`audio_mono_compatibility()` remains recent-window P7a evidence.

P4b may derive historical one-second mono-fold energy from retained Mid/Side summaries via `audio_historical_detail()`. Direct mono Sample Peak/True Peak remain unavailable.

## P8a reference note

P8a references are frozen recent-window measurement profiles only:

```text
audio_capture_reference(...)
audio_list_references()
audio_compare_reference(...)
```

No source audio is stored. References are MCP-session scoped, not persistent and not whole-song truth. P4b does not silently convert P8a into historical reference capture.

Reference differences are context, not automatic EQ/master-match instructions or quality scores.

## Protocol/version note

P4b, P6a, P7a and P8a add no new OSC fields. OSC 1.2 indexes `0..149` remain unchanged, so these MCP-side additions alone do not justify an OSC/control/Product version bump.

## Merge policy

Release docs/workflow changes must follow the same repository rule: never merge a PR with pending/failing relevant CI, and never merge unless the user explicitly authorizes it in the current turn.
