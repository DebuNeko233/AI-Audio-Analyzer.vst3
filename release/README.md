# Release packaging policy

User-facing Release packages are created by:

```text
.github/workflows/release.yml
```

The normal `build` workflow is for development validation/artifacts. It is not the user distribution path.

Current product target:

```text
AI Audio Analyzer 1.2.0
MCP 1.2
OSC analysis protocol 1.2
Analyzer control protocol local revision 1
37 MCP tools
```

## Release audience

The GitHub Release is designed for people who may have **no programming experience at all**.

Expected user flow:

```text
download one ZIP
→ extract once
→ double-click installer
→ restart FL Studio
→ add generated MCP config to the intended Agent
→ import/use the Skill with the same Agent
```

Do not require users to install or understand Python, pip, venv, PyPI, source code, build tools, command-line package managers, or repository structure.

The package must include `MCP-SETUP.md`, which explains how to attach the installed MCP server to an MCP-capable Agent/client and provides copyable Windows/macOS JSON examples. The installer-generated `cherry-studio-mcp.json` remains preferred because it contains the real absolute executable path for that computer.

## Supported targets

```text
Windows x64
macOS Apple Silicon arm64
```

Intel/x86_64 macOS is intentionally not packaged.

## MCP runtime

The MCP executable is built with PyInstaller one-file mode:

```text
-F / --onefile
```

Build-time source entrypoint remains:

```text
mcp/server.py
```

MCP 1.2 imports all required feature modules, including:

```text
performance_tools.py
control_tools.py
song_tools.py
section_tools.py
track_story_tools.py
verification_tools.py
```

into the single executable. Python may be used by the build pipeline, but the **user package must not contain MCP Python source or repository test code**.

