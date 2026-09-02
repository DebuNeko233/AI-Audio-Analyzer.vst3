# AI Analyzer.vst3

AI Analyzer is a JUCE VST3 for **machine-readable audio analysis** in AI/LLM-assisted music-production workflows.

Instead of asking an LLM to inspect a spectrum-analyzer GUI, the plugin extracts compact audio features inside the DAW and sends them over OSC to a Python MCP bridge. Cherry Studio (or another MCP client) can then query spectrum, loudness, true peak, stereo behavior, and track-to-track overlap as structured data.

## Architecture

```text
FL Studio / DAW
    │
    ├─ AI Analyzer.vst3  [Kick]
    ├─ AI Analyzer.vst3  [Bass]
    ├─ AI Analyzer.vst3  [Vocal]
    └─ AI Analyzer.vst3  [Master]
             │
             │ OSC UDP (default 127.0.0.1:9855)
             ▼
      bridge/server.py
       ├─ realtime cache
       ├─ short history
       ├─ loudness / stereo summaries
       ├─ track comparison
       └─ MCP stdio server
             │
             ▼
       Cherry Studio / LLM
```

The DAW realtime audio callback only copies samples into a preallocated SPSC FIFO. FFT, EBU R128 processing, true-peak analysis, OSC networking, and MCP work happen on background threads.

## V0.2 features

- 4096-point FFT, Hann window, 1024-sample hop
- 32 logarithmically spaced spectrum samples from 20 Hz to 20 kHz
- Sample peak dBFS / RMS dBFS / crest factor
- **LUFS-S (3 s short-term loudness)**
- **LUFS-I (integrated loudness with EBU R128 gating)**
- **True Peak dBTP**, including current-hop and session maximum
- Standards-oriented loudness / true-peak backend via `libebur128` 1.2.6
- Spectral centroid / 85% rolloff / flatness
- Full-band stereo correlation / Mid-Side width ratio
- **8 band-limited stereo-correlation values**:
  - 20–60 Hz
  - 60–120 Hz
  - 120–250 Hz
  - 250–500 Hz
  - 500 Hz–1 kHz
  - 1–2 kHz
  - 2–5 kHz
  - 5–20 kHz
- Multiple plugin instances identified by user-set name (`Kick`, `Bass`, `Vocal`, `Master`, ...)
- OSC transmission at ~10 Hz
- Python MCP tools:
  - `audio_list_tracks`
  - `audio_snapshot`
  - `audio_average`
  - `audio_stereo_bands`
  - `audio_compare_tracks`
  - `audio_detect_masking`
  - `audio_master_status`

> `audio_detect_masking` remains a **heuristic spectral-overlap detector**, not a complete psychoacoustic masking model. Timing, level, arrangement, transient behavior, and musical context still matter.

## Loudness / True Peak implementation

`libebur128` implements EBU R128 / ITU-R BS.1770-style loudness measurement and true-peak scanning. AI Analyzer feeds each non-overlapped 1024-sample audio hop into a persistent stereo `ebur128_state`.

The plugin requests:

- short-term loudness mode (`EBUR128_MODE_S`)
- integrated loudness mode (`EBUR128_MODE_I`)
- true-peak mode (`EBUR128_MODE_TRUE_PEAK`)
- histogram-backed integrated loudness (`EBUR128_MODE_HISTOGRAM`)

`LUFS-I` integrates from the most recent analyzer reset/prepare. It is **not** averaged again in the MCP bridge. `audio_average()` instead returns the newest LUFS-I value in the requested history window.

The true-peak implementation in libebur128 uses a polyphase FIR interpolator: 4× oversampling below 96 kHz, 2× below 192 kHz, and no additional oversampling at 192 kHz.

## Band-limited stereo correlation

The plugin computes complex L/R FFTs for each 4096-sample Hann window. For every stereo band it accumulates the real cross-spectrum and L/R powers:

```text
corr_band = Σ Re(XL · conj(XR)) / sqrt(Σ|XL|² · Σ|XR|²)
```

The result is clamped to `[-1, +1]`.

Interpretation:

- near `+1`: strongly correlated / mono-like
- near `0`: wide or weakly correlated
- below `0`: potentially problematic phase relationship

Near-silent bands can have low-information correlation values, so the MCP should interpret correlation together with the corresponding spectrum level.

## Build the VST3

### Requirements

- CMake 3.22+
- C++20 compiler
- macOS: Xcode / Command Line Tools
- Windows: Visual Studio 2022 recommended
- Internet access during configure; CMake FetchContent downloads:
  - JUCE 8.0.8
  - libebur128 1.2.6

### macOS / Apple Silicon

Local Apple Silicon build:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_ARCHITECTURES=arm64
cmake --build build --config Release --parallel
```

Universal macOS binary:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release "-DCMAKE_OSX_ARCHITECTURES=arm64;x86_64"
cmake --build build --config Release --parallel
```

