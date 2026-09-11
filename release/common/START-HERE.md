# AI Audio Analyzer 1.2 — Start Here / 从这里开始

[English guide](INSTALL.en.md) | [中文教程](INSTALL.zh-CN.md) | [Agent / MCP setup](MCP-SETUP.md)

This Release is designed for users with no Python or programming experience. **Unzip the downloaded package once**, then run the installer inside.

## Windows

1. Download the file ending in `Windows.zip`.
2. Right-click it and choose **Extract All**.
3. Open the extracted folder.
4. Double-click `Install.cmd`.
5. Approve the permission prompt if shown.
6. Wait for **Installation completed successfully**.
7. Restart FL Studio and rescan plugins if needed.
8. Follow `MCP-SETUP.md` to add the generated MCP configuration to your Agent.

## macOS Apple Silicon

1. Download the file ending in `macOS.zip`.
2. Double-click it to extract it.
3. Open the extracted folder.
4. Double-click `Install.command`.
5. If macOS blocks it, right-click `Install.command` and choose **Open**.
6. Wait for the installer to report success.
7. Restart FL Studio and rescan plugins if needed.
8. Follow `MCP-SETUP.md` to add Analyzer MCP to your Agent.

Current macOS Release supports **Apple Silicon arm64 only** and is ad-hoc signed rather than Apple-notarized.

## What is inside

```text
AI Audio Analyzer.vst3
mcp/                         standalone one-file MCP executable
skill/                       canonical MCP guides + optional client Skill
Install.cmd / Install.ps1    Windows installer
Install.command / install.sh macOS installer
START-HERE.md
MCP-SETUP.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
```

The user Release contains **no MCP Python source**, `requirements.txt`, venv, PyInstaller `_internal`, developer source config or nested Release ZIP.

The installer generates `cherry-studio-mcp.json` with the correct absolute path to the installed MCP executable.

## MCP surface

P4b PR #36 uses MCP 1.2 with:

```text
48 Tool descriptions
16 MCP Resources under aianalyzer://guide/*
```

The MCP is self-describing. Importing the packaged Skill is optional for clients that already expose MCP Resources.

At a new session, or after a possible project switch/reopen, first call:

```text
audio_project_identity_status()
```

Stable project identity is currently unresolved. Runtime UUIDs identify live plugin instances only. Restart Analyzer MCP after changing/reopening a project when strict retained-state isolation is required.

## What the Agent can do

High-level workflows include:

```text
Song Memory
Section Map / Track Story / Section Relationships
P4b historical one-second deep retained detail
P6a retained Dynamics Distribution
P7a recent Mono-fold Compatibility
P8a frozen session Reference Comparison
Analysis Profile control
recent-window verification
transport-anchored same-range verification
```

Historical P4b queries use:

```text
audio_historical_detail(...)
```

This can avoid replay for past DAW ranges/Sections when deep evidence was retained. Historical resolution is one second; subsecond historical alignment and direct mono-fold Sample Peak/True Peak remain unavailable.

P8a references remain frozen **recent-window** session profiles. P4b does not silently turn them into historical reference captures.

## Sound/project changes remain external

Analyzer MCP may change only its own `Analysis Profile` measurement setting.

Real EQ, compression, gain, pan, routing, synth, automation and project changes belong to the external DAW-control MCP. For important changes over a known passage, use Analyzer same-range Before/After verification with actual host readback.