`mcp/ci_regression.py` is CI-only and must never be shipped to ordinary users.

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
mcp/ci_regression.py
inner Release ZIP files
```

`MCP-SETUP.md` is beginner-facing installation material, not a developer source configuration file, and is required in the Release.

## Licensing

AI Audio Analyzer project code is released under the **MIT License**. The repository-root `LICENSE` file is authoritative and must be copied unchanged into every Windows and macOS user package.

Third-party components retain their own licenses.

## Single-compression rule

Platform jobs stage ordinary directories. The publish job downloads those directories and creates each final Release ZIP exactly once.

The final Release ZIP must not contain another `.zip` file. GitHub Actions artifacts are transport containers only, not another user-facing archive layer.

## Required validation

Before publication, verify at least:

```text
source MCP syntax/self-test
MCP 1.2 exact 37-tool registry
Analyzer control revision 1 parser / deterministic candidate-port regression
historical measurement/evidence regressions
transport 1.2 parser + Song Memory regressions
transport epoch separation / coverage regressions
section-boundary + recurring-family synthetic regression
end-to-end section tools through real OSC parser/Song Memory
cross-instance section alignment with different epoch IDs
Track Story synthetic adjacent-delta / low-coverage / family-spread regression
Track Story end-to-end regression on a section map with different per-instance epoch IDs
closed-loop verification positive/negative regressions
adaptive Full/Eco validity regressions
PyInstaller -F one-file build
packaged MCP native self-test
no PyInstaller _internal tree
Windows x64 VST3 build
macOS arm64 VST3 build/signature
Analyzer profile-control receiver builds on both supported VST3 targets
Windows installer parse
macOS installer syntax
MCP-SETUP.md present in both staged/final packages
MIT LICENSE present in both staged/final packages
no MCP source/developer/test files
no nested ZIP
final checksums
Release draft/prerelease/public state matches workflow inputs
```

`-F / --onefile` is a Release invariant. If `_internal/` appears in staged/final user content, the package is invalid.

A successful source self-test does not prove PyInstaller, VST3, package assembly, asset upload, or publication state succeeded.

## Adaptive-analysis and Analyzer-owned control note

Release notes may explain:

```text
Eco
Balanced
Mix
Full
```

Keep the explanation user-oriented:

- profiles affect Analyzer measurement workload only;
- they do not change/process the audio;
- Full remains the compatibility default;
- `audio_set_analysis_profile()` can change one live Analyzer's own profile;
- `audio_set_project_analysis_profile()` can change selected/all live Analyzer profiles;
- control is loopback-only, runtime-UUID addressed, and returns an explicit ACK;
- profile application occurs outside the realtime audio callback;
- no extra installation step is required.

Keep `control_acknowledged` distinct from `telemetry_confirmed`: ACK proves the live VST3 accepted/applied the request, while telemetry confirmation requires a measurement frame reporting the requested profile.

Do not market `worker_load_ratio` as DAW audio-thread CPU. Do not imply a fixed CPU reduction percentage.

The Analyzer-owned profile control is the **only Analyzer MCP write exception**. It must never be broadened into general DAW/plugin control. EQ, compression, gain, pan, routing, automation, synth parameters, project edits and other sound-changing/technical writes remain the responsibility of the actual DAW-control MCP.

Older VST3 builds that do not implement control revision 1 must time out cleanly; never report a write as successful without ACK.

## Transport-aware Song Memory user-facing note

MCP/OSC 1.2 provides latency-resilient whole-song context:

```text
audio_song_status
audio_song_overview
audio_song_timeline
```

Release notes may explain:

- Analyzer remembers measured evidence against the DAW timeline while the LLM is thinking or using other tools;
- playback starts/seeks/loop jumps create separate continuous playback epochs;
- the worker exposes estimated Analyzer backlog and dropped-block telemetry;
- Song Memory uses observed coverage and is bounded/session-scoped;
- transport coordinates are suitable for whole-song/section reasoning, not sample-accurate editing.

Do not market `estimated_analysis_lag_ms` as total Agent/network latency. Do not claim Song Memory removes all latency; it makes delayed perception **recoverable and auditable**.

## Explainable song-structure and Track Story user-facing note

The current MCP 1.2 runtime additionally exposes:

```text
audio_section_map
audio_section_profile
audio_track_story
37 total MCP tools
```

These layers consume existing Song Memory and therefore do not change OSC analysis protocol 1.2.

Release notes may explain:

- Analyzer can identify section-scale change points from multiple measured evidence families;
- repeated sections can be grouped into neutral A/B/C/... structural families;
- section profiles expose per-track evidence for a selected song range;
- Track Story follows one Analyzer instance across the map and reports coverage-aware section observations, adjacent-section deltas, recurring-family per-dimension variation and relative extrema;
- supporting/target tracks are matched by overlapping DAW time rather than requiring equal instance-local epoch numbers;
- a Track Story target can resolve its own best-overlapping retained epoch even when it was not part of the map's original supporting-track set;
- missing Song Memory is reported as missing coverage rather than interpreted as silence/inactivity/structure;
- the feature is explainable and lightweight; no neural structure model is required for this implementation.

Do **not** market A/B/C as automatic Verse/Chorus/Drop detection. Do not market Track Story as automatic Bass/Vocal/Drums role recognition or as an automatic processing recommender. Exact DAW markers/project labels/track names remain authoritative when available. Boundary strength, family similarity and Track Story comparisons are descriptive/heuristic evidence, not calibrated probabilities or artistic judgments.

## Analyzer control protocol compatibility

The Analyzer-owned profile-control path is separate from `/aianalyzer/frame` and must not repurpose or append analysis-frame indexes merely to support control.

Current control contract:

```text
transport       UDP loopback only
revision        1
scope           Analysis Profile only
identity        live runtime UUID
ACK             explicit request-scoped acknowledgement
```

The analysis OSC frame remains protocol 1.2 with existing indexes `0..149` unchanged.

## Closed-loop verification note

The Release includes controlled measurement verification around changes made by an external DAW-control MCP.

Do not market `controlled_comparison=true` as “the change is better”. It only means technical comparability guardrails passed.

`closed_loop_complete=true` additionally requires caller-supplied actual host readback; it still does not mean artistic success.

Current verification remains recent-window based; do not claim transport-anchored same-range verification until implemented.

## Draft / prerelease semantics

`draft=true` means the Release is intentionally a **Draft**. It is not public and does not become GitHub's Latest release.

When a tag already exists, the workflow must synchronize assets, notes, draft state and prerelease state. Rerunning the same tag with Draft OFF should explicitly publish an existing Draft when requested.

## Historical Release-pipeline validation record

The beginner packaging pipeline has been exercised on both supported platforms, including PyInstaller `-F`, native runtime self-tests, VST3 builds, source/`_internal`/nested-ZIP rejection, final compression, checksums and asset upload.

Packaging success and public publication state remain separate concerns.

## macOS signing

Current macOS builds are ad-hoc signed and are **not Apple Developer ID notarized**. Documentation must not claim notarization until the workflow really performs and verifies it.

## Documentation rule

When Release layout, version metadata, installation behavior, publication semantics, tool count or public capability changes, review together:

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

User-facing Release docs should explain what the person needs to click and how to attach the generated MCP configuration to the intended Agent, not how the software was built.
