# AGENT.md

This file is the working contract and long-term architecture source of truth for AI agents and maintainers modifying **AI Audio Analyzer**.

Read it before changing the repository. Keep implementation, tests, CI, Release packaging, installers, MCP behavior, Skill behavior, history, roadmap state, and public documentation consistent.

---

## 1. System north star

AI Audio Analyzer is the measurement / memory / structure / comparison / verification layer of a larger AI-assisted mixing system.

Long-term loop:

```text
Observe
-> Understand
-> Reason
-> Plan
-> external DAW/plugin action
-> Measure Again
-> Evaluate
-> Keep / Retry / Rollback
```

The Analyzer repository primarily owns:

```text
Observe
Remember
Structure
Compare
Verify
```

General DAW/plugin writes remain external.

The current companion DAW-control project is:

```text
https://github.com/rosasynthesiz/flstudio-mcp
```

Do not duplicate a full FL Studio control implementation inside Analyzer MCP.

---

## 2. Three-layer intelligence boundary

### Semantic layer - LLM / Agent

Owns contextual reasoning such as user intent, arrangement interpretation, reference direction, and whether a measured change is desirable.

### Numeric layer - future optimizer

A future external service may propose bounded numerical settings or initial guesses for gain/EQ/dynamics/stereo/reverb/etc. Do not embed this in the realtime VST3 callback.

### Sensory layer - AI Audio Analyzer

Owns factual structured evidence:

```text
what happened in the audio
where it happened in DAW time
what evidence was retained
whether two measurements are technically comparable
```

Prefer explicit coverage/uncertainty over subjective automatic judgments.

---

## 3. Hard control boundary

Analyzer MCP is **not** a general DAW-control MCP.

The only Analyzer-owned write is:

```text
parameter_id = analysis_profile
Eco / Balanced / Mix / Full
```

That exception is allowed because it changes Analyzer measurement computation only and does not alter the audio signal.

Analyzer MCP must not use it as precedent to write:

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

Those writes, exact project inspection, marker/Playlist metadata, plugin-state readback, transactions, rollback, and project mutation belong to the real DAW-control layer.

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

Never knowingly leave stale:

```text
tool counts
version strings
protocol semantics
control boundaries
roadmap state
packaging lists
Release claims
self-description/resource contracts
```

All LLM-facing Skill/reference content stays **English-only**.

The plugin GUI may be bilingual. Stable technical identifiers remain language-independent.

---

## 5. Current branch metadata

Current metadata on the P6a branch:

```text
Product version             1.2.0
MCP_VERSION                 1.2
OSC analysis protocol       1.2
Analyzer control revision   1
MCP tool count              43
MCP guide resources         14
```

History:

- P4a merged via PR #29 with 41 tools.
- Project Identity Disclosure merged via PR #31 and raised the tool count to 42.
- MCP Self-Describing API merged via PR #32 and added Server instructions, complete Tool descriptions, and 13 Skill-backed Guide Resources without adding another Tool.
- P6a Dynamics Distribution is active on PR #33; it adds `audio_dynamics_distribution()` and `aianalyzer://guide/dynamics-evidence`, raising the branch to 43 tools / 14 Guide Resources.
- These MCP-side changes do not justify a Product/OSC/control-protocol version bump by themselves.

Do not present PR #33 as merged main capability until it is explicitly merged.

---

## 6. VST3 realtime architecture

- JUCE 8.0.8, C++20, CMake.
- Visible product: `AI Audio Analyzer`.
- Internal target: `AIAnalyzer`.
- Bundle ID: `com.debuneko.aianalyzer`.
- Default measurement OSC endpoint: `127.0.0.1:9855`.
- Audio callback writes to a preallocated SPSC FIFO.
- Background worker owns FFT/analysis/reset/latency estimation/measurement OSC.
- `libebur128` provides LUFS / True Peak.

Historical host-visible parameter order must remain:

```text
1  Identify
2  Analysis Profile
```

Realtime callback may contain cheap host reads, atomics and FIFO push only.

Do not put locks, allocation, network parsing, file I/O, FFT, loudness processing, semantic analysis, song structure, relationship analysis, MCP work, Python/model inference, or optimizer orchestration in the audio callback.

