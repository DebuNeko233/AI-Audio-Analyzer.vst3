# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** is a JUCE VST3 + MCP measurement, retained-memory and verification layer for AI/LLM-assisted music production.

It continuously measures audio inside the DAW, publishes structured OSC telemetry, retains transport-aligned evidence, and lets an Agent reason about current or past passages without pretending it can directly hear the DAW in real time.

Current product version: **1.2.0**.

## What it owns

```text
AI Audio Analyzer VST3
  -> realtime-safe measurement + DAW transport context

AI Audio Analyzer MCP
  -> observe / remember / structure / compare / verify
  -> retained Song Memory + Section Map + Track Story
  -> historical deep-range recall (P4b PR #36)
  -> dynamics / mono / reference evidence
  -> Analyzer Analysis Profile control only

External DAW-control MCP
  -> inspect / modify / read back DAW/project/plugin state
```

For FL Studio control, the current companion project is **rosasynthesiz/flstudio-mcp**.

Analyzer MCP is not a general DAW-control server. EQ, compression, gain, pan, routing, synth, automation and project writes remain external.

## Current metadata

On P4b PR #36:

```text
Product version             1.2.0
MCP version                 1.2
OSC analysis protocol       1.2
Analyzer control revision   1
MCP tools                   48
Guide Resources             16
```

P4b adds no OSC fields, VST3 DSP fields or control-protocol changes.

## Architecture

```text
FL Studio / DAW
|
+-- Track A -- AI Audio Analyzer.vst3
+-- Track B -- AI Audio Analyzer.vst3
+-- Master -- AI Audio Analyzer.vst3
                |
                | OSC measurements (default 127.0.0.1:9855)
                v
          Analyzer MCP
          +-- live instance registry + deterministic bindings
          +-- Analysis Profile control/telemetry
          +-- transport + instance-local playback epochs
          +-- 1 s Song Memory + 100 ms coverage accounting
          +-- Section Map / Track Story / relationships
          +-- P4b historical 1 s deep retained detail
          +-- dynamics / mono / reference comparison
          +-- recent + same-range verification
                |
                v
          Cherry Studio / LLM
                |
                +-- real DAW-control MCP for writes/readback
```

Only one Analyzer MCP process should bind measurement UDP port `9855`.

## Measurement capabilities

- Sample Peak, RMS, Crest;
- LUFS-S / LUFS-I / True Peak via `libebur128`;
- 4096-point FFT and 32 logarithmic spectrum bands;
- centroid / rolloff / flatness;
- full-band and frequency-dependent stereo correlation;
- Mid/Side, Side spectrum, Side/Mid and negative-cross evidence;
- Spectral Flux, RMS Rise and low-band temporal energy;
- 12-bin chroma, tonal-center and single-F0 harmonic evidence;
- DAW time / PPQ / BPM / time signature / loop / play / record context;
- estimated Analyzer lag, dropped blocks and worker/FIFO telemetry;
- bounded one-second Song Memory;
- explainable section boundaries and neutral recurring families;
- Track Story and section-aware relationship shortlisting;
- retained dynamics distributions;
- recent direct mono-fold energy evidence;
- P4b historical Mid/Side-derived mono/stereo/masking/temporal evidence;
- frozen session reference comparison;
- recent-window and transport-anchored same-range verification.

`null` means **unavailable**, not zero. Missing retained coverage is not silence.

## Project/runtime identity

Use:

```text
audio_project_identity_status()
```

Current contract:

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
runtime_id scope                        live_plugin_instance
runtime_id persistent                   false
same-project reopen UUID stable         false
binding scope                           mcp_session
cross-project retained-state isolation  not guaranteed
```

Reopening the same project recreates runtime UUIDs. Until authoritative project identity exists, restart Analyzer MCP after changing/reopening projects when strict retained-state isolation is required.

## Deterministic Analyzer ↔ Mixer mapping

Each Analyzer exposes the host parameter:

```text
Parameter ID: identify
Display name: Identify
```

The MCP can bind a runtime UUID to an FL Mixer Track/Slot and later use selectors such as:

```text
mixer:7/slot:9
```

Prefer deterministic Identify binding over guessing by track name or audio content.

## Adaptive Analysis Profiles

```text
0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

Analyzer-owned control tools:

```text
audio_set_analysis_profile(...)
audio_set_project_analysis_profile(...)
```

These affect measurement computation only, never the sound.

## Song Memory and structure

```text
canonical bin size       1 second
coverage slot            100 ms
retention                up to 1200 bins / Analyzer
retained span            about 20 minutes / instance
query resolutions        1 / 2 / 5 / 10 / 15 / 30 seconds
scope                    current MCP session
```

