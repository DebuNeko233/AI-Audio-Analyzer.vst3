# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** is a JUCE VST3 designed for **machine-readable audio analysis in AI/LLM-assisted music-production workflows**.

Instead of asking an LLM to visually inspect a spectrum-analyzer GUI, the plugin extracts compact audio features inside the DAW and sends them over OSC to a Python MCP bridge. Cherry Studio or another MCP client can then query loudness, true peak, spectrum, stereo behavior, signal state, and track-to-track overlap as structured data.

Current project version: **0.4.1**.

## What this project contains

The project is intentionally split into three parts:

```text
AI Audio Analyzer
├─ VST3       perception probe inside the DAW
├─ MCP        structured audio-data bridge for the LLM
└─ Skill      Cherry Studio guidance for correct analysis and decision-making
```

GitHub Actions platform artifacts use the same three-part layout:

```text
AI-Audio-Analyzer-macOS/
├─ AI Audio Analyzer.vst3
├─ mcp/
└─ skill/

AI-Audio-Analyzer-Windows/
├─ AI Audio Analyzer.vst3
├─ mcp/
└─ skill/
```

In the repository, the MCP source lives under `bridge/`, while the Cherry Studio Skill lives under `skills/ai-analyzer-flstudio/`.

## Companion FL Studio MCP

AI Audio Analyzer is the **perception channel**. For DAW control, this project is designed to work together with the FL Studio MCP used in the Cherry Studio workflow:

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

The two MCP servers have different responsibilities:

```text
AI Audio Analyzer MCP   → observe / measure / verify
FL Studio MCP           → inspect / control / modify FL Studio
```

Together they support the closed loop:

```text
OBSERVE → DIAGNOSE → PLAN → CHANGE → READBACK → A/B
```

## Architecture

```text
FL Studio / DAW
│
├─ Mixer 4  Kick
│   └─ AI Audio Analyzer.vst3
├─ Mixer 7  Bass
│   └─ AI Audio Analyzer.vst3
├─ Mixer 12 Lead Vocal
│   └─ AI Audio Analyzer.vst3
└─ Master
    └─ AI Audio Analyzer.vst3
             │
             │ OSC UDP
             │ default: 127.0.0.1:9855
             ▼
        Python Analyzer MCP
        ├─ live instance registry
        ├─ short history
        ├─ signal-state filtering
        ├─ FL mixer instance mapping
        ├─ track comparison
        └─ MCP stdio server
             │
             ▼
      Cherry Studio / LLM
        │               │
        │ perception    │ actuation
        │               ▼
        │      rosasynthesiz/flstudio-mcp
        │               │
        └───────────────┴──> FL Studio
```

## Current capabilities

### Audio analysis

- 4096-point FFT with Hann window
- 1024-sample analysis hop
- 32 logarithmically spaced spectrum features from 20 Hz to 20 kHz
- Sample Peak dBFS / RMS dBFS / Crest Factor
- LUFS-S short-term loudness
- LUFS-I integrated loudness with EBU R128 gating
- True Peak dBTP and session maximum True Peak
- Spectral Centroid / 85% Spectral Rolloff / Spectral Flatness
- Full-band Stereo Correlation
- Mid/Side width ratio
- 8 band-limited stereo-correlation values:
  - 20–60 Hz
  - 60–120 Hz
  - 120–250 Hz
  - 250–500 Hz
  - 500 Hz–1 kHz
  - 1–2 kHz
  - 2–5 kHz
  - 5–20 kHz

Loudness and true-peak measurement use `libebur128` 1.2.6.

### Signal-state handling

AI Audio Analyzer does not treat very low-level tails as meaningful program material forever.

```text
gate close:  below about -50 dBFS for ~0.4 s
gate reopen: above about -48 dBFS
```

The 2 dB hysteresis avoids rapid state flipping near the threshold.

When `signal_present=false`, the MCP bridge treats spectrum, centroid, rolloff, flatness, stereo correlation, width, and band correlations as unavailable instead of returning misleading zeroes.

Important details:

- LUFS-I remains a session-integrated value.
- Session Max True Peak remains available.
- LUFS-S becomes unavailable after sustained silence.
- `audio_average()` reports `active_ratio` and only uses valid active frames for content-dependent analysis.

### Multiple analyzer instances

Any number of plugin instances can share the same OSC endpoint:

```text
Kick ───┐
Bass ───┤
Vocal ──┼─> UDP 127.0.0.1:9855 ─> one Analyzer MCP bridge
Master ─┘
```

Each live plugin instance has a human-readable analyzer name and a runtime UUID generated for that live instance. Duplicate human names are allowed internally, but the MCP bridge will not silently choose one when the name is ambiguous.

### Deterministic FL Studio mixer mapping

Version 0.4 adds a host-visible boolean parameter:

```text
Parameter ID: identify
Name: Identify
```

