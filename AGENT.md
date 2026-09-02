# AGENT.md

This file is the working contract for AI agents and maintainers modifying **AI Audio Analyzer**.

Read it before changing the repository. Keep implementation, tests, CI, Release packaging, installers, MCP behavior, Skill behavior, roadmap, and public documentation consistent.

## 1. Project purpose

AI Audio Analyzer is a machine-readable audio measurement layer for AI/LLM-assisted music-production workflows.

```text
AI Audio Analyzer
├─ VST3    measures audio inside the DAW
├─ MCP     exposes structured measurements / comparisons / evidence
└─ Skill   teaches correct MCP use and parameter semantics
```

Analyzer MCP is the measurement/perception channel. DAW control is separate and currently paired with:

https://github.com/rosasynthesiz/flstudio-mcp

The Analyzer must remain measurement-oriented. Do not encode one artistic mixing style into MCP or Skill.

## 2. Current architecture

### VST3

- JUCE 8.0.8, C++20, CMake.
- Current public/product version: **0.8.0**.
- Visible product name: `AI Audio Analyzer`.
- Internal target: `AIAnalyzer`.
- Bundle ID: `com.debuneko.aianalyzer`.
- Manufacturer/plugin IDs remain stable for DAW-project compatibility.
- Default OSC endpoint: `127.0.0.1:9855`.
- Audio callback only writes to a preallocated SPSC FIFO.
- FFT, loudness, temporal/stereo analysis and OSC run off the realtime audio thread.
- `libebur128` provides LUFS / True Peak measurement.

Do not casually change host/plugin identity fields.

### MCP

There is exactly **one supported source/PyInstaller entrypoint**:

```text
bridge/server.py
```

Do not create `server_v09.py`, `server_v10.py`, or any other version-named startup file. Versions are metadata, not filenames.

Current internal layout:

```text
bridge/server.py          startup, self-test, version metadata, tool registration
bridge/analyzer_core.py   OSC/runtime state, identity/binding, base tools
bridge/project_tools.py   V0.5 project overview / Snapshot A-B
bridge/temporal_tools.py  V0.6 temporal parsing/tools
bridge/masking_tools.py   V0.7 masking evidence
bridge/stereo_tools.py    V0.8 Mid/Side and stereo evidence
```

Current MCP tool count: **22**.

```text
MCP_VERSION = "0.8"
OSC_PROTOCOL_VERSION = "0.8"
```

### Skill

```text
skills/ai-analyzer-flstudio/
```

All LLM-facing Skill content is **English-only**:

```text
SKILL.md
README-CHERRY-STUDIO.md
references/*.md
```

Skill scope is limited to MCP calling strategy, selector/mapping rules, measurement validity, parameter semantics, temporal evidence, masking evidence, Mid/Side/stereo evidence, and limitations.

Do not add fixed genre EQ recipes, LUFS targets, mandatory sidechain rules, stereo recipes, mastering chains, or “metric X always means processor Y”.

## 3. Implemented milestones

### 0.2 — loudness / True Peak / stereo bands

Implemented LUFS-S, LUFS-I, current/session-max True Peak and 8-band L/R correlation.

### 0.3 — signal validity and runtime identity

Implemented approximately:

```text
signal gate close   -50 dBFS
signal gate reopen  -48 dBFS
hold                0.4 s
```

Added `signal_present`, detector peak, silence duration, active-frame validity, and one runtime UUID per live instance. Invalid content-dependent measurements become unavailable instead of misleading zeroes.

### 0.4 — deterministic FL Mixer mapping

Added host-visible Boolean `Identify`. Every transition emits `/aianalyzer/identify`, including while transport is stopped. Runtime UUIDs can be bound to known FL Mixer Track/Slot locations and addressed with selectors such as:

```text
mixer:7/slot:9
```

Never guess Analyzer ↔ Mixer mapping from names or audio content when Identify mapping is available.

### 0.4.1 — packaging / installation foundation

Added automatic installers, bilingual user instructions, PyInstaller standalone MCP, Release workflow, and macOS quarantine/signature handling.

Historical packages contained developer material. Current user Release policy is stricter: **no MCP source or developer fallback files are shipped**.

### 0.5 — project intelligence / Snapshot A-B

Implemented:

```text
audio_project_status()
audio_mix_overview()
audio_capture_snapshot()
audio_list_snapshots()
audio_compare_snapshots()
```

### 0.6 — temporal interaction evidence

Append-only OSC fields:

```text
59  temporal_window_seconds
60  spectral_flux_mean
61  spectral_flux_peak
62  rms_rise_peak_db
63  low_band_energy_db
64  V0.6 schema marker = "0.6"
```

MCP adds:

```text
audio_temporal_profile()
audio_temporal_compare()
```

Temporal results are evidence of time co-occurrence/co-variation, not masking probability or processing instructions.

### 0.7 — stronger masking evidence

V0.7 reuses the V0.6 OSC frame and adds Bridge/MCP evidence:

```text
32 Mid-spectrum features
→ 16 equal ERB-rate regions
→ relative spectral occupancy
→ directional relative-level weighting
→ V0.6 temporal overlap
→ region-level masking evidence
```

