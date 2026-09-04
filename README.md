# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** is a JUCE VST3 machine-readable audio measurement layer for AI/LLM-assisted music-production workflows.

The plugin measures audio inside the DAW, emits compact OSC data to the Analyzer MCP Bridge, and exposes structured level, loudness, spectrum, stereo, temporal, masking, tonal, project, transport-aligned Song Memory, explainable song-structure, A/B, performance, and verification evidence to Cherry Studio or another MCP client.

Current product version: **1.2.0**.

## Project components

```text
AI Audio Analyzer
├─ VST3    realtime-safe measurement probe + DAW transport context
├─ MCP     measurement / Song Memory / structure / comparison / verification tools
└─ Skill   English LLM-facing instructions for correct MCP use and evidence semantics
```

The Analyzer is deliberately evidence-oriented. It does not encode fixed LUFS targets, genre EQ recipes, mandatory sidechain/compression rules, stereo recipes, forced Verse/Chorus/Drop labels, key changes, harmony edits, or mastering chains.

## Companion FL Studio MCP

For DAW topology and control, the current workflow pairs Analyzer MCP with:

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

```text
AI Audio Analyzer MCP   → observe / measure / remember / structure / compare / verify
FL Studio MCP           → inspect / control / modify / read back FL Studio
```

Analyzer MCP does **not** perform DAW writes. Real host/project data and parameter writes remain the responsibility of the actual DAW-control MCP.

## Architecture

```text
FL Studio / DAW
│
├─ Mixer Track A ─ AI Audio Analyzer.vst3
├─ Mixer Track B ─ AI Audio Analyzer.vst3
└─ Master        ─ AI Audio Analyzer.vst3
                         │
                         │ OSC UDP, default 127.0.0.1:9855
                         ▼
                 Analyzer MCP Bridge
                 ├─ live instance registry + deterministic bindings
                 ├─ adaptive-analysis status / worker telemetry
                 ├─ DAW transport + continuous playback epochs
                 ├─ one-second Song Memory + coarse aggregation
                 ├─ explainable section boundaries + A/B/C recurrence families
                 ├─ section profiles / project overview / Snapshot A-B
                 ├─ temporal / masking / stereo / tonal evidence
                 └─ closed-loop verification sessions
                         │
                         ▼
                  Cherry Studio / LLM
                         │
                         └─ external FL Studio control MCP for host changes/readback
```

Multiple Analyzer instances may send to the same UDP port. Only one MCP Bridge process should bind UDP `9855`.

The LLM is intentionally **not** part of the realtime measurement path. Analyzer keeps measuring and remembering DAW-time evidence while the model is thinking, calling tools, or waiting for an external DAW operation.

## Measurement capabilities

Core capabilities include:

- Sample Peak, RMS and Crest Factor;
- LUFS-S / LUFS-I and current/pass-max True Peak via `libebur128`;
- 4096-point FFT, Hann window and 32 log-spaced 20 Hz–20 kHz Mid-spectrum features;
- Spectral Centroid, ~85% Rolloff and Flatness;
- full-band and 8-band L/R Correlation;
- Spectral Flux, RMS Rise and 40–160 Hz temporal energy;
- Mid RMS, Side RMS, Side/Mid dB, Side spectrum, frequency-dependent Side/Mid ratio, low-band stereo relation, and negative cross-spectrum evidence;
- 12-bin Mid-spectrum chroma, tonal-center profile ranking, and single-F0 harmonic-alignment evidence;
- DAW transport position, PPQ/BPM/time-signature context, continuous playback epochs, estimated Analyzer backlog and cumulative dropped-block telemetry;
- bounded one-second Song Memory with 100 ms coverage accounting and 1/2/5/10/15/30-second query aggregation;
- explainable multi-scale song-section boundary detection and neutral recurring A/B/C families;
- section-level per-track profiles aligned by overlapping DAW time even when instance-local epoch numbers differ;
- project overview, Snapshot A/B, masking evidence, controlled Before/After verification, and adaptive-analysis performance telemetry.

### Signal validity

Approximate detector behavior:

```text
close   below -50 dBFS for ~0.4 s
reopen  above -48 dBFS
```

When `signal_present=false`, content-dependent measurements become unavailable rather than returning misleading zeroes. `null` means **unavailable**, not numeric zero.

### Deterministic Analyzer ↔ FL Mixer mapping

Every live Analyzer has a session runtime UUID and exposes a host-visible Boolean parameter:

```text
Parameter ID: identify
Display name: Identify
```

Every Identify transition emits `/aianalyzer/identify`, including while transport is stopped. The Bridge can bind that UUID to a real FL Mixer Track/Slot and later use selectors such as:

```text
mixer:7/slot:9
```

### Adaptive Analysis