Every change of `Identify` emits an OSC identify event containing the instance runtime UUID. The event is independent of audio playback, so discovery can work while the transport is stopped.

With [rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp), the intended discovery flow is:

```text
FL Studio MCP
  ↓
select Mixer Track / plugin slot
  ↓
toggle AI Audio Analyzer: Identify
  ↓
/aianalyzer/identify
  ↓
audio_last_identify()
  ↓
audio_bind_last_identified(track index, track name, slot)
  ↓
audio_instance_map()
```

After binding, an instance can be selected deterministically with:

```text
mixer:7/slot:9
```

instead of relying only on names such as `Bass` or `Track`.

## MCP tools

The current Analyzer bridge exposes:

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
```

`audio_detect_masking()` is a **heuristic spectral-overlap detector**, not a complete psychoacoustic masking model. Timing, arrangement, transient behavior, level, and musical intent still matter.

## Quick start

### 1. Download a platform artifact

Open the latest successful GitHub Actions build and download either:

```text
AI-Audio-Analyzer-macOS
```

or:

```text
AI-Audio-Analyzer-Windows
```

After extraction you should see exactly these top-level items:

```text
AI Audio Analyzer.vst3
mcp/
skill/
```

### 2. Install the VST3

macOS user directory:

```text
~/Library/Audio/Plug-Ins/VST3/
```

macOS system-wide directory:

```text
/Library/Audio/Plug-Ins/VST3/
```

Windows directory is commonly:

```text
C:\Program Files\Common Files\VST3
```

Then rescan plugins in FL Studio.

### 3. Install the Analyzer MCP Python dependencies

From the extracted artifact:

```bash
cd mcp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The bridge uses **MCP Python SDK 2.x** and communicates with Cherry Studio over **stdio**.

### 4. Configure Cherry Studio

Use the Python interpreter from the environment where `mcp` and `python-osc` are installed.

```json
{
  "mcpServers": {
    "ai-audio-analyzer": {
      "command": "/absolute/path/to/mcp/.venv/bin/python",
      "args": [
        "/absolute/path/to/mcp/server.py"
      ],
      "env": {
        "AI_ANALYZER_OSC_HOST": "127.0.0.1",
        "AI_ANALYZER_OSC_PORT": "9855"
      }
    }
  }
}
```

See `mcp/cherry-studio.example.json` in packaged artifacts, or `bridge/cherry-studio.example.json` in the repository.

Do not manually leave another copy of `server.py` running while Cherry Studio also launches it, because only one process should bind UDP port `9855`.

### 5. Add FL Studio control MCP

For the execution/control side of the workflow, install and configure:

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

Keep both MCP servers enabled in Cherry Studio when you want the model to both **observe audio** and **operate FL Studio**.

### 6. Import the Cherry Studio Skill

Import the packaged `skill/` directory into Cherry Studio.

The Skill teaches the model to:

- check bridge and signal state before analysis;
- distinguish measurement facts from diagnosis and recommendations;
- avoid treating `null` as zero;
- use valid-frame averages;
- map multiple analyzer instances to FL mixer tracks;
- avoid inventing plugin parameters;
- use Analyzer readback for Before/After verification.

## Recommended FL Studio workflow

