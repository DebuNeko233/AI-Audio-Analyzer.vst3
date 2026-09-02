# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** is a JUCE VST3 machine-readable audio measurement layer for AI/LLM-assisted music-production workflows.

The plugin measures audio inside the DAW, emits compact OSC data to the Analyzer MCP Bridge, and exposes structured level, loudness, spectrum, stereo, temporal, project, A/B, masking-related, audio-domain tonal, and V1.0 closed-loop verification evidence to Cherry Studio or another MCP client.

Current product version: **1.0.0**.

## Project components

```text
AI Audio Analyzer
├─ VST3    realtime-safe measurement probe inside the DAW
├─ MCP     structured measurement / comparison / verification tools
└─ Skill   English LLM-facing instructions for correct MCP use and parameter semantics
```

The Skill is intentionally **not** a style-specific mixing/harmony guide. It does not encode fixed LUFS targets, EQ/compression/sidechain recipes, stereo recipes, key-change rules, harmony edits, or mastering chains.

## Companion FL Studio MCP

For DAW topology/control, the current workflow pairs Analyzer MCP with:

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

```text
AI Audio Analyzer MCP   → observe / measure / compare / verify
FL Studio MCP           → inspect / control / modify / read back FL Studio
```

V1.0 makes the intended closed loop explicit:

```text
DISCOVER
→ deterministic Analyzer mapping
→ OBSERVE Before
→ external reasoning / user intent
→ CHANGE through the real DAW-control MCP
→ READBACK actual host state
→ OBSERVE After
→ verify Before/After comparability
→ drill into specialized evidence only when needed
```

Analyzer MCP does **not** perform the DAW write.

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
                 ├─ project overview / Snapshot A-B
                 ├─ V0.6 temporal evidence
                 ├─ V0.7 masking evidence
                 ├─ V0.8 Mid/Side + stereo evidence
                 ├─ V0.9 tonal / music-semantic evidence
                 └─ V1.0 closed-loop verification sessions
                         │
                         ▼
                  Cherry Studio / LLM
                         │
                         └─ external FL Studio control MCP for host changes/readback
