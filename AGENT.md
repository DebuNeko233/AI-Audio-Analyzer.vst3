# AGENT.md

This file is the working contract and long-term architecture source of truth for AI agents and maintainers modifying **AI Audio Analyzer**.

Read it before changing the repository. Keep implementation, tests, CI, Release packaging, installers, MCP behavior, Skill behavior, history, roadmap state, and public documentation consistent.

---

## 1. System north star

AI Audio Analyzer is not intended to become only a spectrum meter or an "AI EQ plugin". It is the sensory / measurement / memory / verification layer of a larger AI-assisted mixing system.

The long-term closed loop is:

```text
Observe
-> Understand
-> Reason
-> Plan
-> Act
-> Measure Again
-> Evaluate
-> Accept / Retry / Rollback
```

Equivalent engineering flow:

```text
Measure
-> Interpret
-> Plan
-> external DAW/plugin change
-> Measure Again
-> Compare Before/After
-> Keep / Reject / Rollback / Continue
```

The current repository primarily owns the **Observe / Remember / Structure / Compare / Verify** side of this loop. General DAW/plugin writes remain external.

Do not claim that a future layer already exists merely because it appears in this roadmap.

### Long-term system shape

```text
User Intent
    |
    v
Mixing LLM / Agent
    |---- Mixing Skill / knowledge
    |---- exact project state from DAW-control MCP
    |---- optional Reference profile
    v
Planner / orchestration
    |
    +---- AI Audio Analyzer MCP  -> measurements / memory / structure / verification
    +---- FL Studio MCP          -> exact project inspection + real writes/readback
    +---- optional numeric optimizer / AI service
    v
DAW playback / render
    |
    v
AI Audio Analyzer VST3 instances
    |
    v
structured evidence
    |
    v
LLM evaluation
```

The architecture should remain modular so future models or optimizers can be added without redesigning the realtime Analyzer.

---

## 2. Three-brain boundary

The final system is intentionally separated into three intelligence layers.

### 2.1 Semantic brain - LLM / Agent

Responsible for contextual and semantic reasoning such as:

```text
"the vocal should feel more forward"
"the drop should open up more"
"the low end should feel tighter"
"move toward the user's chosen reference direction"
```

The LLM combines measurement evidence with user intent, arrangement context, exact DAW state, references, and mixing knowledge.

It must not be placed in the realtime audio callback.

### 2.2 Numeric brain - future Mixing Optimizer

Future external service for bounded numerical optimization or initial parameter proposals, for example:

```text
gain
parametric EQ
compressor
expander
reverb
stereo width / panning
other supported differentiable DSP parameters
```

This layer may eventually use differentiable DSP or learned automix models, but it is **not current Analyzer VST3 functionality**.

Keep it outside the realtime VST3. Do not embed Python, PyTorch, large neural models, or optimizer orchestration into the Analyzer audio callback.

### 2.3 Sensory system - AI Audio Analyzer

Responsible for the factual question:

```text
What is actually happening in the audio and where in the DAW timeline is it happening?
```

Analyzer should prefer reliable structured measurements, retained evidence, explainable heuristics, and explicit uncertainty/coverage over subjective automatic judgments.

---

## 3. Hard control boundary

Analyzer MCP is **not** a general DAW-control MCP.

The only allowed Analyzer-owned write today is:

```text
Analysis Profile
parameter_id = analysis_profile
Eco / Balanced / Mix / Full
```

This exception is allowed because it changes Analyzer measurement computation only and does **not** alter the audio signal.

Analyzer MCP must **not** use this exception as precedent to write:

```text
EQ
compression
gain
pan
routing
synth parameters
automation
arrangement/project state
other plugins
other artistic/technical DAW parameters
```

Those writes, exact project inspection, Playlist/marker metadata, plugin parameter readback, transaction/rollback behavior, and project mutation remain the responsibility of the real DAW-control layer.

Current companion DAW-control project:

```text
https://github.com/rosasynthesiz/flstudio-mcp
```

