# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** is a JUCE VST3 machine-readable audio measurement layer for AI/LLM-assisted music-production workflows.

The plugin measures audio inside the DAW, emits compact OSC data to the Analyzer MCP Bridge, and exposes structured level, loudness, spectrum, stereo, temporal, masking, tonal, project, transport-aligned song-memory, A/B, performance, and closed-loop verification evidence to Cherry Studio or another MCP client.

Current product version: **1.2.0**.

## Project components

```text
AI Audio Analyzer
├─ VST3    realtime-safe measurement probe inside the DAW
├─ MCP     structured measurement / timeline / comparison / verification tools
└─ Skill   English LLM-facing instructions for correct MCP use and parameter semantics
```

The Skill is intentionally **not** a style-specific mixing or harmony guide. It does not encode fixed LUFS targets, EQ/compression/sidechain recipes, stereo recipes, key-change rules, harmony edits, or mastering chains.

## Companion FL Studio MCP

For DAW topology and control, the current workflow pairs Analyzer MCP with:

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

```text
AI Audio Analyzer MCP   → observe / measure / remember / compare / verify
FL Studio MCP           → inspect / control / modify / read back FL Studio
```

Analyzer MCP does **not** perform DAW writes. Host-visible Analyzer parameters are changed through the actual DAW-control MCP and then verified from Analyzer telemetry.

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
                 ├─ live instance registry
                 ├─ deterministic FL Track/Slot bindings
                 ├─ DAW transport + continuous playback epochs
                 ├─ one-second song timeline memory / coarse aggregation
                 ├─ project overview / Snapshot A-B
                 ├─ adaptive-analysis status / performance telemetry
                 ├─ temporal / masking evidence
                 ├─ Mid/Side + stereo evidence
                 ├─ tonal / music-semantic evidence
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
- bounded one-second song timeline memory with 1/2/5/10/15/30-second query aggregation;
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

### Adaptive analysis and performance control

Large projects may contain many Analyzer instances. Running every evidence family continuously on every track is unnecessary, so each plugin exposes a host-visible choice parameter:

```text
Parameter ID: analysis_profile
Display name: Analysis Profile

0 Eco
1 Balanced
2 Mix
3 Full
```

Profiles control **measurement computation only**; they do not process or change the audio:

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

`Full` remains the default for backward compatibility. Older saved states that do not contain this parameter also restore as Full.

Scheduling is intentionally different by profile:

```text
Eco       no FFT / loudness analysis
Balanced  reduced FFT scheduling, approximately network-update scale
Mix       hop-level FFT for temporal evidence
Full      Mix + lower-rate semantic analysis
```

The exact observed rates depend on sample rate, transport/audio flow and host scheduling.

Analyzer MCP exposes:

```text
audio_analysis_status(track)
audio_project_performance()
```

These report the actual profile/feature mask received from the plugin plus:

```text
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
```

`worker_load_ratio` describes the **background Analyzer worker**, not the DAW realtime audio-thread CPU. `fifo_fill_ratio` is particularly important: sustained growth means analysis is falling behind incoming audio and measurements may become stale relative to the DAW.

The actual profile write remains the responsibility of the real DAW-control MCP. A typical on-demand flow is:

```text
read audio_analysis_status()
→ use FL Studio MCP to set Analysis Profile only when deeper evidence is needed
→ read the real host parameter back
→ verify Analyzer telemetry changed
→ collect the required evidence
→ restore the previous profile when appropriate
```

Disabled feature families are explicitly marked unavailable in the Bridge. Compatibility placeholder values in the append-only OSC frame are never treated as valid measurements when their feature bit is off.

### Transport-aware song memory

Protocol 1.2 adds DAW-time context so delayed LLM calls do not need to catch an event while it is happening.

```text
DAW playback
→ Analyzer measures continuously
→ each frame is associated with estimated DAW time / PPQ
→ MCP aggregates one-second timeline bins
→ LLM can query the remembered pass later
```

