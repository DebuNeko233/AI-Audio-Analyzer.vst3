# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** is a JUCE VST3 machine-readable audio measurement layer for AI/LLM-assisted music-production workflows.

It measures audio inside the DAW, publishes structured OSC telemetry to the Analyzer MCP, and exposes realtime evidence, transport-aligned Song Memory, explainable structure, Track Story, section-aware relationships, coverage-aware dynamics distributions, direct mono-fold compatibility, frozen reference comparison, performance telemetry, identity-scope disclosure, and closed-loop verification to Cherry Studio or another MCP client.

Current product version: **1.2.0**.

## System boundary

```text
AI Audio Analyzer VST3
  -> realtime-safe measurement + DAW transport context

AI Audio Analyzer MCP
  -> observe / remember / structure / compare / verify
  -> freeze session reference profiles and compare target evidence
  -> disclose current project/runtime identity guarantees
  -> self-describe startup rules, tool purpose and on-demand guides
  -> may control Analyzer's own Analysis Profile only

External DAW-control MCP
  -> inspect / modify / read back DAW/project/plugin state
```

For FL Studio control, the current companion project is:

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

Analyzer MCP is **not** a general DAW-control server. The only Analyzer-owned write is the host-visible `analysis_profile` parameter, because it changes measurement computation only and never changes the audio signal.

EQ, compression, gain, pan, routing, synth, automation, arrangement/project state, and other artistic/technical writes remain external.

## Architecture

```text
FL Studio / DAW
|
+-- Mixer Track A -- AI Audio Analyzer.vst3
+-- Mixer Track B -- AI Audio Analyzer.vst3
+-- Master --------- AI Audio Analyzer.vst3
                         |
                         | OSC measurements, default 127.0.0.1:9855
                         v
                 Analyzer MCP Bridge
                 +-- live instance registry + deterministic bindings
                 +-- Analysis Profile status/control + worker telemetry
                 +-- transport + instance-local playback epochs
                 +-- one-second Song Memory + coverage accounting
                 +-- Section Map / Track Story / relationships
                 +-- retained dynamics distributions
                 +-- direct recent-window mono-fold evidence
                 +-- frozen session reference profiles/comparison
                 +-- recent-window + transport-range verification
                 +-- temporal / masking / stereo / tonal evidence
                         |
                         v
                  Cherry Studio / LLM
                         |
                         +-- external DAW-control MCP for real changes/readback
```

Multiple Analyzer instances may send to the same UDP measurement port. Only one Analyzer MCP process should bind UDP `9855`.

The LLM is outside the realtime measurement path. Analyzer continues measuring while the Agent reasons or calls other tools.

## Measurement capabilities

- Sample Peak, RMS, Crest Factor;
- LUFS-S / LUFS-I and True Peak via `libebur128`;
- 4096-point FFT and 32 log-spaced spectrum bands;
- Spectral Centroid, Rolloff, Flatness;
- full-band and frequency-dependent stereo correlation;
- Mid/Side, Side spectrum, Side/Mid and negative-cross evidence;
- Spectral Flux, RMS Rise and low-band temporal energy;
- 12-bin chroma, tonal-center ranking and single-F0 harmonic evidence;
- DAW time / PPQ / BPM / time signature / loop / play / record context;
- instance-local transport epochs;
- estimated Analyzer lag and cumulative dropped blocks;
- bounded one-second Song Memory with 100 ms coverage slots;
- explainable section boundaries and neutral recurring A/B/C families;
- Section Profiles, Track Story and section-aware relationship shortlisting;
- coverage-aware retained RMS / LUFS-S / Crest / observed Peak / True-Peak distributions;
- direct recent-window mono-fold RMS and energy-aware 32-band-center compatibility evidence;
- frozen session-scoped reference profiles with absolute and RMS-level-normalized comparison;
- project Snapshot A/B, recent-window verification, and transport-anchored same-range verification;
- adaptive Analysis Profiles and worker/FIFO telemetry.

The Analyzer is evidence-oriented. It does not hard-code genre recipes, fixed LUFS targets, mandatory EQ/sidechain/compression/stereo moves, semantic Verse/Chorus/Drop labels, key changes, harmony edits, mastering chains, or reference-matching recipes.

`null` means **unavailable**, not numeric zero. Missing retained coverage is not silence.

## Project/runtime identity scope

Current Analyzer `runtime_id` is a **live plugin-instance UUID**, not a persistent project or track ID. Reopening the same DAW project recreates Analyzer runtime UUIDs.

Use:

```text
audio_project_identity_status()
```

before assuming continuity across a project switch/reopen.

