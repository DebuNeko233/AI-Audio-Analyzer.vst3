# AGENT.md

This file is the working contract for AI agents and maintainers modifying **AI Audio Analyzer**.

Read it before changing the repository. Keep implementation, tests, CI, Release packaging, installers, MCP behavior, Skill behavior, history, and public documentation consistent.

## 1. Project purpose and boundary

AI Audio Analyzer is a machine-readable audio measurement/perception/memory/verification layer for AI/LLM-assisted music-production workflows.

```text
AI Audio Analyzer
├─ VST3    measures audio + DAW transport context inside the DAW
├─ MCP     exposes measurement / song memory / structure / comparison / verification evidence
└─ Skill   teaches correct MCP use, latency handling and evidence semantics
```

Analyzer MCP is read/measure/remember/compare/verify oriented. DAW control is separate and currently paired with:

```text
https://github.com/rosasynthesiz/flstudio-mcp
```

Analyzer must **not** write artistic/technical DAW parameters. Real project inspection, plugin writes, project markers and actual host readback belong to the DAW-control MCP.

Do not encode one artistic mixing, mastering, harmony, arrangement, tuning, stereo, loudness or genre style into MCP or Skill.

The LLM is deliberately **not** part of the realtime measurement loop. Analyzer should continue observing while an Agent is thinking or using another tool, and expose enough retained DAW-time context for the Agent to reason later.

## 2. Repository-wide change rule

