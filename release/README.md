# Release packaging policy

User-facing Release packages are created by:

```text
.github/workflows/release.yml
```

The normal `build` workflow is for development validation/artifacts, not final user distribution.

Current product target:

```text
AI Audio Analyzer 1.2.0
MCP 1.2
OSC analysis protocol 1.2
Analyzer control protocol local revision 1
41 MCP tools
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
-> import the packaged Skill for the same Agent
```

Do not require Python, pip, venv, source code, build tools, package managers, or repository knowledge.

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
project_tools.py
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
```

Repository-only regressions include:

```text
mcp/ci_regression.py
mcp/relationship_regression.py
mcp/range_verification_regression.py
```

Regression/test Python files must never be shipped to ordinary users.

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

`MCP-SETUP.md` and `LICENSE` are required.

## Single-compression rule

Platform jobs stage ordinary directories. The publish job creates each final user ZIP exactly once.

A final Release ZIP must not contain another `.zip` file. GitHub Actions artifacts are transport containers only.

## Required validation

Before publication verify at least:

```text
source MCP py_compile/self-test
MCP 1.2 exact 41-tool registry
Analyzer control revision 1 regression
historical evidence regressions
transport parser + Song Memory coverage/epoch regressions
section boundary/recurrence regressions
Track Story regression
Section Relationship regression
recent-window verification regressions
transport-range verification regression
range normalization / coverage-first pass selection
post-baseline After freshness fence
cross-instance different-epoch same-range comparison
adaptive Full/Eco validity regressions
PyInstaller -F one-file build
packaged runtime native self-test
no _internal tree
Windows x64 VST3 build
macOS arm64 VST3 build/signature
Windows installer parse
macOS installer syntax
MCP-SETUP.md + LICENSE present
no MCP source/developer/test files
no nested ZIP
final checksums
Release draft/prerelease/public state matches workflow inputs
```

A successful source self-test alone does not prove PyInstaller, VST3, package assembly, or publication succeeded.

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
- transport epochs are instance-local;
- transport coordinates are not sample-accurate;
- missing coverage is not silence;
- A/B/C recurrence families are not automatic Verse/Chorus/Drop names;
- Track Story does not infer Bass/Vocal/Drums roles or prescribe processing;
- relationship `shortlist_priority` is an inspection heuristic, not masking/mix-problem probability or quality;
- detailed masking/stereo/temporal pair tools remain recent-window based.

## Closed-loop verification note

MCP 1.2 now contains **two** verification paths.

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
- actual external host readback is still required for `closed_loop_complete=true`.

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

OSC analysis frame remains append-only 1.2 with existing indexes `0..149` unchanged by Track Story, relationships, or range verification.

## Draft / prerelease semantics

`draft=true` means the Release is a Draft and is not public/Latest.

When rerunning an existing tag, assets, notes, draft state and prerelease state must be synchronized with workflow inputs.

## macOS signing

Current macOS builds are ad-hoc signed and are **not Apple Developer ID notarized**. Do not claim notarization until the workflow performs and verifies it.

## Documentation rule

When Release layout, metadata, installation behavior, tool count or public capability changes, review together:

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