Do not duplicate a full FL Studio control implementation inside Analyzer MCP.

---

## 4. Repository-wide change rule

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

Not every file must change every time, but every relevant file must be considered.

Never leave known stale:

```text
tool counts
version strings
protocol semantics
control boundaries
roadmap state
packaging lists
Release claims
```

All LLM-facing Skill content stays **English-only**.

The plugin GUI may be bilingual. Stable technical identifiers such as host parameter IDs, OSC field names, MCP tool names, schema keys, and protocol names remain language-independent.

---

## 5. Current metadata on the P2 development branch

```text
Product version             1.2.0
MCP_VERSION                 1.2
OSC analysis protocol       1.2
Analyzer control revision   1
MCP tool count              38
```

Do not invent a product/MCP/OSC version merely because a derived MCP reasoning feature is added. Version bumps require a real compatibility or release reason.

There is no artificial numbered implementation stage/version beyond the roadmap priorities in this document.

---

## 6. VST3 realtime architecture

- JUCE 8.0.8, C++20, CMake.
- Visible product name: `AI Audio Analyzer`.
- Internal target: `AIAnalyzer`.
- Bundle ID: `com.debuneko.aianalyzer`.
- Default measurement OSC endpoint: `127.0.0.1:9855`.
- Audio callback writes to a preallocated SPSC FIFO.
- Background worker owns FFT/analysis/state resets/latency estimation/measurement OSC.
- `libebur128` provides LUFS / True Peak.

Historical host-visible parameter order must remain:

```text
1  Identify
2  Analysis Profile
```

### Realtime callback rules

Allowed:

```text
cheap host parameter reads
cheap DAW transport reads
atomic scalar handoff
FIFO push
```

Forbidden:

```text
locks
allocation
Thread::notify()
FFT
loudness processing
semantic analysis
song structure analysis
relationship analysis
network/control parsing
file I/O
MCP work
Python/model inference
optimizer work
```

The LLM is deliberately **not** part of the realtime measurement loop.

Analyzer should continue measuring while the Agent is thinking, calling another tool, or waiting for a DAW operation.

### Current measurement scheduling invariants

```text
hop size                    1024 samples
FFT                         4096 samples
measurement OSC update      about 10 Hz
worker short-FIFO wait      bounded 1-20 ms
true peak read              every loudness-enabled hop
LUFS-S / LUFS-I polling     about every 100 ms
```

---

## 7. Adaptive Analysis Profiles

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

Profiles affect measurement computation only and must never alter the audio signal.

`Full` remains the compatibility default.

When a disabled family is re-enabled, rebuild/reset its state rather than pretending measurement continued through the disabled gap.

The LLM should use the lowest profile that provides the evidence required for the current task instead of leaving every project instance at Full.

---

## 8. Analyzer-owned local control protocol

Current control revision:

```text
1
```

This is separate from OSC analysis-frame protocol 1.2.

Purpose:

```text
Analyzer MCP
-> request Eco / Balanced / Mix / Full
-> target live Analyzer runtime UUID
-> VST3 applies host-visible analysis_profile
-> explicit ACK
```

Security/scope invariants:

- loopback only (`127.0.0.1`);
- no remote-network control;
- Analysis Profile only;
- runtime UUID must match;
- no control processing on audio thread;
- network callback validates/queues only;
- actual host parameter mutation occurs through JUCE message-thread handling;
- ACK is request-scoped;
- stopped transport must not prevent ACK;
- old VST3 builds without the receiver must fail by timeout, never optimistic success.

Keep separate:

```text
control_acknowledged
telemetry_confirmed
```

ACK proves the live VST3 accepted/applied the profile request. Telemetry confirmation requires a fresh measurement frame reporting the requested profile.

Deterministic candidate-port regression must remain identical in C++ and Python.

---

## 9. Measurement / interpretation invariants

### `null` is not zero

Unavailable evidence remains unavailable.

### Missing coverage is not silence

Never convert missing or sparse retained Song Memory into inactivity, mute state, a structure boundary, or a conflict disappearance.