The VST3 will be under the generated `AIAnalyzer_artefacts` directory. Copy `AI Analyzer.vst3` to:

```text
~/Library/Audio/Plug-Ins/VST3/
```

Then rescan plugins in FL Studio.

### Windows

```powershell
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --parallel
```

Copy the resulting `AI Analyzer.vst3` bundle to the normal VST3 directory, commonly:

```text
C:\Program Files\Common Files\VST3
```

## Run the OSC + MCP bridge

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r bridge/requirements.txt
python bridge/server.py
```

The bridge listens on:

```text
udp://127.0.0.1:9855
```

Environment overrides:

```bash
AI_ANALYZER_OSC_HOST=127.0.0.1
AI_ANALYZER_OSC_PORT=9855
```

The MCP server uses **stdio**. In normal Cherry Studio use, Cherry Studio launches `bridge/server.py` directly.

## Cherry Studio MCP configuration

Use absolute paths:

```json
{
  "mcpServers": {
    "ai-analyzer": {
      "command": "/absolute/path/to/AI-Analyzer.vst3/.venv/bin/python",
      "args": [
        "/absolute/path/to/AI-Analyzer.vst3/bridge/server.py"
      ],
      "env": {
        "AI_ANALYZER_OSC_HOST": "127.0.0.1",
        "AI_ANALYZER_OSC_PORT": "9855"
      }
    }
  }
}
```

A copy is provided at `bridge/cherry-studio.example.json`.

## FL Studio workflow

1. Put `AI Analyzer` on each mixer track the LLM should observe.
2. Give every instance a unique name, e.g. `Kick`, `Bass`, `Vocal`, `Master`.
3. Keep OSC host `127.0.0.1` and port `9855` unless you changed the bridge.
4. Click **Apply** and start playback.
5. Enable the `ai-analyzer` MCP in Cherry Studio.

Example prompts:

```text
读取 Master 的 LUFS-S、LUFS-I 和 True Peak，只诊断，不修改。
```

```text
检查 Bass 的 20–120 Hz 分频段 stereo correlation，判断 mono compatibility。
```

```text
读取 Kick 和 Bass 最近 5 秒的频谱，找出最明显的重叠频段。
```

For a complete AI producer workflow, bind both an FL Studio control MCP and this analyzer MCP. The agent then has separate **actuation** and **perception** channels.

## OSC frame schema

Address:

```text
/aianalyzer/frame
```

The V0.2 frame preserves the entire V0.1 prefix for backward compatibility.

```text
0  instance_id                    string
1  sample_rate                    float
2  plugin_timestamp               float
3  peak_db                        float
4  rms_db                         float
5  crest_db                       float
6  centroid_hz                    float
7  rolloff_hz                     float
8  flatness                       float
9  stereo_correlation             float
10 stereo_width                   float
11..42 spectrum bands             32 floats (dB)
43 lufs_s                         float (LUFS)
44 lufs_i                         float (LUFS)
45 true_peak_dbtp                 float (current analysis hop)
46 max_true_peak_dbtp             float (since analyzer reset)
47..54 band_stereo_correlation    8 floats
```

The spectrum is intended as compact machine-readable features rather than calibrated SPL measurement.

## Realtime-safety design

```text
Audio thread
  └─ copy L/R samples → preallocated SPSC FIFO

Analysis thread
  ├─ consume non-overlapping 1024-sample hops
  ├─ feed persistent EBU R128 / True Peak meter
  ├─ maintain 4096-sample FFT window
  ├─ spectrum + complex L/R correlation analysis
  └─ send OSC at ~10 Hz
```

If the analysis thread cannot keep up, incoming analysis blocks are dropped instead of blocking the DAW realtime audio thread. The UI reports the dropped-block counter.

## Current limitations

- No LUFS-M display yet (LUFS-S and LUFS-I are implemented).
- No Mid/Side spectra yet.
- No chroma/key/pitch-class analysis yet.
- Spectrum values are compact FFT-derived machine features, not a replacement for a calibrated mastering meter.
- The masking score is relative spectral overlap, not a Bark/ERB psychoacoustic model.
- Band stereo correlation is FFT-window based and should be interpreted together with per-band energy.
- The plugin does not modify the audio signal.

## Roadmap

### V0.3

- LUFS-M
- Mid/Side spectra
- transient density / spectral flux
- resonance detection
- chroma / pitch-class profile
- key / tonal-center assistance
- improved kick-vs-bass temporal analysis
- Bark/ERB masking model

### V1

- tighter integration with FL Studio MCP
- automatic analyzer-instance discovery and semantic track roles
- A/B snapshots
- structured mix diagnosis for a Music Producer Skill

## CI

GitHub Actions builds the project on macOS and Windows. The macOS job requests a universal `arm64;x86_64` binary. Build outputs are uploaded as workflow artifacts.
