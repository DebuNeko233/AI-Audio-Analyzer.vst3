# AGENT.md

This file is the working contract for AI agents and maintainers modifying **AI Audio Analyzer**.

Read it before changing the repository. Keep implementation, tests, CI, Release packaging, installers, MCP behavior, Skill behavior, history, and public documentation consistent.

## 1. Project purpose

AI Audio Analyzer is a machine-readable audio measurement layer for AI/LLM-assisted music-production workflows.

```text
AI Audio Analyzer
├─ VST3    measures audio inside the DAW
├─ MCP     exposes structured measurements / comparisons / verification evidence
└─ Skill   teaches correct MCP use and parameter semantics
```

Analyzer MCP is the measurement/perception/verification channel. DAW control is separate and currently paired with:

https://github.com/rosasynthesiz/flstudio-mcp

The Analyzer must remain measurement-oriented. Do not encode one artistic mixing, mastering, harmony, arrangement, or stereo style into MCP or Skill.

## 2. Current architecture

### VST3

- JUCE 8.0.8, C++20, CMake.
- Current public/product version: **1.0.0**.
- Visible product name: `AI Audio Analyzer`.
- Internal target: `AIAnalyzer`.
- Bundle ID: `com.debuneko.aianalyzer`.
- Manufacturer/plugin IDs remain stable for DAW-project compatibility.
- Default OSC endpoint: `127.0.0.1:9855`.
- Audio callback only writes to a preallocated SPSC FIFO.
- FFT, loudness, temporal, stereo, music-semantic analysis and OSC run off the realtime audio thread.
- V1.0 verification orchestration is Bridge-side only; it does not add realtime DSP work.
- `libebur128` provides LUFS / True Peak measurement.

Do not casually change host/plugin identity fields.

### MCP

There is exactly **one supported source/PyInstaller entrypoint**:

```text
bridge/server.py
```

Do not create `server_v10.py`, `server_v11.py`, or any other version-named startup file. Versions are metadata, not filenames.

Current internal layout:

```text
bridge/server.py             startup, self-test, version metadata, tool registration
bridge/analyzer_core.py      OSC/runtime state, identity/binding, base tools
bridge/project_tools.py      V0.5 project overview / Snapshot A-B
bridge/temporal_tools.py     V0.6 temporal parsing/tools
bridge/masking_tools.py      V0.7 masking evidence
bridge/stereo_tools.py       V0.8 Mid/Side and stereo evidence
bridge/semantic_tools.py     V0.9 chroma / tonal-center / harmonic evidence
bridge/verification_tools.py V1.0 controlled closed-loop verification sessions
bridge/ci_regression.py      repository-only synthetic MCP regression suite
```

Current MCP tool count: **27**.

```text
MCP_VERSION = "1.0"
OSC_PROTOCOL_VERSION = "0.9"
```

V1.0 intentionally keeps OSC protocol at `0.9` because no new VST3 frame fields were added.

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

Skill scope is limited to MCP calling strategy, selector/mapping rules, measurement validity, parameter semantics, temporal evidence, masking evidence, Mid/Side/stereo evidence, V0.9 audio-domain tonal evidence, V1.0 closed-loop verification semantics, and limitations.

Do not add fixed genre EQ recipes, LUFS targets, mandatory sidechain rules, stereo recipes, mastering chains, key-change rules, harmony-edit rules, tuning recipes, or “metric X always means processor/action Y”.

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

V0.8 keeps OSC append-only and appends fields `65..111`.

Measurements:

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

MCP tools:

```text
audio_stereo_profile()
audio_stereo_compare()
```

Keep signed L/R correlation, Side/Mid energy, decorrelation proxy, negative-cross evidence, and frequency-dependent stereo relation independent. No universal stereo target/action is encoded.

### 0.9 — audio-domain music-semantic measurement

V0.9 keeps OSC append-only: existing indexes `0..111` remain unchanged and fields `112..127` are appended.

VST3 fields:

```text
112..123  chroma[12] = C..B
124       chroma_energy_ratio
125       single_f0_harmonic_energy_ratio
126       harmonic_f0_candidate_hz
127       V0.9 schema marker = "0.9"
```

Implementation characteristics:

```text
Chroma source        Mid spectrum
Semantic band        approximately 80 Hz–5 kHz
Pitch-class model    nearest 12-TET pitch class; octave-collapsed
F0 search            approximately 55–1000 Hz
Harmonics            up to 8 integer harmonics with narrow FFT-bin tolerance
```

The final harmonic matched-energy numerator and semantic-energy denominator use the same approximately `80 Hz–5 kHz` band.

MCP adds:

