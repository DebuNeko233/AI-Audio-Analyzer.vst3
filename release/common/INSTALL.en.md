# AI Audio Analyzer 1.1 — Installation Guide

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

At the end, it prints the exact locations of `cherry-studio-mcp.json` and the installed `skill` folder.

## macOS Apple Silicon

1. Download `AI-Audio-Analyzer-v<version>-macOS.zip`.
2. Double-click the ZIP to extract it.
3. Open the extracted folder.
4. Double-click `Install.command`.
5. If macOS blocks the installer, right-click `Install.command` and choose **Open**.
6. Wait for **Installation completed successfully**.
7. Fully restart FL Studio and rescan plugins if needed.

The VST3 is installed to:

```text
~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3
```

Analyzer MCP/Skill files are installed under:

```text
~/Library/Application Support/AI Audio Analyzer/
```

Current macOS builds are ad-hoc signed and are **not Apple Developer ID notarized**.

## Cherry Studio

After the installer finishes, use the generated `cherry-studio-mcp.json` to add the Analyzer MCP server and import the installed `skill` folder.

The Skill is written in English for LLM compatibility. It teaches the model how to discover Analyzer instances, select the minimum analysis profile needed for a request, interpret measurements, and run controlled Before/After verification. It does not impose a mixing, mastering, harmony, or stereo-processing style.

## Analysis Profiles

AI Audio Analyzer can expose these host-visible measurement profiles:

```text
Eco
Balanced
Mix
Full
```

They change **Analyzer measurement workload only**. They do not process or alter the audio.

`Full` is the compatibility default. An AI workflow may temporarily request a lighter or deeper profile through the real DAW-control MCP, read the host setting back, and verify the Analyzer status. You do not need to configure this during installation.

## Closed-loop verification

Analyzer MCP can capture a Before measurement, store actual host readback supplied by the external DAW-control MCP, capture an After window, and report whether the measurement conditions are technically comparable.

This does not mean Analyzer itself controls FL Studio, and technical comparability does not mean an artistic change is better.

Normal users do not need to configure this manually; the Skill explains the agent workflow.

## FL Studio cannot find the plugin

1. Fully close and reopen FL Studio.
2. Open Plugin Manager.
3. Run a plugin rescan.
4. Confirm `AI Audio Analyzer` appears in the plugin list.

## Cherry Studio cannot connect

Run the installer again. It checks the standalone Analyzer connection executable and regenerates `cherry-studio-mcp.json`.

Also make sure another copy of AI Audio Analyzer MCP is not already running on the same computer.

## macOS says the installer cannot be opened

Right-click `Install.command` and choose **Open** instead of double-clicking it. If macOS shows another confirmation dialog, choose **Open** again.

## Important

The Release archive is a finished user package. Do not look for or install Python dependencies from it: they are not included and are not required.
