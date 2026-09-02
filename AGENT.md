# AGENT.md

This file is the working contract for AI agents and maintainers modifying **AI Audio Analyzer**.

Read it before changing the repository. Keep implementation, tests, CI, Release packaging, installation instructions, MCP behavior, Skill behavior, and public documentation consistent.

## 1. Project purpose

AI Audio Analyzer is a machine-readable audio measurement layer for AI/LLM-assisted music-production workflows.

```text
AI Audio Analyzer
├─ VST3    measures audio inside the DAW
├─ MCP     exposes structured measurements / comparisons
└─ Skill   teaches correct MCP use and parameter semantics
```

The Analyzer MCP is the **measurement/perception channel**. DAW control comes from a separate MCP, currently paired with:

https://github.com/rosasynthesiz/flstudio-mcp

The Analyzer should stay focused on trustworthy measurement, deterministic identity/mapping, project observation and readback verification. It must not encode one artistic mixing style.

## 2. Current architecture

### VST3

- JUCE 8.0.8, C++20, CMake.
- Current public/product version: **0.6.0**.
- Visible name: `AI Audio Analyzer`.
- Internal target remains `AIAnalyzer`.
- Bundle ID remains `com.debuneko.aianalyzer`.
- Manufacturer/plugin codes remain stable for DAW compatibility.
- Default OSC endpoint: `127.0.0.1:9855`.
- Audio callback only pushes samples into a preallocated SPSC FIFO.
- FFT, loudness, temporal analysis and OSC run off the realtime audio thread.
- `libebur128` provides LUFS / True Peak measurement.

Do not casually change host/plugin identity fields. Existing DAW projects may depend on them.

### MCP

Stable core parser/server:

```text
bridge/server.py
```

Compatibility layers:

```text
bridge/server_v05.py       project-level entry layer
bridge/project_tools.py    project overview / Snapshot A-B
bridge/server_v06.py       CURRENT MCP ENTRY POINT
bridge/temporal_tools.py   V0.6 temporal parsing/tools
```

Current MCP tool count: **18**.

Release builds package `server_v06.py` with PyInstaller. Normal users should not need Python, pip, a venv or PyPI. Python source remains in Release packages only as a developer/manual fallback.

### Skill

```text
skills/ai-analyzer-flstudio/
```

The Skill scope is intentionally limited to:

```text
MCP calling strategy
parameter semantics
measurement validity
multi-instance identity / mapping
project overview / Snapshot A-B usage
temporal-measurement usage
```

The Skill must **not** become a style-specific mixing guide. Do not add fixed genre EQ recipes, LUFS targets, mandatory sidechain rules, mastering chains, or “metric X means always apply processor Y” behavior.

## 3. Important behavior already implemented

### 0.2 — loudness / True Peak / stereo bands

Implemented LUFS-S, LUFS-I, current/session-max True Peak and 8-band stereo correlation.

### 0.3 — signal validity and safe multi-instance identity

Implemented:

```text
signal gate close   ≈ -50 dBFS
signal gate reopen  ≈ -48 dBFS
hold                ≈ 0.4 s
```

Also implemented `signal_present`, detector peak, silence duration, active-frame validity and one runtime UUID per live plugin instance. Invalid content-dependent measurements become unavailable rather than misleading zeros. Runtime UUIDs are session-scoped.

### 0.4 — deterministic FL Mixer Track / Slot mapping

Implemented host-visible Boolean `Identify`. Every transition emits `/aianalyzer/identify`, including while transport is stopped. The Bridge binds emitted runtime UUIDs to known FL Mixer Track/Slot locations and exposes selectors such as:

```text
mixer:7/slot:9
```

Identify events are consumed once. Never guess Analyzer ↔ Mixer mapping from names or audio content when deterministic Identify mapping is available.

### 0.4.1 — packaging / installation foundation

Implemented development artifacts, user-facing manual Release workflow, automatic installers, Chinese/English manuals, PyInstaller standalone MCP, source fallback, and macOS quarantine/Gatekeeper handling.

Current user Release platform policy:

```text
Windows x64
macOS Apple Silicon arm64 only
```

Do not reintroduce Intel macOS / x86_64 unless explicitly requested.

### 0.5 — project intelligence and A/B

Implemented:

```text
audio_project_status()
audio_mix_overview()
audio_capture_snapshot()
audio_list_snapshots()
audio_compare_snapshots()
```

