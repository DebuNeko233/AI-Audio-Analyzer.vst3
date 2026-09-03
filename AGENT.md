# AGENT.md

This file is the working contract for AI agents and maintainers modifying **AI Audio Analyzer**.

Read it before changing the repository. Keep implementation, tests, CI, Release packaging, installers, MCP behavior, Skill behavior, history, and public documentation consistent.

## 1. Project purpose

AI Audio Analyzer is a machine-readable audio measurement layer for AI/LLM-assisted music-production workflows.

```text
AI Audio Analyzer
├─ VST3    measures audio + DAW transport context inside the DAW
├─ MCP     exposes measurement / timeline memory / comparison / verification evidence
└─ Skill   teaches correct MCP use, latency handling and parameter semantics
```

Analyzer MCP is the measurement/perception/memory/verification channel. DAW control is separate and currently paired with:

https://github.com/rosasynthesiz/flstudio-mcp

The Analyzer must remain measurement-oriented. Do not encode one artistic mixing, mastering, harmony, arrangement, tuning, or stereo style into MCP or Skill.

The LLM is deliberately **not** part of the realtime measurement loop. The Analyzer should continue observing while an Agent is thinking or using another tool, and expose enough retained DAW-time context for the Agent to reason later without pretending it observed the audio live.

## 2. Current architecture

### VST3

- JUCE 8.0.8, C++20, CMake.
- Current development/product version: **1.2.0**.
- Visible product name: `AI Audio Analyzer`.
- Internal target: `AIAnalyzer`.
- Bundle ID: `com.debuneko.aianalyzer`.
- Manufacturer/plugin IDs remain stable for DAW-project compatibility.
- Default OSC endpoint: `127.0.0.1:9855`.
- Audio callback writes to a preallocated SPSC FIFO and does not run FFT, loudness, semantic analysis, OSC, MCP, file/network I/O, or verification orchestration.
- Audio callback may read host transport and hand a compact snapshot to the worker through atomics only.
- Background worker owns analysis, state reset, latency estimation and OSC.
- `libebur128` provides LUFS / True Peak measurement.
- Historical host-visible `Identify` remains the first parameter.
- Host-visible `Analysis Profile` remains the second parameter.

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

### Transport-aware song memory

Protocol 1.2 adds a DAW-time context tail and MCP-side bounded song memory.

The VST3 reads host transport from `AudioPlayHead::PositionInfo` during `processBlock()` and hands only atomics to the worker. The worker estimates the DAW-time position of the analyzed FFT window by compensating for:

```text
current FIFO backlog
+
half of the 4096-sample FFT window
```

This is intended for whole-song/section reasoning, not sample-accurate editing.

A `transport_epoch` is one **instance-local continuous playback pass**. Playback start, seek, loop jump, or another detected discontinuity increments the epoch. When the worker observes an epoch change it:

```text
discards queued pre-jump FIFO audio
clears analysis windows / temporal continuity
resets Semantic cache
resets Loudness state when Loudness is enabled
```

This prevents old-position audio from being mislabeled as new-position audio.

Epoch counters are generated independently in every live VST3 instance. Do not treat an equal numeric epoch across instances as a permanent project-wide pass ID. MCP project/song tools must expose consistency and DAW-time ranges instead of silently assuming equality.

MCP canonical song memory uses **1-second bins**, bounded to **1200 bins / 20 minutes per instance**, and can aggregate to 1/2/5/10/15/30-second query bins. It is MCP-session memory, not yet a persistent project database.

### MCP

There is exactly **one supported source/PyInstaller entrypoint**:

```text
mcp/server.py
```

Do not create version-named startup files.

Current internal layout:

```text
mcp/server.py             startup / self-test / version metadata / tool registration
mcp/analyzer_core.py      OSC/runtime state, identity/binding, base tools
mcp/project_tools.py      project overview / Snapshot A-B
mcp/temporal_tools.py     temporal parsing/tools
mcp/masking_tools.py      masking evidence
mcp/stereo_tools.py       Mid/Side and stereo evidence
mcp/semantic_tools.py     chroma / tonal-center / harmonic evidence
mcp/performance_tools.py  adaptive-profile / worker-performance telemetry
mcp/song_tools.py         transport parser / song-pass memory / latency-aware summaries
mcp/verification_tools.py controlled closed-loop verification sessions
mcp/ci_regression.py      repository-only synthetic MCP regression suite
```

The repository source directory is named `mcp/`. Do not reintroduce a parallel `bridge/` source directory; “Bridge” may still appear as a conceptual/runtime term and in historical/public tool names such as `audio_bridge_status`.

