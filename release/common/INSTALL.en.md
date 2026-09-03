# AI Audio Analyzer 1.1 — Installation Guide

[中文教程](INSTALL.zh-CN.md) | [Agent / MCP setup](MCP-SETUP.md)

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
mcp/                         standalone Analyzer MCP executable
skill/                       Cherry Studio Skill
START-HERE.md
MCP-SETUP.md                 Agent/MCP setup + JSON examples
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
platform installer files
```

The user Release deliberately does **not** include MCP Python source, repository regression/test code, `requirements.txt`, developer source configuration examples, a PyInstaller `_internal` tree, or another ZIP inside the ZIP.

## Windows

1. Download `AI-Audio-Analyzer-v<version>-Windows.zip`.
2. Right-click it and choose **Extract All**.
3. Open the extracted folder.
4. Double-click `Install.cmd`.
5. Approve the Windows Administrator prompt when it appears. This is needed only to copy the VST3 into the standard plugin folder.
6. Wait for **Installation completed successfully**.
7. Fully restart FL Studio.
8. Open FL Studio Plugin Manager and rescan VST3 plugins if AI Audio Analyzer is not already visible.
9. Follow `MCP-SETUP.md` to add the generated MCP configuration to the Agent/Assistant that will use Analyzer.

The installer places the user-side Analyzer files under:

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

At the end, it prints the exact locations of `cherry-studio-mcp.json`, `MCP-SETUP.md`, and the installed `skill` folder.

## macOS Apple Silicon

1. Download `AI-Audio-Analyzer-v<version>-macOS.zip`.
2. Double-click the ZIP to extract it.
3. Open the extracted folder.
4. Double-click `Install.command`.
5. If macOS blocks the installer, right-click `Install.command` and choose **Open**.
6. Wait for **Installation completed successfully**.
7. Fully restart FL Studio and rescan plugins if needed.
8. Follow `MCP-SETUP.md` to add the generated MCP configuration to the Agent/Assistant that will use Analyzer.

The VST3 is installed to:

```text
~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3
```

Analyzer MCP/Skill files are installed under:

```text
~/Library/Application Support/AI Audio Analyzer/
```

Current macOS builds are ad-hoc signed and are **not Apple Developer ID notarized**.

## Add Analyzer MCP to an Agent

The installer generates a ready-to-use `cherry-studio-mcp.json` containing the real absolute path to the installed standalone MCP executable.

Open `MCP-SETUP.md` for the full beginner flow and copyable Windows/macOS JSON examples. In short:

1. open the MCP server settings in Cherry Studio or another MCP-compatible client;
2. import the generated `cherry-studio-mcp.json`, or manually add the same `mcpServers.ai-audio-analyzer` entry;
3. enable/select that MCP server for the Agent/Assistant that will use Analyzer;
4. import the installed `skill` folder for the same Agent;
5. refresh/restart the Agent session and verify it can see Analyzer tools such as `audio_project_status()`.

The generated file is preferable to typing the path manually because it already contains the correct installation path for the current computer.

## Cherry Studio Skill

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

## The Agent cannot see Analyzer MCP tools

1. Run the installer again so it checks the standalone MCP executable and regenerates `cherry-studio-mcp.json`.
2. Confirm the generated MCP server is enabled for the current Agent/Assistant.
3. Refresh or restart the MCP client after changing configuration.
4. Follow `MCP-SETUP.md` and compare your configuration with the JSON example.
5. Make sure another copy of AI Audio Analyzer MCP is not already running on the same computer.

## macOS says the installer cannot be opened

Right-click `Install.command` and choose **Open** instead of double-clicking it. If macOS shows another confirmation dialog, choose **Open** again.

## Important

The Release archive is a finished user package. Do not look for or install Python dependencies from it: they are not included and are not required.