Purpose: reduce long low-level tool chains, expose project readiness/topology, summarize recent measurements and support measurement-oriented Before/After verification without embedding aesthetic judgment.

### 0.6 — temporal interaction evidence

Implemented VST3 temporal descriptors at the internal 1024-sample FFT hop and aggregated into the ~10 Hz OSC stream:

```text
temporal_window_seconds
spectral_flux_mean
spectral_flux_peak
rms_rise_peak_db
low_band_energy_db   # FFT-derived 40–160 Hz energy feature
```

`/aianalyzer/frame` remains append-only. V0.6 fields are appended after runtime UUID:

```text
59  temporal_window_seconds
60  spectral_flux_mean
61  spectral_flux_peak
62  rms_rise_peak_db
63  low_band_energy_db
64  frame_schema_version = "0.6"
```

Existing indexes `0..58` must not be reordered or silently repurposed.

MCP 0.6 adds:

```text
audio_temporal_profile(track, seconds=5)
audio_temporal_compare(track_a, track_b, seconds=5,
                       low_hz=40, high_hz=160,
                       alignment_tolerance_ms=80)
```

Semantics:

- Spectral flux is normalized positive spectral redistribution, not overall gain change.
- RMS rise is the largest positive adjacent-window RMS increase inside an emitted temporal aggregate.
- 40–160 Hz energy is an FFT-derived machine feature, not calibrated SPL.
- Temporal comparison aligns independent Analyzer streams using plugin timestamps and reports selected-band envelope correlation / relative temporal overlap.
- Onset/change candidates are explicit threshold-based heuristics, not ground-truth annotated musical onsets.
- Temporal overlap/correlation are evidence, not masking probability and not processing instructions.

## 4. Current roadmap

Roadmap describes measurement capability, not artistic policy.

### 0.7 — stronger masking evidence

Target additions:

- Bark or ERB-oriented auditory bands;
- relative-level weighting;
- temporal weighting using 0.6 evidence;
- critical-band interaction;
- clearer region-level candidate evidence.

Outputs must remain labeled as estimates/evidence unless implementation justifies stronger claims.

### 0.8 — deeper Mid/Side and stereo measurement

Potential additions:

- Mid spectrum;
- Side spectrum;
- frequency-dependent M/S energy;
- stronger distinction between wide, decorrelated and phase-opposed behavior.

### 0.9 — music-semantic measurements

Only add audio-domain inference where useful, such as chroma, pitch-class distribution or tonal-center evidence. Do not duplicate information obtainable more reliably from DAW/MIDI/project data through another MCP.

### 1.0 — reliable closed-loop measurement system

Target system:

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

## 5. MCP / measurement design rules

### Preserve semantics and compatibility

Metrics must not silently change meaning. If semantics must change, document the reason, update tests/docs/Skill, preserve compatibility when practical, and call out breaks explicitly.

OSC evolution should be append-only when practical. Preserve existing frame prefix/index meaning.

### `null` is not zero

Unavailable measurements remain unavailable. Never reinterpret `null` as numeric 0.

### Stable windows vs snapshots

Use window/project tools for observations requiring temporal stability. `audio_snapshot()` is current-state data, not a replacement for a stable window.

### Temporal evidence quality

Temporal results must expose enough context to judge reliability:

```text
window length
valid/active coverage
aligned pair count
band range
alignment tolerance
actual alignment offset where relevant
```

Do not overinterpret sparse or poorly aligned data.

### A/B is measurement-oriented

Snapshot comparison returns measurements and deltas, not claims such as “better”, “warmer” or “more professional”.

### Heuristics must be labeled

Spectral overlap, masking candidates, onset/change candidates and temporal overlap are heuristic/measurement evidence unless backed by a stronger validated model.

## 6. Release and platform rules

### Development CI

Keep path-aware incremental behavior:

```text
Source/** / CMake/plugin files
→ rebuild Windows x64 + macOS arm64 VST3

bridge/**
→ validate/package MCP + Skill
→ do not rebuild VST3 unless plugin code also changed

skills/**
→ validate/package MCP + Skill
→ do not rebuild VST3

release/** / release workflow
→ validate installer/release logic

README/docs only
→ no VST3 rebuild
```

Do not waste VST3 builds on unrelated docs/Skill/Python changes.

### User Release workflow

```text
.github/workflows/release.yml
```

Expected assets:

```text
AI-Audio-Analyzer-v<version>-Windows.zip
AI-Audio-Analyzer-v<version>-macOS.zip
SHA256SUMS.txt
```

