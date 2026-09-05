# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** is a JUCE VST3 machine-readable audio measurement layer for AI/LLM-assisted music-production workflows.

It measures audio inside the DAW, publishes structured OSC telemetry to the Analyzer MCP Bridge, and exposes level, loudness, spectrum, stereo, temporal, masking, tonal, project, transport-aligned Song Memory, explainable song structure, Track Story, section-aware mix relationships, performance telemetry, and closed-loop verification evidence to Cherry Studio or another MCP client.

Current product version: **1.2.0**.

## System boundary

```text
AI Audio Analyzer VST3
  -> realtime-safe measurement + DAW transport context

AI Audio Analyzer MCP
  -> observe / remember / structure / compare / verify
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
                 +-- adaptive-analysis status / worker telemetry
                 +-- Analyzer-owned loopback Profile control + ACK
                 +-- DAW transport + instance-local playback epochs
                 +-- one-second Song Memory + coverage accounting
                 +-- explainable section boundaries + recurrence families
                 +-- Track Story across sections/families
                 +-- bounded section-aware relationship shortlist
                 +-- recent-window + transport-range verification
                 +-- temporal / masking / stereo / tonal evidence
                         |
                         v
                  Cherry Studio / LLM
                         |
                         +-- external DAW-control MCP for real changes/readback
```

Multiple Analyzer instances may send to the same UDP measurement port. Only one MCP Bridge should bind UDP `9855`.

The LLM is intentionally outside the realtime measurement path. Analyzer continues measuring while the Agent is reasoning or calling other tools.

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
- section profiles, Track Story and section-aware relationship shortlisting;
- project Snapshot A/B and recent-window verification;
- transport-anchored same-range Before/After verification;
- adaptive Analysis Profiles and worker/FIFO telemetry.

The Analyzer is evidence-oriented. It does not hard-code genre recipes, fixed LUFS targets, mandatory EQ/sidechain/compression/stereo moves, semantic Verse/Chorus/Drop labels, key changes, harmony edits, or mastering chains.

`null` means **unavailable**, not numeric zero.

Missing retained coverage is not silence.

## Deterministic Analyzer ↔ FL Mixer mapping

Each live Analyzer has a session runtime UUID and exposes:

```text
Parameter ID: identify
Display name: Identify
```

Each Identify transition emits `/aianalyzer/identify`. The Bridge can bind that runtime UUID to a real FL Mixer Track/Slot and later use selectors such as:

```text
mixer:7/slot:9
```

Prefer deterministic binding over guessing identity from track name or audio content.

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

Keep these two confirmations separate:

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

Transport coordinates are appropriate for whole-song/section/range reasoning, not sample-accurate edits.

## Explainable song structure

```text
Song Memory
-> robust normalization
-> 2 / 4 / 8 s novelty comparison
-> adaptive boundaries
-> S01 / S02 / ...
-> neutral recurrence families A / B / C / ...
```

Tools:

```text
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
```

A/B/C families are recurrence labels only. They are not automatically Intro/Verse/Chorus/Drop.

### Track Story

`audio_track_story(track, map_id)` summarizes one Analyzer across the section map using activity, levels, spectrum, stereo, temporal, chroma, coverage/lag/drop, adjacent deltas, same-family per-dimension variation and relative extrema.

It does not create one overall quality/consistency score, infer a track role, or prescribe processing.

### Section-aware Mix Relationships

`audio_section_relationships(...)` returns a bounded shortlist of track pairs worth deeper inspection in particular sections/families.

`shortlist_priority` is inspection priority only. It is not masking probability, audibility probability, mix-problem probability, quality score, or a processing recommendation.

Detailed masking/stereo/temporal pair tools remain recent-window based. A historical section shortlist does not automatically turn those detailed tools into historical range analyzers.

## Controlled verification

Two verification paths coexist.

### Recent-window verification

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

Use this when an explicit retained DAW-time range is unavailable or unnecessary.

Its comparability checks include window duration, topology, target validity and an active-ratio passage guard.

### Transport-anchored same-range verification

Prefer this when the Agent can name/replay a specific DAW-time range:

```text
audio_begin_range_verification(
  label,
  start_seconds,
  end_seconds,
  target_selectors=None,
  minimum_coverage=...
)

-> external DAW-control MCP performs the real write
-> external DAW-control MCP reads back actual host state
-> replay the returned effective_range

audio_complete_range_verification(
  verification_id,
  change_summary="...",
  host_readback="..."
)

audio_range_verification_status(...)
```

Important semantics:

- fractional requests are returned alongside the normalized one-second `effective_range`;
- each Analyzer independently chooses its best retained local epoch;
- pass selection is coverage-first, then recency;
- equal numeric epochs across tracks are not required;
- After must come from a clean retained pass first observed after the frozen receive-time fence;
- pre-change Song Memory cannot silently be reused as After;
- retained feature availability is used for historical comparability instead of pretending the current live Profile describes the past;
- a higher selected After dropped-block count blocks a controlled comparison;
- `active_ratio` is descriptive in same-range mode, not a proxy for passage identity;
- arbitrary-range LUFS-I delta is intentionally unavailable because current retained `lufs_i_latest` is pass-cumulative, not range-integrated;
- Analyzer still performs no sound-changing write.

```text
controlled_comparison=true
```

means technical comparability only.

```text
closed_loop_complete=true
```

additionally requires caller-supplied actual host readback.

Neither means After is artistically better.

See `skills/ai-analyzer-flstudio/references/verification-evidence.md`.

## MCP tools

MCP **1.2 exposes 41 tools**.

High-level tools include:

```text
audio_project_status()
audio_set_analysis_profile(...)
audio_set_project_analysis_profile(...)
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
audio_begin_range_verification(...)
audio_complete_range_verification(...)
audio_range_verification_status(...)
```

Do not mechanically run all 41 tools. Start high-level and drill down only where needed.

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
skill/
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
MCP tools                   41
```

Runtime modules:

```text
mcp/server.py
mcp/analyzer_core.py
mcp/project_tools.py
mcp/temporal_tools.py
mcp/masking_tools.py
mcp/stereo_tools.py
mcp/semantic_tools.py
mcp/performance_tools.py
mcp/control_tools.py
mcp/song_tools.py
mcp/section_tools.py
mcp/track_story_tools.py
mcp/section_relationship_tools.py
mcp/verification_tools.py
mcp/range_tools.py
mcp/range_verification_tools.py
```

Repository-only regressions:

```text
mcp/ci_regression.py
mcp/relationship_regression.py
mcp/range_verification_regression.py
```

Regression files are not shipped in beginner user Releases.

## OSC protocol

Analysis address: `/aianalyzer/frame`.

OSC **1.2** remains append-only. Existing indexes `0..149` are unchanged by Track Story, section relationships, or transport-range verification.

The Analyzer-owned Analysis Profile control is a separate loopback-only control protocol, revision 1.

## Skill

LLM-facing Skill/reference content is English-only and documents evidence semantics, validity, tool order, and control boundaries.

Key references include:

```text
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/references/song-memory.md
skills/ai-analyzer-flstudio/references/section-structure.md
skills/ai-analyzer-flstudio/references/track-story.md
skills/ai-analyzer-flstudio/references/section-relationships.md
skills/ai-analyzer-flstudio/references/verification-evidence.md
skills/ai-analyzer-flstudio/references/analyzer-mcp.md
```

## License

AI Audio Analyzer is released under the **MIT License**. See [LICENSE](LICENSE).