Current metadata:

```text
MCP_VERSION = "1.2"
OSC_PROTOCOL_VERSION = "1.2"
MCP tool count = 32
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

Skill scope is MCP calling strategy, selector/mapping rules, profile selection, measurement validity, parameter semantics, transport/song-memory semantics, latency/data-quality handling, performance telemetry, temporal/masking/stereo/tonal evidence, closed-loop verification, and limitations.

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
- adaptive analysis profiles and worker/FIFO performance telemetry;
- repository MCP source normalized under `mcp/`, with beginner-facing `MCP-SETUP.md` and copyable Agent/client JSON examples;
- transport-aware continuous playback epochs, Analyzer backlog/drop telemetry and bounded DAW-time song memory so LLM/tool latency does not erase past musical evidence.

Protocol evolution remains append-only. Current tail is:

```text
128  analysis_profile
129  analysis_feature_mask
130  worker_load_ratio
131  fifo_fill_ratio
132  fft_runs_per_second
133  semantic_runs_per_second
134  schema marker = "1.1"
135  transport_supported
136  transport_time_seconds
137  transport_ppq_position
138  transport_bpm
139  transport_time_signature_numerator
140  transport_time_signature_denominator
141  transport_is_playing
142  transport_is_recording
143  transport_is_looping
144  transport_loop_start_ppq
145  transport_loop_end_ppq
146  transport_epoch
147  estimated_analysis_lag_ms
148  dropped_blocks
149  schema marker = "1.2"
```

Indexes `0..134` must not be silently repurposed.

## 4. Why the current milestones exist

Adaptive analysis was driven by a real multi-instance performance need: a project may contain many Analyzer instances, and every instance does not need every evidence family continuously.

Transport-aware song memory is driven by a different reliability need: LLM reasoning, MCP calls, external DAW writes and human/host interaction all take time. A measurement layer that only exposes “the latest few seconds” cannot reliably support whole-song mixing/mastering because the relevant passage may have ended before the Agent reads it.

The 1.2 milestone is therefore a scoped protocol/product evolution tied to an observed workflow gap, not version-number momentum.

There is **no predefined next numbered roadmap**. Do not invent another stage merely to advance numbering. Future milestones require an observed reliability gap, real workflow need, compatibility issue, validated measurement improvement, or Release/install problem.

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

Transport/Core context may remain available under Eco because it is lightweight host/context metadata, not FFT/Semantic analysis.

### Keep independent concepts independent

Do not collapse correlation, Side/Mid energy, decorrelation proxy and negative-cross evidence into one opaque stereo score.

Do not collapse chroma coverage, entropy, tonal profile correlation, top-2 margin, harmonic ratio and F0 candidate into one opaque music-confidence score.

Do not collapse topology consistency, active coverage, target validity and host readback into a “change quality” score.

Do not collapse worker load, FIFO fill, FFT rate, estimated lag, dropped blocks and data age into one opaque “performance quality” score.

### Heuristics and estimates must be labeled

Spectral overlap, onset/change candidates, temporal overlap, ERB-rebinned evidence, negative-cross evidence, decorrelation proxies, tonal-center rankings, single-F0 harmonic alignment, verification guardrails, transport-window alignment and FIFO-derived analysis lag are evidence/heuristics/estimates unless replaced by a validated stronger model.

### Prefer exact project data for exact symbolic facts

If DAW/MIDI/project tooling exposes exact notes, chords, key metadata, tuning, markers, section labels, routing or other symbolic state, use it for exact claims. Audio inference may complement it but must not silently override exact project data.

Do not claim `audio_song_overview()` has identified Verse/Chorus/Bridge; automatic musical-form labeling is not implemented yet.

## 6. Performance, transport and realtime rules

Any change to profiles, scheduling, FIFO behavior, transport handling, timeline memory, or telemetry must review all of the following before merge:

```text
1. realtime callback work
2. host parameter compatibility / state restoration
3. actual feature computation skipped, not merely hidden
4. Bridge validity/null behavior for disabled families
5. profile-transition state reset semantics
6. transport-discontinuity / epoch reset semantics
7. FIFO backlog / measurement staleness / data-age behavior
8. Windows x64 + macOS arm64 compilation
9. MCP synthetic regressions
10. Skill / README / Release documentation impact
```

### Realtime handoff is atomic-only

The audio callback may cheaply read the host parameter and DAW transport and update atomic worker state. It must not call `Thread::notify()`, take a lock, allocate, perform network I/O, run FFT, or execute heavyweight control work for profile/transport changes.

The worker observes requested profile and transport epoch asynchronously on its own loop. Non-realtime config/profile paths may use the normal worker setter when an immediate wake-up is useful.

### Transport discontinuities must not relabel queued audio

On a requested transport epoch change, the **consumer/worker** owns FIFO discard. The audio callback must not reset or mutate FIFO read state.

Current invariant:

```text
producer detects host discontinuity
→ atomically publishes new transport epoch
→ worker observes epoch
→ worker discards queued pre-jump samples
→ worker resets pass-dependent state
→ new epoch analysis begins
```

This may intentionally discard a small amount of newly pushed audio around the discontinuity. That is preferable to falsely labeling old pre-seek audio under a new DAW position.

### Transport coordinate semantics

`transport_time_seconds` / `transport_ppq_position` are estimated analyzed-window coordinates, not latest host-read coordinates and not sample-accurate edit points.

Current lag model:

```text
analysisDelaySamples = fifo.available() + kFftSize / 2
estimated_analysis_lag_ms = analysisDelaySamples / sampleRate * 1000
```

PPQ correction uses current BPM and the time correction. Do not describe this as exact tempo-map reconstruction across abrupt tempo changes.

`estimated_analysis_lag_ms` excludes network/MCP/LLM/external-control latency.

### Worker wake and loudness polling invariants

The audio callback still does **not** wake the worker. When the FIFO contains less than one analysis hop, the worker estimates the arrival time of missing samples from sample rate and sleeps for a bounded interval of **1–20 ms**.

When Loudness is enabled:

- every 1024-sample hop is passed to `ebur128_add_frames_float()`;
- `ebur128_prev_true_peak()` is read every hop;
- pass max True Peak is the running maximum of those per-hop values;
- LUFS-S and LUFS-I aggregate queries are polled every **100 ms**;
- a protocol-1.2 transport epoch change resets Loudness state so LUFS-I/pass-max TP represent the new continuous playback pass;
- disabling then re-enabling Loudness also starts a fresh Loudness state.

Legacy pre-1.2 frame parsing does not retroactively change old plugin loudness behavior.

`tests/WorkerSchedulingTests.cpp` must continue verifying idle-wait boundaries and True Peak accumulation semantics. Do not change the hop or true-peak strategy without re-reviewing those regressions.

### Profile transitions must not bridge unmeasured gaps

When a disabled family is re-enabled:

- Loudness state is rebuilt;
- Temporal previous-spectrum/RMS and aggregate state are cleared;
- Semantic cache is cleared.

If new stateful analysis families are added later, define equivalent transition semantics explicitly.

### Telemetry semantics

`worker_load_ratio` is Analyzer background-worker busy ratio. It is **not** DAW realtime CPU, system CPU, whole-plugin CPU, or dropout probability.

`fifo_fill_ratio` is queued Analyzer input capacity. Sustained growth is a measurement-lag warning.

`estimated_analysis_lag_ms` is FIFO + half-window delay estimate. It is not total end-to-end Agent latency.

`dropped_blocks` is cumulative FIFO push failure count for the live VST3 instance. Non-zero means some input audio was not analyzed.

`data_age_seconds` is MCP wall-clock age of retained evidence. Historical evidence can be old and still valid for an explicitly requested past DAW-time range.

`coverage_ratio` must reflect actually retained canonical timeline coverage. Aggregating sparse 1-second bins into a 5/10/30-second result must **not** falsely turn partial coverage into 100% coverage.

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

## 7. Song-memory rules

High-level tools:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline()
```

