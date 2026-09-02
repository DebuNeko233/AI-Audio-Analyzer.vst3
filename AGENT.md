# AGENT.md

This file is the working contract for AI agents and maintainers modifying **AI Audio Analyzer**.

Read this file before making changes. Keep implementation, CI, release packaging, installation instructions, MCP behavior, Skill behavior, and public documentation consistent with each other.

---

## 1. Project purpose

AI Audio Analyzer is a machine-readable audio analysis layer for AI/LLM-assisted music-production workflows.

The project is intentionally split into three user-facing parts:

```text
AI Audio Analyzer
├─ VST3    audio measurement inside the DAW
├─ MCP     structured access to Analyzer data
└─ Skill   instructions for using the MCP correctly and interpreting measurements
```

The Analyzer MCP is the **perception / measurement channel**. DAW control is expected to come from a separate FL Studio MCP, currently:

https://github.com/rosasynthesiz/flstudio-mcp

The intended closed loop is conceptually:

```text
OBSERVE → REASON → ACT → READBACK → COMPARE
```

The Analyzer project itself should stay focused on trustworthy measurement, identity/mapping, project-level observation, and verification.

---

## 2. Current architecture

### VST3

- JUCE 8.0.8
- C++20
- CMake
- internal target remains `AIAnalyzer`
- visible product name is `AI Audio Analyzer`
- Bundle ID remains `com.debuneko.aianalyzer`
- manufacturer/plugin codes remain stable for DAW compatibility
- OSC default endpoint: `127.0.0.1:9855`
- audio callback only pushes into a preallocated lock-free FIFO
- FFT/network/MCP-related analysis is off the realtime audio thread
- libebur128 is used for standards-oriented loudness / true-peak measurement

Current VST3 project version in `CMakeLists.txt`: **0.4.1**.

Do not casually change the internal target, Bundle ID, manufacturer code, plugin code, or other host identity fields. Existing FL Studio projects may depend on them.

### MCP

The stable core bridge is `bridge/server.py`.

The current project-level entry point is:

```text
bridge/server_v05.py
```

with project-level functionality implemented in:

```text
bridge/project_tools.py
```

The 0.5 layer extends the stable 0.4 bridge instead of replacing the OSC/VST3 protocol.

Release builds package the MCP with PyInstaller so normal users do not need Python, pip, a virtual environment, or PyPI access. Python source remains available under `mcp/source/` in Release packages as a developer/manual fallback.

### Skill

The Skill lives in:

```text
skills/ai-analyzer-flstudio/
```

Its scope is intentionally narrow:

```text
MCP calling strategy
parameter semantics
measurement validity
multi-instance identity / mapping
snapshot / A-B usage
```

The Skill must **not** become a style-specific mixing guide.

Do not add fixed artistic preferences such as:

- genre-specific EQ recipes;
- fixed LUFS targets;
- mandatory sidechain rules;
- fixed mastering chains;
- “if metric X then always apply processor Y” logic;
- subjective tonal-balance recipes presented as Analyzer truth.

The Skill should explain what a measurement means, when it is valid, what it cannot prove, and which MCP tool is appropriate.

---

## 3. Important behavior already implemented

### 0.2 — core measurement expansion

Implemented:

- LUFS-S
- LUFS-I
- True Peak
- session maximum True Peak
- 8-band stereo correlation

### 0.3 — signal validity and safe multi-instance identity

Implemented:

- signal gate close around `-50 dBFS`
- reopen around `-48 dBFS`
- roughly `0.4 s` hold behavior
- `signal_present`
- detector peak / silence duration
- invalid spectrum/stereo fields become `null` instead of misleading zeroes
- LUFS-S becomes unavailable after sustained silence
- LUFS-I and session max True Peak remain session-level values
- runtime UUID per live plugin instance
- duplicate human-readable Analyzer names no longer overwrite each other

Runtime UUIDs are intentionally session-scoped and are not permanent project identities.

### 0.4 — deterministic FL Mixer Track / Slot mapping

Implemented:

- host-visible boolean parameter `Identify`
- every Identify state transition sends `/aianalyzer/identify`
- Identify works even when transport is stopped
- bridge-side binding from runtime UUID to FL Mixer Track/Slot
- consumed Identify events so one event cannot be reused for another binding
- selectors such as:

```text
mixer:7/slot:9
```

- instance topology through `audio_instance_map()`

The Analyzer MCP does not directly call FL Studio MCP. The Agent/model coordinates the two MCP servers.

Never guess Analyzer ↔ Mixer mapping from track names, spectrum shape, or musical content when deterministic Identify mapping is available.

### 0.4.1 — packaging / installation foundation

Implemented:

- three-part development artifacts: VST3 + MCP + Skill
- manual user-facing Release workflow
- separate Windows and macOS lazy packages
- automatic installers
- Chinese and English installation manuals
- standalone PyInstaller MCP runtime
- Python-source fallback retained for developers
- macOS Gatekeeper/quarantine handling in the installer

Current user-facing Release platform policy:

