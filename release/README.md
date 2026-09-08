# Release packaging policy

User-facing Release packages are created by:

```text
.github/workflows/release.yml
```

The normal `build` workflow is for development validation/artifacts, not final user distribution.

Current target:

```text
AI Audio Analyzer 1.2.0
MCP 1.2
OSC analysis protocol 1.2
Analyzer control protocol local revision 1
47 MCP tools
16 MCP guide resources
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
mcp/dynamics_regression.py
mcp/mono_compatibility_regression.py
mcp/reference_regression.py
```

Regression/test Python files must never be shipped to ordinary users.

## MCP Self-Describing API

The Release MCP must remain understandable without requiring a client-imported Skill.

Required protocol-facing layers:

```text
Server instructions
non-empty description for every one of the 47 MCP Tools
16 discoverable aianalyzer://guide/* Resources
```

The packaged/repository `skills/ai-analyzer-flstudio/SKILL.md` and `references/*.md` remain the canonical long-form content source. MCP Resources read those same files on demand.

The complete beginner Release must include the physical `skill/` directory and must fail package validation if canonical guide files are unavailable.

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
MCP 1.2 exact 47-tool registry
non-empty Tool descriptions for all tools
non-empty Server instructions
exact 16-guide Resource registry + descriptions
source/repository guide lookup
packaged/final-Release guide lookup with AI_ANALYZER_REQUIRE_GUIDES=1
project/runtime identity disclosure regression
Analyzer control revision 1 regression
transport parser + Song Memory coverage/epoch regressions
section boundary/recurrence regressions
Track Story regression
Section Relationship regression
recent-window verification regressions
transport-range verification regression
P6a dynamics distribution regression
P7a mono compatibility regression
P8a reference comparison regression
P8a pure-gain absolute-vs-normalized behavior
P8a missing feature families remain unavailable
P8a no automatic match / quality score semantics
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

## Identity and retained-state note

`audio_project_identity_status()` currently reports no stable project identity.

Release docs must preserve:

- `runtime_id` is live plugin-instance identity, not persistent project/track identity;
- reopening the same project creates new runtime UUIDs;
- a new UUID does not prove another project opened;
- current Mixer/Slot bindings are session locations, not persistent identity;
- MCP session memory can remain after a project switch/reopen;
- Song Memory, Section Maps, snapshots, relationships, P8a references and verification sessions are not partitioned by a stable Project ID;
- restart Analyzer MCP after changing/reopening projects when strict state isolation is required and authoritative identity is unavailable.

## Analysis Profile note

`Eco / Balanced / Mix / Full` are Analyzer measurement-performance profiles only.

`audio_set_analysis_profile()` and `audio_set_project_analysis_profile()` may change only Analyzer's own `analysis_profile` through loopback-only control with explicit ACK.

Keep `control_acknowledged` distinct from `telemetry_confirmed`. Do not market `worker_load_ratio` as DAW realtime audio-thread CPU.

## Song Memory / structure note

MCP/OSC 1.2 provides transport-aware retained evidence.

User-facing claims must preserve:

- Song Memory is bounded and MCP-session scoped;
- transport epochs are instance-local;
- transport coordinates are not sample-accurate;
- missing coverage is not silence;
- A/B/C recurrence families are not automatic Verse/Chorus/Drop names;
- Track Story does not infer roles or prescribe processing;
- relationship `shortlist_priority` is an inspection heuristic;
- detailed masking/stereo/temporal pair tools remain recent-window based.

## P6a dynamics note

P6a is MCP-side and adds no new realtime DSP or OSC fields.

Do not relabel LUFS-S P90-P10 as standardized EBU LRA. Arbitrary-range Integrated LUFS and PLR remain unavailable until authoritative compatible-scope measurement exists.

## P7a mono note

P7a is MCP-side and reuses current Mid/Side evidence.

Do not interpret `inspection_priority` as a quality score/probability. Historical arbitrary Section 32-band mono evidence and direct mono Sample Peak/True Peak are unavailable in P7a.

## P8a reference note

P8a adds:

```text
audio_capture_reference(...)
audio_list_references()
audio_compare_reference(...)
aianalyzer://guide/reference-comparison
```

It stores compact derived measurement profiles only, never source audio.

User-facing claims must preserve:

- current references are frozen and MCP-session scoped;
- capture is recent-window and does not prove whole-song coverage;
- comparison direction is target-minus-reference;
- RMS-level-normalized spectrum is a comparison view only and applies no gain;
- a difference from the reference is not automatically a defect;
- no automatic EQ/master matching, quality score or processing recommendation is emitted;
- no cross-song Section semantic equivalence is assumed;
- persistent libraries, historical arbitrary Section 32-band reference capture, and external-file fast scan remain future work.

## Protocol/version note

P8a adds no VST3 DSP, GUI, OSC fields or Analyzer control field. OSC 1.2 indexes `0..149` remain unchanged, so no protocol/version bump is justified by P8a alone.