The canonical storage resolution is one second. Query-time coarser aggregation may reduce LLM token load but must preserve:

```text
transport epoch
DAW-time range
active coverage
data age
estimated Analyzer lag
dropped blocks
feature validity
```

Do not persist every 10 Hz OSC frame merely to make the LLM read more data. The purpose of the layer is compact, latency-resilient musical context.

The current store is in-memory and bounded. Persistence/change ledgers/section detection may be future milestones, but do not claim they already exist.

## 8. Closed-loop verification rules

Analyzer MCP owns measurement, identity/binding evidence, Before/After capture, comparability checks, deltas and audit context.

External FL Studio control MCP owns project/host inspection, actual writes and actual host-state readback.

`audio_begin_verification()` must occur before an externally controlled change when a measured Before/After experiment is requested.

`host_readback` must represent actual returned host state, not the intended value.

`controlled_comparison=true` is a technical comparability gate only. It does not mean After is better, correct, preferred, professional, or should be kept.

`closed_loop_complete=true` additionally requires caller-supplied host readback. It still does not imply artistic success.

Current verification is still recent-window based. Do not claim same-DAW-time transport-anchored verification until it is explicitly implemented and regression-tested.

Verification sessions are in-memory and not permanent project identifiers.

## 9. Release and platform rules

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
→ add generated MCP configuration to the intended Agent/Assistant
→ import/use the Skill with the same Agent
```

User packages must contain only the product/plugin runtime, standalone MCP runtime, Skill and beginner-facing install material.

Mandatory invariants:

```text
one final ZIP per platform
no ZIP-inside-ZIP
PyInstaller -F / --onefile MCP executable
no MCP Python source
no requirements.txt
no developer source examples/config
MCP-SETUP.md included with copyable user JSON examples
installer-generated cherry-studio-mcp.json uses the real absolute installed executable path
no venv
no _internal
```

`MCP-SETUP.md` is beginner-facing installation material and is allowed/required even though developer configuration examples such as repository `mcp/cherry-studio.example.json` remain excluded from user Releases.

Windows package includes `Install.cmd` / `Install.ps1`. macOS package includes `Install.command` / `install.sh`.

Do not require end users to understand Python, pip, venv, PyPI, CMake, compilers, package managers, source code, or shell commands.

Current macOS package is arm64 and ad-hoc signed, not Apple-notarized.

## 10. CI and regression rules

Do not claim a plugin change is complete until the relevant **latest PR head** has passed:

```text
MCP source/self-test
exact expected tool registry
mcp/ci_regression.py
release installer validation
worker scheduling / True Peak C++ regressions
Windows x64 VST3 build
macOS arm64 VST3 build
```

Do not substitute an older green run after the head has moved.

### Development workflow scope

`.github/workflows/build.yml` is intentionally path-scoped. Changes unrelated to plugin source/build files, MCP source, Analyzer Skill, Release installer material, or build/release workflows should not start the development workflow.

`tests/**` is part of plugin validation scope. Internal C++ regressions are enabled in development CI with `AI_ANALYZER_BUILD_TESTS=ON`; ordinary Release builds leave that option off and do not ship the test executable.

For `pull_request` `synchronize` events, component detection compares the previous PR head (`github.event.before`) with the new head instead of repeatedly comparing the PR base with the full current head. This is deliberate.

A build-workflow change itself requires all validation families, including both plugin builds.

### CMake / JUCE build cache

The VST3 jobs use `actions/cache` with separate OS/architecture keys to restore CMake/JUCE/libebur128 state and reusable objects.

Cache keys are tied to `CMakeLists.txt` and `.github/workflows/build.yml`. Every VST3 job still configures and builds; a cache hit is never evidence that the latest source compiled successfully.

The development workflow uses concurrency cancellation so a newer commit on the same PR/ref cancels an obsolete in-progress build run.

`mcp/ci_regression.py` must remain development-only and must not ship in beginner Releases.

Regression coverage must include at least:

- Full-profile legacy evidence remains valid;
- Eco/disabled families become unavailable, not misleading zeroes;
- parser indices and feature mask are correct;
- exact expected 32-tool registry;
- protocol-1.2 transport tail parsing;
- song memory survives LLM delay conceptually by retaining DAW-time bins independent of recent-window history;
- transport epochs remain separately addressable and do not merge after seek/loop/start;
- partial timeline aggregation does not falsely report complete coverage;
- lag/drop telemetry remains transparent;
- earlier mapping/project/temporal/masking/stereo/tonal/verification regressions remain intact.

## 11. Documentation impact review — mandatory

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
release/common/MCP-SETUP.md
release/common/INSTALL.en.md
release/common/INSTALL.zh-CN.md
.github/workflows/build.yml
.github/workflows/release.yml
mcp/cherry-studio.example.json
release installers
```

“No behavior change required” after inspection is acceptable; skipping the review is not.

README feature headings should describe the capability, not lead with historical version labels. Protocol/schema version numbers remain where semantically necessary.

## 12. Repository discipline

- Keep `mcp/server.py` as the only startup/PyInstaller entrypoint.
- Keep repository MCP source under `mcp/`; do not create a second `bridge/` source tree.
- Preserve host/plugin identity fields.
- Keep user-facing platform policy Windows x64 + macOS arm64 only.
- Keep LLM-facing Skill content English-only.
- Keep Release beginner-first and source-free while including `MCP-SETUP.md`.
- Keep evidence transparent and measurement-oriented.
- Prefer compact high-level LLM context over indiscriminate raw-frame/tool dumping.
- Do not claim CI, packaged-runtime, Release, or installer success without actual evidence.
- Do not merge a PR while required latest-head CI is failing or still pending.