### Feature mask is authoritative

Disabled feature families must be invalidated downstream even if compatibility fields still physically exist in an append-only packet.

### Heuristics must remain labelled as heuristics

Examples:

```text
spectral overlap
temporal overlap
ERB masking evidence
negative-cross evidence
tonal-center ranking
harmonic alignment
transport-window alignment
section boundary strength
recurrence similarity
Track Story deltas
relationship shortlist_priority
```

These are evidence/estimates, not calibrated probabilities unless a future validated model explicitly proves otherwise.

### Do not collapse independent evidence into one score

Do not create one synthetic score from independent concepts such as:

```text
stereo correlation + Side/Mid + negative-cross
Track Story energy + spectrum + stereo + temporal
structure boundary + recurrence + semantic naming
relationship overlap + level + stereo
worker load + FIFO + lag + drops
```

### Exact project data wins for exact symbolic facts

If DAW/MIDI/project tooling exposes exact:

```text
track names
markers
section labels
routing
plugin chain
parameter values
MIDI notes/chords
```

use that data for exact claims. Audio inference may complement it but must not silently override it.

---

## 10. OSC analysis protocol 1.2

Analysis address:

```text
/aianalyzer/frame
```

Protocol is append-only.

Existing indexes `0..149` must never be silently repurposed.

Current tail:

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

If a future measurement field is needed, append after 149. Do not overload local control or MCP-derived reasoning into analysis-frame indexes.

---

## 11. Current measurement/perception capabilities

Current VST3/MCP evidence includes:

```text
signal validity
Sample Peak / RMS / Crest
LUFS-S / LUFS-I / True Peak
32-band spectrum
spectral centroid / rolloff / flatness
full-band + frequency-dependent stereo correlation
Mid / Side evidence
Side spectrum / band Side-Mid relation
negative-cross evidence
temporal flux / RMS rise / low-band temporal energy
12-bin chroma
single-F0 harmonic-alignment evidence
DAW transport / PPQ / BPM / time signature
transport epochs
estimated analysis lag
dropped blocks
worker/FIFO telemetry
```

Do not automatically infer a track role such as Kick/Bass/Vocal solely from these measurements.

Future exact Track Role should prefer project metadata or explicit user context.

---

## 12. Transport-aware Song Memory

A `transport_epoch` is one **instance-local continuous playback pass**.

Playback start, seek, loop jump, or detected discontinuity creates a new epoch.

Epoch IDs are generated independently by each VST3 instance. Equal numeric epoch values across tracks are not project-global pass identity.

Song Memory:

```text
canonical bin size       1 second
coverage slot            100 ms
max retained bins        1200 / instance
max retained span        about 20 minutes / instance
query resolutions        1 / 2 / 5 / 10 / 15 / 30 seconds
scope                    running MCP session
```

Supporting tracks must be aligned by overlapping DAW-time coverage, not by requiring equal epoch numbers.

Transport coordinates are for whole-song/section reasoning, not sample-accurate editing.

---

## 13. Structure, Track Story, and P2 relationships

These reasoning layers live entirely in MCP and add no realtime DSP or analysis-frame fields.

Current/active tools:

```text
audio_section_map()
audio_section_profile()
audio_track_story()
audio_section_relationships()
```

### Neutral structure semantics

A/B/C/... are recurring-family labels only.

Never automatically map:

```text
A = Intro
B = Verse
C = Chorus
```

Exact DAW markers/labels or explicit user structure are authoritative for semantic names.

### Track Story

Summarizes one track across sections with:

```text
activity
RMS / LUFS-S / crest
spectral centroid / coarse regions
stereo correlation / width
temporal flux
chroma / pitch-class evidence
coverage / lag / drops
adjacent deltas
same-family per-dimension variation
relative extrema
```

It must not create one track-quality or consistency score.

### Section-aware Mix Relationships

P2 uses a bounded shortlist to identify pairs worth deeper inspection in particular sections/families.

Current P2 principles:

