# AI Analyzer.vst3

AI Analyzer is a JUCE VST3 made for **machine-readable audio analysis** in AI/LLM-assisted music production workflows.

Instead of asking an LLM to "look at" a spectrum-analyzer UI, the plugin extracts compact audio features inside the DAW and sends them over OSC to a Python MCP bridge. Cherry Studio (or another MCP client) can then query track spectra, dynamics, stereo behavior, and track-to-track overlap as structured data.

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
       ├─ track comparison
       └─ MCP stdio server
             │
             ▼
       Cherry Studio / LLM
```

The realtime audio callback only copies samples into a preallocated SPSC FIFO. FFT, feature extraction, OSC networking, JSON-like structuring, and MCP work happen outside the DAW realtime audio thread.

## V0.1 features

- 4096-point FFT, Hann window, 1024-sample hop
- 32 logarithmically spaced spectrum samples from 20 Hz to 20 kHz
- Peak dBFS
- RMS dBFS
- Crest factor
- Spectral centroid
- 85% spectral rolloff
- Spectral flatness
- Stereo correlation
- Mid/Side width ratio
- Multiple plugin instances identified by a user-set name (`Kick`, `Bass`, `Vocal`, `Master`, ...)
- OSC transmission at ~10 Hz
- Python MCP tools:
  - `audio_list_tracks`
  - `audio_snapshot`
  - `audio_average`
  - `audio_compare_tracks`
  - `audio_detect_masking`
  - `audio_master_status`

> `audio_detect_masking` is currently a **heuristic spectral-overlap detector**, not a complete psychoacoustic masking model. Timing, level, arrangement, transient behavior, and musical context still matter.

## Build the VST3

### Requirements

- CMake 3.22+
- C++20 compiler
- macOS: Xcode / Command Line Tools
- Windows: Visual Studio 2022 recommended
- Internet access during configure (JUCE 8.0.8 is fetched with CMake FetchContent)

### macOS / Apple Silicon

For a local Apple Silicon build:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_ARCHITECTURES=arm64
cmake --build build --config Release --parallel
```

For a universal macOS binary:

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

Copy the resulting `AI Analyzer.vst3` bundle to your normal VST3 location (commonly `C:\Program Files\Common Files\VST3`).

## Run the OSC + MCP bridge

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r bridge/requirements.txt
```

Run directly for testing:

```bash
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

The MCP server itself uses **stdio**, so in normal Cherry Studio use, Cherry Studio should launch `bridge/server.py`; do not separately pipe its stdout through another program.

## Cherry Studio MCP configuration

Use absolute paths. Example:

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

1. Put `AI Analyzer` on the mixer track you want the LLM to observe.
2. Open the plugin UI.
3. Set a unique `Instance` name, for example `Kick`, `Bass`, `Vocal`, or `Master`.
4. Keep OSC host `127.0.0.1` and port `9855` unless you changed the bridge.
5. Click **Apply**.
6. Start playback.
7. In Cherry Studio, with the `ai-analyzer` MCP enabled, try:

```text
列出当前所有 AI Analyzer 轨道。
```

Then:

```text
读取 Kick 和 Bass 的最近 5 秒平均频谱，检查最明显的重叠频段。
```

Or:

```text
检查 Master 当前峰值、动态和立体声相关性，只诊断，不修改工程。
```

For a full AI-producer workflow, bind both:

- an FL Studio control MCP (to read/write mixer/plugin/Piano Roll state), and
- this AI Analyzer MCP (to observe audio).

That gives the agent separate **actuation** and **perception** channels.

## OSC frame schema

Address:

```text
/aianalyzer/frame
```

Arguments:

```text
0  instance_id          string
1  sample_rate          float
2  plugin_timestamp     float
3  peak_db              float
4  rms_db               float
5  crest_db             float
6  centroid_hz          float
7  rolloff_hz           float
8  flatness             float
9  stereo_correlation   float
10 stereo_width         float
11..42 spectrum bands   32 floats (dB)
```

The 32 band centers are logarithmically spaced from 20 Hz to 20 kHz. They are intended as compact machine features rather than a calibrated SPL measurement.

## Realtime-safety design

The plugin intentionally avoids FFT and network I/O in `processBlock()`.

```text
Audio thread
  └─ copy L/R samples → preallocated SPSC FIFO

Analysis thread
  ├─ consume 1024-sample hops
  ├─ maintain 4096-sample window
  ├─ FFT + spectral/dynamic/stereo features
  └─ send OSC at ~10 Hz
```

If the analysis thread cannot keep up, incoming analysis blocks are dropped instead of blocking the DAW audio thread. The UI reports the dropped-block counter.

## Important V0.1 limitations

- No LUFS yet.
- No true-peak/inter-sample peak yet.
- No band-limited stereo correlation yet.
- No chroma/key/pitch-class analysis yet.
- Spectrum values are compact FFT-derived machine features, not a replacement for a calibrated mastering meter.
- The masking score is relative spectral overlap, not a Bark/ERB psychoacoustic model.
- The plugin does not modify the audio signal.

## Roadmap

### V0.2

- LUFS-M / LUFS-S / LUFS-I
- True Peak
- Mid/Side spectra
- per-band stereo correlation
- transient density / spectral flux
- resonance detection

### V0.3

- chroma / pitch-class profile
- key / tonal-center assistance
- fundamental/pitch confidence
- improved kick-vs-bass temporal analysis
- Bark/ERB masking model
- reference-track comparison snapshots

### V1

- tighter integration with FL Studio MCP
- automatic analyzer-instance discovery and semantic track roles
- A/B snapshots
- structured mix diagnosis for a Music Producer Skill

## CI

GitHub Actions builds the project on macOS and Windows. The macOS job requests a universal `arm64;x86_64` binary. Build outputs are uploaded as workflow artifacts.
