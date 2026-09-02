# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** is a JUCE VST3 + MCP measurement layer for AI/LLM-assisted music-production workflows. The VST3 measures audio inside the DAW, the MCP exposes structured measurements to a model, and the bundled Skill teaches correct tool usage and parameter semantics without imposing a mixing style.

Current product version: **0.6.0**.

## Project structure

```text
AI Audio Analyzer
├─ VST3    realtime-safe audio measurement inside the DAW
├─ MCP     machine-readable measurement / comparison tools
└─ Skill   MCP calling strategy + parameter semantics
```

For FL Studio control, use a separate control MCP. The workflow is designed to pair with:

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

```text
AI Audio Analyzer MCP   → observe / measure / compare / verify
FL Studio MCP           → inspect / control / modify FL Studio
```

The Analyzer itself intentionally stays measurement-oriented. Its Skill does not encode fixed LUFS targets, EQ recipes, mandatory sidechain rules, or other style-specific mixing policies.

## Architecture

```text
FL Studio / DAW
│
├─ Mixer Track A ─ AI Audio Analyzer.vst3
├─ Mixer Track B ─ AI Audio Analyzer.vst3
└─ Master        ─ AI Audio Analyzer.vst3
                      │
                      │ OSC UDP 127.0.0.1:9855
                      ▼
              AI Audio Analyzer MCP
              ├─ live-instance registry
              ├─ signal validity
              ├─ deterministic FL Track/Slot bindings
              ├─ recent-history windows
              ├─ project overview / A-B snapshots
              └─ temporal comparison
                      │
                      ▼
               Cherry Studio / LLM
```

The audio callback only copies samples into a preallocated SPSC FIFO. FFT, loudness analysis, temporal analysis, OSC and MCP work stay off the realtime audio thread.

## Current capabilities

### Core measurements

- 4096-point FFT, Hann window, 1024-sample hop
- 32 logarithmic spectrum bands from 20 Hz to 20 kHz
- Sample Peak dBFS / RMS dBFS / Crest Factor
- LUFS-S / LUFS-I through `libebur128`
- current and session-max True Peak dBTP
- Spectral Centroid / 85% Rolloff / Flatness
- full-band Stereo Correlation
- Mid/Side width ratio
- 8 band-limited stereo-correlation values

### V0.3 signal validity

```text
gate close   below about -50 dBFS for ~0.4 s
gate reopen  above about -48 dBFS
```

When `signal_present=false`, content-dependent spectrum/stereo measurements are returned as unavailable instead of misleading zeroes. `null` means unavailable, not numeric zero.

### V0.4 deterministic multi-instance mapping

Each live VST3 instance has a session-scoped runtime UUID. The plugin also exposes a host-visible Boolean parameter:

```text
Parameter ID: identify
Display name: Identify
```

Every state transition sends `/aianalyzer/identify`. An agent that knows which FL Mixer Track/Slot it just operated can bind that host location to the emitted runtime UUID:

```text
FL Mixer Track / Slot
        ↕
Analyzer runtime UUID
```

After discovery, prefer selectors such as:

```text
mixer:7/slot:9
```

instead of guessing from duplicate display names or audio content.

### V0.5 project intelligence and A/B

The MCP adds project-level readiness, recent-window overview and session-memory snapshots so an agent does not need a long chain of low-level calls for every task.

### V0.6 temporal analysis

VST3 0.6 computes temporal descriptors at the internal FFT-hop rate and aggregates them into the ~10 Hz OSC stream:

```text
temporal_window_seconds
spectral_flux_mean
spectral_flux_peak
rms_rise_peak_db
low_band_energy_db   # FFT-derived 40–160 Hz energy
```

The MCP adds:

```text
audio_temporal_profile(track, seconds=5)
audio_temporal_compare(track_a, track_b, seconds=5,
                       low_hz=40, high_hz=160,
                       alignment_tolerance_ms=80)
```

`audio_temporal_profile()` summarizes spectral change, rapid RMS rise, 40–160 Hz energy movement, and threshold-based onset/change candidates.

`audio_temporal_compare()` time-aligns two Analyzer streams and reports selected-band envelope correlation, co-active ratio and normalized temporal overlap. These are measurement/heuristic evidence, not automatic mixing instructions or a complete psychoacoustic masking probability.

## MCP tools

MCP 0.6 exposes **18 tools**:

```text
audio_bridge_status()
audio_list_tracks()
audio_last_identify()
audio_bind_last_identified(fl_track_index, fl_track_name, slot)
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
audio_temporal_compare(track_a, track_b, seconds=5,
                       low_hz=40, high_hz=160,
                       alignment_tolerance_ms=80)
```

`audio_detect_masking()` remains heuristic spectral-overlap evidence. V0.6 temporal tools add timing evidence but still do not turn the Analyzer into a full psychoacoustic masking model.

## Recommended user installation

User-facing Releases are separate from development artifacts.

Current supported Release platforms:

```text
Windows x64
macOS Apple Silicon arm64
```

**Intel macOS / x86_64 is not packaged.**

A Release contains:

```text
AI Audio Analyzer.vst3
mcp/
├─ runtime/   standalone PyInstaller MCP
└─ source/    Python source fallback
skill/
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
platform installer scripts
```

Normal users do **not** need to install Python, pip, a virtual environment, MCP SDK, or access PyPI.

### Windows

Extract the Release and double-click:

```text
Install.cmd
```

The installer copies the VST3 to the standard VST3 location, installs the standalone MCP under the current user, runs its self-test, copies the Skill, and generates `cherry-studio-mcp.json`.