- Master excluded by default;
- bounded track candidates per section;
- bounded project-level returned pair count;
- requires sufficient retained coverage;
- shortlists using common activity plus coarse spectral-shape, level and stereo-width evidence;
- preserves directional B-minus-A descriptors where valid;
- reports family presence/absence and adjacent relationship changes;
- does not call the pair a confirmed masking problem;
- does not recommend EQ/sidechain/compression automatically.

`shortlist_priority` means **inspection priority only**. It is not:

```text
masking probability
mix-problem probability
audibility probability
quality score
processing recommendation
```

Detailed current masking/stereo/temporal pair tools are recent-window based. Until transport-anchored same-range pair analysis exists, the Agent must replay/select the relevant section before using those deeper tools as evidence for that section.

---

## 14. Verification and future mixing transaction boundary

Current controlled verification is:

```text
Before baseline
-> external DAW-control MCP write
-> actual host readback
-> comparable After capture
-> comparability guardrails
-> After-minus-Before deltas
```

Current verification remains recent-window based, not exact transport-anchored same-range verification.

`controlled_comparison=true` means technical comparability only.

`closed_loop_complete=true` additionally requires caller-supplied actual host readback.

Neither means the artistic change is better.

### Future Mixing Transaction - NOT IMPLEMENTED

Long-term system should support an external project-control transaction concept:

```text
Begin
-> Snapshot
-> Apply one or more DAW/plugin changes
-> Measure
-> Compare
-> Commit or Rollback
```

Possible future API concepts:

```text
begin_mix_transaction()
commit_mix_transaction()
rollback_mix_transaction()
```

These names are conceptual only until a real implementation exists.

Transaction state belongs with the layer that can actually restore DAW/plugin parameters. Analyzer may provide measurement verification, but Analyzer MCP must not become a hidden general project writer.

---

## 15. High-level API strategy

Do not force the LLM to call dozens of tiny APIs when a stable higher-level summary can answer the first question.

Preferred reasoning pattern:

```text
high-level project/song/section summary
-> identify relevant track/section/pair
-> drill into specialized evidence only where needed
```

Current high-level building blocks include:

```text
audio_project_status()
audio_song_status()
audio_song_overview()
audio_section_map()
audio_section_profile()
audio_track_story()
audio_section_relationships()
```

Future facade concepts such as:

```text
analyze_mix()
compare_mix_state()
```

may aggregate existing evidence to reduce token/tool overhead, but are **not implemented merely because they are documented here**.

Any future `analyze_mix()` should expose evidence and warnings with provenance/coverage, not convert the whole mix into opaque "detected problems" without explainable supporting data.

---

## 16. Reference Engine - future

Reference comparison is a future system layer, not current functionality.

Desired architecture:

```text
Target Mix -> Analyzer profile
Reference  -> compatible Analyzer profile
             |
             v
level-aware / section-aware comparison
             |
             v
LLM interpretation
```

Reference comparison should operate on structured evidence such as:

```text
spectral balance
dynamics distributions
stereo evidence
loudness
section energy/contrast
```

Do not implement naive logic such as:

```text
Reference has +2 dB at 8 kHz
-> therefore add +2 dB at 8 kHz to Master
```

The LLM must still decide which track or processing stage, if any, should change.

Reference direction is context, not an automatic processing recipe.

---

## 17. Numeric optimizer / learned automix - future

Do not prioritize a large Automatic Mixing Model before the perception-control-verification loop is stable.

Preferred future order:

```text
stable closed loop first
-> reference / transactions / persistent state
-> optional numeric optimizer
-> optional learned initial-guess model
-> only later a custom Mix Model if evidence justifies it
```

A future automix model should preferably provide bounded **initial guesses** or proposals rather than replace LLM reasoning.

Example role:

```text
multitrack
-> automix model
-> initial gain/pan/processor parameters
-> LLM contextual refinement
-> real DAW write/readback
-> Analyzer verification
```

Differentiable DSP / optimizer code belongs in an external Python/AI service, not the Analyzer VST3.

