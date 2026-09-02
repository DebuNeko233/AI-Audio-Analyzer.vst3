# Release packaging policy

User-facing Release packages are created by:

```text
.github/workflows/release.yml
```

The normal `build` workflow is for development validation/artifacts. It is not the user distribution path.

Current product target: **AI Audio Analyzer 1.0.0 / MCP 1.0 / OSC 0.9**.

V1.0 intentionally leaves OSC at `0.9` because closed-loop verification is implemented in the Bridge and adds no VST3 frame fields.

## Release audience

The GitHub Release is designed for people who may have **no programming experience at all**.

The expected user flow is intentionally limited to:

```text
download ZIP
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

MCP 1.0 imports all required feature modules, including `verification_tools.py`, into that single executable. The build pipeline may use Python internally, but the **user package must not contain MCP Python source or repository test code**.

`bridge/ci_regression.py` is CI-only and must never be shipped to ordinary users.

## User package layout

Windows:

```text
AI Audio Analyzer.vst3
mcp/
└─ ai-audio-analyzer-mcp.exe
skill/
Install.cmd
Install.ps1
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
```

macOS Apple Silicon:

```text
AI Audio Analyzer.vst3
mcp/
└─ ai-audio-analyzer-mcp
skill/
Install.command
install.sh
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
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

## Single-compression rule

Do not create a final ZIP in platform packaging jobs and then upload that ZIP inside a GitHub Actions artifact.

Required pipeline:

```text
build/stage Windows directory
build/stage macOS directory
→ upload directory artifacts
→ publish job downloads those directories
→ publish job creates each final Release ZIP exactly once
```

The final Release ZIP must not contain another `.zip` file.

GitHub Actions artifacts are transport containers only. Their contents should be unpacked user-package files, not another pre-built Release archive.

## Required validation

Before publication, verify at least:

```text
source MCP syntax/self-test
MCP 1.0 / exact 27-tool registry
V0.4–V0.9 measurement/evidence regressions
V1.0 controlled-verification positive/negative regressions
PyInstaller one-file build
packaged MCP self-test on its native OS
no PyInstaller _internal tree in staged/final user package
Windows x64 VST3 build
macOS arm64 VST3 build
Windows installer parse
macOS installer syntax
macOS VST3 signature
no MCP source/developer/test files in user package
no nested ZIP in user package
final checksums
Release draft/prerelease/public state matches workflow inputs
```

`-F / --onefile` is a Release invariant: if an `_internal/` directory appears in staged or final user content, treat the package as invalid rather than silently accepting an `onedir` runtime.

A successful source self-test does not prove PyInstaller, VST3, final package assembly, asset upload, or publication state succeeded.

## Draft / prerelease semantics

Workflow input:

```text
draft = true
```

means the Release is intentionally a **Draft**. It is not public and does not become GitHub's Latest release.

The UI description should make this explicit so ordinary packaging success is not mistaken for public publication.

When a tag already exists, the Release workflow must synchronize:

```text
assets
notes
draft state
prerelease state
```

Do not assume that updating assets on an existing Draft publishes it. Rerunning the same tag with Draft OFF should explicitly turn the existing Draft into a non-draft release when the workflow is intended to publish it.

## V0.9 Release-pipeline validation record

The complete 0.9 beginner packaging pipeline was actually exercised successfully on both supported platforms:

```text
PyInstaller -F Windows x64 runtime + native self-test
PyInstaller -F macOS arm64 runtime + native self-test
Windows x64 VST3 build
macOS arm64 VST3 build/signature
beginner package staging
no source / requirements / _internal / nested ZIP checks
single final compression
SHA256 generation
GitHub Release asset upload
```

That run used `draft=true`, so `v0.9.0` was created as a Draft. Packaging success and public publication are separate states.

## V1.0 user-facing capability note

Release notes may explain that MCP 1.0 adds:

```text
audio_begin_verification
audio_complete_verification
audio_verification_status
27 total MCP tools
```

Describe this as controlled measurement verification around changes made by an **external DAW-control MCP**.

Do not imply that Analyzer itself modifies FL Studio.

Do not market `controlled_comparison=true` as “the change is better”. It only means the Before/After measurement conditions passed the documented technical comparability guardrails.

Do not claim caller-supplied `host_readback` was independently verified by Analyzer.

The Skill remains measurement/tool oriented and must not prescribe key changes, harmony edits, tuning edits, mixing style, stereo style, mastering style, or automatic processing actions.

## macOS signing

Current macOS builds are ad-hoc signed and are **not Apple Developer ID notarized**.

The installer handles the current quarantine/local-signature path. Documentation must not claim notarization until the workflow really performs and verifies it.

## Documentation rule

When Release layout, version metadata, installation behavior, publication semantics, or public capability changes, review and update together:

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