For **every code, workflow, protocol, MCP, packaging or behavior change**, inspect and update as appropriate:

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
.github/workflows/*.yml
mcp/cherry-studio.example.json
release/windows/*
release/macos/*
```

Not every file must change every time, but every relevant file must be **considered**. Never leave known stale tool counts, version strings, semantics or packaging lists.

All LLM-facing Skill content stays **English-only**.

## 3. Current architecture

### VST3

- JUCE 8.0.8, C++20, CMake.
- Current product version: **1.2.0**.
- Visible product name: `AI Audio Analyzer`.
- Internal target: `AIAnalyzer`.
- Bundle ID: `com.debuneko.aianalyzer`.
- Manufacturer/plugin IDs remain stable for DAW-project compatibility.
- Default OSC endpoint: `127.0.0.1:9855`.
- Audio callback writes to a preallocated SPSC FIFO.
- Audio callback does **not** run FFT, loudness, semantic analysis, OSC, MCP, file/network I/O, structure analysis, or verification orchestration.
- Audio callback may read the host Analysis Profile and DAW transport, then hand fixed-size scalar state to the worker through atomics only.
- Background worker owns FFT/analysis/state resets/latency estimation/OSC.
- `libebur128` provides LUFS / True Peak.
- Historical host-visible `Identify` remains parameter 1.
- Host-visible `Analysis Profile` remains parameter 2.

Do not casually change host/plugin identity fields or reorder historical host parameters.

### Adaptive Analysis Profiles

```text
Parameter ID: analysis_profile
Display name: Analysis Profile
0 Eco
1 Balanced
2 Mix
3 Full
```

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

`Full` is default for backward compatibility. Profiles change measurement computation only; they must never alter the audio signal.

Scheduling intent:

```text
Eco       no FFT / loudness work
Balanced  reduced FFT scheduling around network-update scale
Mix       hop-level FFT for temporal evidence
Full      Mix + lower-rate semantic analysis
```

### Transport-aware Song Memory

Protocol 1.2 appends DAW transport/data-quality context and MCP-side bounded Song Memory.

The VST3 reads `AudioPlayHead::PositionInfo` in `processBlock()` and hands transport state to the worker through atomics only.

The worker estimates the DAW-time coordinate of analyzed evidence using approximately:

```text
current FIFO backlog
+
half of the 4096-sample FFT window
```

This is for whole-song/section reasoning, not sample-accurate editing.

A `transport_epoch` is one **instance-local continuous playback pass**. Playback start, seek, loop jump, or another detected discontinuity creates a new epoch.

Epoch change invariant:

```text
producer detects discontinuity
→ publishes requested epoch atomically
→ worker acknowledges epoch
→ old queued FIFO content is discarded by consumer/worker
→ pass-dependent analysis state resets
→ transport publication for new epoch becomes valid
```

Transport must not be published under a new epoch until the worker has acknowledged it. Prefer a short coverage gap over `old audio + new DAW position` mislabeling.

On epoch change the worker resets/clears as appropriate:

```text
FFT/window continuity
Temporal continuity/accumulators
Semantic cache
LUFS-I / pass-max True Peak state when Loudness is enabled
```

Epoch counters are generated independently in every live VST3 instance. Never treat equal numeric epochs across instances as a permanent project-wide pass identity.

Song Memory:

```text
canonical bin size       1 second
coverage slot            100 ms
max retained bins        1200 / instance
max retained span        about 20 minutes / instance
query resolutions        1 / 2 / 5 / 10 / 15 / 30 seconds
scope                    running MCP session
```

Coverage aggregation must use observed coverage slots. Sparse canonical bins must **not** become false 100% coverage after coarse aggregation.

### Explainable song structure

The song-structure layer lives entirely in MCP and consumes retained Song Memory. It adds **no realtime DSP** and **no OSC fields**.

Current tools:

```text
audio_section_map()
audio_section_profile()
```

Current boundary detector:

```text
one-second reference Song Memory
→ robust feature normalization
→ multi-scale 2/4/8-second left/right comparison
→ explainable novelty components
→ adaptive threshold
→ local novelty peaks
→ minimum-section spacing
→ sections S01/S02/...
```

Evidence families include:

```text
cross-track activity
energy/loudness
spectral balance
chroma
stereo
dynamics
temporal change
```

Current recurrence layer:

```text
section summaries
→ transparent weighted similarity
→ neutral A/B/C/... recurring families
```

A/B/C family IDs are **not** semantic arrangement labels. Never automatically map:

```text
A = Intro
B = Verse
C = Chorus
```

Exact DAW markers, Playlist labels, pattern/arrangement metadata, MIDI/project annotations, or explicit user-provided structure win for exact naming.

Supporting tracks are aligned to the reference DAW-time range by the retained epoch/pass with the strongest overlapping coverage. Do **not** require equal instance-local epoch numbers.

Missing Song Memory is missing evidence. A coverage gap is **not silence** and must **not** become a structural boundary merely because data disappeared.

`map_id` is bounded MCP-session state, not a persistent project identifier.

### MCP

There is exactly one supported source/PyInstaller entrypoint:

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
mcp/section_tools.py      explainable boundaries / recurring families / section profiles
mcp/verification_tools.py controlled closed-loop verification sessions
mcp/ci_regression.py      repository-only synthetic MCP regression suite
```

The source directory is `mcp/`. Do not reintroduce a parallel `bridge/` source tree. “Bridge” may remain as a conceptual/runtime term and in historical tool names such as `audio_bridge_status`.

Current metadata:

```text
Product version       1.2.0
MCP_VERSION           1.2
OSC_PROTOCOL_VERSION  1.2
MCP tool count        34
```

### Skill

```text
skills/ai-analyzer-flstudio/
```

All LLM-facing files are English-only:

```text
SKILL.md
README-CHERRY-STUDIO.md
references/*.md
```

Skill scope includes MCP calling strategy, selector/mapping rules, profile selection, measurement validity, transport/Song Memory semantics, structure boundary/recurrence semantics, latency/data quality, performance telemetry, temporal/masking/stereo/tonal evidence, verification, and limitations.

Do not add fixed genre EQ recipes, LUFS targets, mandatory sidechain rules, stereo recipes, mastering chains, forced Verse/Chorus/Drop labels, key-change rules, harmony-edit rules, tuning recipes, or “metric X always means processor/action Y”.

## 4. Implemented evolution / history

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
- MCP source normalized under `mcp/`, with beginner-facing `MCP-SETUP.md`;
- transport-aware continuous playback epochs, Analyzer lag/drop telemetry and bounded DAW-time Song Memory;
- explainable section-scale novelty detection, neutral recurrence families and section-level project profiles built on Song Memory.

The section layer did **not** require a protocol or product version bump because it consumes existing 1.2 retained data.

Protocol evolution remains append-only. Current tail:

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

Indexes `0..149` must not be silently repurposed. New protocol fields, if ever needed, append after 149.

## 5. Why these milestones exist

Adaptive analysis addresses multi-instance compute cost.

Transport-aware Song Memory addresses LLM/tool/human latency: a model that only sees “latest few seconds” cannot reliably understand a whole song.

The structure layer addresses context selection: raw one-second timelines are too large and too low-level to be the default LLM representation of an entire song. Explainable boundaries and recurrence let the Agent reason in section-sized units first, then drill down selectively.

There is **no predefined next numbered stage/version**. Do not invent a new version merely to create momentum. Future milestones require an observed reliability gap, workflow need, compatibility issue, validated measurement improvement, or Release/install problem.

## 6. Measurement and compatibility rules

### Preserve semantics

Do not silently change metric meaning. If semantics change, update implementation, regressions, Skill, README, Release docs and AGENT together.

### `null` is not zero

Unavailable evidence remains unavailable.

### Feature mask is authoritative

Append-only compatibility fields can physically remain in a packet when a profile disables their computation. MCP parsing must invalidate disabled families.

```text
Loudness off  → LUFS / True Peak unavailable
Spectrum off  → spectrum validity false / arrays unavailable
Stereo off    → stereo validity false / deep stereo unavailable
Temporal off  → temporal validity false / temporal descriptors unavailable
Semantic off  → semantic validity false / chroma/harmonic unavailable
```

Transport/Core context may remain available under Eco.

### Keep independent concepts independent

Do not collapse:

```text
correlation + Side/Mid + negative-cross → one stereo score
chroma + entropy + tonal ranking + F0 → one music confidence score
verification topology + coverage + readback → one change-quality score
worker load + FIFO + lag + drops + age → one performance score
structure boundary + recurrence + semantic naming → one form-confidence score
```

### Heuristics and estimates must be labeled

Spectral overlap, temporal overlap, ERB evidence, negative-cross evidence, tonal-center ranking, harmonic alignment, transport-window alignment, FIFO-derived lag, section boundary strength and recurrence similarity are evidence/heuristics/estimates unless replaced by validated stronger models.

### Prefer exact project data for exact symbolic facts

If DAW/MIDI/project tooling exposes exact notes, chords, key metadata, tuning, markers, arrangement labels, routing or other symbolic state, use it for exact claims. Audio inference may complement it but must not silently override exact project data.

`audio_section_map()` may discover neutral structural recurrence. It does **not** make an exact Verse/Chorus/Bridge claim by itself.

## 7. Realtime, performance and transport rules

Any change to profiles, scheduling, FIFO behavior, transport handling, timeline memory or telemetry must review:

```text
1. realtime callback work
2. host parameter compatibility / state restoration
3. actual feature computation skipped, not merely hidden
4. MCP validity/null behavior for disabled families
5. profile-transition state reset semantics
6. transport-discontinuity / epoch reset semantics
7. FIFO backlog / staleness / data-age behavior
8. Windows x64 + macOS arm64 compilation
9. MCP synthetic regressions
10. Skill / README / Release impact
```

Realtime callback rules:

```text
allowed: cheap host parameter/transport reads + atomic scalar handoff + FIFO push
forbidden: locks, allocation, Thread::notify(), FFT, loudness, semantic analysis, structure analysis, OSC/network, file I/O, MCP work
```

The audio callback still does not wake the worker.

Current worker scheduling/measurement invariants:

```text
hop size                    1024 samples
FFT                          4096 samples
OSC update                   about 10 Hz
worker short-FIFO wait       bounded 1–20 ms
true peak read               every loudness-enabled hop
LUFS-S / LUFS-I polling      about every 100 ms
```

`tests/WorkerSchedulingTests.cpp` must continue protecting scheduling and True Peak accumulation semantics.

### Profile transitions must not bridge unmeasured gaps

When a disabled family is re-enabled:

- Loudness state is rebuilt;
- Temporal previous-spectrum/RMS and aggregate state are cleared;
- Semantic cache is cleared.

### Telemetry semantics

- `worker_load_ratio` = background Analyzer worker busy ratio, not DAW audio-thread CPU.
- `fifo_fill_ratio` = queued Analyzer input capacity; sustained growth can indicate lag.
- `estimated_analysis_lag_ms` = FIFO + half-window estimate, not total Agent latency.
- `dropped_blocks` = cumulative FIFO push failures; nonzero means some audio was not analyzed.
- `data_age_seconds` = wall-clock age of retained evidence; old historical evidence may still be the requested evidence.
- `coverage_ratio` = observed retained time coverage, not confidence probability.
- `fft_runs_per_second` / `semantic_runs_per_second` are observed scheduler rates, not guarantees.

## 8. Song Memory and structure invariants

### Song Memory

High-level tools:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline()
```

Do not persist/read every 10 Hz OSC frame merely to give the LLM more tokens. The purpose is compact, latency-resilient musical context.

### Section structure

High-level tools:

```text
audio_section_map()
audio_section_profile()
```

Required invariants:

```text
missing coverage != silence
missing coverage != structural boundary
family A/B/C != semantic Verse/Chorus/Drop
boundary strength != calibrated probability
map_id != persistent project ID
same numeric epoch across instances != same project pass
```

Default cross-instance section alignment must prefer overlapping DAW-time coverage rather than epoch-number equality.

Regression coverage must include at least one synthetic arrangement with repeated structure, currently `A → B → A`, and at least one end-to-end case where supporting tracks use different epoch numbers from the reference.

## 9. Closed-loop verification rules

Analyzer MCP owns measurement, binding evidence, Before/After capture, comparability checks, deltas and audit context.

External DAW-control MCP owns real writes and actual host-state readback.

Canonical flow:

```text
audio_begin_verification()
→ confirm ready_for_external_change
→ external DAW write
→ actual host readback
→ replay comparable passage
→ audio_complete_verification()
```

`controlled_comparison=true` means technical comparability only.

`closed_loop_complete=true` means comparability plus caller-supplied actual host readback.

Neither means the change is artistically better.

Current verification remains recent-window based; do not claim transport-anchored same-range verification exists until it actually does.

## 10. Release contract

Release is for users who may have never programmed.

Supported user platforms:

```text
Windows x64
macOS Apple Silicon arm64
```

Final package rules:

- one ZIP per platform;
- no nested ZIP;
- PyInstaller **one-file** (`-F`) MCP runtime;
- no MCP `.py` source;
- no `requirements.txt`;
- no venv;
- no PyInstaller `_internal`;
- no developer-only `cherry-studio.example.json`;
- include VST3, standalone MCP executable, Skill, beginner docs, installer and LICENSE;
- generated client config uses the actual absolute installed MCP executable path.

Windows installed MCP path:

```text
%LOCALAPPDATA%\AI Audio Analyzer\mcp\ai-audio-analyzer-mcp.exe
```

macOS installed MCP path:

```text
~/Library/Application Support/AI Audio Analyzer/mcp/ai-audio-analyzer-mcp
```

Release workflows must include every imported MCP source module in validation/packaging. Adding a module such as `section_tools.py` requires CI and Release source lists to be reviewed immediately.

## 11. CI and merge rules

Never merge while the **latest PR head** has pending or failing required CI.

Before merge:

```text
1. fetch current PR head SHA
2. fetch workflow run(s) for exactly that SHA
3. confirm latest-head required jobs are completed successfully
4. only then merge
```

Relevant checks include as applicable:

```text
MCP source compile
exact tool registry self-test
synthetic MCP regressions
section boundary/recurrence regressions
Release installer validation
Windows x64 VST3 build
macOS arm64 VST3 build
WorkerScheduling / True Peak tests
PyInstaller/runtime smoke test in Release workflow
```

Do not claim CI is green based on an older commit.

## 12. Roadmap rule

Roadmap is capability-driven, not version-number-driven.

Implemented foundation:

```text
measurement → deterministic identity → project overview
→ temporal/masking/stereo/tonal evidence
→ controlled verification
→ adaptive analysis
→ DAW Transport + Song Memory + latency/data-quality model
→ explainable section boundaries + recurring families + section profiles
```

Potential future capability gaps may include, only when justified by real need:

```text
track story across sections
section-aware mix relationships / routing graph
transport-anchored same-range verification
change ledger / Agent cursor-digest
whole-pass mastering distributions (LRA/PLR/percentiles)
energy-aware stereo/mono-fold evidence
reference-track comparison
persistent project cache with stable external project ID
stronger tonal representation (HPCP/CQT/tuning)
offline fast scan
optional learned music embeddings if explainable structure evidence proves insufficient
```

Do not predeclare the next product version or stage from this list.

## 13. Documentation language and evidence discipline

Public docs may be English and Chinese as appropriate. LLM-facing Skill files remain English-only.

Never present these as Analyzer-measured facts without an exact external source:

- “this is definitely the Chorus/Verse/Drop” from A/B/C recurrence alone;
- “this needs EQ/sidechain/compression” from masking evidence alone;
- “this must hit X LUFS” as a universal rule;
- “this is certainly the song key” from tonal-center ranking;
- “this F0 is certainly the played note”;
- “Full is higher audio quality than Eco”;
- “worker_load_ratio is DAW CPU”;
- “controlled_comparison means After is better”.

Prefer transparent evidence plus limitations over opaque quality scores or universal processing rules.