---

## 18. Research-project lessons / dependency caution

The project plan may learn architectural ideas from external projects such as:

```text
hellyee
  Agent loop, MCP/Core separation, meter readback, Measure->Act->Measure, Skill, Fake DAW/testing ideas

automix-toolkit
  differentiable mixing console, automix training/evaluation, parameter-estimation ideas

FxNorm-Automix
  effect-normalization and automatic-mixing training-data strategy

Diff-MST
  reference-guided mixing / mixing-style-transfer research direction

dasp-pytorch
  differentiable DSP / numerical optimization ideas
```

Do not copy a research implementation merely because the architecture is useful.

Before importing code, models, data, weights, or substantial implementation from any external project, verify its **current license** and commercial compatibility independently.

The planning note currently flags Diff-MST as non-commercial/share-alike research code; treat that as a reason to re-check the license and prefer independent reimplementation of ideas if future commercial distribution is possible.

---

## 19. MCP source layout

Stable source/PyInstaller entrypoint:

```text
mcp/server.py
```

Do not create version-numbered startup files.

Current P2 development layout:

```text
mcp/server.py
mcp/analyzer_core.py
mcp/project_tools.py
mcp/temporal_tools.py
mcp/masking_tools.py
mcp/stereo_tools.py
mcp/semantic_tools.py
mcp/performance_tools.py
mcp/control_tools.py
mcp/song_tools.py
mcp/section_tools.py
mcp/track_story_tools.py
mcp/section_relationship_tools.py
mcp/verification_tools.py
mcp/ci_regression.py
mcp/relationship_regression.py
```

`mcp/ci_regression.py` and `mcp/relationship_regression.py` are repository/CI tests and must not be shipped in beginner Releases.

The source directory is `mcp/`. Do not reintroduce a parallel `bridge/` source tree.

---

## 20. Skill boundary

Skill explains:

```text
professional knowledge
strategy
evidence interpretation
tool calling order
limitations
verification discipline
```

MCP provides:

```text
facts
state
measurements
structured evidence
safe APIs
Analyzer-owned profile control
```

The real DAW-control layer provides actual project/plugin writes.

Do not encode one mandatory genre/style recipe into Analyzer MCP or its core Skill.

Genre-specific knowledge may exist as optional knowledge/reference material, but must not silently override user intent, exact reference context, or measured evidence.

---

## 21. CI and merge rules

Never merge a PR while its latest relevant head has pending or failing CI.

For VST3/control code, verify at least:

```text
Windows x64 VST3 build
macOS Apple Silicon arm64 VST3 build
WorkerSchedulingTests
```

For MCP changes, verify:

```text
py_compile
AI_ANALYZER_SELF_TEST=1 python mcp/server.py
mcp/ci_regression.py
feature-specific synthetic regression when present
exact tool registry count
```

For P2, `mcp/relationship_regression.py` must pass.

Path-aware synchronize runs may legitimately skip expensive jobs on later docs-only commits. Record both the last implementation head with full relevant green CI and the final docs-only head with its own green path-aware CI.

When merging, use exact expected PR head SHA guard.

Do not merge unless the user explicitly asks to merge.

---

## 22. Release packaging rules

GitHub Release is beginner-first.

Supported user platforms:

```text
Windows x64
macOS Apple Silicon arm64
```

Requirements:

- one final ZIP per platform;
- no nested ZIP;
- no MCP Python source in user package;
- no `requirements.txt`;
- no venv;
- no PyInstaller `_internal`;
- no developer source config examples;
- MCP runtime built with PyInstaller `-F` / onefile;
- package includes VST3, one-file MCP runtime, Skill, setup/install docs, VERSION, LICENSE, installer scripts.

Canonical MCP build shape:

```text
python -m PyInstaller -F \
  --name ai-audio-analyzer-mcp \
  --paths mcp \
  --collect-all mcp \
  --collect-all pythonosc \
  mcp/server.py
```

Current install destinations:

