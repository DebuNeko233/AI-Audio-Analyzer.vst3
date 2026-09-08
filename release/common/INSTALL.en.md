# AI Audio Analyzer 1.2 — Installation Guide

[中文教程](INSTALL.zh-CN.md) | [Agent / MCP setup](MCP-SETUP.md)

This Release is packaged for people who do not use programming tools. Normal installation requires **no Python, pip, venv, source code, package manager, Terminal, or PowerShell commands**.

Supported packages:

```text
Windows x64
macOS Apple Silicon arm64
```

Intel/x86_64 macOS is not included.

## Package contents

```text
AI Audio Analyzer.vst3
mcp/                         standalone PyInstaller -F one-file MCP executable
skill/                       canonical long-form guides + optional client Skill
START-HERE.md
MCP-SETUP.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
platform installer files
```

The user Release deliberately contains no MCP Python source, repository regression/test code, `requirements.txt`, developer source config, PyInstaller `_internal`, or nested ZIP.

## Windows

1. Download `AI-Audio-Analyzer-v<version>-Windows.zip`.
2. Right-click it and choose **Extract All**.
3. Open the extracted folder.
4. Double-click `Install.cmd`.
5. Approve the Administrator prompt if shown.
6. Wait for **Installation completed successfully**.
7. Restart FL Studio and rescan VST3 plugins if needed.
8. Follow `MCP-SETUP.md` to enable the generated MCP configuration for the intended Agent.
9. Optional: import the installed `skill` folder if the client supports Skills or does not expose MCP Resources.

User-side Analyzer files are installed under:

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

## macOS Apple Silicon

1. Download `AI-Audio-Analyzer-v<version>-macOS.zip`.
2. Double-click it to extract.
3. Open the extracted folder.
4. Double-click `Install.command`.
5. If macOS blocks it, right-click `Install.command` and choose **Open**.
6. Wait for installation success.
7. Restart FL Studio and rescan plugins if needed.
8. Follow `MCP-SETUP.md` to add Analyzer MCP to the Agent.
9. Optional: import the installed `skill` folder if useful for that client.

VST3 location:

```text
~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3
```

MCP/Skill files:

```text
~/Library/Application Support/AI Audio Analyzer/
```

Current macOS packages are ad-hoc signed and **not Apple Developer ID notarized**.

## MCP setup

The installer generates `cherry-studio-mcp.json` with the real absolute path to the installed standalone MCP executable. Prefer that generated file over typing paths manually.

AI Audio Analyzer MCP 1.2 exposes **47 tools** and **16 Guide Resources**.

The MCP is self-describing through Server instructions, Tool descriptions and `aianalyzer://guide/*` Resources. The installed `skill/` directory remains the canonical long-form Markdown source.

At a new session, or after a possible project switch/reopen, first inspect:

```text
audio_project_identity_status()
```

Current stable Project ID is unresolved. Runtime UUIDs are live plugin-instance identities, not persistent Project/Track IDs. If strict retained-state isolation matters after switching/reopening a project, restart Analyzer MCP.

Then inspect:

```text
audio_project_status()
audio_song_status()
```

## Whole-song and mix evidence

High-level tools include:

```text
audio_song_overview()
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
audio_dynamics_distribution(...)
audio_mono_compatibility(...)
```

Missing coverage is not silence. A/B/C Section families are neutral recurrence labels, not automatic Verse/Chorus/Drop names.

P6a dynamics statistics are descriptive. LUFS-S P90-P10 is not standardized EBU LRA; arbitrary-range Integrated LUFS and PLR remain unavailable.

P7a direct mono-fold evidence is recent-window only. Historical arbitrary Section 32-band mono evidence and mono-fold Sample Peak/True Peak are unavailable.

## Reference comparison

P8a tools:

```text
audio_capture_reference(track, label="", seconds=10.0)
audio_list_references()
audio_compare_reference(reference_id, target, seconds=None)
```

A P8a reference is a frozen compact measurement profile, not copied source audio.

Current scope:

```text
recent receive-time window
current MCP session only
not persistent
not a whole-song claim
```

Comparison includes absolute `target - reference` evidence plus an explicit RMS-level-normalized spectral-shape view. The normalized view applies no real gain and changes no audio.

A difference from a reference is context, not automatically a defect or processing command. P8a does not emit automatic EQ/master matching or a quality score.

## Real DAW changes and verification

Analyzer MCP can change only its own `Analysis Profile` measurement setting.

All EQ, compression, gain, pan, routing, synth, automation and project changes remain with the external DAW-control MCP.

For a known passage, prefer:

```text
audio_begin_range_verification(...)
-> external change + actual host readback
-> replay effective_range
audio_complete_range_verification(...)
```

`controlled_comparison=true` means technical comparability only. `closed_loop_complete=true` additionally requires actual host readback. Neither means After is artistically better.

## Troubleshooting

If the Agent cannot see Analyzer tools:

1. confirm the installer completed successfully;
2. confirm the generated JSON points to the installed executable;
3. confirm the MCP is enabled for the current Agent;
4. restart/refresh the MCP client after configuration changes;
5. ensure another Analyzer MCP process is not already using the local OSC endpoint `127.0.0.1:9855`.

Normal user Releases must run the installed one-file MCP executable, not repository Python source.