1. Insert `AI Audio Analyzer` on every mixer track the model should observe.
2. Keep all analyzers on the same OSC host/port unless you intentionally changed the bridge.
3. Enable both the Analyzer MCP and [FL Studio MCP](https://github.com/rosasynthesiz/flstudio-mcp) in Cherry Studio.
4. Ask the agent to scan Analyzer instances.
5. Let the agent bind each Analyzer to its Mixer Track/Slot through `Identify`.
6. Start playback when actual audio measurements are required.
7. Prefer 3–10 second `audio_average()` windows for mix decisions.

Example initialization prompt:

```text
Scan all AI Audio Analyzer instances in the current FL Studio project, use Identify to bind them to Mixer Track/Slot, then show the complete analyzer topology. Do not modify the mix.
```

Example analysis prompts:

```text
Read the Master over the last 10 seconds and analyze LUFS-S, LUFS-I, True Peak, dynamics, and stereo. Diagnose only.
```

```text
Compare Kick and Bass over the last 5 seconds. Find the most important 40–160 Hz conflict, but do not assume that spectral overlap automatically requires sidechain compression.
```

```text
Check the Master 20–120 Hz stereo correlation and determine whether there is a meaningful mono-compatibility risk.
```

## OSC protocol

### Analysis frames

Address:

```text
/aianalyzer/frame
```

The protocol keeps the older frame prefix for backward compatibility.

```text
0      analyzer_name                 string
1      sample_rate                   float
2      plugin_timestamp              float
3      peak_db                       float
4      rms_db                        float
5      crest_db                      float
6      centroid_hz                   float
7      rolloff_hz                    float
8      flatness                      float
9      stereo_correlation            float
10     stereo_width                  float
11..42 spectrum bands               32 floats
43     lufs_s                        float
44     lufs_i                        float
45     true_peak_dbtp                float
46     max_true_peak_dbtp            float
47..54 band_stereo_correlation       8 floats
55     signal_present                int
56     detector_peak_db              float
57     silence_seconds               float
58     runtime_uuid                  string
```

### Identify events

Address:

```text
/aianalyzer/identify
```

The identify event contains the runtime UUID, analyzer name, timestamp, and protocol/schema marker used by the bridge to bind a live plugin instance to FL Studio Mixer Track/Slot context.

## Loudness and True Peak

`libebur128` provides EBU R128 / ITU-R BS.1770-oriented loudness and true-peak measurement.

AI Audio Analyzer maintains a persistent stereo loudness state and requests short-term loudness, integrated loudness, true peak, and histogram-backed integrated loudness.

`LUFS-I` accumulates from the most recent analyzer reset/prepare. If only a chorus loop was played, the result represents that measured session rather than the complete song.

## Stereo correlation

For every 4096-sample FFT window the plugin computes complex L/R spectra. Band correlation is derived from normalized cross-spectrum energy:

```text
corr_band = Σ Re(XL · conj(XR)) / sqrt(Σ|XL|² · Σ|XR|²)
```

Interpretation is contextual:

```text
+1     strongly correlated / mono-like
 0     weakly correlated / potentially wide
<0     possible phase-cancellation risk
```

Correlation should always be interpreted together with actual band energy. A near-silent band does not contain useful stereo information.

## Realtime-safety design

```text
Audio thread
  └─ copy L/R samples into preallocated SPSC FIFO

Analysis thread
  ├─ consume analysis hops
  ├─ update EBU R128 / True Peak
  ├─ maintain FFT window
  ├─ compute spectrum / stereo features
  └─ send OSC at about 10 Hz
```

The audio callback does not perform FFT, network IO, or MCP work. If the analysis worker cannot keep up, analysis input is dropped instead of blocking the DAW realtime thread.

## macOS Gatekeeper

Current CI builds are ad-hoc signed, not Apple Developer ID notarized releases. A downloaded build can therefore be blocked by macOS Gatekeeper.

For local development builds, after copying the bundle into the VST3 directory you can remove quarantine metadata:

```bash
xattr -dr com.apple.quarantine \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

Then verify the bundle signature:

```bash
codesign --verify --deep --strict --verbose=4 \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

For frictionless public distribution, the macOS artifact should eventually use Developer ID signing plus Apple notarization.

## Build from source

Requirements:

- CMake 3.22+
- C++20 compiler
- macOS: Xcode / Command Line Tools
- Windows: Visual Studio 2022 recommended
- Internet access during CMake configure

CMake FetchContent downloads JUCE 8.0.8 and libebur128 1.2.6.

### macOS universal build

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
  "-DCMAKE_OSX_ARCHITECTURES=arm64;x86_64"

cmake --build build --config Release --parallel
```

### Windows

```powershell
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --parallel
```

The generated plugin is under `build/AIAnalyzer_artefacts/`.

## CI and packaging

The workflow uses path-aware incremental builds:

```text
Source/** / CMakeLists.txt / plugin resources
  → rebuild macOS + Windows VST3
  → package VST3 + mcp/ + skill/

bridge/**
  → validate MCP
  → package MCP + Skill components
  → no VST3 rebuild

skills/ai-analyzer-flstudio/**
  → package MCP + Skill components
  → no VST3 rebuild

README / normal docs
  → no VST3 rebuild
```

## Current limitations

- No LUFS-M output yet.
- No Mid/Side spectra yet.
- No chroma, key, or pitch-class analysis yet.
- Spectrum values are compact FFT-derived machine features, not calibrated SPL measurements.
- Masking detection is relative spectral overlap, not a Bark/ERB psychoacoustic model.
- Band stereo correlation is FFT-window based and should be interpreted with band energy.
- Runtime UUIDs are intentionally session-scoped and can change after a plugin reload.
- FL Mixer Track/Slot mapping requires an FL Studio control MCP or equivalent host-side parameter control.
- The plugin observes audio and does not intentionally alter the audio signal.

## Repository layout

```text
.
├─ Source/                         VST3 source
├─ bridge/                         MCP v2 bridge source
├─ skills/
│  └─ ai-analyzer-flstudio/        Cherry Studio Skill
├─ .github/workflows/build.yml     CI / packaging
├─ CMakeLists.txt
├─ README.md
└─ README.zh-CN.md
```

## Version summary

```text
0.2   LUFS-S / LUFS-I / True Peak / 8-band stereo correlation
0.3   signal gate, valid/invalid analysis state, runtime UUID, safe multi-instance handling
0.4   host-visible Identify parameter and deterministic FL Mixer Track/Slot mapping
0.4.1 three-part platform artifact layout: VST3 + mcp/ + skill/
```