```text
Parameter ID: analysis_profile
Display name: Analysis Profile
0 Eco
1 Balanced
2 Mix
3 Full
```

Profiles control **measurement computation only**:

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

`Full` remains the default for backward compatibility.

Analyzer MCP exposes:

```text
audio_analysis_status(track)
audio_project_performance()
```

Runtime telemetry includes:

```text
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
```

`worker_load_ratio` describes the Analyzer **background worker**, not DAW realtime audio-thread CPU. Sustained FIFO growth can indicate measurement lag.

The actual Analysis Profile write remains the responsibility of the DAW-control MCP. Disabled feature families are explicitly marked unavailable in MCP.

## Transport-aware Song Memory

Protocol 1.2 adds DAW-time context so delayed LLM calls do not need to catch an event while it is happening.

```text
DAW playback
→ Analyzer measures continuously
→ frames are associated with estimated DAW time / PPQ
→ MCP builds one-second Song Memory
→ LLM can query the remembered pass later
```

High-level tools:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(track, resolution_seconds=5, ...)
```

A `transport_epoch` is one **continuous playback pass for one Analyzer instance**. Playback start, seek, loop jump, or another detected discontinuity starts a new epoch.

The worker discards queued pre-jump audio and resets pass-dependent Loudness/Temporal/Semantic state. Transport publication is gated until the worker acknowledges the new epoch so old audio is not mislabeled with the new DAW position.

Epoch counters are instance-local. Equal numbers across independently loaded Analyzer instances are not permanent project-wide pass IDs.

Transport coordinates compensate approximately for FIFO backlog plus half the FFT window and expose:

```text
estimated_analysis_lag_ms
dropped_blocks
data_age_seconds
coverage_ratio
```

The canonical MCP memory keeps at most 1200 one-second bins per Analyzer instance (about 20 minutes). Coverage is tracked in 100 ms slots so sparse data cannot become false 100% coverage after coarse aggregation.

For protocol-1.2 instances, LUFS-I and pass-max True Peak restart when the transport epoch changes. Snapshot tools do not independently reset loudness.

## Explainable song structure

The first song-structure layer is built on Song Memory and adds **no OSC fields or realtime DSP work**.

```text
Song Memory
→ robust feature normalization
→ multi-scale 2 / 4 / 8 s left-right novelty comparison
→ adaptive boundary threshold + minimum spacing
→ sections S01 / S02 / ...
→ transparent section-to-section similarity
→ neutral recurring A / B / C / ... families
```

Tools:

```text
audio_section_map(
  reference_track=None,
  transport_epoch=None,
  min_section_seconds=8,
  sensitivity=0.55,
  family_similarity=0.78,
  max_sections=48,
  max_tracks=32
)

audio_section_profile(section_id, map_id=None, max_tracks=32, max_related=8)
```

Boundary evidence can include:

```text
cross-track active/inactive changes
RMS / LUFS-S changes
spectral centroid / broad spectral balance changes
chroma changes
stereo changes
crest / spectral-flux changes
```

`boundary strength` is structural novelty evidence, **not** a calibrated probability that a human would mark a formal section boundary.

Recurring families are deliberately neutral:

```text
S01  A
S02  B
S03  C
S04  B
S05  C
```

The Analyzer does **not** automatically assert:

```text
A = Intro
B = Verse
C = Chorus
```

Exact DAW markers, Playlist/arrangement labels, MIDI/project annotations, or explicit user-provided structure are authoritative for exact semantic names. An LLM can interpret A/B/C later when it has those additional sources.

Supporting tracks are aligned by overlapping **DAW-time coverage**, not equal numeric `transport_epoch` values. Missing Song Memory is reported as missing coverage; a gap is not interpreted as silence or a structural transition.

Recommended whole-song path:

```text
audio_project_status()
→ audio_song_status()
→ capture/play enough of the intended pass
→ audio_section_map()
→ audio_section_profile() for relevant sections
→ audio_song_timeline() only if raw time evolution is still needed
→ specialized Temporal / Masking / Stereo / Tonal tools only for the relationships that matter
```

This reduces LLM token load and prevents “latest-frame” reasoning from dominating whole-song decisions.

## Evidence layers

### Temporal

```text
audio_temporal_profile()
audio_temporal_compare()
```

Temporal overlap/correlation is evidence of time co-occurrence/co-variation, not a masking probability or processing instruction.

### Masking

```text
audio_masking_evidence()
audio_project_masking_scan()
```

The current model rebins Analyzer spectrum into 16 equal ERB-rate regions, applies relative-level evidence and temporal interaction when available. It is not a calibrated cochlear model or audible-masking probability.

### Stereo / Mid-Side

```text
audio_stereo_profile()
audio_stereo_compare()
```

Signed L/R correlation, Side/Mid energy, negative-cross evidence and frequency-dependent stereo relation remain separate. No universal stereo target is defined.

### Tonal / music-semantic evidence

```text
audio_tonal_profile()
audio_tonal_compare()
```

The Analyzer exposes normalized 12-bin chroma, tonal-center template correlations and single-F0 harmonic-alignment evidence. These are not exact key/note probabilities. Prefer exact DAW/MIDI symbolic data for exact facts.

## Controlled verification

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

Canonical flow:

```text
Before baseline
→ external DAW-control MCP write
→ actual host readback
→ comparable After capture
→ comparability guardrails
→ After-minus-Before deltas
```

`controlled_comparison=true` means technical comparability only. `closed_loop_complete=true` additionally requires caller-supplied actual host readback. Neither means the change is artistically better.

Current verification remains recent-window based; transport-anchored same-range verification is not yet implemented.

## MCP tools

MCP **1.2 exposes 34 tools**. Whole-song/structure high-level tools are:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
audio_section_map(...)
audio_section_profile(...)
```