```text
Windows: x64
macOS:   Apple Silicon arm64 only
```

Do not reintroduce macOS x86_64 / Intel packaging unless explicitly requested.

### 0.5 — project-level observation and A/B verification

Current MCP direction adds project-level tools such as:

```text
audio_project_status()
audio_mix_overview()
audio_capture_snapshot()
audio_list_snapshots()
audio_compare_snapshots()
```

Goals:

- reduce long chains of low-level tool calls;
- expose Analyzer readiness / topology at project level;
- summarize recent Analyzer state across tracks;
- capture controlled measurement snapshots;
- compare before / after measurements without embedding artistic judgment.

0.5 should remain primarily a Bridge/Skill evolution unless the feature genuinely requires new DSP data from the VST3.

---

## 4. Roadmap

This roadmap describes technical capability, not artistic mixing policy.

### 0.5 — Project Intelligence

Primary goals:

- complete project-level Analyzer overview;
- reliable project readiness status;
- snapshot lifecycle and controlled A/B comparison;
- clearer instance-map lifecycle / reset behavior;
- reduce repeated low-level MCP calls;
- keep outputs factual and measurement-oriented.

Prefer Bridge/Skill changes over VST3 DSP changes when the current measurements are sufficient.

### 0.6 — Time-domain / temporal interaction analysis

Possible additions:

- transient detection;
- spectral flux;
- onset density;
- band-energy envelopes;
- low-frequency envelope correlation;
- attack/decay approximations;
- timing-aware overlap information.

Purpose: distinguish spectral coexistence from actual temporal interaction.

### 0.7 — Better masking evidence

Possible additions:

- Bark or ERB-oriented auditory bands;
- relative-level weighting;
- temporal overlap weighting;
- critical-band interaction;
- clearer region-level masking candidates.

Important: outputs must still be described as evidence/estimation rather than absolute psychoacoustic truth unless the implementation justifies stronger claims.

### 0.8 — Mid/Side and deeper stereo analysis

Possible additions:

- Mid spectrum;
- Side spectrum;
- frequency-dependent M/S energy;
- stronger mono-compatibility diagnostics;
- better separation between “wide”, “decorrelated”, and “phase-opposed”.

### 0.9 — Music-semantic measurements

Possible additions where audio-domain inference is useful:

- chroma;
- pitch-class distribution;
- key / tonal-center evidence;
- harmonic relationships.

Do not duplicate information that can be obtained more reliably from DAW/MIDI/project data through another MCP.

### 1.0 — reliable closed-loop measurement system

Target state:

```text
project discovery
→ deterministic Analyzer mapping
→ project observation
→ external reasoning / user intent
→ DAW change through control MCP
→ Analyzer readback
→ controlled before/after comparison
```

1.0 does not mean the Analyzer should encode one mixing style. The system should provide reliable observations and verification so the model/user can apply their own artistic goals.

---

## 5. MCP and measurement design rules

### Preserve measurement semantics

A metric must not silently change meaning across versions.

If semantics must change:

1. document the reason;
2. update all affected docs and Skill references;
3. update CI/regression tests;
4. preserve backward compatibility where practical;
5. explicitly note compatibility breaks.

### `null` is not zero

Unavailable measurements must remain unavailable.

Examples:

- no valid signal → spectrum/stereo values may be `null`;
- `null` must never be interpreted as “0 dB energy” or “correlation = 0”.

### Prefer stable windows over single frames

Use `audio_average()` / project overview for observations that need temporal stability. `audio_snapshot()` is for current state, not a replacement for a measurement window.

### A/B must be measurement-oriented

Snapshot comparison should return deltas and comparability information. Avoid embedding statements such as “better”, “warmer”, “more professional”, or other aesthetic judgments into MCP outputs.

### Heuristics must be labeled

Spectral overlap / masking candidates are heuristic unless backed by a stronger model. Names, tool descriptions, docs, and Skill text must not overclaim.

---

## 6. Release and platform rules

### Development CI

Keep path-aware incremental behavior.

General principle:

```text
Source/** or CMake/plugin build files
→ rebuild VST3

bridge/**
→ validate/package MCP
→ do not rebuild VST3 unless actually needed

skills/**
→ validate/package Skill
→ do not rebuild VST3

release/** or release workflow
→ validate installer/release logic
→ do not rebuild normal development VST3 solely because docs/installers changed

README / docs-only changes
→ no VST3 rebuild
```

Do not cause expensive VST3 builds for documentation, Skill-only, or Python-only changes unless there is a concrete dependency.

### User Release workflow

User-facing lazy packages are generated manually through:

```text
.github/workflows/release.yml
```

Expected Release assets:

```text
AI-Audio-Analyzer-v<version>-Windows.zip
AI-Audio-Analyzer-v<version>-macOS.zip
SHA256SUMS.txt
```

Current targets:

```text
Windows x64
macOS arm64 / Apple Silicon
```

The packaged MCP runtime must run its built-in self-test before an artifact is accepted.

### PyInstaller