High-level tools:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
```

A/B/C families are neutral recurrence labels, not automatic Intro/Verse/Chorus/Drop labels.

## P4b historical deep recall — PR #36

P4b reduces forced replay for historical questions:

```text
audio_historical_detail(
  track,
  start_seconds=None,
  end_seconds=None,
  map_id=None,
  section_id=None,
  compare_track=None,
  minimum_coverage=0.8,
  max_masking_regions=8,
  temporal_low_hz=40,
  temporal_high_hz=160
)
```

It reuses the same canonical one-second Song Memory and P4a range resolver. It does **not** store raw audio.

When those feature families were measured during capture, historical results can include:

- 32-band Mid/Side retained spectrum;
- full-band + frequency-dependent stereo context;
- Mid/Side-derived mono-fold energy evidence;
- bounded one-second temporal summaries;
- optional same-range ERB masking/overlap, stereo, mono and temporal pair evidence.

Important boundaries:

- historical resolution is one second;
- no subsecond/sample-accurate historical alignment claim;
- each track independently selects the best local transport epoch by coverage;
- equal epoch numbers are not required across tracks;
- missing deep history remains unavailable, never silence;
- dedicated recent masking/stereo/temporal tools remain recent-window APIs with finer current-frame context;
- direct mono-fold Sample Peak / True Peak remain unavailable;
- no quality score or processing recommendation is emitted.

P4b regression currently guards a shallow Python container/array estimate around **1918 B/bin**, about **2.20 MiB/track** at 1200 detail bins. This is a bounded implementation estimate, not exact process RSS.

## Dynamics distributions

```text
audio_dynamics_distribution(...)
```

P6a provides coverage-aware retained RMS, LUFS-S, Crest, observed Sample-Peak and observed True-Peak distributions.

LUFS-S P90-P10 is descriptive and is **not standardized EBU LRA**. Arbitrary-range Integrated LUFS and PLR remain unavailable rather than being fabricated from pass-cumulative state.

## Mono compatibility

```text
audio_mono_compatibility(track, seconds=5.0)
```

P7a is a recent-window direct mono-fold RMS/energy tool based on existing Mid/Side math.

P4b historical mono energy is available separately through `audio_historical_detail()` at one-second retained resolution. Direct mono-fold Sample Peak and True Peak remain future optional P7b work.

## Session Reference Engine

P8a is merged and provides:

```text
audio_capture_reference(...)
audio_list_references()
audio_compare_reference(...)
```

References are frozen compact **recent-window measurement profiles**, not copied audio. They are MCP-session scoped and not whole-song truth.

P4b does not silently upgrade P8a into historical reference capture; a future reference extension must opt into retained historical profiles explicitly.

Reference deltas are context, not automatic EQ/master-match instructions.

## Controlled verification

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

Same-range mode selects clean retained passes by coverage, prevents pre-change evidence from silently becoming After, and requires caller-supplied actual host readback for `closed_loop_complete=true`.

`controlled_comparison=true` means technical comparability only. Neither it nor `closed_loop_complete=true` means a change sounds better.

## Self-describing MCP

The MCP provides:

```text
Server instructions
Tool descriptions
MCP Resources under aianalyzer://guide/*
```

The packaged/repository `skill/` directory remains the canonical long-form guide source. Clients should read only the relevant guide.

## High-level MCP tools

MCP 1.2 exposes **48 tools** on PR #36. Start high-level and drill down only where needed:

```text
audio_project_identity_status()
audio_project_status()
audio_song_status()
audio_song_overview()
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
audio_historical_detail(...)
audio_dynamics_distribution(...)
audio_mono_compatibility(...)
audio_capture_reference(...)
audio_list_references()
audio_compare_reference(...)
audio_begin_range_verification(...)
audio_complete_range_verification(...)
```

Do not mechanically run all 48 tools.

## Installation

Supported beginner packages:

```text
Windows x64
macOS Apple Silicon arm64
```

Each platform gets one final ZIP containing the VST3, standalone PyInstaller `-F` MCP runtime, canonical `skill/`, install/setup docs, VERSION and LICENSE.

User packages deliberately contain no MCP Python source, `requirements.txt`, venv, PyInstaller `_internal`, developer source config or nested ZIP.

Windows: extract once and run `Install.cmd`.

macOS Apple Silicon: extract once and run `Install.command`. Current builds are ad-hoc signed rather than Apple-notarized.

## Repository architecture

Stable source/PyInstaller entrypoint:

```text
mcp/server.py
```

P4b runtime modules:

```text
mcp/historical_detail_store.py
mcp/historical_detail_profile.py
mcp/historical_detail_pair.py
mcp/historical_detail_tools.py
```

`mcp/p4b_regression.py` is CI-only and must not ship in beginner Releases.

## License

AI Audio Analyzer is released under the **MIT License**. See [LICENSE](LICENSE).
