# Release packaging policy

User-facing Release packages are created by:

```text
.github/workflows/release.yml
```

The normal `build` workflow is for development validation/artifacts. It is not the user distribution path.

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

Build-time source entrypoint:

```text
bridge/server.py
```

The build pipeline may use Python internally, but the **user package must not contain MCP Python source**.

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
inner Release ZIP files
```

## Single-compression rule

Do not create a final ZIP in the platform packaging jobs and then upload that ZIP inside a GitHub Actions artifact.

The pipeline should be:

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
PyInstaller one-file build
packaged MCP self-test on its native OS
Windows VST3 build
macOS arm64 VST3 build
Windows installer parse
macOS installer syntax
macOS VST3 signature
no MCP source/developer files in user package
no nested ZIP in user package
final checksums
```

A successful source self-test does not prove PyInstaller, VST3, final package assembly, or publication succeeded.

## macOS signing

Current macOS builds are ad-hoc signed and are **not Apple Developer ID notarized**.

The installer handles the current quarantine/local-signature path. Documentation must not claim notarization until the workflow really performs and verifies it.

## Documentation rule

When Release layout or installation behavior changes, review and update together:

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
