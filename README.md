# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** is a JUCE VST3 designed as a machine-readable audio measurement layer for AI/LLM-assisted music-production workflows.

Instead of asking an LLM to visually inspect an analyzer UI, the plugin measures audio inside the DAW, sends compact OSC frames to a Python MCP Bridge, and exposes structured level, loudness, spectrum, stereo, temporal, project, A/B, and masking-evidence data to Cherry Studio or another MCP client.

Current product version: **0.7.0**.

## Project components

```text
AI Audio Analyzer
├─ VST3    real-time-safe measurement probe inside the DAW
├─ MCP     structured access to Analyzer measurements
└─ Skill   English LLM-facing instructions for correct MCP use and parameter semantics
```

The Skill is intentionally **not** a style-specific mixing guide. It does not encode fixed LUFS targets, EQ/compression/sidechain recipes, or mastering chains.

## Companion FL Studio MCP

For DAW topology/control, the current workflow pairs Analyzer MCP with:

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

Responsibilities remain separate:

```text
AI Audio Analyzer MCP   → observe / measure / compare / verify
FL Studio MCP           → inspect / control / modify FL Studio
```

A typical closed loop is:

```text
OBSERVE → REASON → CHANGE → READBACK → COMPARE
```

## Architecture

```text
FL Studio / DAW
│
├─ Mixer Track A
│   └─ AI Audio Analyzer.vst3
├─ Mixer Track B
│   └─ AI Audio Analyzer.vst3
└─ Master
    └─ AI Audio Analyzer.vst3
             │
             │ OSC UDP, default 127.0.0.1:9855
             ▼
        Analyzer MCP Bridge
        ├─ live instance registry
        ├─ recent history
        ├─ signal validity
        ├─ deterministic FL Track/Slot bindings
        ├─ project overview / Snapshot A-B
        ├─ V0.6 temporal evidence
        └─ V0.7 masking evidence
             │
             ▼
      Cherry Studio / LLM
```

All Analyzer instances may send to the same UDP port. Only one MCP Bridge process should bind UDP `9855`.

## Measurement capabilities

### Core spectrum / dynamics / loudness

- 4096-point FFT, Hann window
- 1024-sample analysis hop
- 32 log-spaced 20 Hz–20 kHz spectrum features
- Sample Peak dBFS
- RMS dBFS
- Crest Factor
- LUFS-S
- LUFS-I with EBU R128 gating
- current True Peak dBTP
- session maximum True Peak
- Spectral Centroid
- ~85% Spectral Rolloff
- Spectral Flatness
- full-band Stereo Correlation
- Mid/Side width ratio
- 8-band Stereo Correlation

Loudness and True Peak use `libebur128`.

### V0.3 Signal State

Approximate gate behavior:

```text
close   below -50 dBFS for ~0.4 s
reopen  above -48 dBFS
```

When `signal_present=false`, content-dependent spectrum/stereo measurements become unavailable instead of returning misleading zeroes.

`null` means **unavailable**, not numeric zero.

### V0.4 deterministic Analyzer ↔ FL Mixer mapping

Each live Analyzer has a session runtime UUID and exposes a host-visible Boolean parameter:

```text
Parameter ID: identify
Display name: Identify
```

Every Identify transition emits `/aianalyzer/identify`, including while transport is stopped.

A controller can bind the emitted runtime UUID to a known FL Mixer Track/Slot and then use selectors such as:

```text
mixer:7/slot:9
```

This avoids guessing from duplicate display names or audio content.

### V0.5 project intelligence / Snapshot A-B

Project-level tools provide readiness, recent mix overview, and session-scoped Before/After snapshots.

### V0.6 temporal analysis

The VST3 computes temporal descriptors at the internal analysis hop and aggregates them into the ~10 Hz OSC stream:

```text
temporal_window_seconds
spectral_flux_mean
spectral_flux_peak
rms_rise_peak_db
low_band_energy_db   # FFT-derived 40–160 Hz feature
```

MCP can summarize one track with `audio_temporal_profile()` or align two Analyzer streams with `audio_temporal_compare()`.

Temporal overlap/correlation is evidence of time co-occurrence/co-variation, not a masking probability or processing instruction.

### V0.7 stronger masking evidence

V0.7 is primarily a Bridge/MCP evidence layer. It reuses the V0.6 VST3 measurements and does **not** add new OSC fields.

Current model:

```text
existing 32 Analyzer spectrum features
→ 16 equal ERB-rate regions
→ relative spectral occupancy
→ directional relative-level weighting
→ V0.6 temporal overlap
→ region-level masking evidence
```

Important limitation: this is **equal-ERB-rate re-binning**, not a gammatone/cochlear filterbank and not a calibrated psychoacoustic hearing-threshold model.

V0.7 adds:

```text
audio_masking_evidence()
audio_project_masking_scan()
```

Scores are transparent heuristic evidence for ranking/querying candidates. They are **not** probabilities of audible masking and do not prescribe EQ, sidechain, compression, or any other mix action.

## MCP tools

MCP 0.7 exposes **20 tools**:

```text
audio_bridge_status()
audio_list_tracks()
audio_last_identify()
audio_bind_last_identified(...)
audio_instance_map()
audio_snapshot(track)
audio_average(track, seconds)
audio_stereo_bands(track)
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
audio_master_status(track="Master")
audio_project_status()
audio_mix_overview(seconds=10, max_tracks=32)
audio_capture_snapshot(name, seconds=5)
audio_list_snapshots()
audio_compare_snapshots(before, after)
audio_temporal_profile(track, seconds=5)
audio_temporal_compare(...)
audio_masking_evidence(...)
audio_project_masking_scan(...)
```