Implemented:

```text
audio_masking_evidence()
audio_project_masking_scan()
```

ERB is feature re-binning, not a gammatone/cochlear filterbank. Scores are transparent heuristic evidence, not probabilities of audible masking.

### 0.7 — MCP entrypoint consolidation

Removed historical `server_v05.py`, `server_v06.py`, and `server_v07.py`. `bridge/server.py` is permanently the single startup entrypoint.

### 0.7 — beginner Release cleanup

Current user Release policy:

```text
single final ZIP per platform
no ZIP-inside-ZIP
PyInstaller -F / --onefile MCP executable
no MCP Python source in user package
no requirements.txt / developer examples / venv / _internal
click-oriented installers and guides
```

The Release is designed for people with **zero programming experience**.

### 0.8 — deeper Mid/Side and stereo measurement

V0.8 keeps OSC append-only: existing indexes `0..64` remain unchanged and fields `65..111` are appended.

New VST3 measurements:

```text
mid_rms_db
side_rms_db
side_to_mid_db
negative_cross_energy_ratio
low_band_20_120_correlation
low_band_20_120_side_to_mid_db
32 Side-spectrum bands
8 Side/Mid frequency-band ratios
```

Historical `bands_db` remains the 32-band **Mid spectrum**.

New MCP tools:

```text
audio_stereo_profile()
audio_stereo_compare()
```

V0.8 deliberately keeps these concepts separate:

```text
signed L/R correlation
Side/Mid energy
decorrelation proxy = 1 - abs(correlation)
negative cross-spectrum evidence
frequency-dependent stereo relation
```

Important semantics:

- low correlation is not anti-correlation;
- high Side energy is not proof of phase opposition;
- `negative_cross_energy_ratio` is weighted negative real cross-spectrum evidence, not a phase-angle histogram, mono-cancellation percentage, audibility probability, or quality score;
- no universal stereo target or processing action is encoded.

## 4. Current roadmap

### 0.9 — music-semantic measurements

Evaluate useful audio-domain evidence such as:

- chroma / pitch-class distribution;
- tonal-center evidence;
- harmonic vs non-harmonic distribution where technically defensible.

Do not duplicate information available more reliably from DAW/MIDI/project data through another MCP. Any semantic inference must expose uncertainty/validity and remain measurement evidence rather than an artistic prescription.

### 1.0 — reliable closed-loop measurement system

```text
project discovery
→ deterministic Analyzer mapping
→ project observation
→ external reasoning / user intent
→ DAW change through control MCP
→ Analyzer readback
→ controlled Before/After comparison
```

1.0 does not mean encoding one mixing aesthetic.

## 5. MCP / measurement rules

### Preserve semantics and compatibility

Do not silently change metric meaning. If semantics must change, document the reason, update tests/docs/Skill, preserve compatibility when practical, and explicitly call out breaks.

OSC evolution should remain append-only when practical. Existing indexes must not be silently repurposed.

### One entrypoint only

`bridge/server.py` is the only source/PyInstaller entrypoint.

### `null` is not zero

Unavailable measurements remain unavailable.

### Prefer stable windows

Use window/project tools for observations requiring temporal stability. `audio_snapshot()` is current-state data, not a stable-window substitute.

### Evidence quality must be visible

Expose enough context to judge reliability: window length, active coverage, valid frame count, aligned pair count when applicable, frequency/ERB/stereo region, alignment tolerance/offset, and usable temporal pairs.

### Heuristics must be labeled

Spectral overlap, onset/change candidates, temporal overlap, ERB-rebinned evidence, negative-cross evidence, decorrelation proxies, and candidate rankings are measurement/heuristic evidence unless replaced by a validated stronger model.

### Keep independent stereo concepts independent

Do not collapse correlation, Side/Mid energy, decorrelation proxy, and negative-cross evidence into one opaque “stereo quality” score.

### A/B is measurement-oriented

Snapshot/stereo comparisons return measurements and deltas, not subjective claims such as “better”, “warmer”, “wider”, or “professional”.

## 6. Release and platform rules

### Supported user platforms

```text
Windows x64
macOS Apple Silicon arm64 only
```

Do not re-add Intel/x86_64 macOS unless explicitly requested.

### Release audience — mandatory

The GitHub Release is for ordinary end users, including people who have never programmed.

Normal flow:

```text
download ZIP
→ extract once
→ double-click installer
→ restart FL Studio
→ use generated Cherry Studio config / Skill
```

Do not require users to install or understand Python, pip, venv, PyPI, source code, CMake, compilers, package managers, or shell commands.

User-facing docs should explain **what to click**, not how the software is built.

### User package contents

Windows:

```text
AI Audio Analyzer.vst3
mcp/ai-audio-analyzer-mcp.exe
skill/
Install.cmd
Install.ps1
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
```

macOS:

```text
AI Audio Analyzer.vst3
mcp/ai-audio-analyzer-mcp
skill/
Install.command
install.sh
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
```

Forbidden in user Releases:

