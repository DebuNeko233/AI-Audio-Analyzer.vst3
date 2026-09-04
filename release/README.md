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
OSC 1.2
34 MCP tools
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
song_tools.py
section_tools.py
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
MCP 1.2 exact 34-tool registry
historical measurement/evidence regressions
transport 1.2 parser + Song Memory regressions
transport epoch separation / coverage regressions
section-boundary + recurring-family synthetic regression
end-to-end section tools through real OSC parser/Song Memory
cross-instance section alignment with different epoch IDs
closed-loop verification positive/negative regressions
adaptive Full/Eco validity regressions
PyInstaller -F one-file build
packaged MCP native self-test
no PyInstaller _internal tree
Windows x64 VST3 build
macOS arm64 VST3 build/signature
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

## Adaptive-analysis user-facing note

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
- an Agent/DAW-control workflow may temporarily enable deeper measurement only when needed;
- no extra installation step is required.

Do not market `worker_load_ratio` as DAW audio-thread CPU. Do not imply a fixed CPU reduction percentage. Analyzer MCP does not write FL Studio parameters.

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

## Explainable song-structure user-facing note

The current MCP 1.2 runtime additionally exposes:

```text
audio_section_map
audio_section_profile
34 total MCP tools
```

This layer consumes existing Song Memory and therefore does not change OSC 1.2.

Release notes may explain:

- Analyzer can identify section-scale change points from multiple measured evidence families;
- repeated sections can be grouped into neutral A/B/C/... structural families;
- section profiles expose per-track evidence for a selected song range;
- supporting tracks are matched by overlapping DAW time rather than requiring equal instance-local epoch numbers;
- missing Song Memory is reported as missing coverage rather than interpreted as silence/structure;
- the feature is explainable and lightweight; no neural structure model is required for this first implementation.

Do **not** market A/B/C as automatic Verse/Chorus/Drop detection. Exact DAW markers/project labels remain authoritative when available. Boundary strength and family similarity are heuristic structural evidence, not calibrated probabilities or artistic judgments.

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