### macOS Apple Silicon

Extract the Release and double-click:

```text
Install.command
```

If Gatekeeper blocks the script itself, right-click it and choose **Open**, or run:

```bash
bash ./install.sh
```

The installer copies the arm64 VST3, removes quarantine metadata where possible, verifies/repairs the local ad-hoc signature, installs the standalone arm64 MCP, runs its self-test, copies the Skill, and generates `cherry-studio-mcp.json`.

Current GitHub builds are ad-hoc signed and are **not Apple Developer ID notarized**.

Full instructions are included in every Release package under `INSTALL.en.md` and `INSTALL.zh-CN.md`.

## Developer / source MCP fallback

The normal Release path uses the PyInstaller executable. Source mode is for development or unusual fallback cases.

Requirements:

- Python 3.10+; Python 3.12 recommended
- dependencies from `bridge/requirements.txt`

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r bridge/requirements.txt
AI_ANALYZER_SELF_TEST=1 python bridge/server_v06.py
```

Windows PowerShell activation differs, but the entry point is still:

```text
bridge/server_v06.py
```

`bridge/cherry-studio.example.json` contains a source-mode example.

## Cherry Studio + FL Studio workflow

For a new project/session:

```text
audio_project_status()
↓
if needed: Identify each Analyzer and bind Track/Slot
↓
audio_instance_map()
↓
use overview / average / temporal tools as needed
```

When a model needs to compare before/after measurements:

```text
audio_capture_snapshot("before", 5)
↓
external DAW change through FL Studio MCP
↓
audio_capture_snapshot("after", 5)
↓
audio_compare_snapshots("before", "after")
```

The Analyzer Skill explains tool usage and measurement semantics; artistic decisions remain driven by user intent, musical context and the model's own reasoning.

## OSC protocol

Analysis frames use:

```text
/aianalyzer/frame
```

The protocol is append-only.

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

Identify events remain:

```text
/aianalyzer/identify
```

with the V0.4 identify schema. The Identify schema did not need to change for V0.6 temporal measurement.

## Temporal semantics in brief

- `spectral_flux_*`: normalized positive change in spectral distribution, intentionally less sensitive to simple overall gain scaling.
- `rms_rise_peak_db`: largest positive adjacent-window RMS rise within the emitted temporal aggregate.
- `low_band_energy_db`: FFT-derived 40–160 Hz energy feature, not calibrated SPL.
- `band_envelope_correlation`: Pearson correlation of two time-aligned selected-band energy envelopes.
- `normalized_band_temporal_overlap`: relative simultaneous selected-band occupancy after each track is normalized to its own window peak.
- onset/change candidates are explicit heuristics with thresholds returned by the tool; they are not ground-truth annotated onsets.

## Build from source

Requirements:

- CMake 3.22+
- C++20 compiler
- JUCE 8.0.8 fetched by CMake
- libebur128 1.2.6 fetched by CMake

macOS development/release policy is arm64:

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
  -DCMAKE_OSX_ARCHITECTURES=arm64
cmake --build build --config Release --parallel
```

Windows:

```powershell
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --parallel
```

## CI and Release

Development CI is path-aware:

```text
Source/** / CMakeLists.txt
→ rebuild VST3 on Windows + macOS arm64

bridge/**
→ validate/package MCP + Skill

skills/**
→ validate/package MCP + Skill

release/** / release workflow
→ installer/release validation

docs only
→ no VST3 rebuild
```

The manual user-facing Release workflow is:

```text
.github/workflows/release.yml
```

It builds standalone MCP runtimes, self-tests them, rebuilds platform VST3s, assembles lazy packages, generates SHA256 checksums and publishes/updates a GitHub Release.

## Current limitations

- no LUFS-M output yet;
- no Mid/Side spectra yet;
- no chroma/key/pitch-class analysis yet;
- masking remains heuristic evidence, not a complete Bark/ERB psychoacoustic model;
- V0.6 temporal comparison is limited by the Analyzer OSC update cadence and alignment tolerance;
- onset candidates are heuristic frame-level change candidates, not sample-accurate annotated onset events;
- runtime UUIDs and FL bindings are session-scoped;
- macOS Release is arm64 only and not notarized;
- the plugin observes audio and does not intentionally alter the signal.

## Repository layout

```text
.
├─ Source/                          VST3 source
├─ bridge/
│  ├─ server.py                     stable core bridge
│  ├─ server_v05.py                 project-intelligence layer
│  ├─ project_tools.py
│  ├─ server_v06.py                 current MCP entry point
│  └─ temporal_tools.py
├─ skills/ai-analyzer-flstudio/     neutral MCP usage Skill
├─ release/                         lazy-package installers/docs
├─ .github/workflows/build.yml      development CI
├─ .github/workflows/release.yml    manual Release workflow
├─ CMakeLists.txt
├─ AGENT.md                         agent/maintainer contract + roadmap
├─ README.md
└─ README.zh-CN.md
```

## Version history / roadmap

```text
0.2   LUFS / True Peak / 8-band stereo correlation
0.3   signal validity + runtime UUID
0.4   Identify + deterministic FL Mixer Track/Slot mapping
0.4.1 packaging / installer foundation
0.5   project overview + snapshot A/B
0.6   temporal descriptors + time-aligned band-envelope comparison

next: 0.7 stronger masking evidence (Bark/ERB + level + temporal weighting)
      0.8 deeper Mid/Side analysis
      0.9 music-semantic measurements where audio inference is useful
      1.0 reliable closed-loop measurement system
```