```text
audio_tonal_profile()
audio_tonal_compare()
```

Tonal-center candidates use 24 major/minor Krumhansl-Kessler profile Pearson correlations. Chroma, candidate ranking, top-2 margin, entropy, harmonic ratio and F0 candidate remain evidence, not exact symbolic truth/probabilities.

When exact notes, chords, key, or tuning metadata are available through DAW/MIDI/project tooling, prefer that exact source for exact symbolic claims.

### 1.0 — reliable closed-loop verification

V1.0 consolidates the measurement system around a controlled experiment lifecycle without turning Analyzer MCP into a DAW controller.

New tools:

```text
audio_begin_verification(label, seconds=5, target_selectors=None)
audio_complete_verification(verification_id, seconds=0, change_summary="", host_readback="")
audio_verification_status(verification_id="")
```

Canonical workflow:

```text
project discovery
→ deterministic Analyzer mapping
→ Before baseline
→ external reasoning / user intent
→ actual DAW change through external control MCP
→ actual host readback through external control MCP
→ After measurement
→ transparent comparability checks
→ After-minus-Before measurement deltas
→ specialized Analyzer evidence only when needed
```

V1.0 records/guards:

```text
verification_id
Before/After capture timestamps and window duration
target selectors
live Analyzer topology fingerprints
requested target presence and analysis validity
Before/After active-ratio comparability
external change summary
caller-supplied host readback
basic measurement deltas
```

Current active-ratio comparability tolerance:

```text
0.15 absolute difference
```

`controlled_comparison=true` only when the current technical guardrails pass: at least one compared target, same window duration, unchanged Analyzer topology/identity set, no missing requested targets, valid active analysis in both windows, and active-ratio difference within tolerance.

This Boolean is **not** an artistic quality score. It does not mean After is better, correct, preferred, or should be kept.

`host_readback` is caller-supplied evidence from the external control MCP. Analyzer stores it for auditability but does not independently query/verify FL Studio control state.

Verification sessions are Bridge-session memory only and disappear when the MCP process exits. Re-completing an already completed verification returns the stored completed result rather than silently replacing the After state.

### 1.0 — regression-suite consolidation

The large MCP synthetic regression was extracted from workflow YAML into:

```text
bridge/ci_regression.py
```

It preserves V0.4–V0.9 regressions and adds V1.0 positive/negative verification tests, including topology drift and active-coverage mismatch.

This file is development/test code and must not be shipped in beginner Releases.

### 0.9 Release-pipeline validation note

The complete 0.9 beginner Release pipeline was successfully exercised on both supported platforms, including PyInstaller `-F`, native packaged-runtime self-tests, VST3 builds, source/_internal/nested-ZIP rejection, single final compression, checksums and asset upload.

That run was intentionally/accidentally created with `draft=true`, so the resulting `v0.9.0` is a Draft Release and does not become public/Latest merely because packaging succeeded.

V1.0 fixes update semantics so rerunning an existing tag with Draft OFF explicitly synchronizes draft/prerelease state rather than only replacing assets/notes.

## 4. Current roadmap/status

**1.0 is the current scoped product milestone. There is no predefined post-1.0 numbered roadmap.**

Do not invent `1.1`, `1.2`, `2.0`, or another stage merely to advance numbering. Add a future milestone only when there is a real scoped need with a defensible implementation plan.

Post-1.0 work should normally be driven by observed reliability gaps, real user workflows, compatibility issues, validated measurement improvements, or Release/installation problems rather than version-number momentum.

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

Expose enough context to judge reliability: window length, active coverage, valid frame count, aligned pair count when applicable, frequency/ERB/stereo/pitch-class region, alignment tolerance/offset, usable temporal pairs, chroma coverage, tonal candidate separation, and V1.0 verification comparability fields.

### Heuristics must be labeled

Spectral overlap, onset/change candidates, temporal overlap, ERB-rebinned evidence, negative-cross evidence, decorrelation proxies, tonal-center rankings, single-F0 harmonic alignment, candidate rankings, and verification guardrails are measurement/heuristic/technical evidence unless replaced by a validated stronger model.

### Prefer exact symbolic project data for exact symbolic facts

If MIDI/DAW/project tooling exposes exact notes, chords, key metadata, tuning, or other symbolic state, use that source for exact symbolic claims. Analyzer audio inference may complement it but must not silently override exact project data.

### Keep independent concepts independent

Do not collapse correlation, Side/Mid energy, decorrelation proxy and negative-cross evidence into one opaque stereo score.

Do not collapse chroma coverage, entropy, tonal profile correlation, top-2 margin, harmonic ratio and candidate F0 into one opaque music-confidence/correctness score.