Current scheduling invariants:

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
0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

Profiles affect measurement computation only and never audio quality or the audio signal.

`Full` is the compatibility default.

When a disabled family is re-enabled, rebuild/reset its state rather than pretending measurement continued through the disabled gap.

Use the lowest profile that provides the evidence required for the current task.

---

## 8. Analyzer-owned local control protocol

Control revision remains:

```text
1
```

It is separate from OSC analysis-frame protocol 1.2.

Security/scope invariants:

- loopback only;
- Analysis Profile only;
- runtime UUID target must match;
- network callback validates/queues only;
- host parameter mutation occurs on JUCE message thread;
- ACK is request-scoped;
- stopped transport must not block ACK;
- old VST3 builds without receiver fail by timeout, never optimistic success.

Keep separate:

```text
control_acknowledged
telemetry_confirmed
```

ACK proves the target VST3 applied the request. Telemetry confirmation requires a fresh measurement frame reporting the requested profile.

---

## 9. Measurement / interpretation invariants

### `null` is not zero

Unavailable evidence remains unavailable.

### Missing coverage is not silence

Never convert missing/sparse Song Memory into inactivity, mute state, a structure boundary, or relationship disappearance.

### Feature availability is authoritative

Disabled/unavailable feature families must not be interpreted merely because compatibility packet positions exist.

For historical range comparisons, use measurement families actually represented in the selected retained Before/After evidence. Do not substitute the current live Profile for historical availability.

Content-dependent retained availability differences are audit context, not proof that the historical Analysis Profile changed. Interpret only dimensions/families represented in both passes; no common retained measurement family is a hard comparability blocker.

### Project/runtime identity is explicit and currently unresolved

Current machine-readable identity contract is exposed by:

```text
audio_project_identity_status()
```

