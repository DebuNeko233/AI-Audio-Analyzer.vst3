# AGENT.md

This file is the working contract for AI agents and maintainers modifying **AI Audio Analyzer**.

Read it before changing the repository. Keep implementation, tests, CI, Release packaging, installation instructions, MCP behavior, Skill behavior, and public documentation consistent.

## 1. Project purpose

AI Audio Analyzer is a machine-readable audio measurement layer for AI/LLM-assisted music-production workflows.

```text
AI Audio Analyzer
├─ VST3    measures audio inside the DAW
├─ MCP     exposes structured measurements / comparisons / evidence
└─ Skill   teaches correct MCP use and parameter semantics
```

The Analyzer MCP is the **measurement/perception channel**. DAW control is separate and currently paired with:

https://github.com/rosasynthesiz/flstudio-mcp

The Analyzer should stay focused on trustworthy measurement, deterministic identity/mapping, project observation, evidence, and readback verification. It must not encode one artistic mixing style.

## 2. Current architecture

### VST3

- JUCE 8.0.8, C++20, CMake.
- Current public/product version: **0.7.0**.
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

Feature layers:

```text
bridge/server_v05.py       project-level compatibility layer
bridge/project_tools.py    project overview / Snapshot A-B
bridge/server_v06.py       temporal-analysis entry layer
bridge/temporal_tools.py   V0.6 temporal parsing/tools
bridge/server_v07.py       CURRENT MCP ENTRY POINT
bridge/masking_tools.py    V0.7 auditory-band masking evidence
```

Current MCP tool count: **20**.

Release builds package `server_v07.py` with PyInstaller. Normal users should not need Python, pip, a venv, or PyPI. Python source remains in Release packages as developer/manual fallback.

### Skill

```text
skills/ai-analyzer-flstudio/
```

All **LLM-facing Skill content must be written in English**:

```text
SKILL.md
README-CHERRY-STUDIO.md
references/*.md
```

Human-facing public documentation remains bilingual where appropriate (`README.md` + `README.zh-CN.md`, `INSTALL.en.md` + `INSTALL.zh-CN.md`).

Skill scope is intentionally limited to:

```text
MCP calling strategy
parameter semantics
measurement validity
multi-instance identity / mapping
project overview / Snapshot A-B usage
temporal evidence usage
masking-evidence usage and limitations
```

The Skill must **not** become a style-specific mixing guide. Do not add fixed genre EQ recipes, LUFS targets, mandatory sidechain rules, mastering chains, or “metric X means always apply processor Y” behavior.

## 3. Important implemented milestones

### 0.2 — loudness / True Peak / stereo bands

Implemented LUFS-S, LUFS-I, current/session-max True Peak and 8-band stereo correlation.

### 0.3 — signal validity and runtime identity

Implemented:

```text
signal gate close   ≈ -50 dBFS
signal gate reopen  ≈ -48 dBFS
hold                ≈ 0.4 s
```

Also implemented `signal_present`, detector peak, silence duration, active-frame validity, and one runtime UUID per live plugin instance. Invalid content-dependent measurements become unavailable rather than misleading zeros.

### 0.4 — deterministic FL Mixer Track / Slot mapping

Implemented host-visible Boolean `Identify`. Every transition emits `/aianalyzer/identify`, including while transport is stopped. The Bridge binds emitted runtime UUIDs to known FL Mixer Track/Slot locations and exposes selectors such as:

```text
mixer:7/slot:9
```

Never guess Analyzer ↔ Mixer mapping from names or audio content when deterministic Identify mapping is available.

### 0.4.1 — packaging / installation foundation

Implemented development artifacts, user-facing manual Release workflow, automatic installers, Chinese/English manuals, PyInstaller standalone MCP, source fallback, and macOS quarantine/Gatekeeper handling.

Current Release platform policy:

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

Purpose: reduce long low-level tool chains, expose project readiness/topology, summarize recent measurements, and support measurement-oriented Before/After verification without embedding aesthetic judgment.

### 0.6 — temporal interaction evidence

VST3 appends temporal descriptors to the existing OSC frame:

```text
59  temporal_window_seconds
60  spectral_flux_mean
61  spectral_flux_peak
62  rms_rise_peak_db
63  low_band_energy_db
64  frame_schema_version = "0.6"
```

Indexes `0..58` remain unchanged.

MCP adds:

```text
audio_temporal_profile()
audio_temporal_compare()
```

Temporal results expose spectral flux, RMS-rise evidence, selected-band envelope correlation/overlap, alignment quality, and threshold-based onset/change candidates.

These are measurement/heuristic evidence, not processing instructions or masking probabilities.

### 0.7 — stronger masking evidence

V0.7 is primarily a Bridge/MCP evidence layer. It does **not** add OSC fields beyond the V0.6 frame.

Current model:

```text
existing 32 Analyzer spectrum features
→ 16 equal ERB-rate regions
→ relative spectral occupancy
→ directional relative-level weighting
→ V0.6 temporal overlap
→ region-level masking evidence
```

Implemented tools:

```text
audio_masking_evidence()
audio_project_masking_scan()
```

Important semantics:

