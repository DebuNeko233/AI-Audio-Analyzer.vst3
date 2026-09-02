# AI Audio Analyzer 1.0 — Installation Guide

[中文教程](INSTALL.zh-CN.md)

This Release is intentionally packaged for people who do not use programming tools.

You do **not** need Python, pip, a virtual environment, source code, a package manager, or Terminal/PowerShell commands for normal installation.

Supported packages:

```text
Windows x64
macOS Apple Silicon arm64
```

Intel/x86_64 macOS is not included.

## Package contents

```text
AI Audio Analyzer.vst3
mcp/                         standalone Analyzer connection executable
skill/                       Cherry Studio Skill
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
platform installer files
```

The user Release deliberately does **not** include MCP Python source, repository regression/test code, `requirements.txt`, developer configuration examples, a PyInstaller `_internal` tree, or another ZIP inside the ZIP.

## Windows

1. Download `AI-Audio-Analyzer-v<version>-Windows.zip`.
2. Right-click it and choose **Extract All**.
3. Open the extracted folder.
4. Double-click `Install.cmd`.
5. Approve the Windows Administrator prompt when it appears. This is needed only to copy the VST3 into the standard plugin folder.
6. Wait for **Installation completed successfully**.
7. Fully restart FL Studio.
8. Open FL Studio Plugin Manager and rescan VST3 plugins if AI Audio Analyzer is not already visible.

The installer places the user-side Analyzer files under:

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

At the end, the installer prints the exact locations of:

```text
cherry-studio-mcp.json
skill\
```

Use those two locations when adding the Analyzer MCP and importing the Skill in Cherry Studio.

## macOS Apple Silicon

1. Download `AI-Audio-Analyzer-v<version>-macOS.zip`.
2. Double-click the ZIP to extract it.
3. Open the extracted folder.
4. Double-click `Install.command`.
5. If macOS blocks the installer, right-click `Install.command` and choose **Open**.
6. Wait for **Installation completed successfully**.
7. Fully restart FL Studio and rescan plugins if needed.

The installer places the VST3 here:

```text
~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3
```

Analyzer MCP/Skill files are placed here:

```text
~/Library/Application Support/AI Audio Analyzer/
```

If you want to open that folder without using Terminal, in Finder choose **Go → Go to Folder…** and paste the path above.

Current macOS builds are ad-hoc signed and are **not Apple Developer ID notarized**. The installer handles the package quarantine/signature steps needed by the current Release.

## Cherry Studio

After the installer finishes, it shows two paths:

1. `cherry-studio-mcp.json` — use this to add the Analyzer MCP server;
2. `skill` — import this folder as the AI Audio Analyzer Skill.

The Skill is written in English for LLM compatibility. It teaches the model how to call Analyzer tools, understand measurements, and use V1.0 verification correctly; it does not impose a specific mixing, mastering, harmony, or stereo-processing style.

AI Audio Analyzer 1.0 adds controlled Before/After verification around changes performed by an external DAW-control MCP. There is **no additional installation step** for this feature.

## What V1.0 verification means

For an AI workflow that changes FL Studio, Analyzer MCP can now keep a Before baseline, accept the external control MCP's actual host-state readback, capture an After window, and report whether the two measurement windows satisfy transparent comparability checks.

This does not mean Analyzer itself controls FL Studio, and a technically controlled comparison does not mean the artistic change is better.

Normal users do not need to configure this manually; the LLM-facing Skill explains how the agent should call the tools.

## FL Studio cannot find the plugin

Try these steps in order:

1. fully close and reopen FL Studio;
2. open Plugin Manager;
3. run a plugin rescan;
4. confirm `AI Audio Analyzer` appears in the plugin list.

## Cherry Studio cannot connect

Run the installer again. It automatically checks the standalone Analyzer connection executable and regenerates `cherry-studio-mcp.json`.

Also make sure another copy of AI Audio Analyzer MCP is not already running on the same computer.

## macOS says the installer cannot be opened

Right-click `Install.command` and choose **Open** instead of double-clicking it. macOS may then show an additional confirmation dialog; choose **Open** again.

## Important

The Release archive is a finished user package. Do not look for or install Python dependencies from it: they are not included and are not required.