High-level tools:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(track, resolution_seconds=5, ...)
```

A `transport_epoch` represents one **continuous playback pass for one Analyzer instance**. Playback start, seek, loop jump, or another detected transport discontinuity starts a new epoch. The worker discards queued pre-jump audio and resets pass-dependent loudness, temporal, and semantic state so old and new song positions are not silently blended.

Epoch counters are instance-local. If Analyzer instances were loaded at different times, the same epoch number is not a permanent project-wide pass ID. Project-level song tools report whether counters are consistent and preserve DAW-time spans instead of pretending otherwise.

Transport coordinates are latency-aware estimates for the analyzed window. The worker compensates for queued FIFO audio plus half of the FFT window and exposes:

```text
estimated_analysis_lag_ms
dropped_blocks
data_age_seconds
```

`estimated_analysis_lag_ms` is Analyzer backlog/window latency, **not** network latency and not LLM reasoning latency. Song memory is specifically designed so those later delays do not erase the evidence.

The canonical MCP memory keeps at most 1200 one-second bins per Analyzer instance (20 minutes) in the running MCP session. It can return 1, 2, 5, 10, 15 or 30-second aggregate bins. Automatic Verse/Chorus/Bridge naming is not implemented yet; future section detection can build on this retained timeline.

For protocol-1.2 instances, LUFS-I and pass-max True Peak restart when the transport epoch changes. Snapshot tools do not independently reset loudness. Legacy instances retain their historical reset/prepare-scoped loudness semantics.

### Project intelligence / Snapshot A-B

Project tools provide readiness, recent overview, and Bridge-session Before/After snapshots.

### Temporal evidence

```text
audio_temporal_profile()
audio_temporal_compare()
```

Temporal overlap/correlation is evidence of time co-occurrence/co-variation, not a masking probability or processing instruction. Temporal tools require a profile with Temporal enabled.

### Stronger masking evidence

```text
32 Mid-spectrum features
→ 16 equal ERB-rate regions
→ relative spectral occupancy
→ directional relative-level weighting
→ temporal overlap when available
→ region-level masking evidence
```

Tools:

```text
audio_masking_evidence()
audio_project_masking_scan()
```

This is **equal-ERB-rate feature re-binning**, not a gammatone/cochlear filterbank or calibrated hearing-threshold model. Scores are heuristic evidence, not audible-masking probabilities.

### Deeper Mid/Side and stereo evidence

```text
audio_stereo_profile(track, seconds=5)
audio_stereo_compare(track_a, track_b, seconds=5)
```

This layer keeps signed L/R correlation, Side/Mid energy, decorrelation proxy, negative cross-spectrum evidence, low-frequency stereo relation, Mid/Side spectra, and frequency-dependent stereo evidence separate. No universal stereo target is defined.

### Audio-domain tonal / music-semantic evidence

```text
audio_tonal_profile(track, seconds=8)
audio_tonal_compare(track_a, track_b, seconds=8)
```

The Analyzer exposes normalized 12-bin chroma, chroma energy coverage, tonal-center template correlations and single-F0 harmonic-alignment evidence. Chroma uses Mid-spectrum power approximately over `80 Hz–5 kHz`; candidate F0 search is approximately `55–1000 Hz`.

Tonal-center ranking uses 24 major/minor Krumhansl-Kessler profile correlations. These are audio-domain evidence, not exact key/note probabilities. Prefer exact MIDI/DAW note, key, chord, or tuning metadata for exact symbolic facts when available. Tonal tools require Semantic enabled, normally `Full`.

### Reliable closed-loop verification

```text
audio_begin_verification(label, seconds=5, target_selectors=None)
audio_complete_verification(verification_id, seconds=0, change_summary="", host_readback="")
audio_verification_status(verification_id="")
```

Canonical flow:

```text
Before baseline
→ external DAW-control MCP change
→ actual host readback
→ After capture
→ comparability guardrails
→ After-minus-Before measurement deltas
```

`controlled_comparison=true` means only that the current technical Before/After guardrails passed. It does **not** mean the change is better, correct, more professional, or should be kept.

`closed_loop_complete=true` additionally requires caller-supplied actual host readback. Analyzer stores that readback for auditability but does not independently query the FL Studio control state.

Verification sessions are Bridge-session memory only. Transport-anchored same-range verification is a later layer; current verification tools still use recent-window captures.

## MCP tools

MCP **1.2 exposes 32 tools**. The new high-level whole-song layer adds:

```text
audio_song_status()
audio_song_overview(transport_epoch=None, max_tracks=32)
audio_song_timeline(track, resolution_seconds=5, transport_epoch=None, start_seconds=None, end_seconds=None, max_bins=240)
```

Use tools progressively. For a whole-song mixing/mastering request, start with project readiness and `audio_song_status()`, then prefer `audio_song_overview()` / `audio_song_timeline()` before drilling into low-level recent-window evidence. Do not mechanically run all measurements on all tracks.

## User installation

GitHub **Release packages are beginner-first** and designed for users with no programming experience.

Supported packages:

```text
Windows x64
macOS Apple Silicon arm64
```

Intel/x86_64 macOS is not packaged.

Each platform has one final ZIP. Extract it once; there is no Release ZIP nested inside it.

```text
AI Audio Analyzer.vst3
mcp/
└─ ai-audio-analyzer-mcp[.exe]   standalone PyInstaller -F executable
skill/
START-HERE.md
MCP-SETUP.md                     Agent/MCP setup + copyable JSON examples
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
platform installer file(s)
```

User Releases deliberately contain **no MCP Python source**, `requirements.txt`, venv, PyInstaller `_internal`, developer source configuration examples, or nested ZIP.

Windows: extract once and double-click `Install.cmd`.

macOS Apple Silicon: extract once and double-click `Install.command`. If Gatekeeper blocks it, right-click and choose **Open**. Current macOS builds are ad-hoc signed, not Apple Developer ID notarized.

The installer generates `cherry-studio-mcp.json` with the real absolute MCP executable path. Follow `MCP-SETUP.md` to import/add that configuration to an MCP-capable client and **enable it for the Agent/Assistant that will use Analyzer**, then import the `skill` folder for the same Agent.

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
MCP tools             32
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
mcp/verification_tools.py controlled verification sessions
mcp/ci_regression.py      repository-only synthetic regression suite
```