Current guarantees:

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
runtime_id scope                        live_plugin_instance
runtime_id persistent                   false
same-project reopen UUID stable         false
binding scope                           mcp_session
cross-project retained-state isolation  not guaranteed
```

Until authoritative project identity is integrated, restart Analyzer MCP after changing/reopening projects when strict retained-state isolation is required.

## Deterministic Analyzer ↔ FL Mixer mapping

Each live Analyzer exposes:

```text
Parameter ID: identify
Display name: Identify
```

Each Identify transition emits `/aianalyzer/identify`. The Bridge can bind the runtime UUID to a real FL Mixer Track/Slot and later use selectors such as:

```text
mixer:7/slot:9
```

Prefer deterministic binding over guessing identity from track names or audio content. Bindings are MCP-session scoped.

## Adaptive Analysis Profile

```text
Parameter ID: analysis_profile
Display name: Analysis Profile

0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

`Full` remains the compatibility default.

Analyzer-owned profile-control tools:

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

Keep these confirmations separate:

```text
control_acknowledged  target VST3 accepted/applied the request
telemetry_confirmed   a fresh frame reports the requested profile
```

The local control path is loopback-only, session-scoped, and does not alter audio.

## Transport-aware Song Memory

Protocol 1.2 attaches DAW transport context to Analyzer measurements so the LLM can inspect a passage after it happened.

```text
DAW playback
-> Analyzer measures continuously
-> MCP stores one-second DAW-time bins
-> LLM can query retained evidence later
```

High-level tools:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
```

Song Memory characteristics:

```text
canonical bin size       1 second
coverage slot            100 ms
retained bins            up to 1200 / Analyzer instance
retained span            about 20 minutes / instance
query resolutions        1 / 2 / 5 / 10 / 15 / 30 seconds
scope                    current MCP session
```

A `transport_epoch` is one continuous playback pass for one Analyzer instance. Epoch counters are independent across instances. Equal numeric epoch values are not project-global identity.

## Explainable song structure

Tools:

```text
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
```

A/B/C families are recurrence labels only. They are not automatically Intro/Verse/Chorus/Drop.

`audio_track_story()` summarizes one track across sections. `audio_section_relationships()` returns a bounded pair shortlist. `shortlist_priority` is inspection priority only, not masking probability, mix-problem probability, quality score, or a processing recommendation.

Detailed masking/stereo/temporal pair tools remain recent-window based until deeper historical retained detail is implemented.

## Coverage-aware dynamics distributions

P6a is merged and provides:

```text
audio_dynamics_distribution(
  track,
  transport_epoch=None,
  start_seconds=None,
  end_seconds=None,
  map_id=None,
  section_id=None,
  compare_section_id=None,
  minimum_range_coverage=...,
  minimum_bin_coverage=...
)
```

Coverage policy:

```text
minimum per-bin coverage floor
+
covered-seconds weighting for accepted one-second bins
```

Descriptive distributions include RMS, LUFS-S, Crest, observed Sample-Peak maxima and observed True-Peak maxima with P10/P25/P50/P75/P90, IQR and P90-P10 spread where available.

Important boundaries:

- `lufs_s_interpercentile_range_lu` is descriptive P90-P10 evidence, **not EBU Loudness Range**;
- standardized EBU LRA is not implemented in P6a;
- arbitrary-range Integrated LUFS is unavailable because retained LUFS-I is pass-cumulative;
- arbitrary-range PLR is unavailable without scope-compatible peak and integrated-loudness evidence;
- section deltas are descriptive context only, not a quality score or processing recommendation.

See `skills/ai-analyzer-flstudio/references/dynamics-evidence.md`.

## Energy-aware mono-fold compatibility

P7a is merged and provides:

```text
audio_mono_compatibility(track, seconds=5.0)
```

The VST3 already computes:

```text
M = 0.5 * (L + R)
S = 0.5 * (L - R)
(L_power + R_power)/2 = M_power + S_power
```

so P7a requires no new realtime DSP or OSC fields.

It exposes full-band mono-fold RMS loss plus 32 band-center Mid/Side energy evidence and grouped summaries across `20-120 Hz`, `120-500 Hz`, `500 Hz-2 kHz`, `2-5 kHz`, and `5-20 kHz`.

`inspection_priority` is only an energy-aware shortlist aid. It is not audibility probability, a phase-problem probability, a quality score, pass/fail threshold, or processing recommendation.

Current deliberate limits:

- historical arbitrary Section 32-band mono-fold analysis is unavailable until deeper retained detail exists;
- mono-fold Sample Peak and True Peak are unavailable in P7a and must not be inferred from stereo metrics;
- direct peak/True-Peak fold-down belongs to optional P7b.

See `skills/ai-analyzer-flstudio/references/mono-compatibility.md`.

## Session-scoped Reference Engine

P8a adds:

```text
audio_capture_reference(track, label="", seconds=10.0)
audio_list_references()
audio_compare_reference(reference_id, target, seconds=None)
```

A P8a reference is a **frozen compact measurement profile**, not copied audio. It is scoped to the running MCP session and currently captures a recent receive-time window.

The comparison keeps independent evidence groups separate:

```text
energy / loudness
32-band spectrum + coarse regions
stereo correlation / width
P7a mono-fold compatibility
```

Two spectral views are returned:

```text
absolute target_minus_reference