```text
Windows:
%LOCALAPPDATA%\AI Audio Analyzer\mcp\ai-audio-analyzer-mcp.exe

macOS:
~/Library/Application Support/AI Audio Analyzer/mcp/ai-audio-analyzer-mcp
```

Current macOS Release is Apple Silicon arm64 and ad-hoc signed unless the workflow explicitly changes to Developer ID notarization.

---

## 23. Implemented evolution / history

Implemented or currently merge-ready milestones include:

- loudness / True Peak / stereo correlation;
- signal validity and runtime UUID identity;
- Identify mapping to FL Mixer Track/Slot;
- project overview and Snapshot A/B;
- temporal evidence;
- ERB-style masking evidence;
- deeper Mid/Side / Side-spectrum / negative-cross evidence;
- chroma / tonal-center / harmonic evidence;
- controlled Before/After verification around external writes/readback;
- adaptive Eco/Balanced/Mix/Full measurement profiles;
- worker/FIFO/lag/drop telemetry;
- transport-aware continuous playback epochs;
- bounded DAW-time Song Memory;
- explainable section novelty and neutral recurrence families;
- section-level project profiles;
- bilingual plugin GUI and transport/health visibility;
- Analyzer-owned loopback Analysis Profile control with explicit ACK;
- Track Story across sections/families (PR #19 merge-ready, not DONE until merged);
- bounded section-aware Mix Relationships currently active on dependent PR #20.

---

## 24. Ordered P1-P10 roadmap

`AGENT.md` is the source of truth for roadmap state. Do not rely only on conversation memory.

Status vocabulary:

```text
ACTIVE       implementation in progress on a development branch
QUEUED       near-term candidate after active dependency
LATER        useful but not near-term
BLOCKED      requires unresolved design or external capability
DONE         implemented, documented, regression-covered, and merged to main
```

### P1 - Track Story across sections

Status: **ACTIVE / IMPLEMENTATION COMPLETE / MERGE-READY** on PR #19.

Do not mark DONE until merged to `main`.

### P2 - Section-aware Mix Relationships

Status: **ACTIVE** on dependent Draft PR #20.

Goal: bounded, coverage-aware relationship shortlisting across sections/families without O(N^2) output explosion or automatic processing prescriptions.

Completion requires:

- bounded project-level output;
- section/family context;
- explicit per-track coverage/activity evidence;
- directional evidence where meaningful;
- missing coverage cannot create false relationship changes;
- synthetic family appearance/disappearance regression;
- current tool count/docs/Release workflow synchronized;
- full relevant CI green after #19 dependency is resolved.

### P3 - Exact DAW context integration

Status: **BLOCKED** on companion DAW-control capability/contract details.

Target exact context:

```text
project identity
stable Mixer track IDs/names
plugin chain / slot identity
routing / sends
Playlist markers / labels
clips / patterns where available
MIDI/symbolic notes where available
actual plugin parameter readback
```

Exact project metadata wins over audio inference for exact symbolic claims.

### P4 - Transport-anchored same-range verification

Status: **QUEUED**.

Goal:

```text
Before exact DAW range X..Y
-> external change + host readback
-> After exact same DAW range X..Y
-> comparable deltas
```

This also enables deeper historical section pair analysis without requiring manual replay for every specialized tool.

### P5 - Persistent project memory + stable external identity

Status: **BLOCKED** until P3 provides trustworthy identity.

Persist candidates:

```text
project / track mappings
section maps
Track Stories
relationship summaries
analysis digests
verification/change history
coverage/schema metadata
```

Runtime UUID and instance-local epoch must never become permanent project IDs.

### P6 - Dynamics / mastering distributions

Status: **QUEUED**.

Target evidence:

```text
RMS/LUFS percentiles
peak/crest distributions
LRA
PLR-like evidence when semantics are valid
section-aware dynamic range
transient density/distribution
```

Do not claim whole-song values from incomplete coverage.

### P7 - Energy-aware mono-fold / stereo compatibility evidence

Status: **QUEUED**.

Target evidence:

```text
mono-fold RMS delta
bandwise energy loss
mono-fold peak delta
spectral delta after L+R fold
```

Keep these separate from correlation / Side-Mid / negative-cross metrics.

### P8 - Reference-track comparison

Status: **LATER**, but part of the long-term Reference Engine.

Must be level-aware, section-aware, coverage-aware, and descriptive rather than an automatic copy/match recipe.

### P9 - Stronger tonal representation

Status: **LATER**.

Candidate upgrades:

```text
HPCP
CQT/log-frequency representation
tuning offset estimation
multi-pitch/chord evidence only if justified
```

Exact MIDI/project symbolic data remains authoritative when available.

### P10 - Offline fast scan

Status: **LATER / BLOCKED** on render/input workflow design.

Potential paths:

```text
external offline analyzer executable/library
DAW render handoff from companion control MCP
compatible reuse of Song/Section/Relationship schemas
```

Never put render orchestration or file decoding into the realtime audio callback.

---

## 25. Higher-level system phases after/beside P1-P10

The uploaded system plan defines a broader product sequence. Treat this as a system-level map, not a replacement for the concrete P1-P10 repository backlog.

### System Phase A - stabilize the closed loop

Priority:

```text
Analyzer
-> MCP
-> LLM
-> external Plugin/DAW Control
-> Analyzer Feedback
```

Goal: the Agent can make a real change, read it back, and measure again.

### System Phase B - perception + safety

Build on:

```text
Track Relationships
Section Timeline / Track Story
Before/After same-range verification
Mixing Transaction
Rollback
persistent change history
```

Goal: move from "can operate" to "can verify and recover".

### System Phase C - Reference Engine

Add structured reference profiles and target-vs-reference evidence.

Goal: support "move in the direction of this reference" without naive Master matching.

### System Phase D - Numeric Mixing Optimizer

Add an external differentiable-DSP / optimization service for bounded parameter initialization or local numerical search.

Goal: reduce random parameter guessing while preserving LLM context and real DAW verification.

### System Phase E - learned Mix Model

Only after the previous loop is reliable, consider training:

```text
Audio Encoder
Track Relationship Model
Mix Parameter Model
```

Possible inputs may include:

```text
multitrack audio
user intent
genre/context
reference profile
project state
```

Possible output: bounded parameter proposals, not unverified direct control.

---

## 26. Current genuine limitations

Keep these explicit in code/docs/Skill:

- transport time/PPQ are approximate, not sample-accurate;
- historical tempo-map reconstruction is not implemented;
- Song Memory is MCP RAM/session-scoped;
- section maps / Track Stories / relationships are session-scoped;
- section detector works at one-second retained-summary scale;
- no automatic semantic Verse/Chorus/Drop naming by design;
- no exact FL Studio marker/Playlist metadata integration yet;
- runtime UUID is session identity, not project identity;
- epoch IDs are instance-local;
- estimated analysis lag excludes OSC/MCP/LLM/DAW-control latency;
- no exact routing graph until P3 exact DAW context exists;
- current detailed pair tools are recent-window based;
- Mixing Transaction / rollback are not implemented;
- Reference Engine is not implemented;
- numeric optimizer / dasp / automix model service is not implemented;
- no custom learned Mix Model is implemented;
- offline fast scan is not implemented.

Never present a roadmap item as current capability.

---

## 27. Final product principle

The project should ultimately support a professional engineering loop rather than merely software control:

```text
professional mixing knowledge
+
realtime / retained audio perception
+
whole-song structure understanding
+
multi-track relationship understanding
+
reference analysis
+
DAW/VST control
+
optional numeric optimization
+
Before/After verification
+
rollback
+
long-term Mix State
```

The priority today remains:

```text
LLM
-> perception
-> reasoning
-> real operation
-> re-perception
-> verification
```

Stabilize that loop first. Future neural models, differentiable DSP, audio encoders, or specialized audio LLMs should plug into this architecture as optional modules rather than forcing a redesign of the Analyzer core.