Repository/source development may use Python 3.12 and `mcp/requirements.txt`; that developer workflow is **not shipped in the user Release**.

## Skill

LLM-facing Skill content is English-only. Important references include:

```text
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/README-CHERRY-STUDIO.md
skills/ai-analyzer-flstudio/references/analyzer-mcp.md
skills/ai-analyzer-flstudio/references/parameters.md
skills/ai-analyzer-flstudio/references/performance-evidence.md
skills/ai-analyzer-flstudio/references/song-memory.md
skills/ai-analyzer-flstudio/references/masking-evidence.md
skills/ai-analyzer-flstudio/references/stereo-evidence.md
skills/ai-analyzer-flstudio/references/tonal-evidence.md
skills/ai-analyzer-flstudio/references/verification-evidence.md
```

The Skill teaches tool use, selector/mapping rules, profile selection, validity, timeline/latency semantics, and parameter/evidence semantics. It does not prescribe a mixing aesthetic or processing action.

## OSC protocol

Analysis address: `/aianalyzer/frame`.

OSC **1.2** remains append-only:

```text
0..58     historical core / signal / identity fields
59..64    temporal fields + schema marker
65..111   Mid/Side + stereo fields + schema marker
112..123  12 chroma bins: C..B
124       chroma_energy_ratio
125       single_f0_harmonic_energy_ratio
126       harmonic_f0_candidate_hz
127       schema marker = "0.9"
128       analysis_profile
129       analysis_feature_mask
130       worker_load_ratio
131       fifo_fill_ratio
132       fft_runs_per_second
133       semantic_runs_per_second
134       schema marker = "1.1"
135       transport_supported
136       transport_time_seconds
137       transport_ppq_position
138       transport_bpm
139       transport_time_signature_numerator
140       transport_time_signature_denominator
141       transport_is_playing
142       transport_is_recording
143       transport_is_looping
144       transport_loop_start_ppq
145       transport_loop_end_ppq
146       transport_epoch
147       estimated_analysis_lag_ms
148       dropped_blocks
149       schema marker = "1.2"
```