Current targets are Windows x64 and macOS arm64 only.

A packaged MCP runtime must pass its built-in self-test before it is accepted. Current PyInstaller entry point is `bridge/server_v06.py` and the executable name remains `ai-audio-analyzer-mcp` / `.exe`.

### macOS

Current builds are ad-hoc signed, not Apple Developer ID notarized. Installation scripts/docs must stay truthful about quarantine/Gatekeeper behavior. Never claim notarization until the workflow actually performs and verifies it.

## 7. Documentation synchronization — mandatory

**Every repository change must include a documentation-impact review before it is complete.** This is mandatory even when the conclusion is “no documentation change required”.

At minimum inspect as relevant:

```text
README.md
README.zh-CN.md
AGENT.md

release/README.md
release/common/START-HERE.md
release/common/INSTALL.en.md
release/common/INSTALL.zh-CN.md

skills/ai-analyzer-flstudio/README-CHERRY-STUDIO.md
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/references/analyzer-mcp.md
skills/ai-analyzer-flstudio/references/parameters.md

bridge/cherry-studio.example.json
bridge/requirements.txt

.github/workflows/build.yml
.github/workflows/release.yml
```

For every change ask:

```text
Did public version change?
Did MCP entry point/tool count/tool args/defaults/output fields change?
Did OSC schema or metric semantics change?
Did signal validity or temporal validity change?
Did Identify/binding/selectors change?
Did supported OS/architecture change?
Did package/install layout change?
Did Python/PyInstaller behavior change?
Did Gatekeeper/signing behavior change?
Did Cherry Studio config change?
Did Skill calling strategy/scope change?
Did CI trigger/build behavior change?
Did roadmap/current-status change?
```

If yes, update every affected document in the same change whenever practical.

### English / Chinese parity

`README.md` and `README.zh-CN.md` must describe the same current facts. `INSTALL.en.md` and `INSTALL.zh-CN.md` must describe the same installation behavior. They need not be literal translations, but versions, platforms, paths, entry points, tool counts and limitations must not contradict each other.

### No stale roadmap

When a roadmap item is implemented, move it to implemented history and advance the roadmap. Do not leave shipped features marked “planned”.

## 8. Agent change procedure

```text
1. Read AGENT.md.
2. Inspect actual current files.
3. Identify affected VST3 / MCP / Skill / CI / Release / docs layers.
4. Make the smallest coherent implementation.
5. Add/update regression tests when behavior changes.
6. Perform mandatory documentation-impact review.
7. Update affected English/Chinese docs and references.
8. Verify intended CI path: build vs skip.
9. Inspect actual CI/runtime evidence before claiming success.
10. Update AGENT.md for meaningful architecture/history/roadmap changes.
```

Distinguish these states explicitly:

```text
source syntax/self-test
MCP regression
PyInstaller build
packaged-runtime self-test
VST3 build
package assembly
Release publication
```

One succeeding does not prove the others succeeded.

## 9. Versioning guidance

VST3 DSP/protocol changes and public product releases should bump the CMake product version. Bridge/Skill-only internal iterations do not automatically require a VST3 bump unless they are intentionally part of a new public release.

For a public version change review at least:

```text
CMakeLists.txt
README.md / README.zh-CN.md
AGENT.md
release docs/workflow
Cherry Studio example
Skill compatibility text
VERSION.txt generation
```

## 10. Guardrails

- Visible product name is `AI Audio Analyzer`; repository naming does not require host identity changes.
- Do not rename Bundle ID / plugin IDs casually.
- Do not guess FL Studio MCP tool names; inspect what it actually exposes.
- Do not guess Analyzer ↔ Mixer mapping when Identify is available.
- Do not treat `null` as zero.
- Do not treat spectral/temporal overlap as proof of audible masking.
- Do not call onset candidates ground-truth onsets.
- Do not encode one mixing aesthetic into MCP or Skill.
- Do not re-add Intel macOS Release support unless explicitly requested.
- Do not make ordinary users install Python while standalone MCP is available.
- Do not claim macOS notarization when it is not notarized.
- Do not trigger VST3 builds for unrelated changes.

## 11. Maintaining this file

`AGENT.md` is living project memory. Update it when architecture, supported platforms, Release strategy, MCP entry point/tools, protocol/identity model, measurement semantics, Skill scope, major milestones, roadmap priorities or CI/build policy materially change.

Keep it decision-focused rather than turning it into a raw commit log.