```

Multiple Analyzer instances may send to the same UDP port. Only one MCP Bridge process should bind UDP `9855`.

## Measurement capabilities

Core measurements include:

- 4096-point FFT, Hann window, 1024-sample hop;
- 32 log-spaced 20 Hz–20 kHz **Mid-spectrum** features;
- Sample Peak, RMS and Crest Factor;
- LUFS-S / LUFS-I and current/session-max True Peak via `libebur128`;
- Spectral Centroid, ~85% Rolloff and Flatness;
- full-band L/R Correlation and legacy Mid/Side width ratio;
- 8-band L/R Correlation;
- V0.6 Spectral Flux, RMS Rise and 40–160 Hz temporal energy;
- V0.8 Mid RMS, Side RMS, Side/Mid dB, Side spectrum, frequency-dependent Side/Mid ratio, low-band stereo relation, and negative cross-spectrum evidence;
- V0.9 12-bin Mid-spectrum chroma, chroma analysis coverage, tonal-center profile ranking, and single-F0 harmonic-alignment evidence.

### V0.3 signal validity

Approximate detector behavior:

```text
close   below -50 dBFS for ~0.4 s
reopen  above -48 dBFS
```

When `signal_present=false`, content-dependent measurements become unavailable rather than returning misleading zeroes. `null` means **unavailable**, not numeric zero.

### V0.4 deterministic Analyzer ↔ FL Mixer mapping

Every live Analyzer has a session runtime UUID and exposes a host-visible Boolean parameter:

```text
Parameter ID: identify
Display name: Identify
```

Every Identify transition emits `/aianalyzer/identify`, including while transport is stopped. The Bridge can bind that UUID to a real FL Mixer Track/Slot and later use selectors such as:

```text
mixer:7/slot:9
```

### V0.5 project intelligence / Snapshot A-B

Project tools provide readiness, recent overview, and Bridge-session Before/After snapshots.

### V0.6 temporal evidence

```text
audio_temporal_profile()
audio_temporal_compare()
```

Temporal overlap/correlation is evidence of time co-occurrence/co-variation, not a masking probability or processing instruction.

### V0.7 stronger masking evidence

```text
32 Mid-spectrum features
→ 16 equal ERB-rate regions
→ relative spectral occupancy
→ directional relative-level weighting
→ V0.6 temporal overlap
→ region-level masking evidence
```

Tools:

```text
audio_masking_evidence()
audio_project_masking_scan()
```

This is **equal-ERB-rate feature re-binning**, not a gammatone/cochlear filterbank or calibrated hearing-threshold model. Scores are heuristic evidence, not audible-masking probabilities.

### V0.8 deeper Mid/Side and stereo evidence

V0.8 separates signed L/R correlation, Side/Mid energy, decorrelation proxy, negative cross-spectrum evidence, low-frequency stereo relation, Mid/Side spectra, and frequency-dependent stereo evidence.

```text
audio_stereo_profile(track, seconds=5)
audio_stereo_compare(track_a, track_b, seconds=5)
```

No universal width, correlation, Side/Mid, or low-frequency stereo target is defined.

### V0.9 audio-domain tonal / music-semantic evidence

V0.9 provides:

```text
12-bin normalized chroma: C..B
chroma_energy_ratio
single_f0_harmonic_energy_ratio
harmonic_f0_candidate_hz
```

Chroma is derived from Mid-spectrum power approximately over `80 Hz–5 kHz`, mapped to the nearest 12-TET pitch class and octave-collapsed. The harmonic ratio uses the same approximately `80 Hz–5 kHz` semantic-energy band while its candidate F0 search is approximately `55–1000 Hz`.

```text
audio_tonal_profile(track, seconds=8)
audio_tonal_compare(track_a, track_b, seconds=8)
```

Tonal-center ranking uses 24 major/minor Krumhansl-Kessler profile correlations. These are audio-domain evidence, not exact key/note probabilities. Prefer exact MIDI/DAW note, key, chord, or tuning metadata for exact symbolic facts when available.

### V1.0 reliable closed-loop verification

V1.0 adds **Bridge-side verification orchestration**, not new DSP or OSC fields:

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

The verification record checks explicit conditions such as same requested window duration, deterministic Analyzer topology consistency, requested-target presence/validity, and Before/After active-coverage similarity. The current active-ratio tolerance is `0.15` absolute difference.

`controlled_comparison=true` means only that the current measurement conditions satisfy those transparent technical guardrails. It does **not** mean the change is better, correct, more professional, or should be kept.

`host_readback` is caller-supplied actual state reported by the external control MCP. Analyzer stores it for auditability but does not independently validate the FL Studio control state.

Verification sessions are Bridge-session memory only.

## MCP tools

MCP 1.0 exposes **27 tools**. In addition to the existing 24 measurement/evidence tools, V1.0 adds:

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

Do not mechanically call every tool. Start at project level and choose only the evidence family required by the question. When changing the DAW and verifying the result, wrap the external write/readback with the V1.0 verification tools.

## User installation

GitHub **Release packages are beginner-first** and are designed for users with no programming experience.

Current targets:

```text
Windows x64
macOS Apple Silicon arm64
```

Intel/x86_64 macOS is not packaged.

Each platform has one final ZIP. Extract it once; there is no Release ZIP nested inside it.

Extracted package:

```text
AI Audio Analyzer.vst3
mcp/
└─ ai-audio-analyzer-mcp[.exe]   standalone PyInstaller -F executable
skill/
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
platform installer file(s)
```

User Releases deliberately contain **no MCP Python source**, `requirements.txt`, venv, PyInstaller `_internal`, developer configuration examples, or nested ZIP.

### Windows

Download the Windows ZIP, choose **Extract All**, then double-click:

```text
Install.cmd
```

### macOS Apple Silicon

Download the macOS ZIP, extract it, then double-click:

```text
Install.command
```

If Gatekeeper blocks it, right-click `Install.command` and choose **Open**.

Current macOS builds are ad-hoc signed, **not Apple Developer ID notarized**.

## Repository MCP architecture

There is exactly one supported source/PyInstaller entrypoint:

```text
bridge/server.py
```

Versions are metadata, not startup filenames:

```text
Product version       1.0.0
MCP version           1.0
OSC protocol version  0.9
```

V1.0 intentionally keeps OSC at `0.9` because no VST3 frame fields changed.

Internal modules:

```text
bridge/server.py             startup / self-test / shared tool registry
bridge/analyzer_core.py      OSC state, identity/binding, base tools
bridge/project_tools.py      project overview / Snapshot A-B
bridge/temporal_tools.py     V0.6 temporal layer
bridge/masking_tools.py      V0.7 masking-evidence layer
bridge/stereo_tools.py       V0.8 Mid/Side and stereo layer
bridge/semantic_tools.py     V0.9 chroma / tonal-center / harmonic evidence
bridge/verification_tools.py V1.0 controlled verification sessions
```

`bridge/ci_regression.py` is repository-only synthetic regression code. It is not shipped in beginner Releases.

Repository/source development may use Python 3.12 and `bridge/requirements.txt`; that developer workflow is **not shipped in the user Release**.

## Skill

LLM-facing Skill content is English-only:

```text
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/README-CHERRY-STUDIO.md
skills/ai-analyzer-flstudio/references/analyzer-mcp.md
skills/ai-analyzer-flstudio/references/parameters.md
skills/ai-analyzer-flstudio/references/masking-evidence.md
skills/ai-analyzer-flstudio/references/stereo-evidence.md
skills/ai-analyzer-flstudio/references/tonal-evidence.md
skills/ai-analyzer-flstudio/references/verification-evidence.md
```

The Skill teaches tool use, selector/mapping rules, validity, and parameter/evidence semantics. It does not prescribe a mixing aesthetic, key change, harmony edit, or processing action.

## OSC protocol

Analysis address: `/aianalyzer/frame`.

MCP 1.0 continues to use the append-only **OSC protocol 0.9**:

```text
0..58    V0.1–V0.4-compatible fields
59..64   V0.6 temporal fields + schema marker
65..111  V0.8 Mid/Side + stereo fields + schema marker
112..123 12 chroma bins: C..B
124      chroma_energy_ratio
125      single_f0_harmonic_energy_ratio
126      harmonic_f0_candidate_hz
127      V0.9 schema marker = "0.9"
```

Historical indexes `11..42` remain the 32-band **Mid spectrum**. V1.0 adds no tail after index `127`.

Identify address remains `/aianalyzer/identify`.

## Realtime design

The audio callback does not perform FFT, loudness, semantic analysis, OSC, MCP, verification orchestration, allocation-heavy work, or file/network I/O. Samples are pushed into a preallocated SPSC FIFO and analyzed on a background worker thread.

## Current limitations

- V0.7 ERB handling is feature re-binning, not a true auditory filterbank.
- Masking evidence remains heuristic.
- V0.8 negative-cross evidence is not a phase-angle histogram or mono-cancellation percentage.
- V0.8 Side/Mid and correlation metrics are measurements, not stereo-quality scores.
- V0.9 chroma is FFT-derived 12-TET pitch-class evidence, not transcription.
- V0.9 tonal-center ranking is profile correlation, not exact key detection.
- V0.9 single-F0 harmonic evidence is a heuristic and can be unstable on polyphonic/noisy/inharmonic material.
- V1.0 topology fingerprint is a live Analyzer consistency marker, not a complete persistent DAW-project hash.
- V1.0 `host_readback` is supplied by the caller/external control MCP and is not independently validated by Analyzer.
- V1.0 verification sessions are in-memory and disappear when the Bridge exits.
- Temporal stream alignment is limited by independent OSC timing/update resolution.
- LUFS-I and session max True Peak are cumulative session measurements.
- FL Mixer bindings are session-scoped and may require rediscovery after reopening/reinstantiating plugins.
- macOS Release support is Apple Silicon only and currently not notarized.

## Repository layout

```text
Source/                         JUCE VST3
bridge/server.py                single MCP entrypoint
bridge/analyzer_core.py         stable internal MCP/OSC core
bridge/*_tools.py               feature modules
bridge/ci_regression.py         repository-only MCP regression suite
skills/ai-analyzer-flstudio/    English LLM-facing Skill
release/                        beginner Release installers/docs
.github/workflows/build.yml     development CI
.github/workflows/release.yml   manual Release packaging
AGENT.md                        agent/maintainer history and rules
```

Before modifying the repository, read `AGENT.md`.
