# AGENT.md

This file is the working contract for AI agents and maintainers modifying **AI Audio Analyzer**.

Read it before changing the repository. Keep implementation, tests, CI, Release packaging, installers, MCP behavior, Skill behavior, history, and public documentation consistent.

## 1. Project purpose

AI Audio Analyzer is a machine-readable audio measurement layer for AI/LLM-assisted music-production workflows.

```text
AI Audio Analyzer
├─ VST3    measures audio inside the DAW
├─ MCP     exposes structured measurement / comparison / verification / performance evidence
└─ Skill   teaches correct MCP use and parameter semantics
```

Analyzer MCP is the measurement/perception/verification channel. DAW control is separate and currently paired with:

https://github.com/rosasynthesiz/flstudio-mcp

The Analyzer must remain measurement-oriented. Do not encode one artistic mixing, mastering, harmony, arrangement, tuning, or stereo style into MCP or Skill.

## 2. Current architecture

### VST3

- JUCE 8.0.8, C++20, CMake.
- Current development/product version: **1.1.0**.
- Visible product name: `AI Audio Analyzer`.
- Internal target: `AIAnalyzer`.
- Bundle ID: `com.debuneko.aianalyzer`.
- Manufacturer/plugin IDs remain stable for DAW-project compatibility.
- Default OSC endpoint: `127.0.0.1:9855`.
- Audio callback writes to a preallocated SPSC FIFO and does not run FFT, loudness, semantic analysis, OSC, MCP, file/network I/O, or verification orchestration.
- Background worker owns analysis and OSC.
- `libebur128` provides LUFS / True Peak measurement.
- Historical host-visible `Identify` remains the first parameter.
- Host-visible `Analysis Profile` is the second parameter.

Do not casually change host/plugin identity fields or reorder historical host parameters.

### Adaptive analysis profiles

Host parameter:

```text
Parameter ID: analysis_profile
Display name: Analysis Profile

0 Eco
1 Balanced
2 Mix
3 Full
```

Feature groups:

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

`Full` is the default for backward compatibility. Saved states without an `analysisProfile` attribute restore as Full.

Scheduling intent:

```text
Eco       no FFT / loudness work
Balanced  reduced FFT scheduling around network-update scale
Mix       hop-level FFT for temporal evidence
Full      Mix + lower-rate semantic analysis
```

These are performance profiles, not sonic modes. They must never alter the audio signal.

### MCP

There is exactly **one supported source/PyInstaller entrypoint**:

```text
bridge/server.py
```

Do not create version-named startup files.

Current internal layout:

```text
bridge/server.py             startup / self-test / version metadata / tool registration
bridge/analyzer_core.py      OSC/runtime state, identity/binding, base tools
bridge/project_tools.py      project overview / Snapshot A-B
bridge/temporal_tools.py     temporal parsing/tools
bridge/masking_tools.py      masking evidence
bridge/stereo_tools.py       Mid/Side and stereo evidence
bridge/semantic_tools.py     chroma / tonal-center / harmonic evidence
bridge/verification_tools.py controlled closed-loop verification sessions
bridge/performance_tools.py  adaptive-profile / worker-performance telemetry
bridge/ci_regression.py      repository-only synthetic MCP regression suite
```

Current metadata:

```text
MCP_VERSION = "1.1"
OSC_PROTOCOL_VERSION = "1.1"
MCP tool count = 29
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

Skill scope is MCP calling strategy, selector/mapping rules, profile selection, measurement validity, parameter semantics, performance telemetry, temporal/masking/stereo/tonal evidence, closed-loop verification, and limitations.

Do not add fixed genre EQ recipes, LUFS targets, mandatory sidechain rules, stereo recipes, mastering chains, key-change rules, harmony-edit rules, tuning recipes, or “metric X always means processor/action Y”.

## 3. Implemented evolution

The current product incorporates these milestones:

- loudness / True Peak / 8-band stereo correlation;
- signal validity and one runtime UUID per live instance;
- deterministic `Identify` mapping to FL Mixer Track/Slot;
- project overview and Snapshot A/B;
- temporal flux/RMS-rise/low-band evidence;
- 16-region equal-ERB-rate masking evidence;
- one stable MCP entrypoint;
- beginner Release packaging with PyInstaller `-F` and no developer source;
- deeper Mid/Side, Side-spectrum and negative-cross evidence;
- 12-bin chroma, tonal-center profile ranking and single-F0 harmonic evidence;
- controlled Before/After verification around external DAW writes/readback;
- adaptive analysis profiles and worker/FIFO performance telemetry.

Protocol evolution remains append-only. Current tail after the existing semantic fields is:

```text
128  analysis_profile
129  analysis_feature_mask
130  worker_load_ratio
131  fifo_fill_ratio
132  fft_runs_per_second
133  semantic_runs_per_second
134  schema marker = "1.1"
```

Indexes `0..127` must not be silently repurposed.

## 4. Why the adaptive-analysis milestone exists

This milestone is driven by a real multi-instance performance need: a project may contain many Analyzer instances, and every instance does not need every evidence family continuously.

This is a valid scoped post-1.0 milestone, not version-number momentum.

There is **no predefined next numbered roadmap**. Do not invent 1.2, 2.0, or another stage merely to advance numbering. Future milestones require an observed reliability gap, real workflow need, compatibility issue, validated measurement improvement, or Release/install problem.

## 5. Measurement and compatibility rules

### Preserve semantics

Do not silently change metric meaning. If semantics must change, update implementation, regression tests, Skill, README, Release docs, and AGENT together.

### `null` is not zero

Unavailable measurements remain unavailable.

### Feature mask is authoritative

The append-only OSC frame retains older field positions even when a profile disables their computation. Bridge-side adaptive parsing must invalidate disabled families so old tools cannot consume compatibility placeholders as real evidence.

Expected behavior includes:

```text
Loudness off  → LUFS / True Peak unavailable
Spectrum off  → spectrum validity false / spectral arrays unavailable
Stereo off    → stereo validity false / deep stereo fields unavailable
Temporal off  → temporal validity false / temporal descriptors unavailable
Semantic off  → semantic validity false / chroma/harmonic fields unavailable
```

### Keep independent concepts independent

Do not collapse correlation, Side/Mid energy, decorrelation proxy and negative-cross evidence into one opaque stereo score.

Do not collapse chroma coverage, entropy, tonal profile correlation, top-2 margin, harmonic ratio and F0 candidate into one opaque music-confidence score.

Do not collapse topology consistency, active coverage, target validity and host readback into a “change quality” score.

Do not collapse worker load, FIFO fill and FFT rate into one opaque “performance quality” score.

### Heuristics must be labeled

Spectral overlap, onset/change candidates, temporal overlap, ERB-rebinned evidence, negative-cross evidence, decorrelation proxies, tonal-center rankings, single-F0 harmonic alignment, and verification guardrails are evidence/heuristics unless replaced by a validated stronger model.

### Prefer exact project data for exact symbolic facts

If DAW/MIDI/project tooling exposes exact notes, chords, key metadata, tuning, or other symbolic state, use it for exact claims. Audio inference may complement it but must not silently override exact project data.

## 6. Performance and realtime rules

Any change to profiles, scheduling, FIFO behavior, or telemetry must review all of the following before merge:

```text
1. realtime callback work
2. host parameter compatibility / state restoration
3. actual feature computation skipped, not merely hidden
4. Bridge validity/null behavior for disabled families
5. profile-transition state reset semantics
6. FIFO backlog / measurement staleness behavior
7. Windows x64 + macOS arm64 compilation
8. MCP synthetic regressions
9. Skill / README / Release documentation impact
```

### No per-block control wakeups

The audio callback may cheaply read the host parameter, but it must only notify the worker when the profile actually changes. Do not add locks, allocation, network I/O, FFT, or heavyweight control work to `processBlock()`.

### Profile transitions must not bridge unmeasured gaps

When a disabled family is re-enabled:

- Loudness state is rebuilt so LUFS-I/True Peak history does not pretend the disabled interval was measured;
- Temporal previous-spectrum/RMS and aggregate state are cleared so flux/rise does not compare frames across a disabled gap;
- Semantic cache is cleared before new semantic evidence is considered current.

If new stateful analysis families are added later, define equivalent transition semantics explicitly.

### Telemetry semantics

`worker_load_ratio` is the Analyzer background-worker busy ratio. It is **not** DAW realtime CPU, system CPU, whole-plugin CPU, or dropout probability.

`fifo_fill_ratio` is queued Analyzer input capacity. Sustained growth is a measurement-lag warning because the worker may be falling behind the DAW.

`fft_runs_per_second` and `semantic_runs_per_second` are observed scheduler rates, not guaranteed constants.

### Control boundary

Analyzer MCP reads/verifies `Analysis Profile`; it does not write the DAW parameter.

Canonical profile-change flow:

```text
audio_analysis_status()
→ inspect actual DAW parameter through FL Studio control MCP
→ write Analysis Profile through the real control MCP
→ read actual host state back
→ audio_analysis_status() again
→ collect required evidence
→ restore previous profile when appropriate
```

Never invent FL Studio MCP tool names.

## 7. Closed-loop verification rules

Analyzer MCP owns measurement, identity/binding evidence, Before/After capture, comparability checks, deltas and audit context.

External FL Studio control MCP owns project/host inspection, actual writes and actual host-state readback.

`audio_begin_verification()` must occur before an externally controlled change when a measured Before/After experiment is requested.

`host_readback` must represent actual returned host state, not the intended value.

`controlled_comparison=true` is a technical comparability gate only. It does not mean After is better, correct, preferred, professional, or should be kept.

`closed_loop_complete=true` additionally requires caller-supplied host readback. It still does not imply artistic success.

Verification sessions are in-memory and not permanent project identifiers.

## 8. Release and platform rules

Supported user platforms:

```text
Windows x64
macOS Apple Silicon arm64 only
```

Do not re-add Intel/x86_64 macOS unless explicitly requested.

The GitHub Release is for ordinary users, including people who have never programmed.

Normal flow:

```text
download one ZIP
→ extract once
→ double-click installer
→ restart FL Studio
→ use generated configuration / Skill
```

User packages must contain only the product/plugin runtime, standalone MCP runtime, Skill and beginner-facing install material.

Mandatory invariants:

```text
one final ZIP per platform
no ZIP-inside-ZIP
PyInstaller -F / --onefile MCP executable
no MCP Python source
no requirements.txt
no developer examples/config
no venv
no _internal
```

Windows package includes `Install.cmd` / `Install.ps1`. macOS package includes `Install.command` / `install.sh`.

Do not require end users to understand Python, pip, venv, PyPI, CMake, compilers, package managers, source code, or shell commands.

Current macOS package is arm64 and ad-hoc signed, not Apple-notarized.

## 9. CI and regression rules

Do not claim a plugin change is complete until the relevant **latest PR head** has passed:

```text
MCP source/self-test
exact expected tool registry
bridge/ci_regression.py
release installer validation
Windows x64 VST3 build
macOS arm64 VST3 build
```

Do not substitute an older green run after the head has moved.

`bridge/ci_regression.py` must remain development-only and must not ship in beginner Releases.

Adaptive-analysis regressions must include at least:

- Full-profile legacy evidence remains valid;
- Eco/disabled families become unavailable, not misleading zeroes;
- parser indices and feature mask are correct;
- new MCP performance tools register correctly;
- earlier mapping/project/temporal/masking/stereo/tonal/verification regressions remain intact.

## 10. Documentation impact review — mandatory

For every code or workflow change, inspect whether these need updates:

```text
README.md
README.zh-CN.md
AGENT.md
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/README-CHERRY-STUDIO.md
skills/ai-analyzer-flstudio/references/*.md
release/README.md
release/common/START-HERE.md
release/common/INSTALL.en.md
release/common/INSTALL.zh-CN.md
.github/workflows/build.yml
.github/workflows/release.yml
bridge/cherry-studio.example.json
release installers
```

“No behavior change required” after inspection is acceptable; skipping the review is not.

README feature headings should describe the capability, not lead with historical version labels. Protocol/schema version numbers remain where they are semantically necessary.

## 11. Repository discipline

- Keep `bridge/server.py` as the only startup/PyInstaller entrypoint.
- Preserve host/plugin identity fields.
- Keep user-facing platform policy Windows x64 + macOS arm64 only.
- Keep LLM-facing Skill content English-only.
- Keep Release beginner-first and source-free.
- Keep evidence transparent and measurement-oriented.
- Do not claim CI, packaged-runtime, Release, or installer success without actual evidence.
- Do not merge a PR while required latest-head CI is failing or still pending.
