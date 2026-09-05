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
5. Approve the Administrator prompt if shown; this is needed to copy the VST3 into the standard plugin directory.
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
9. Optional: import the installed `skill` folder if the client benefits from client-side Skill loading.

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

AI Audio Analyzer MCP 1.2 exposes **44 tools** on the stacked P7a branch.

## MCP Self-Describing API

The MCP remains understandable even if the client does not import the packaged Skill.

It exposes:

```text
Server instructions
44 Tool descriptions
15 MCP Resources under aianalyzer://guide/*
```

The `skill/` directory remains the canonical long-form Markdown source for MCP Resources and can also be imported directly by Skill-capable clients.

If the client supports MCP Resources, read `aianalyzer://guide/index` and then only the guide relevant to the current task. P6a dynamics details are available at `aianalyzer://guide/dynamics-evidence`; P7a mono-fold details are available at `aianalyzer://guide/mono-compatibility`. If the client does not expose Resources, importing the installed `skill` folder is the preferred way to provide the same detailed guidance.

If the physical `skill` directory is missing, Server instructions and Tool descriptions still provide the minimum operating contract, but detailed guide Resources are unavailable.

At a new session, and whenever the user may have switched or reopened the DAW project, first inspect:

```text
audio_project_identity_status()
```

Current limitation:

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
runtime_id scope                        live_plugin_instance
same-project reopen UUID stable         false
cross-project retained-state isolation  not guaranteed
```

Analyzer runtime UUIDs are not persistent project/track IDs. Reopening the same FL Studio project creates new Analyzer runtime UUIDs, so a new UUID does not prove that a different project was opened.

If Analyzer MCP keeps running through a project switch/reopen, retained Song Memory, Section Maps, snapshots, relationships and verification sessions may still exist in RAM and are not yet partitioned by a stable Project ID. Until exact project identity is integrated, restart Analyzer MCP after changing/reopening projects when strict state isolation is required.

Then inspect current-session readiness:

```text
audio_project_status()
```

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
audio_dynamics_distribution(...)
audio_mono_compatibility(...)
```

Song Memory retains bounded one-second DAW-time evidence. Playback starts, seeks and loop jumps create separate instance-local playback epochs. Song Memory is MCP-session state and is not yet partitioned by stable Project ID.

A/B/C families are neutral recurrence labels, not automatic Verse/Chorus/Drop names. Track Story does not infer Bass/Vocal/Drums roles or prescribe processing. Relationship `shortlist_priority` is an inspection heuristic, not masking/mix-problem probability or quality score.

Detailed masking/stereo/temporal pair tools remain recent-window based. P7a mono compatibility is also recent-window based and must not be presented as arbitrary historical/Section 32-band evidence.

## Coverage-aware dynamics distributions

Use:

```text
audio_dynamics_distribution(...)
```

for a selected retained transport-pass span, explicit DAW-time range or cached section. P6a filters retained one-second bins with a minimum coverage floor and weights accepted observations by covered seconds.

The tool exposes descriptive distributions for RMS, LUFS-S, Crest, observed per-bin Sample Peak maxima and observed per-bin True Peak maxima, including weighted percentiles where available. Missing bins remain missing and are never inserted as silence or zero.

Important boundaries:

- `lufs_s_interpercentile_range_lu` is descriptive P90-P10 LUFS-S spread, not standardized EBU Loudness Range;
- standardized EBU LRA is not implemented in P6a;
- arbitrary-range Integrated LUFS is unavailable because retained `lufs_i_latest` is pass-cumulative;
- arbitrary-range PLR is unavailable without scope-compatible peak and integrated-loudness evidence;
- section-to-section deltas are descriptive only and are not a quality score or processing recommendation.

## Direct mono-fold compatibility

Use:

```text
audio_mono_compatibility(track, seconds=5.0)
```

P7a reuses the Analyzer's existing Mid/Side evidence. Existing Mid RMS is the ordinary `(L+R)/2` mono-fold RMS, and the existing Mid/Side band-center powers allow direct sampled fold-down energy comparison without new realtime DSP or OSC fields.

Important boundaries:

- current scope is a recent receive-time window, not arbitrary historical/Section 32-band analysis;
- `inspection_priority` is an energy-aware shortlist aid only, not a quality score, audibility probability, pass/fail result, or processing instruction;
- correlation, Side/Mid, negative-cross and direct mono-fold energy remain separate evidence dimensions;
- `floor_censored=true` means Mid reached the Analyzer `-120 dB` measurement floor, so cancellation below that floor is not known precisely;
- unmeasurable Mid+Side band-center energy remains unavailable rather than becoming an artificial extreme cancellation result;
- P7a does not directly measure mono-fold Sample Peak or True Peak;
- mono peak/True Peak must not be inferred from stereo Peak, True Peak, RMS, correlation or Side/Mid;
- direct peak/True-Peak fold-down belongs to optional P7b.

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

`controlled_comparison=true` means technical comparability only. `closed_loop_complete=true` additionally requires actual caller-supplied host readback. Neither means the result is artistically better or establishes persistent project identity.

Recent-window verification remains available when explicit retained DAW-time anchoring is not practical:

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

Do not carry either verification mode across a suspected project switch/reopen without authoritative external identity or a clean MCP restart.

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
connect Analyzer MCP
-> use Server instructions / Tool descriptions as the minimum contract
-> when detailed semantics are needed, read the relevant aianalyzer://guide/* Resource if supported
-> audio_project_identity_status()
-> if project was switched/reopened and strict isolation is required, restart Analyzer MCP
-> audio_project_status()
-> bind unbound Analyzer instances through Identify when needed
-> audio_song_status() for whole-song work
-> capture enough of the intended pass
-> audio_section_map()
-> Track Story / Section Profile / Section Relationships as needed
-> audio_dynamics_distribution() when retained dynamics evidence is needed
-> audio_mono_compatibility() when recent direct mono translation evidence is needed
-> use transport-range verification for a known Before/After passage
-> use specialized Temporal / Masking / Stereo / Tonal evidence only when required
```

## Troubleshooting

If the plugin is not visible, restart FL Studio, rescan VST3 plugins, and confirm the VST3 exists in the normal platform plugin directory.

If the Agent cannot see MCP tools, confirm installation, use generated `cherry-studio-mcp.json`, enable the MCP server for the intended Agent, and refresh/restart the Agent session. Importing the Skill is not required for the tools themselves to appear.

If Analyzer Profile control times out, verify the VST3 and MCP runtime came from the same current Release. No ACK means no confirmed profile write.

For MCP configuration details, use `MCP-SETUP.md`.