Current semantics:

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
project_switch_detection                not_available
runtime_id.scope                        live_plugin_instance
runtime_id.persistent                   false
runtime_id.serialized_with_project      false
runtime_id.stable_when_same_project_is_reopened  false
binding.scope                           mcp_session
binding.persistent                      false
retained_state.scope                    mcp_session
retained_state.automatically_partitioned_by_stable_project_id  false
retained_state.cross_project_isolation_guaranteed              false
```

Critical rules:

- reopening the same DAW project recreates Analyzer runtime UUIDs;
- a new runtime UUID therefore does not prove that the project changed;
- current Mixer/Slot binding is deterministic current-session location, not persistent track identity;
- while MCP keeps running, retained Song Memory, Section Maps, snapshots, relationships and verification sessions can outlive a DAW project switch/reopen;
- until P3 provides authoritative project identity, do not silently reuse retained project-level state across a suspected switch/reopen;
- when strict isolation is required before stable identity exists, restart Analyzer MCP and rebuild current-session bindings/evidence;
- never manufacture a project ID from runtime UUID, BPM, track count, names, Mixer indexes, topology fingerprints, transport epochs, or audio fingerprints unless a future explicit identity contract defines that method.

### P6a dynamics-distribution terminology stays descriptive

P6a uses retained one-second Song Memory, a minimum per-bin coverage floor, and covered-seconds weighting for accepted observations.

Keep these distinctions explicit:

- weighted RMS/LUFS-S/crest/peak percentiles are descriptive retained-observation statistics;
- dB percentiles are not power-domain means; if both are exposed they must remain separate fields;
- `lufs_s_interpercentile_range_lu` means P90(LUFS-S) - P10(LUFS-S) over accepted retained bins and must never be relabelled as standardized EBU LRA;
- arbitrary-range Integrated LUFS is unavailable while retained `lufs_i_latest` remains pass-cumulative;
- arbitrary-range PLR is unavailable without scope-compatible peak and integrated-loudness evidence;
- missing bins are missing, not zero/silence;
- low-coverage bins must not dominate distributions;
- section-to-section distribution deltas are descriptive context, not a dynamics/mastering quality score or processing recommendation;
- no fixed genre loudness, crest, LRA, or PLR target belongs in MCP core logic.

### Heuristics stay labelled as heuristics

Examples include spectral overlap, temporal overlap, ERB masking evidence, negative-cross evidence, tonal ranking, harmonic alignment, section novelty, recurrence similarity, Track Story deltas, relationship `shortlist_priority`, range pass selection, and retained weighted distribution summaries.

They are not calibrated probabilities unless a future validated model explicitly establishes that.

### Do not collapse independent evidence into one score

Keep stereo dimensions, Track Story dimensions, relationship evidence, dynamics distributions, and performance telemetry separate.

### Exact project data wins for exact symbolic facts

If external DAW/MIDI/project tooling exposes exact track names, routing, markers, labels, plugin chain/state, or MIDI notes/chords, use that for exact claims. Audio inference may complement but not silently override it.

---

## 10. OSC analysis protocol 1.2

Analysis address:

```text
/aianalyzer/frame
```

Protocol is append-only. Existing indexes `0..149` must never be repurposed.

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

P1/P2/P4a, project-identity disclosure, MCP self-description and P6a retained distributions add no OSC fields and no realtime DSP work.

---

## 11. Current measurement/perception capabilities

Current evidence includes:

```text
signal validity
Sample Peak / RMS / Crest
LUFS-S / LUFS-I / True Peak
32-band spectrum
centroid / rolloff / flatness
full-band + frequency-dependent stereo correlation
Mid / Side evidence
Side spectrum / Side-Mid relations
negative-cross evidence
temporal flux / RMS rise / low-band energy
12-bin chroma
single-F0 harmonic evidence
DAW transport / PPQ / BPM / time signature
instance-local transport epochs
estimated analysis lag
dropped blocks
worker/FIFO telemetry
```

Do not infer track role such as Kick/Bass/Vocal solely from these measurements.

---

## 12. Transport-aware Song Memory

A `transport_epoch` is one **instance-local continuous playback pass**.

Playback start, seek, loop jump, or detected discontinuity creates a new epoch.

Epoch IDs are independent per Analyzer instance. Equal numbers across tracks are not project-global identity.

Song Memory:

```text
canonical bin size       1 second
coverage slot            100 ms
max retained bins        1200 / instance
max retained span        about 20 minutes / instance
query resolutions        1 / 2 / 5 / 10 / 15 / 30 seconds
scope                    running MCP session
```

Supporting tracks align by overlapping DAW-time coverage, not equal epoch IDs.

Song Memory is not yet partitioned by a stable DAW Project ID. A running MCP can retain old-project evidence after the DAW switches/reopens a project. Use the project identity contract before assuming continuity.

Transport coordinates are for whole-song/section/range reasoning, not sample-accurate editing.

---

## 13. Structure, Track Story and relationships

Current tools:

```text
audio_section_map()
audio_section_profile()
audio_track_story()
audio_section_relationships()
```

A/B/C/... are neutral recurrence-family labels only. Never automatically map them to Intro/Verse/Chorus/Drop.

Track Story summarizes one track across sections using activity, levels, spectrum, stereo, temporal, chroma, coverage/lag/drop, adjacent deltas, same-family per-dimension variation and relative extrema. It must not create one overall quality/consistency score.

Section-aware relationships use a bounded shortlist. `shortlist_priority` means inspection priority only, not masking probability, audibility probability, mix-problem probability, quality score, or processing recommendation.

Detailed masking/stereo/temporal pair tools remain recent-window based. P4a same-range verification does **not** automatically turn those detailed tools into historical section-range analyzers.

---

## 14. Verification boundary

Two verification modes now coexist.

### 14.1 Recent-window verification

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

This older path captures comparable recent windows. Its active-ratio guard remains a passage-comparability heuristic, not a quality threshold.

### 14.2 Transport-anchored same-range verification - P4a

```text
audio_begin_range_verification(label, start_seconds, end_seconds, ...)
audio_complete_range_verification(verification_id, ...)
audio_range_verification_status(verification_id="")
```

Canonical flow:

```text
capture retained Before range
-> freeze receive-time fence
-> external DAW-control MCP write
-> actual host readback
-> replay the same effective DAW-time range
-> select a clean post-fence retained pass per Analyzer
-> compare After - Before
```

P4a invariants:

- requested fractional boundaries are explicit;
- effective range is normalized to canonical one-second Song Memory bins;
- each Analyzer independently selects the best instance-local epoch;
- pass selection is coverage-first, recency only breaks ties;
- equal numeric epochs across tracks are never required;
- After cannot silently reuse pre-change Song Memory;
- missing coverage is not silence;
- historical feature interpretation is per dimension using retained evidence common to Before and After;
- content-dependent retained feature mismatch is an audit warning, not automatic proof of Profile mismatch;
- no common retained measurement family blocks controlled comparison;
- higher selected After dropped-block evidence blocks a controlled comparison;
- `active_ratio` is descriptive in same-range mode, not a proxy for passage identity;
- range LUFS-I delta is intentionally unavailable because retained `lufs_i_latest` is pass-cumulative, not range-integrated;
- actual external host readback is still required for `closed_loop_complete=true`;
- Analyzer performs no sound-changing write.

`controlled_comparison=true` means technical comparability only.

`closed_loop_complete=true` means technical comparability plus supplied actual host readback.

Neither means After is artistically better.

A verification session does not establish persistent project identity and must not silently cross a suspected project switch/reopen.

---

## 15. High-level API strategy

Prefer:

```text
high-level project/song/section/range summary
-> identify relevant target
-> drill into specialized evidence only where needed
```

Do not force the LLM to call dozens of tiny APIs mechanically.

Current high-level building blocks include:

```text
audio_project_identity_status()
audio_project_status()
audio_song_status()
audio_song_overview()
audio_section_map()
audio_section_profile()
audio_track_story()
audio_section_relationships()
audio_dynamics_distribution()
audio_begin_range_verification()
audio_complete_range_verification()
```

---

## 16. MCP source layout

Stable source/PyInstaller entrypoint:

```text
mcp/server.py
```

Do not create version-numbered startup files or reintroduce a parallel `bridge/` source tree.

Current runtime modules include:

```text
mcp/server.py
mcp/analyzer_core.py
mcp/self_description.py
mcp/project_tools.py
mcp/project_identity_tools.py
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
mcp/range_tools.py
mcp/range_verification_tools.py
mcp/dynamics_tools.py
```

Repository/CI-only regressions include:

```text
mcp/ci_regression.py
mcp/relationship_regression.py
mcp/range_verification_regression.py
mcp/dynamics_regression.py
```

CI-only regressions must not be shipped in beginner Release runtime/source folders.

---

## 17. MCP Self-Describing API and Skill boundary

The MCP must be safe and understandable even when the client has **not imported an external Skill**.

Protocol-facing self-description has three layers:

```text
Server instructions
-> short global startup order + cross-cutting hard rules