RMS-level-normalized shape:
target_gain_to_reference_db = reference_rms - target_rms
normalized_delta = (target_band + target_gain_to_reference_db) - reference_band
```

The normalized view removes one broad RMS offset for comparison only. It does not modify either source.

Reference evidence is context, not a recipe. The MCP does **not** automatically turn `+2 dB at 8 kHz` into `add +2 dB at 8 kHz`, does not emit a quality score, and does not assume section labels from unrelated songs are semantically equivalent.

Current P8a limits:

- references disappear when MCP exits;
- recent-window capture is not a whole-song claim;
- historical arbitrary Section 32-band reference capture waits for deeper retained detail;
- persistent reference libraries wait for trustworthy project identity/project memory;
- external reference-file faster-than-realtime scanning is future work.

See `skills/ai-analyzer-flstudio/references/reference-comparison.md`.

## Controlled verification

Two verification paths coexist.

Recent-window:

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

Transport-anchored same-range:

```text
audio_begin_range_verification(...)
audio_complete_range_verification(...)
audio_range_verification_status(...)
```

Same-range mode normalizes requested boundaries to retained one-second bins, independently chooses the best local epoch per Analyzer by coverage, prevents pre-change evidence from silently becoming After, and requires caller-supplied actual external host readback for `closed_loop_complete=true`.

`controlled_comparison=true` means technical comparability only. Neither it nor `closed_loop_complete=true` means After is artistically better.

## Self-describing MCP API

The MCP provides:

```text
Server instructions
Tool descriptions
MCP Resources under aianalyzer://guide/*
```

The packaged/repository `skill/` remains the canonical long-form content source. MCP Resources read the same Markdown on demand.

Guide namespace currently contains **16 Resources**, including:

```text
aianalyzer://guide/index
aianalyzer://guide/core
aianalyzer://guide/analyzer-mcp
aianalyzer://guide/dynamics-evidence
aianalyzer://guide/mono-compatibility
aianalyzer://guide/reference-comparison
aianalyzer://guide/verification-evidence
```

Clients should load only the guide relevant to the current task.

## MCP tools

MCP **1.2 exposes 47 tools**.

High-level tools include:

```text
audio_project_identity_status()
audio_project_status()
audio_set_analysis_profile(...)
audio_set_project_analysis_profile(...)
audio_song_status()
audio_song_overview()
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
audio_dynamics_distribution(...)
audio_mono_compatibility(...)
audio_capture_reference(...)
audio_list_references()
audio_compare_reference(...)
audio_begin_range_verification(...)
audio_complete_range_verification(...)
```

Do not mechanically run all 47 tools. Start high-level and drill down only where needed.

## User installation

GitHub Release packages are beginner-first.

Supported packages:

```text
Windows x64
macOS Apple Silicon arm64
```

Each platform gets one final ZIP. User Releases deliberately contain no MCP Python source, `requirements.txt`, venv, PyInstaller `_internal`, developer source config, or nested ZIP.

Typical contents:

```text
AI Audio Analyzer.vst3
mcp/
  ai-audio-analyzer-mcp[.exe]   standalone PyInstaller -F executable
skill/                          canonical Skill + MCP Resource content
START-HERE.md
MCP-SETUP.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
platform installer file(s)
```

Windows: extract once and run `Install.cmd`.

macOS Apple Silicon: extract once and run `Install.command`. Current macOS builds are ad-hoc signed, not Developer ID notarized.

## Repository MCP architecture

There is exactly one supported source/PyInstaller entrypoint:

```text
mcp/server.py
```

Current metadata:

```text
Product version             1.2.0
MCP version                 1.2
OSC analysis protocol       1.2
Analyzer control protocol   local revision 1
MCP tools                   47
Self-description schema     1
Guide resources             16
```

P8a adds `mcp/reference_tools.py` but does not change OSC analysis indexes `0..149`, VST3 DSP, or Analyzer control revision.

Repository-only `mcp/reference_regression.py` is CI code and is not shipped in beginner Releases.

## Skill

LLM-facing Skill/reference content is English-only and documents evidence semantics, validity, tool order, identity scope, reference comparison, and control boundaries.

Key references include:

```text
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/references/song-memory.md
skills/ai-analyzer-flstudio/references/section-structure.md
skills/ai-analyzer-flstudio/references/track-story.md
skills/ai-analyzer-flstudio/references/section-relationships.md
skills/ai-analyzer-flstudio/references/dynamics-evidence.md
skills/ai-analyzer-flstudio/references/mono-compatibility.md
skills/ai-analyzer-flstudio/references/reference-comparison.md
skills/ai-analyzer-flstudio/references/verification-evidence.md
skills/ai-analyzer-flstudio/references/analyzer-mcp.md
```

## License

AI Audio Analyzer is released under the **MIT License**. See [LICENSE](LICENSE).