Do not mechanically run all 34 tools. Start high-level, then drill down only where the song/section context requires it.

## User installation

GitHub **Release packages are beginner-first** and designed for users with no programming experience.

Supported packages:

```text
Windows x64
macOS Apple Silicon arm64
```

Each platform has one final ZIP. Extract it once.

Typical contents:

```text
AI Audio Analyzer.vst3
mcp/
└─ ai-audio-analyzer-mcp[.exe]   standalone PyInstaller -F executable
skill/
START-HERE.md
MCP-SETUP.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
platform installer file(s)
```

User Releases deliberately contain **no MCP Python source**, `requirements.txt`, venv, PyInstaller `_internal`, developer source configuration examples, or nested ZIP.

Windows: extract once and double-click `Install.cmd`.

macOS Apple Silicon: extract once and double-click `Install.command`. Current macOS builds are ad-hoc signed, not Apple Developer ID notarized.

The installer generates `cherry-studio-mcp.json` with the real absolute MCP executable path. Follow `MCP-SETUP.md`, then import the `skill` folder for the same Agent/Assistant.

## Repository MCP architecture

There is exactly one supported source/PyInstaller entrypoint:

```text
mcp/server.py
```

Current metadata:

```text
Product version       1.2.0
MCP version           1.2
OSC protocol version  1.2
MCP tools             34
```

Internal modules:

```text
mcp/server.py             startup / self-test / shared tool registry
mcp/analyzer_core.py      OSC state, identity/binding, base tools
mcp/project_tools.py      project overview / Snapshot A-B
mcp/temporal_tools.py     temporal layer
mcp/masking_tools.py      masking-evidence layer
mcp/stereo_tools.py       Mid/Side and stereo layer
mcp/semantic_tools.py     chroma / tonal-center / harmonic evidence
mcp/performance_tools.py  adaptive profile / worker telemetry layer
mcp/song_tools.py         DAW transport / pass memory / latency-aware song summaries
mcp/section_tools.py      explainable boundaries / recurring families / section profiles
mcp/verification_tools.py controlled verification sessions
mcp/ci_regression.py      repository-only synthetic regression suite
```

## Skill

LLM-facing Skill content is English-only. Important references include:

```text
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/README-CHERRY-STUDIO.md
skills/ai-analyzer-flstudio/references/analyzer-mcp.md
skills/ai-analyzer-flstudio/references/parameters.md
skills/ai-analyzer-flstudio/references/performance-evidence.md
skills/ai-analyzer-flstudio/references/song-memory.md
skills/ai-analyzer-flstudio/references/section-structure.md
skills/ai-analyzer-flstudio/references/masking-evidence.md
skills/ai-analyzer-flstudio/references/stereo-evidence.md
skills/ai-analyzer-flstudio/references/tonal-evidence.md
skills/ai-analyzer-flstudio/references/verification-evidence.md
```

## OSC protocol

Analysis address: `/aianalyzer/frame`.

OSC **1.2** remains append-only. The current tail is:

```text
128  analysis_profile
129  analysis_feature_mask
130  worker_load_ratio
131  fifo_fill_ratio
132  fft_runs_per_second
133  semantic_runs_per_second
134  schema marker = "1.1"
135  transport_supported
136  transport_time_seconds
137  transport_ppq_position
138  transport_bpm
139  transport_time_signature_numerator
140  transport_time_signature_denominator
141  transport_is_playing
142  transport_is_recording
143  transport_is_looping
144  transport_loop_start_ppq
145  transport_loop_end_ppq
146  transport_epoch
147  estimated_analysis_lag_ms
148  dropped_blocks
149  schema marker = "1.2"
```

The song-structure layer consumes MCP Song Memory and does not change this wire format.

## License

AI Audio Analyzer is released under the **MIT License**. See [LICENSE](LICENSE).
