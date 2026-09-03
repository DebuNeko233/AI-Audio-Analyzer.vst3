# Release packaging policy

User-facing Release packages are created by:

```text
.github/workflows/release.yml
```

The normal `build` workflow is for development validation/artifacts. It is not the user distribution path.

Current product target:

```text
AI Audio Analyzer 1.1.0
MCP 1.1
OSC 1.1
29 MCP tools
```

## Release audience

The GitHub Release is designed for people who may have **no programming experience at all**.

Expected user flow:

```text
download one ZIP
→ extract once
→ double-click installer
→ restart FL Studio
→ add generated Cherry Studio config / Skill
```

Do not require users to install or understand Python, pip, venv, PyPI, source code, build tools, command-line package managers, or repository structure.

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
bridge/server.py
```

MCP 1.1 imports all required feature modules, including `performance_tools.py`, into that single executable. Python may be used by the build pipeline, but the **user package must not contain MCP Python source or repository test code**.

`bridge/ci_regression.py` is CI-only and must never be shipped to ordinary users.

## User package layout

Windows:

```text
AI Audio Analyzer.vst3
mcp/ai-audio-analyzer-mcp.exe
skill/
Install.cmd
Install.ps1
START-HERE.md
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
bridge/ci_regression.py
inner Release ZIP files
```

## Licensing

AI Audio Analyzer project code is released under the **MIT License**. The repository-root `LICENSE` file is authoritative and must be copied unchanged into every Windows and macOS user package.

Third-party components and dependencies retain their own licenses; including them in or using them to build AI Audio Analyzer does not relicense those third-party works under MIT.

## Single-compression rule

Platform jobs stage ordinary directories. The publish job downloads those directories and creates each final Release ZIP exactly once.

The final Release ZIP must not contain another `.zip` file. GitHub Actions artifacts are transport containers only, not another user-facing archive layer.

## Required validation

Before publication, verify at least:

```text
source MCP syntax/self-test
MCP 1.1 exact 29-tool registry
historical measurement/evidence regressions
closed-loop verification positive/negative regressions
adaptive Full/Eco validity regressions
PyInstaller -F one-file build
packaged MCP native self-test
no PyInstaller _internal tree
Windows x64 VST3 build
macOS arm64 VST3 build/signature
Windows installer parse
macOS installer syntax
MIT LICENSE present in both staged/final platform packages
no MCP source/developer/test files
no nested ZIP
final checksums
Release draft/prerelease/public state matches workflow inputs
```

`-F / --onefile` is a Release invariant. If `_internal/` appears in staged/final user content, the package is invalid.

A successful source self-test does not prove PyInstaller, VST3, package assembly, asset upload, or publication state succeeded.

## Adaptive-analysis user-facing note

Release notes may explain that Analyzer now supports lower-cost measurement profiles for projects with many plugin instances:

```text
Eco
Balanced
Mix
Full
```

Keep this explanation user-oriented:

- profiles affect Analyzer measurement workload only;
- they do not change or process the audio;
- Full remains the compatibility default;
- the LLM/DAW-control workflow may temporarily enable a deeper profile when a requested measurement needs it;
- no additional installation step is required.

MCP 1.1 adds:

```text
audio_analysis_status
audio_project_performance
29 total MCP tools
```

Do not market `worker_load_ratio` as DAW audio-thread CPU. Do not imply a fixed CPU reduction percentage. Do not imply Analyzer MCP writes FL Studio parameters; actual profile writes/readback belong to the external DAW-control MCP.

## Closed-loop verification note

The Release also includes controlled measurement verification around changes made by an external DAW-control MCP.

Do not market `controlled_comparison=true` as “the change is better”. It only means the documented technical comparability guardrails passed.

`closed_loop_complete=true` additionally requires caller-supplied actual host readback; it still does not mean artistic success.

## Draft / prerelease semantics

`draft=true` means the Release is intentionally a **Draft**. It is not public and does not become GitHub's Latest release.

When a tag already exists, the workflow must synchronize assets, notes, draft state and prerelease state. Rerunning the same tag with Draft OFF should explicitly publish an existing Draft when that is the requested state.

## Historical Release-pipeline validation record

The complete 0.9 beginner packaging pipeline was actually exercised successfully on both supported platforms, including PyInstaller `-F`, native runtime self-tests, both VST3 builds, source/`_internal`/nested-ZIP rejection, one final compression, checksums and asset upload.

That run used `draft=true`, so packaging success and public publication remained separate states.

## macOS signing

Current macOS builds are ad-hoc signed and are **not Apple Developer ID notarized**. Documentation must not claim notarization until the workflow really performs and verifies it.

## Documentation rule

When Release layout, version metadata, installation behavior, publication semantics, or public capability changes, review together:

```text
release/common/START-HERE.md
release/common/INSTALL.en.md
release/common/INSTALL.zh-CN.md
release/windows/Install.ps1
release/macos/install.sh
README.md
README.zh-CN.md
AGENT.md
```

User-facing Release docs should explain what the person needs to click, not how the software was built.