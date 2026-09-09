# AI Audio Analyzer 1.2 — Start Here / 从这里开始

[English guide](INSTALL.en.md) | [中文教程](INSTALL.zh-CN.md) | [Agent / MCP setup](MCP-SETUP.md)

This Release is designed for users with no Python or programming experience. **Unzip the downloaded package once**, then run the installer inside.

## Windows

1. Download the file ending in `Windows.zip`.
2. Right-click it and choose **Extract All**.
3. Open the extracted folder.
4. Double-click `Install.cmd`.
5. Approve the permission prompt if Windows shows one.
6. Wait for **Installation completed successfully**.
7. Restart FL Studio and rescan plugins if needed.
8. Follow `MCP-SETUP.md` to add the generated MCP configuration to the Agent/Assistant that will use Analyzer.
9. Optional: import the packaged `skill` folder if the client supports Skills or does not expose MCP Resources.

## macOS Apple Silicon

1. Download the file ending in `macOS.zip`.
2. Double-click it to extract it.
3. Open the extracted folder.
4. Double-click `Install.command`.
5. If macOS blocks it, right-click `Install.command` and choose **Open**.
6. Wait for the installer to report success.
7. Restart FL Studio and rescan plugins if needed.
8. Follow `MCP-SETUP.md` to add Analyzer MCP to the Agent.
9. Optional: import the packaged `skill` folder if the client benefits from client-side Skill loading.

Current macOS Release supports **Apple Silicon arm64 only**. It is ad-hoc signed, not Apple Developer ID notarized.

## What is inside

```text
AI Audio Analyzer.vst3
mcp/                         standalone one-file MCP executable
skill/                       canonical long-form MCP guides + optional client Skill
Install.cmd / Install.ps1    Windows installer
Install.command / install.sh macOS installer
START-HERE.md
MCP-SETUP.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
```

The user Release contains **no MCP Python source**, `requirements.txt`, venv, PyInstaller `_internal`, developer source config, or nested Release ZIP.

The installer generates `cherry-studio-mcp.json` with the correct absolute path to the installed MCP executable.

## The MCP can explain itself

AI Audio Analyzer MCP does not require a client-imported Skill for basic correct use.

It exposes:

```text
Server instructions
47 Tool descriptions
16 MCP Resources under aianalyzer://guide/*
```

If the client supports MCP Resources, it can read `aianalyzer://guide/index` and then only the guide needed for the task.

The packaged `skill/` directory remains the canonical Markdown source. Importing it directly into a Skill-capable client is optional.

## What the Agent can do

MCP 1.2 exposes **47 tools** for evidence workflows, including:

```text
project/runtime identity-scope disclosure
Song Memory
explainable Section Map
Track Story
Section-aware Mix Relationships
coverage-aware retained Dynamics Distribution
direct recent-window Mono-fold Compatibility
frozen session Reference Capture / Comparison
Analysis Profile control
recent-window verification
transport-anchored same-range verification
```

At a new session, and whenever the DAW project may have been switched or reopened, the Agent should first call:

```text
audio_project_identity_status()
```

Current stable project identity is unresolved. Analyzer runtime UUIDs are live plugin-instance identities, not persistent Project/Track IDs. If strict retained-state isolation matters after switching/reopening a project, restart Analyzer MCP before continuing.

## Reference comparison note

P8a reference tools are:

```text
audio_capture_reference(...)
audio_list_references()
audio_compare_reference(...)
```

A reference is a frozen compact measurement profile, not copied audio. It exists only in the current MCP session and currently represents a recent receive-time window.

The comparison can show absolute target-minus-reference differences and an explicit RMS-level-normalized spectral-shape view. This is context for the Agent, not an automatic EQ/mastering recipe.

The Agent should not assume that a difference from a reference is wrong or that Section labels in unrelated songs have the same meaning.

## Sound/project changes remain external

Analyzer MCP may change only its own `Analysis Profile` measurement setting.

Real EQ, compression, gain, pan, routing, synth, automation and project changes belong to the external DAW-control MCP. For important changes over a known passage, use Analyzer same-range Before/After verification with actual host readback.