The packaged MCP should contain everything normal users need.

Normal users should not be forced to troubleshoot:

- Python installation;
- pip;
- venvs;
- PyPI mirrors;
- MCP SDK version conflicts.

Python/source installation remains a fallback and development path.

Avoid pulling unnecessary optional modules into the runtime when a smaller, explicit dependency graph is practical. If PyInstaller collection logic is changed, verify the packaged executable on every supported platform.

### macOS

Current Release support is Apple Silicon arm64 only.

Current builds are ad-hoc signed rather than Apple Developer ID notarized. Installation documentation and scripts must remain accurate about quarantine/Gatekeeper behavior.

Do not claim notarization unless the workflow actually performs Developer ID signing and Apple notarization successfully.

---

## 7. Documentation synchronization rule — mandatory

**Every repository change must include a documentation-impact review before it is considered complete.**

This is mandatory even when the final decision is “no documentation change required”.

After every code/config/workflow change, review whether each relevant document needs updating.

At minimum inspect this documentation set:

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
```

Also inspect workflow/package documentation when touching:

```text
.github/workflows/build.yml
.github/workflows/release.yml
release/**
```

### Documentation-impact checklist

For every change, ask:

```text
Did the public version change?
Did an MCP tool get added/removed/renamed?
Did a tool argument/default/output field change?
Did OSC schema or metric semantics change?
Did signal-validity behavior change?
Did Identify / binding / selector behavior change?
Did supported OS/architecture change?
Did artifact/package layout change?
Did install paths change?
Did Python/PyInstaller requirements change?
Did Gatekeeper/signing behavior change?
Did Cherry Studio configuration change?
Did Skill scope or usage strategy change?
Did the roadmap/current-status description change?
Did CI trigger/build behavior change?
```

If any answer is yes, update every affected document in the same change whenever practical.

### English / Chinese parity

`README.md` and `README.zh-CN.md` should describe the same current product behavior.

`INSTALL.en.md` and `INSTALL.zh-CN.md` should describe the same installation behavior.

They do not need to be literal translations, but facts, supported platforms, commands, paths, tool counts, versions, and limitations must not contradict each other.

### Do not leave stale roadmap text

When a roadmap item is implemented, move it into current capability/history and update the roadmap.

Do not leave documentation saying a feature is “planned” after the repository already implements it.

---

## 8. Change procedure for agents

Use this sequence for repository work:

```text
1. Read AGENT.md.
2. Inspect the actual current files involved.
3. Identify whether the change touches VST3, MCP, Skill, CI, Release, or docs.
4. Make the smallest coherent implementation change.
5. Update regression/smoke tests when behavior changes.
6. Perform the mandatory documentation-impact review.
7. Update all affected English/Chinese docs and references.
8. Verify the intended CI path: build vs skip.
9. Do not claim success before CI/runtime evidence exists.
10. Record meaningful architectural/history changes in AGENT.md when they affect future work.
```

When a change fails CI, inspect the failing job logs and fix the actual failure rather than guessing.

Do not claim a build succeeded because source validation passed. Distinguish clearly between:

```text
source self-test
PyInstaller build
packaged-runtime self-test
VST3 build
package assembly
Release publication
```

---

## 9. Versioning guidance

The VST3 CMake version and MCP feature-layer version do not always move in lockstep.

For example, the current VST3 project remains 0.4.1 while the Bridge has a 0.5 project-tool layer.

Only bump the VST3 project version when the plugin/release version should actually change. Do not bump it solely because Skill text or Bridge-only behavior changed unless the intended product release requires it.

When a public Release version changes, review:

```text
CMakeLists.txt
README.md
README.zh-CN.md
release docs
Release workflow assumptions
VERSION.txt generation
Skill compatibility text
AGENT.md history/current-state notes
```

---

## 10. Known constraints / guardrails

- Repository name may remain `AI-Analyzer.vst3`; visible product name is `AI Audio Analyzer`.
- Do not rename host/plugin identity fields casually.
- Do not guess FL Studio MCP tool names; use the tools actually exposed by that MCP.
- Do not guess Analyzer ↔ Mixer mapping from content when Identify mapping can be used.
- Do not treat heuristic spectral overlap as proof of audible masking.
- Do not treat `null` as zero.
- Do not encode one mixing aesthetic into the Analyzer MCP or Skill.
- Do not re-add Intel macOS Release support unless explicitly requested.
- Do not make ordinary users install Python when the standalone MCP runtime is available.
- Do not say macOS is notarized unless it actually is.
- Do not trigger VST3 rebuilds for unrelated docs/Skill/Python changes.

---

## 11. Maintaining this file

`AGENT.md` is a living project-memory document.

Update it when any of these change materially:

- architecture;
- supported platforms;
- release strategy;
- MCP entry point;
- key tools;
- protocol/identity model;
- Skill scope;
- major completed roadmap milestones;
- roadmap priorities;
- CI/build policy.

Do not turn this file into a raw commit log. Keep the history focused on decisions that matter to future agents and maintainers.