- ERB is used for **feature re-binning**, not as a gammatone/cochlear filterbank.
- `auditory_band_model.filterbank=false` is intentional.
- Direction weights are bounded functions of relative regional level, not calibrated masking thresholds.
- Combined evidence mixes spectral/level evidence with V0.6 temporal overlap using a documented formula.
- Scores are transparent heuristic evidence for ranking/querying, not probabilities of audible masking.
- No universal pass/fail threshold is defined.
- V0.7 does not prescribe EQ, sidechain, compression, gain, panning, or other mix actions.

## 4. Current roadmap

Roadmap describes measurement capability, not artistic policy.

### 0.8 — deeper Mid/Side and stereo measurement

Target additions:

- Mid spectrum;
- Side spectrum;
- frequency-dependent M/S energy;
- clearer distinction between wide, decorrelated, and phase-opposed behavior;
- better low-frequency mono-compatibility evidence.

Prefer append-only OSC evolution if new VST3 measurements are required.

### 0.9 — music-semantic measurements

Only add audio-domain inference where useful, such as chroma, pitch-class distribution, or tonal-center evidence. Do not duplicate information obtainable more reliably from DAW/MIDI/project data through another MCP.

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

Metrics must not silently change meaning. If semantics must change:

1. document the reason;
2. update tests/docs/Skill;
3. preserve compatibility when practical;
4. explicitly call out compatibility breaks.

OSC evolution should be append-only when practical. Existing frame indexes must not be silently repurposed.

### `null` is not zero

Unavailable measurements remain unavailable. Never reinterpret `null` as numeric 0.

### Prefer stable windows over single frames

Use window/project tools for observations requiring temporal stability. `audio_snapshot()` is current-state data, not a replacement for a stable window.

### Evidence quality must be visible

Temporal/masking evidence should expose enough context to judge reliability:

```text
window length
active coverage
aligned pair count
frequency/ERB region
alignment tolerance
actual alignment offset
temporal usable-pair count
```

Do not overinterpret sparse, stale, mostly silent, or poorly aligned data.

### Heuristics must be labeled

Spectral overlap, masking candidates, onset/change candidates, temporal overlap, ERB-rebinned masking evidence, and project candidate rankings are heuristic/measurement evidence unless backed by a stronger validated model.

### Keep formulas auditable

If evidence scores combine multiple components, return or document the formula and constants. Do not hide opaque scoring logic behind a single “quality” number.

### A/B is measurement-oriented

Snapshot comparison returns measurements and deltas, not claims such as “better”, “warmer”, or “more professional”.

## 6. Release and platform rules

### Development CI

Keep path-aware incremental behavior:

```text
Source/** / CMake/plugin files
→ rebuild Windows x64 + macOS arm64 VST3

bridge/**
→ validate/package MCP + Skill
→ do not rebuild VST3 unless plugin/version files also changed

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

Current targets: Windows x64 and macOS arm64 only.

A packaged MCP runtime must pass its built-in self-test before it is accepted. Current PyInstaller entry point is:

```text
bridge/server_v07.py
```

The executable name remains `ai-audio-analyzer-mcp` / `.exe`.

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
skills/ai-analyzer-flstudio/references/masking-evidence.md

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
Did signal/temporal/evidence validity change?
Did Identify/binding/selectors change?
Did supported OS/architecture change?
Did package/install layout change?
Did Python/PyInstaller behavior change?
Did Gatekeeper/signing behavior change?
Did Cherry Studio config change?
Did Skill calling strategy/scope/language policy change?
Did CI trigger/build behavior change?
Did roadmap/current-status change?
```

If yes, update every affected document in the same change whenever practical.

### English / Chinese parity

`README.md` and `README.zh-CN.md` must describe the same current facts. `INSTALL.en.md` and `INSTALL.zh-CN.md` must describe the same installation behavior. They need not be literal translations, but versions, platforms, paths, entry points, tool counts, and limitations must not contradict each other.

### English-only LLM Skill

All LLM-facing Skill files are English-only. Do not add Chinese sections back into `SKILL.md` or `references/*.md` unless the project policy is explicitly changed.

### No stale roadmap

When a roadmap item is implemented, move it to implemented history and advance the roadmap.

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

A public product release may bump the CMake version even when the new user-facing capability is Bridge/MCP-heavy, so GitHub Release tags and package versions remain coherent.

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

Do not change host identity fields merely because the product version changes.

## 10. Guardrails

- Visible product name is `AI Audio Analyzer`; repository naming does not require host identity changes.
- Do not rename Bundle ID / plugin IDs casually.
- Do not guess FL Studio MCP tool names; inspect what it actually exposes.
- Do not guess Analyzer ↔ Mixer mapping when Identify is available.
- Do not treat `null` as zero.
- Do not treat spectral/temporal/ERB-rebinned evidence as proof of audible masking.
- Do not call onset candidates ground-truth onsets.
- Do not call V0.7 ERB re-binning a gammatone/cochlear filterbank.
- Do not encode one mixing aesthetic into MCP or Skill.
- Keep LLM-facing Skill content in English.
- Do not re-add Intel macOS Release support unless explicitly requested.
- Do not make ordinary users install Python while standalone MCP is available.
- Do not claim macOS notarization when it is not notarized.
- Do not trigger VST3 builds for unrelated changes.

## 11. Maintaining this file

`AGENT.md` is living project memory. Update it when architecture, supported platforms, Release strategy, MCP entry point/tools, protocol/identity model, measurement/evidence semantics, Skill scope/language, major milestones, roadmap priorities, or CI/build policy materially change.

Keep it decision-focused rather than turning it into a raw commit log.