Existing indexes `0..134` are not repurposed. Historical indexes `11..42` remain the 32-band Mid spectrum. Identify address remains `/aianalyzer/identify`.

## Realtime design

The audio callback does not perform FFT, loudness, semantic analysis, OSC, MCP, verification orchestration, allocation-heavy work, or file/network I/O. Samples are pushed into a preallocated SPSC FIFO and analyzed on a background worker thread.

Profile changes are forwarded to the worker only when the host parameter actually changes; normal audio blocks do not wake the worker just to restate the current profile.

DAW transport is sampled from the host in `processBlock()` and handed to the worker using atomics only. A detected playback epoch change is handled asynchronously by the worker, which discards queued pre-jump audio before resetting pass-dependent state. This prevents stale FIFO data from being labeled with a new song position without adding locks/network work to the callback.

When a disabled family is re-enabled, state that would otherwise span the unmeasured gap is reset: loudness measurement state is rebuilt, temporal previous-frame/accumulator state is cleared, and semantic cache is cleared.

## Current limitations

- Transport coordinates are worker-side estimates corrected for current FIFO backlog and FFT-window center; they are intended for song/section reasoning, not sample-accurate editing or transient placement.
- Song memory is in-memory and MCP-session scoped; it is not yet a persistent project database.
- Automatic Verse/Chorus/Bridge segmentation and labeling are not implemented yet.
- `transport_epoch` is instance-local, not a persistent project-wide pass identifier.
- Performance telemetry is Analyzer-worker instrumentation, not calibrated DAW/system CPU profiling.
- Adaptive profiles reduce Analyzer work but do not promise a fixed CPU reduction on every host or sample rate.
- ERB handling is feature re-binning, not a true auditory filterbank; masking evidence remains heuristic.
- Stereo, tonal and temporal metrics are measurements/evidence, not quality scores.
- Chroma is FFT-derived pitch-class evidence, not transcription; tonal-center ranking is not exact key detection.
- Single-F0 harmonic evidence can be unstable on polyphonic/noisy/inharmonic material.
- The topology fingerprint is a live Analyzer consistency marker, not a complete persistent DAW-project hash.
- `host_readback` is supplied by the caller/external control MCP and is not independently validated by Analyzer.
- Verification sessions and FL Mixer bindings are session-scoped.
- For protocol-1.2 instances, LUFS-I/pass-max True Peak accumulate within the current continuous transport epoch while Loudness is enabled; a playback start/seek/loop discontinuity or Loudness re-enable starts a fresh loudness state. Legacy instances retain historical reset/prepare behavior.
- macOS Release support is Apple Silicon only and currently not notarized.

## Repository layout

```text
Source/                         JUCE VST3
mcp/server.py                   single MCP entrypoint
mcp/analyzer_core.py            stable internal MCP/OSC core
mcp/*_tools.py                  feature modules, including song timeline memory
mcp/ci_regression.py            repository-only MCP regression suite
skills/ai-analyzer-flstudio/    English LLM-facing Skill
release/                        beginner Release installers/docs
.github/workflows/build.yml     development CI
.github/workflows/release.yml   manual Release packaging
AGENT.md                        agent/maintainer contract and history
```

Before modifying the repository, read `AGENT.md`.

## License

AI Audio Analyzer project code is released under the **MIT License**. See [LICENSE](LICENSE) for the full text.

Third-party dependencies and components retain their own licenses; the MIT License for this repository does not replace or override those third-party license terms.