The historical `audio_detect_masking()` remains a spectrum-only heuristic. Prefer `audio_masking_evidence()` for the stronger current pairwise evidence model.

## Recommended query progression

```text
audio_project_status()
    ↓
audio_mix_overview()
    ↓
audio_project_masking_scan()      # when interaction candidates matter
    ↓
audio_masking_evidence(a, b)      # detailed pair evidence
    ↓
audio_temporal_compare(a, b, ...) # custom-band time drill-down when needed
```

Do not mechanically call every tool if a higher-level result already answers the question.

## User installation

The recommended user path is the GitHub **Release lazy package**, not manual Python setup.

Current Release targets:

```text
Windows x64
macOS Apple Silicon arm64
```

Intel/x86_64 macOS is not packaged.

Each Release contains roughly:

```text
AI Audio Analyzer.vst3
mcp/
├─ runtime/    PyInstaller standalone MCP
└─ source/     Python source fallback
skill/
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
platform installer script(s)
```

Normal users do **not** need to install Python, pip, a virtual environment, or access PyPI. The standalone MCP runtime is built with PyInstaller.

### Windows

Run:

```text
Install.cmd
```

The VST3 is installed to the standard VST3 location and MCP/Skill files remain under the current user's application-data directory.

### macOS Apple Silicon

Run:

```text
Install.command
```

If Gatekeeper blocks the downloaded script, right-click → **Open**, or run:

```bash
bash ./install.sh
```

Current macOS builds are ad-hoc signed, **not Apple Developer ID notarized**. The installer handles current quarantine/Gatekeeper requirements.

Full instructions are inside each Release package.

## MCP source layout and entrypoint

There is exactly one supported MCP source/PyInstaller entrypoint:

```text
bridge/server.py
```

Version numbers are metadata, not entrypoint filenames:

```text
MCP version          0.7
OSC protocol version 0.6
```

Internal implementation is split by responsibility:

```text
bridge/server.py          single startup / self-test / tool registry entrypoint
bridge/analyzer_core.py   stable OSC state, identity, base measurements and base tools
bridge/project_tools.py   project overview and Snapshot A-B
bridge/temporal_tools.py  V0.6 temporal parsing and comparison
bridge/masking_tools.py   V0.7 masking-evidence layer
```

Python 3.12 is recommended for source mode:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r bridge/requirements.txt
AI_ANALYZER_SELF_TEST=1 python bridge/server.py
```

Windows uses the equivalent `.venv\Scripts\Activate.ps1` flow.

Source mode is a developer/debug fallback. Normal users should use the packaged runtime.

## Cherry Studio source example

`bridge/cherry-studio.example.json` points to `bridge/server.py`. The packaged installer instead generates a configuration whose `command` points directly to the standalone MCP executable.

Do not run a manual Bridge process while Cherry Studio starts another copy on the same UDP port.

## Skill

The bundled Skill lives in:

```text
skills/ai-analyzer-flstudio/
```

LLM-facing Skill files are English-only by project policy:

```text
SKILL.md
README-CHERRY-STUDIO.md
references/analyzer-mcp.md
references/parameters.md
references/masking-evidence.md
```

The Skill teaches tool use, selector/mapping rules, validity, parameter semantics, temporal evidence, and masking-evidence limitations. It does not prescribe a mixing aesthetic.

## OSC protocol

Analysis address:

```text
/aianalyzer/frame
```

The frame remains append-compatible. V0.7 adds no new OSC fields.

```text
0      analyzer_name
1      sample_rate
2      plugin_timestamp
3      peak_db
4      rms_db
5      crest_db
6      centroid_hz
7      rolloff_hz
8      flatness
9      stereo_correlation
10     stereo_width
11..42 32 spectrum bands
43     lufs_s
44     lufs_i
45     true_peak_dbtp
46     max_true_peak_dbtp
47..54 8 band stereo correlations
55     signal_present
56     detector_peak_db
57     silence_seconds
58     runtime_uuid
59     temporal_window_seconds
60     spectral_flux_mean
61     spectral_flux_peak
62     rms_rise_peak_db
63     low_band_energy_db
64     frame_schema_version = "0.6"
```

Identify address:

```text
/aianalyzer/identify
```

## Realtime design

The audio callback does not perform FFT, loudness, OSC, MCP, allocation-heavy work, or file/network I/O. Audio samples are pushed into a preallocated SPSC FIFO and analyzed on a background worker thread.

## Current limitations

- V0.7 ERB handling is feature re-binning, not a true auditory filterbank.
- Masking evidence is heuristic and should not be presented as psychoacoustic ground truth.
- Temporal stream alignment is limited by independent OSC timing/update resolution.
- LUFS-I and session max True Peak are cumulative session measurements.
- FL Mixer bindings are session-scoped and may need rediscovery after reopening/reinstantiating plugins.
- macOS Release support is Apple Silicon only and currently not notarized.

## Repository layout

```text
Source/                         JUCE VST3
bridge/server.py                single MCP entrypoint
bridge/analyzer_core.py         stable internal MCP/OSC core
bridge/*_tools.py               feature modules
skills/ai-analyzer-flstudio/    English LLM-facing Skill
release/                        lazy-package installers/docs
.github/workflows/build.yml     development CI
.github/workflows/release.yml   manual Release packaging
AGENT.md                        agent/maintainer roadmap and rules
```

Before modifying the repository, read `AGENT.md`.
