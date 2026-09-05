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
mcp/                         standalone one-file MCP executable
skill/                       Cherry Studio / LLM Skill
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
5. Approve the Administrator prompt if shown; this is needed to copy the VST3 into the standard plugin directory.
6. Wait for **Installation completed successfully**.
7. Restart FL Studio and rescan VST3 plugins if needed.
8. Follow `MCP-SETUP.md` to enable the generated MCP configuration for the intended Agent.
9. Import the installed `skill` folder for the same Agent.

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
8. Follow `MCP-SETUP.md` and import the installed `skill` folder for the same Agent.

VST3 location:

```text
~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3
```

MCP/Skill files:

```text
~/Library/Application Support/AI Audio Analyzer/
```

Current macOS packages are ad-hoc signed and **not Apple Developer ID notarized**.

## Add Analyzer MCP to an Agent

The installer generates `cherry-studio-mcp.json` with the real absolute path to the installed standalone MCP executable.

Prefer that generated file over typing paths manually. Full JSON examples are in `MCP-SETUP.md`.

A useful first Agent call is:

```text
audio_project_status()
```

AI Audio Analyzer MCP 1.2 currently exposes **41 tools**.

## Whole-song and section workflows

High-level tools include:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
```

Song Memory retains bounded one-second DAW-time evidence. Playback starts, seeks and loop jumps create separate instance-local playback epochs.

A/B/C families are neutral recurrence labels, not automatic Verse/Chorus/Drop names. Track Story does not infer Bass/Vocal/Drums roles or prescribe processing. Relationship `shortlist_priority` is an inspection heuristic, not masking/mix-problem probability or quality score.

Detailed masking/stereo/temporal pair tools remain recent-window based.

## Same-range Before/After verification

For a real DAW/plugin change over a known passage, prefer:

```text
audio_begin_range_verification(...)
-> external DAW-control MCP performs the real write
-> external DAW-control MCP reads actual host state back
-> replay the returned effective_range
audio_complete_range_verification(...)
```

Same-range behavior:

- fractional requests are normalized explicitly to one-second retained Song Memory bins;
- each Analyzer independently selects its best retained local epoch by coverage first, then recency;
- equal epoch numbers across tracks are not required;
- After must come from a clean pass first observed after the frozen baseline receive-time fence;
- pre-change retained memory cannot silently become After;
- historical feature comparability uses fields actually retained in the selected passes, not the current live Analysis Profile;
- higher selected After dropped-block evidence blocks a controlled comparison;
- arbitrary-range LUFS-I is not fabricated from pass-cumulative retained state.

`controlled_comparison=true` means technical comparability only. `closed_loop_complete=true` additionally requires actual caller-supplied host readback. Neither means the result is artistically better.

Recent-window verification remains available when explicit retained DAW-time anchoring is not practical:

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

## Analysis Profiles

```text
0 Eco
1 Balanced
2 Mix
3 Full
```

Profiles affect Analyzer measurement computation only, not the audio signal.

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

Analyzer-owned profile tools:

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

Keep separate:

```text
control_acknowledged  VST3 accepted/applied the Profile request
telemetry_confirmed   a fresh measurement frame reports the Profile
```

This is the only Analyzer MCP write capability. All sound/project writes and actual host readback remain the responsibility of the real DAW-control MCP.

## Suggested first workflow

```text
audio_project_status()
-> bind unbound Analyzer instances through Identify when needed
-> audio_song_status() for whole-song work
-> capture enough of the intended pass
-> audio_section_map()
-> Track Story / Section Profile / Section Relationships as needed
-> use transport-range verification for a known Before/After passage
-> use specialized Temporal / Masking / Stereo / Tonal evidence only when required
```

## Troubleshooting

If the plugin is not visible, restart FL Studio, rescan VST3 plugins, and confirm the VST3 exists in the normal platform plugin directory.

If the Agent cannot see MCP tools, confirm installation, use generated `cherry-studio-mcp.json`, enable the MCP server for the same Agent that receives the Skill, and refresh/restart the Agent session.

If Analyzer Profile control times out, verify the VST3 and MCP runtime came from the same current Release. No ACK means no confirmed profile write.

For MCP configuration details, use `MCP-SETUP.md`.