Do not collapse topology consistency, active coverage, target validity and host readback into one opaque “change quality” score.

### A/B is measurement-oriented

Snapshot/stereo/tonal/verification comparisons return measurements and deltas, not subjective claims such as “better”, “warmer”, “wider”, “more musical”, “in key”, “professional”, or “correct”.

## 6. V1.0 closed-loop rules

### Analyzer does not control the DAW

Analyzer MCP owns:

```text
measurement
identity/binding evidence
Before/After capture
comparability checks
measurement deltas
audit context
```

External FL Studio control MCP owns:

```text
project/host inspection
actual parameter/control writes
actual host state readback
```

Never invent FL Studio MCP tool names. Inspect the actual exposed tools/parameters.

### Begin before write

If measured Before/After verification is required, call `audio_begin_verification()` before the external DAW change. Do not perform the change first and then label a later capture as the Before baseline.

### Host readback must be actual readback

After an external write, use the control MCP to read the real host state. The `host_readback` string should represent that returned state, not the intended setting or an assumption that the write succeeded.

Analyzer does not independently validate caller-supplied readback text.

### `controlled_comparison` semantics are strict

Treat it as a technical comparability gate only.

If false, report the specific comparability failure before making a strong A/B interpretation.

If topology changed intentionally, the result can still be useful evidence, but it is intentionally not labelled a controlled comparison.

### Verification sessions are in-memory

Do not imply verification persistence across MCP restarts. `verification_id` is not a permanent project identifier.

## 7. Release and platform rules

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
bridge/ci_regression.py
```

Repository source/test files remain in the repository only.

### PyInstaller policy

Release MCP uses:

```text
-F / --onefile
```

The native packaged runtime must pass self-test before package assembly. If `_internal/` appears in staging/final user content, treat the package as invalid.

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

### Draft / prerelease state must be explicit

`draft=true` means the Release is intentionally not public and will not become Latest.

When updating an existing tag, workflow logic must synchronize draft/prerelease state as well as assets/notes. Do not assume replacing assets publishes an existing Draft.

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

## 8. Documentation synchronization — mandatory

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
skills/ai-analyzer-flstudio/references/tonal-evidence.md
skills/ai-analyzer-flstudio/references/verification-evidence.md
bridge/cherry-studio.example.json
bridge/requirements.txt
bridge/ci_regression.py
.github/workflows/build.yml
.github/workflows/release.yml
```

For every change ask:

```text
Did public version change?
Did MCP entrypoint/tool count/arguments/defaults/output change?
Did OSC schema/indexes or metric semantics change?
Did signal/temporal/masking/stereo/semantic validity change?
Did tonal/chroma/harmonic evidence semantics change?
Did verification lifecycle/comparability/readback semantics change?
Did exact-symbolic-data preference or evidence limitations change?
Did Identify/binding/selectors change?
Did supported OS/architecture change?
Did Release contents/layout change?
Did PyInstaller behavior change?
Did Draft/prerelease publication behavior change?
Did installer behavior change?
Did Gatekeeper/signing behavior change?
Did Cherry Studio config change?
Did Skill calling strategy/scope/language change?
Did CI trigger/build/regression behavior change?
Did current product status/history change?
```

If yes, update every affected document in the same change whenever practical.

`README.md` / `README.zh-CN.md` and `INSTALL.en.md` / `INSTALL.zh-CN.md` must describe the same current facts.

When a planned milestone is implemented, move it into implemented history. Do not invent a new roadmap number without a real requirement.

## 9. Agent change procedure

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
10. Update AGENT.md for meaningful architecture/history/status changes.
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
Release creation/update
Draft/prerelease/publication state
```

One succeeding does not prove the others succeeded.

## 10. Guardrails

- Do not rename Bundle ID / plugin IDs casually.
- Keep `bridge/server.py` as the only MCP entrypoint.
- Do not reintroduce `server_vXX.py` startup files.
- Keep Release MCP in PyInstaller one-file mode unless explicitly changing policy.
- Do not ship MCP source/test code in user Releases.
- Do not create nested Release ZIPs.
- Keep user Releases understandable without programming knowledge.
- Do not re-add macOS Intel/x86_64 packages unless explicitly requested.
- Do not guess FL Studio MCP tool names; inspect actual exposed tools.
- Do not guess Analyzer ↔ Mixer mapping when Identify is available.
- Do not claim external DAW write success without actual host readback when readback is available/required.
- Do not call `controlled_comparison=true` an artistic success signal.
- Do not silently treat topology drift or active-coverage mismatch as a controlled A/B.
- Do not invent a post-1.0 version roadmap merely for numbering.
