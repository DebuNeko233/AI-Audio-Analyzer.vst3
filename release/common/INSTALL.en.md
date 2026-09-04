# AI Audio Analyzer 1.2 — Installation Guide

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
skill/                       Cherry Studio / LLM Skill
START-HERE.md
MCP-SETUP.md                 Agent/MCP setup + JSON examples
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
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
10. Import the installed `skill` folder for the same Agent/Assistant.

The installer places user-side Analyzer files under:

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
9. Import the installed `skill` folder for the same Agent/Assistant.

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

1. open MCP server settings in Cherry Studio or another MCP-compatible client;
2. import generated `cherry-studio-mcp.json`, or manually add the same `mcpServers.ai-audio-analyzer` entry;
3. enable/select that MCP server for the Agent/Assistant that will use Analyzer;
4. import the installed `skill` folder for the same Agent;
5. refresh/restart the Agent session and verify it can see tools such as `audio_project_status()`.

The generated file is preferable to typing the path manually because it already contains the correct installation path.

## What AI Audio Analyzer 1.2 adds

The 1.2 measurement path is designed for Agent latency rather than requiring the model to watch realtime frames continuously.

High-level whole-song tools include:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
```

The MCP retains bounded one-second DAW-time Song Memory. Playback starts, seeks and loop jumps create separate continuous playback epochs so unrelated positions are not silently blended.

The current MCP also provides explainable structure and Track Story tools:

```text
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
```

`audio_section_map()` can identify section-scale change points and group recurring sections into neutral A/B/C/... families. `audio_section_profile()` inspects many Analyzer tracks inside one selected section. `audio_track_story()` follows one Analyzer instance across the map and summarizes coverage-aware activity, energy, spectrum, stereo, temporal and tonal evidence, adjacent-section deltas, recurring-family per-dimension variation and relative extrema.

A/B/C are structural recurrence labels, **not automatic Verse/Chorus/Drop names**. Track Story does not infer Bass/Vocal/Drums roles from measurements alone and does not prescribe EQ/compression/stereo actions. Exact DAW markers/project metadata remain authoritative when available.

MCP 1.2 currently exposes **37 tools**.

## Analysis Profiles

AI Audio Analyzer exposes:

```text
0 Eco
1 Balanced
2 Mix
3 Full
```

Profiles affect Analyzer measurement computation only. They do not process the audio or define a sonic mode.

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

`Full` remains the compatibility default.

Current Analyzer MCP can control the live VST3's own profile directly:

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

The control path is local/loopback-only, addresses a live Analyzer runtime UUID, applies the real host-visible `analysis_profile` parameter outside the realtime audio callback, and returns an explicit acknowledgement.

Keep these states separate:

```text
control_acknowledged  the target VST3 accepted/applied the request
telemetry_confirmed   a fresh measurement frame reports the requested profile
```

Playback can be stopped and still produce a control ACK; fresh telemetry generally requires new audio processing.

This is intentionally the **only** Analyzer MCP write capability. It cannot change EQ, compressors, gain, pan, routing, synths, automation, arrangement, or other DAW/plugin state. Those writes and their actual host readback remain the responsibility of the real DAW-control MCP.

## First use

A sensible first Agent flow is:

```text
audio_project_status()
→ bind unbound Analyzer instances through Identify when needed
→ audio_song_status() for whole-song work
→ play/capture enough of the intended pass
→ audio_section_map() for structural context
→ audio_track_story() for tracks whose behavior across sections matters
→ audio_section_profile() for sections that need multi-track drill-down
→ use detailed Temporal / Masking / Stereo / Tonal tools only when required
```

When a required evidence family is disabled, use the minimum suitable Analysis Profile rather than setting every Analyzer to Full.

The Analyzer returns measurement evidence. It does not automatically decide EQ, compression, sidechain, stereo processing, mastering targets, song key, track roles, or semantic section names.

## Troubleshooting

If the plugin is not visible after installation:

- fully restart FL Studio;
- rescan VST3 plugins;
- verify the VST3 exists in the normal platform VST3 directory.

If the Agent cannot see Analyzer MCP tools:

- confirm the installer completed successfully;
- use the generated `cherry-studio-mcp.json` rather than guessing the executable path;
- make sure the MCP server is enabled for the same Agent that receives the Skill;
- restart/refresh the Agent session.

If Analyzer profile-control tools time out:

- verify the installed VST3 and MCP runtime came from the same current Release;
- older VST3 builds do not implement the local profile-control receiver;
- never treat a request without an ACK as a successful profile write.

If macOS blocks the installer, right-click `Install.command` and choose **Open**. Current builds are not notarized.

For MCP configuration details, use `MCP-SETUP.md`.