```text
mcp/source/
*.py
requirements.txt
cherry-studio.example.json
venv/
_internal/
nested *.zip
```

Repository source files remain in the repository only.

### PyInstaller policy

Release MCP uses:

```text
-F / --onefile
```

The native packaged runtime must pass its self-test before package assembly.

### Single-compression policy

**Final user archives are compressed exactly once.**

Required flow:

```text
stage Windows directory
stage macOS directory
→ upload unpacked directory artifacts
→ publish downloads directories
→ publish creates final Windows/macOS ZIPs once
```

Final Release ZIPs must be checked for nested `.zip` files before publication.

### Development CI

Keep path-aware incremental behavior:

```text
Source/** / CMake/plugin files
→ rebuild Windows x64 + macOS arm64 VST3

bridge/**
→ validate/package MCP + Skill
→ no VST3 rebuild unless plugin/version files also changed

skills/**
→ validate/package MCP + Skill
→ no VST3 rebuild

release/** / release workflow
→ validate installer/release logic

README/docs only
→ no VST3 rebuild
```

### macOS

Current builds are ad-hoc signed, not Apple Developer ID notarized. Never claim notarization until the workflow performs and verifies it.

## 7. Documentation synchronization — mandatory

**Every repository change must include a documentation-impact review before it is complete**, even when the result is “no documentation change required”.

At minimum inspect as relevant:

```text
README.md
README.zh-CN.md
AGENT.md
release/README.md
release/common/START-HERE.md
release/common/INSTALL.en.md
release/common/INSTALL.zh-CN.md
release/windows/Install.ps1
release/macos/install.sh
skills/ai-analyzer-flstudio/README-CHERRY-STUDIO.md
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/references/analyzer-mcp.md
skills/ai-analyzer-flstudio/references/parameters.md
skills/ai-analyzer-flstudio/references/masking-evidence.md
skills/ai-analyzer-flstudio/references/stereo-evidence.md
bridge/cherry-studio.example.json
bridge/requirements.txt
.github/workflows/build.yml
.github/workflows/release.yml
```

For every change ask:

```text
Did public version change?
Did MCP entrypoint/tool count/arguments/defaults/output change?
Did OSC schema/indexes or metric semantics change?
Did signal/temporal/masking/stereo validity change?
Did Identify/binding/selectors change?
Did supported OS/architecture change?
Did Release contents/layout change?
Did PyInstaller behavior change?
Did installer behavior change?
Did Gatekeeper/signing behavior change?
Did Cherry Studio config change?
Did Skill calling strategy/scope/language change?
Did CI trigger/build behavior change?
Did roadmap/current status change?
```

If yes, update every affected document in the same change whenever practical.

`README.md` / `README.zh-CN.md` and `INSTALL.en.md` / `INSTALL.zh-CN.md` must describe the same current facts.

When a roadmap item is implemented, move it into implemented history and advance the roadmap.

## 8. Agent change procedure

```text
1. Read AGENT.md.
2. Inspect actual current files.
3. Identify affected VST3 / MCP / Skill / CI / Release / docs layers.
4. Make the smallest coherent implementation.
5. Add/update regression tests when behavior changes.
6. Perform mandatory documentation-impact review.
7. Update affected English/Chinese docs and Skill references.
8. Verify intended CI path: build vs skip.
9. Inspect actual CI/runtime evidence before claiming success.
10. Update AGENT.md for meaningful architecture/history/roadmap changes.
```

Distinguish these states:

```text
source syntax/self-test
MCP regression
VST3 build
PyInstaller build
packaged-runtime self-test
package staging
final ZIP creation
Release publication
```

One succeeding does not prove the others succeeded.

## 9. Guardrails

- Do not rename Bundle ID / plugin IDs casually.
- Keep `bridge/server.py` as the only MCP entrypoint.
- Do not reintroduce `server_vXX.py` startup files.
- Keep Release MCP in PyInstaller one-file mode unless explicitly changing policy.
- Do not ship MCP source code in user Releases.
- Do not create nested Release ZIPs.
- Keep user Releases understandable without programming knowledge.
- Do not guess FL Studio MCP tool names; inspect actual exposed tools.
- Do not guess Analyzer ↔ Mixer mapping when Identify is available.
- Do not treat `null` as zero.
- Do not present masking/temporal/stereo heuristic evidence as ground truth.
- Do not call low correlation anti-correlation without checking sign.
- Do not treat Side/Mid energy as proof of phase opposition.
- Do not describe negative-cross evidence as a mono-cancellation percentage.
- Do not encode one mixing aesthetic into MCP or Skill.
- Keep LLM-facing Skill content in English.
- Do not re-add Intel macOS Release support unless explicitly requested.
- Do not claim macOS notarization when it is not notarized.
- Do not trigger VST3 builds for unrelated changes.

## 10. Maintaining this file

`AGENT.md` is living project memory. Update it when architecture, supported platforms, Release strategy, MCP entrypoint/tools, protocol/identity model, measurement/evidence semantics, Skill scope/language, milestones, roadmap, or CI/build policy materially change.

Keep it decision-focused rather than turning it into a raw commit log.