Tool descriptions
-> every MCP Tool has a non-empty purpose/usage description discoverable through tools/list

MCP Resources
-> long-form guides under aianalyzer://guide/*, read only when needed
```

Current P6a branch Guide Resource contract:

```text
aianalyzer://guide/index
aianalyzer://guide/core
aianalyzer://guide/analyzer-mcp
aianalyzer://guide/parameters
aianalyzer://guide/performance-evidence
aianalyzer://guide/song-memory
aianalyzer://guide/section-structure
aianalyzer://guide/track-story
aianalyzer://guide/section-relationships
aianalyzer://guide/dynamics-evidence
aianalyzer://guide/masking-evidence
aianalyzer://guide/stereo-evidence
aianalyzer://guide/tonal-evidence
aianalyzer://guide/verification-evidence
```

The external/repository Skill remains the **canonical long-form knowledge source**:

```text
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/references/*.md
```

MCP Resources read those same Markdown files. Do not maintain a second copied long-form guide inside Python constants.

Relationship rules:

- client-side Skill import is optional for basic correct MCP use;
- clients with MCP Resource support should read `aianalyzer://guide/index` and only the relevant guide for the current task;
- clients without Resource support may import the packaged Skill to receive the same long-form guidance;
- Server instructions and Tool descriptions form the minimum fallback if guide files are unavailable;
- complete beginner Releases must still include `skill/` and must fail package validation if canonical guide files cannot be found;
- do not load all guides mechanically;
- Skill explains professional usage, strategy, evidence interpretation, tool calling order, limitations, and verification discipline; it does not become a mandatory mixing recipe.

MCP provides measurements, state, retained evidence, safe APIs, identity-scope disclosure, self-description, and Analyzer-owned Profile control.

The real DAW-control layer owns sound/project writes.

Do not encode one mandatory genre/style recipe into Analyzer MCP or its core Skill.

---

## 18. CI and merge rules

Never merge a PR while the latest relevant head has pending or failing CI.

For VST3/control changes verify at least:

```text
Windows x64 VST3 build
macOS Apple Silicon arm64 VST3 build
WorkerSchedulingTests
```

For MCP changes verify:

```text
py_compile
AI_ANALYZER_SELF_TEST=1 python mcp/server.py
mcp/ci_regression.py
feature-specific regression when present
exact tool registry count
```

For Project Identity Disclosure verify:

```text
audio_project_identity_status() registry presence
UNRESOLVED stable project identity contract
same-project reopen runtime UUID instability disclosed
cross-project retained-state isolation not overclaimed
strict-isolation action disclosed
```

For MCP Self-Describing API additionally verify:

```text
all current tools have non-empty descriptions
Server instructions are non-empty and retain required hard rules
exact current Guide Resource registry
all Guide Resources have non-empty descriptions
canonical Skill/reference files resolve in source/development package
AI_ANALYZER_REQUIRE_GUIDES=1 passes in complete packaged/final Release layout
```

Current P6a branch expectations are 43 tools and 14 Guide Resources.

P2 additionally requires `mcp/relationship_regression.py`.

P4a additionally requires `mcp/range_verification_regression.py`.

P6a additionally requires `mcp/dynamics_regression.py` and must prove:

```text
coverage-weighted percentiles are deterministic
low-coverage bins cannot dominate distributions
missing bins are not inserted as zero/silence
LUFS-S absence remains unavailable
range/section selection is transport-anchored
LUFS-S spread is not exported as standardized LRA
arbitrary-range integrated LUFS/PLR remain unavailable
section deltas are descriptive only
```

Path-aware synchronize runs may legitimately skip expensive jobs on later docs-only commits. Record the last implementation head with full relevant green CI and the final docs-only head with its own green path-aware CI.

When merging, use an exact expected PR head SHA guard.

Do not merge unless the user explicitly asks to merge.

---

## 19. Release packaging rules

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
- package includes VST3, one-file MCP runtime, canonical `skill/` guides, setup/install docs, VERSION, LICENSE, installer scripts;
- importing the Skill into the client is optional for basic MCP use;
- complete user packages must pass strict Guide Resource lookup using the installed sibling `skill/` directory.

Canonical runtime build:

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

---

## 20. Implemented evolution / history

Merged milestones include:

- loudness / True Peak / stereo correlation;
- signal validity and runtime UUID identity;
- Identify mapping to FL Mixer Track/Slot;
- project overview and Snapshot A/B;
- temporal evidence;
- ERB-style masking evidence;
- deeper Mid/Side / Side-spectrum / negative-cross evidence;
- chroma / tonal-center / harmonic evidence;
- recent-window controlled Before/After verification around external writes/readback;
- adaptive Eco/Balanced/Mix/Full measurement profiles;
- worker/FIFO/lag/drop telemetry;
- transport-aware continuous playback epochs;
- bounded DAW-time Song Memory;
- explainable section novelty and neutral recurrence families;
- section-level project profiles;
- bilingual plugin GUI and transport/health visibility;
- Analyzer-owned loopback Analysis Profile control with explicit ACK;
- **P1 Track Story merged via PR #19**;
- **P2 Section-aware Mix Relationships merged via PR #20**;
- **P4a retained-range resolver + same-range verification merged via PR #29** (`c833487c6efbd98206d3f454e0875d4698b1f6af`);
- **Project Identity Disclosure merged via PR #31** (`70e95f83f2e938cb2bf619c7ffb1e0aabd4b9b9b`);
- **MCP Self-Describing API merged via PR #32** (`2bcc868413f33737481fcc1704eb641d7042e75e`).

Current open implementation work:

- **PR #33 P6a Coverage-aware Dynamics Distribution** — MCP-side retained RMS/LUFS-S/crest/peak/True-Peak distributions, coverage weighting, section comparison and explicit standardized-loudness boundaries. Not merged until explicitly authorized.

---

## 21. Ordered P1-P10 roadmap

`AGENT.md` is the roadmap source of truth. Do not rely only on conversation memory.

Status vocabulary:

```text
ACTIVE       implementation in progress
QUEUED       near-term candidate after active dependency
LATER        useful but not near-term
BLOCKED      requires unresolved design/external capability
DONE         implemented, documented, regression-covered, and merged to main
```

### P1 - Track Story across sections

Status: **DONE**.

Merged PR: **#19**.

### P2 - Section-aware Mix Relationships

Status: **DONE**.

Merged PR: **#20**.

### P3 - Exact DAW context integration

Status: **BLOCKED** on companion DAW-control capability/contract details.

Target exact context includes project identity, stable track IDs/names, routing/sends, plugin chain/slot identity, Playlist markers/labels, clips/patterns where available, MIDI/symbolic data where available, and actual plugin parameter readback.

Exact project metadata wins over audio inference for exact symbolic claims.

### P4 - Transport-anchored same-range verification

Status: **ACTIVE** — P4a is DONE; P4b is QUEUED.

#### P4a - common retained-range resolver + same-range Before/After verification

Status: **DONE**.

Merged PR: **#29**.

Merge commit:

```text
c833487c6efbd98206d3f454e0875d4698b1f6af
```

Final exact PR head and CI gate:

```text
head      18c2dfbcaf750747d6a8e9863e211d7e20b39a43
build     #329 / run 33944568983
result    success
```

Implemented:

```text
mcp/range_tools.py
mcp/range_verification_tools.py
audio_begin_range_verification()
audio_complete_range_verification()
audio_range_verification_status()
mcp/range_verification_regression.py
```

Completion evidence:

- 41-tool registry synchronized at the #29 merge point;
- same-range regression green;
- Release runtime validation includes new runtime modules;
- public docs/Skill/Release docs synchronized;
- exact-head CI green;
- merged with expected-head guard.

#### P4b - deeper historical range reuse

Status: **QUEUED**.

Potential next work:

- reuse common Range Resolver for historical section-specific evidence;
- expose range-scoped deeper metrics only where current retained schema can support them honestly;
- do not fake sample accuracy or range-integrated metrics that are not actually retained.

### P5 - Persistent project memory + stable external identity

Status: **BLOCKED** until P3 provides trustworthy identity.

Persist candidates: project/track mappings, section maps, Track Stories, relationship summaries, analysis digests, verification/change history, coverage/schema metadata.

Runtime UUID and local epoch must never become permanent project IDs.

Project Identity Disclosure is a safety contract only; it does not implement persistent identity or persistence.

### P6 - Dynamics / mastering distributions

Status: **ACTIVE** — P6a is implemented on PR #33; P6b is QUEUED.

#### P6a - coverage-aware retained distributions

Status: **IMPLEMENTED ON PR #33 / NOT DONE UNTIL MERGED**.

Current branch surface:

```text
audio_dynamics_distribution(...)
mcp/dynamics_tools.py
mcp/dynamics_regression.py
aianalyzer://guide/dynamics-evidence
```

Supported scopes:

```text
selected retained transport-pass span
explicit DAW-time range
cached Section Map section
optional section-to-section comparison
```

Coverage/statistics policy:

```text
minimum per-bin coverage floor
+
covered-seconds weighting for accepted bins
```

Current descriptive distributions include RMS, LUFS-S, crest, observed sample-peak maxima and observed True-Peak maxima with min/max, P10/P25/P50/P75/P90, IQR and P90-P10 spread where available. RMS also exposes a separately labelled covered-seconds power-domain mean.

P6a deliberately leaves these standardized/scope-incompatible metrics unavailable:

```text
EBU LRA
arbitrary-range Integrated LUFS
arbitrary-range PLR
```

`lufs_s_interpercentile_range_lu` is descriptive only and must never be presented as EBU LRA.

No VST3 DSP, OSC 1.2 index, or Analyzer control protocol change is required for P6a.

#### P6b - authoritative standardized loudness metrics

Status: **QUEUED**.

Audit current libebur128 state/modes before implementation. Potential future metrics include authoritative EBU-style LRA and pass-scope integrated loudness / peak relations only when measurement scope and reset semantics are compatible. Benchmark added worker state before enabling it broadly.

Do not claim whole-song values from incomplete coverage.

### P7 - Energy-aware mono-fold / stereo compatibility

Status: **QUEUED**.

Target evidence: mono-fold RMS delta, bandwise energy loss, mono-fold peak delta, spectral delta after L+R fold.

Keep these separate from correlation / Side-Mid / negative-cross metrics.

### P8 - Reference-track comparison

Status: **LATER**.

Must be level-aware, section-aware, coverage-aware and descriptive rather than an automatic copy/match recipe.

### P9 - Stronger tonal representation

Status: **LATER**.

Candidates: HPCP, CQT/log-frequency representation, tuning offset estimation, multi-pitch/chord evidence only if justified.

Exact MIDI/project symbolic data remains authoritative when available.

### P10 - Offline fast scan

Status: **LATER / BLOCKED** on render/input workflow design.

Potential paths: external offline analyzer executable/library, DAW render handoff from companion control MCP, compatible reuse of Song/Section/Relationship/Range schemas.

Never put render orchestration or file decoding into the realtime callback.

---

## 22. Future system layers

### Mixing Transaction / rollback

Not implemented. Transaction state belongs with the layer that can actually restore DAW/plugin parameters.

Analyzer may verify a transaction but must not become a hidden project writer.

### Reference Engine

Not implemented. Future comparison should operate on structured spectral/dynamics/stereo/loudness/section evidence and must not become naive inverse EQ matching.

### Numeric optimizer / learned automix

Not implemented. Stabilize perception-control-verification first. Future optimizers/models should provide bounded proposals/initial guesses and remain external to the realtime Analyzer.

---

## 23. Current genuine limitations

Keep these explicit in code/docs/Skill:

- transport time/PPQ are approximate, not sample-accurate;
- historical tempo-map reconstruction is not implemented;
- stable DAW project identity is currently unresolved;
- automatic project-switch detection is not implemented;
- runtime UUID is live plugin-instance identity and changes when the same project is reopened;
- current Mixer/Slot binding is MCP-session scoped, not persistent track identity;
- Song Memory is MCP RAM/session-scoped and not partitioned by stable Project ID;
- section maps / Track Stories / relationships / range verifications are session-scoped and can outlive a DAW project switch while MCP keeps running;
- strict cross-project isolation currently requires an explicit clean MCP session when authoritative identity is unavailable;
- section detector works at one-second retained-summary scale;
- A/B/C families are neutral recurrence labels;
- exact FL Studio marker/Playlist integration is not implemented;
- epoch IDs are instance-local;
- estimated analysis lag excludes OSC/MCP/LLM/DAW-control latency;
- no exact routing graph until P3;
- detailed masking/stereo/temporal pair tools remain recent-window based;
- same-range P4a uses one-second retained bins, not sample-accurate boundaries;
- arbitrary-range LUFS-I is not implemented;
- P6a distributions are one-second retained-observation statistics, not reconstructed raw-audio distributions;
- standardized EBU LRA is not implemented in P6a;
- arbitrary-range Integrated LUFS and PLR are not implemented in P6a;
- MCP guide Resources require the canonical packaged/repository Skill files for full long-form content; Server instructions + Tool descriptions are the fallback if those files are absent;
- Mixing Transaction / rollback is not implemented;
- Reference Engine is not implemented;
- numeric optimizer / automix service is not implemented;
- offline fast scan is not implemented.

Never present a roadmap item or an open PR as merged current-main capability.

---

## 24. Final product principle

The system should support a professional engineering loop:

```text
professional mixing knowledge
+
realtime / retained audio perception
+
whole-song structure understanding
+
multi-track relationship understanding
+
DAW/VST control
+
Before/After same-range verification
+
future rollback / persistent Mix State / reference / optimization
```

Priority remains:

```text
LLM
-> perception
-> reasoning
-> real operation
-> re-perception
-> verification
```

Stabilize that loop first. Future neural models, differentiable DSP, encoders, or specialized audio LLMs should plug into this architecture as optional modules rather than forcing a redesign of the Analyzer core.