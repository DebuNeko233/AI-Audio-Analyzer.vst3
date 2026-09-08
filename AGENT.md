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

## 2. Intelligence and control boundaries

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
how a chosen target differs from a frozen reference profile
```

Prefer explicit coverage/uncertainty over subjective automatic judgments.

Analyzer MCP is **not** a general DAW-control MCP.

The only Analyzer-owned write is:

```text
parameter_id = analysis_profile
Eco / Balanced / Mix / Full
```

That exception is allowed because it changes Analyzer measurement computation only and does not alter the audio signal.

Analyzer MCP must not use it as precedent to write EQ, compression, gain, pan, routing, synth parameters, automation, arrangement/project state, other plugins, or other artistic/technical DAW parameters.

Those writes, exact project inspection, marker/Playlist metadata, plugin-state readback, transactions, rollback, and project mutation belong to the real DAW-control layer.

---

## 3. Repository-wide change rule

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

## 4. Current branch metadata and merge history

Current metadata on the **P8a PR #35 branch**:

```text
Product version             1.2.0
MCP_VERSION                 1.2
OSC analysis protocol       1.2
Analyzer control revision   1
MCP tool count              47
MCP guide resources         16
```

Current `main` before P8a merge remains:

```text
44 tools
15 Guide Resources
main head at P8a branch point: a4924b80986d01f622784ec7db6087240f7c34ca
```

Merged milestones relevant to the current architecture:

- P1 Track Story merged via PR #19.
- P2 Section-aware Mix Relationships merged via PR #20.
- P4a retained-range resolver + same-range verification merged via PR #29 (`c833487c6efbd98206d3f454e0875d4698b1f6af`).
- Project Identity Disclosure merged via PR #31 (`70e95f83f2e938cb2bf619c7ffb1e0aabd4b9b9b`).
- MCP Self-Describing API merged via PR #32 (`2bcc868413f33737481fcc1704eb641d7042e75e`).
- P6a Coverage-aware Dynamics Distribution merged via PR #33 (`56b9e0cbfa0a350976beccd594f4d887196f4436`).
- P7a Energy-aware Mono-fold Compatibility merged via PR #34 (`a4924b80986d01f622784ec7db6087240f7c34ca`).

Current open implementation work:

- **PR #35 P8a Session-scoped Reference Engine** — three MCP tools plus one guide Resource. It is not merged main capability until explicitly merged.

P6a and P7a are **already merged main capability**. Do not describe #33/#34 as open, stacked, draft, or unmerged.

These MCP-side P6a/P7a/P8a changes do not justify a Product/OSC/control-protocol version bump by themselves.

---

## 5. VST3 realtime architecture

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

Do not put locks, allocation, network parsing, file I/O, FFT, loudness processing, semantic analysis, song structure, relationship analysis, MCP work, Python/model inference, reference comparison, or optimizer orchestration in the audio callback.

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

## 6. Adaptive Analysis Profiles

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

## 7. Analyzer-owned local control protocol

Control revision remains `1`, separate from OSC analysis protocol 1.2.

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

## 8. Measurement / interpretation invariants

### `null` is not zero

Unavailable evidence remains unavailable.

### Missing coverage is not silence

Never convert missing/sparse Song Memory into inactivity, mute state, a structure boundary, relationship disappearance, or a zero-valued reference feature.

### Feature availability is authoritative

Disabled/unavailable feature families must not be interpreted merely because compatibility packet positions exist.

For historical range comparisons, use measurement families actually represented in selected retained evidence. Do not substitute the current live Profile for historical availability.

### Project/runtime identity is explicit and currently unresolved

Use:

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
- retained Song Memory, Section Maps, snapshots, relationships, reference profiles and verification sessions can outlive a DAW project switch/reopen while MCP keeps running;
- until P3 provides authoritative project identity, do not silently reuse retained project-level state across a suspected switch/reopen;
- when strict isolation is required before stable identity exists, restart Analyzer MCP and rebuild current-session bindings/evidence;
- never manufacture a project ID from runtime UUID, BPM, track count, names, Mixer indexes, topology fingerprints, transport epochs, or audio fingerprints unless a future explicit identity contract defines that method.

### P6a dynamics distributions stay descriptive

P6a uses retained one-second Song Memory, a minimum per-bin coverage floor, and covered-seconds weighting for accepted observations.

Keep these distinctions explicit:

- weighted RMS/LUFS-S/crest/peak percentiles are descriptive retained-observation statistics;
- dB percentiles are not power-domain means;
- `lufs_s_interpercentile_range_lu` is P90(LUFS-S) - P10(LUFS-S), never standardized EBU LRA;
- arbitrary-range Integrated LUFS is unavailable while retained `lufs_i_latest` remains pass-cumulative;
- arbitrary-range PLR is unavailable without scope-compatible peak and integrated-loudness evidence;
- missing bins are missing, not zero/silence;
- low-coverage bins must not dominate distributions;
- section-to-section distribution deltas are descriptive context, not a dynamics/mastering quality score or processing recommendation;
- no fixed genre loudness, crest, LRA, or PLR target belongs in MCP core logic.

### P7a mono-fold evidence is direct energy evidence, not a quality score

Current Worker math:

```text
M = 0.5 * (L + R)
S = 0.5 * (L - R)
(L_power + R_power)/2 = M_power + S_power
```

P7a derives direct recent-window mono-fold evidence without new realtime DSP or OSC fields:

```text
mono_fold_rms_db       = Mid RMS
mono_fold_rms_delta_db = 10*log10(P_mid / P_stereo)
P_stereo               = (L_power + R_power)/2
```

For the existing 32 Analyzer band-center representation:

```text
stereo_equivalent_band_power ~= mid_power + side_power
mono_fold_band_power         ~= mid_power
mono_fold_band_delta_db       = 10*log10(mid_power / (mid_power + side_power))
```

Keep these boundaries explicit:

- band-center sampled evidence is not a perfect integrated-band transfer function;
- `inspection_priority` is only an inspection shortlist aid;
- correlation, Side/Mid, negative-cross and direct mono-fold loss remain independent evidence dimensions;
- Mid at the Analyzer `-120 dB` floor is floor-censored; do not claim cancellation precision below the floor;
- completely unmeasurable Mid+Side energy stays unavailable;
- current P7a scope is recent receive-time only because Song Memory does not retain full historical 32-band Mid/Side detail;
- direct mono-fold Sample Peak and True Peak are unavailable in P7a and must not be inferred from stereo metrics;
- optional P7b owns any future direct mono-fold peak/true-peak worker/protocol extension;
- no fixed rule such as `correlation < 0 = bad`, `all lows must be mono`, or `mono_fold_delta < X = fail` belongs in MCP core logic.

### P8a reference comparison is context, not matching

P8a currently freezes compact recent-window measurement profiles in MCP session memory.

Rules:

- reference profiles are frozen at capture time;
- no source audio is stored;
- references are not persistent across MCP restart;
- recent-window capture is not a whole-song claim;
- current P8a does not silently claim arbitrary historical Section 32-band reference evidence;
- absolute comparison direction is `target - reference`;
- RMS-level-normalized spectral comparison explicitly removes one broad level offset for a shape view only;
- level normalization does not modify either source;
- a reference difference is not automatically a defect;
- never convert reference deltas directly into inverse EQ, master-match, widening, compression, loudness, or other processing commands;
- P8a never silently assumes A/B/C or user section names are semantically equivalent across unrelated songs;
- no universal reference similarity/quality score is emitted.

### Heuristics stay labelled as heuristics

Examples include spectral overlap, temporal overlap, ERB masking evidence, negative-cross evidence, tonal ranking, harmonic alignment, section novelty, recurrence similarity, Track Story deltas, relationship `shortlist_priority`, range pass selection, retained weighted distributions, mono-fold `inspection_priority`, and future reference matching helpers.

They are not calibrated probabilities unless a future validated model explicitly establishes that.

### Exact project data wins for exact symbolic facts

If external DAW/MIDI/project tooling exposes exact track names, routing, markers, labels, plugin chain/state, or MIDI notes/chords, use that for exact claims. Audio inference may complement but not silently override it.

---

## 9. OSC analysis protocol 1.2

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

P1/P2/P4a, project-identity disclosure, MCP self-description, P6a retained distributions, P7a derived mono-fold evidence, and P8a session reference comparison add no OSC fields and no realtime DSP work.

---

## 10. Current measurement/perception capabilities

Current merged measurement evidence includes:

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
recent-window direct mono-fold RMS / band-center energy compatibility
```

P8a branch additionally exposes frozen session reference comparison over existing evidence; it does not add a new DSP measurement family.

Do not infer track role such as Kick/Bass/Vocal solely from these measurements.

---

## 11. Transport-aware Song Memory

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

Song Memory is not yet partitioned by a stable DAW Project ID. A running MCP can retain old-project evidence after the DAW switches/reopens a project.

Transport coordinates are for whole-song/section/range reasoning, not sample-accurate editing.

---

## 12. Structure, Track Story and relationships

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

Detailed masking/stereo/temporal pair tools and P7a mono compatibility remain recent-window based. P4a same-range verification does **not** automatically turn those detailed tools into historical section-range analyzers.

---

## 13. Verification boundary

Two verification modes coexist.

### Recent-window verification

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

This path captures comparable recent windows. Its active-ratio guard remains a passage-comparability heuristic, not a quality threshold.

### Transport-anchored same-range verification - P4a

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
- historical feature interpretation uses retained evidence common to Before and After;
- higher selected After dropped-block evidence blocks a controlled comparison;
- `active_ratio` is descriptive in same-range mode, not a proxy for passage identity;
- range LUFS-I delta is intentionally unavailable because retained `lufs_i_latest` is pass-cumulative, not range-integrated;
- actual external host readback is still required for `closed_loop_complete=true`;
- Analyzer performs no sound-changing write.

`controlled_comparison=true` means technical comparability only.

`closed_loop_complete=true` means technical comparability plus supplied actual host readback.

Neither means After is artistically better.

---

## 14. High-level API strategy

Prefer:

```text
high-level project/song/section/range/reference summary
-> identify relevant target
-> drill into specialized evidence only where needed
```

Do not force the LLM to call dozens of tiny APIs mechanically.

Current P8a branch high-level building blocks include:

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
audio_mono_compatibility()
audio_capture_reference()
audio_list_references()
audio_compare_reference()
audio_begin_range_verification()
audio_complete_range_verification()
```

---

## 15. MCP source layout

Stable source/PyInstaller entrypoint:

```text
mcp/server.py
```

Do not create version-numbered startup files or reintroduce a parallel `bridge/` source tree.

Current P8a branch runtime modules include:

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
mcp/mono_compatibility_tools.py
mcp/reference_tools.py
```

Repository/CI-only regressions include:

```text
mcp/ci_regression.py
mcp/relationship_regression.py
mcp/range_verification_regression.py
mcp/dynamics_regression.py
mcp/mono_compatibility_regression.py
mcp/reference_regression.py
```

CI-only regressions must not be shipped in beginner Release runtime/source folders.

---

## 16. MCP Self-Describing API and Skill boundary

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

Current P8a branch Guide Resource contract:

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
aianalyzer://guide/mono-compatibility
aianalyzer://guide/reference-comparison
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

Rules:

- client-side Skill import is optional for basic correct MCP use;
- read only relevant Resource guides on demand;
- Server instructions + Tool descriptions are the minimum fallback;
- complete beginner Releases must include `skill/` and fail package validation if canonical guide files cannot be found;
- Skill explains professional usage, strategy, evidence interpretation, tool order, limitations and verification discipline; it does not become a mandatory mixing recipe.

---

## 17. CI and merge rules

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

For MCP Self-Describing API additionally verify:

```text
all tools have non-empty descriptions
Server instructions are non-empty and retain required hard rules
exact Guide Resource registry
all Guide Resources have non-empty descriptions
canonical Skill/reference files resolve in source/development package
AI_ANALYZER_REQUIRE_GUIDES=1 passes in complete packaged/final Release layout
```

Current P8a branch expectations are:

```text
47 tools
16 Guide Resources
```

P2 additionally requires `mcp/relationship_regression.py`.

P4a additionally requires `mcp/range_verification_regression.py`.

P6a additionally requires `mcp/dynamics_regression.py` and must prove deterministic coverage-weighted statistics, missing != silence, descriptive LUFS-S spread != LRA, range-integrated LUFS/PLR unavailable, and section deltas descriptive only.

P7a additionally requires `mcp/mono_compatibility_regression.py` and must prove correlated/one-sided/anti-phase math, measurement-floor censoring, energy-aware shortlist behavior, historical limits, and no fake peak/TP or quality score.

P8a additionally requires `mcp/reference_regression.py` and must prove:

```text
identical profiles -> near-zero descriptive deltas
pure gain offset remains in absolute view but disappears from RMS-normalized spectral shape
spectral-shape differences survive level normalization
missing feature families remain unavailable/null
reference profiles are frozen/session-scoped
no cross-song/section equivalence is assumed
no automatic EQ/master-match or quality score is emitted
```

Development/package validation must include `mcp/reference_tools.py` and exclude `mcp/reference_regression.py`.

Path-aware synchronize runs may legitimately skip expensive jobs on later docs-only commits. Record the last implementation head with full relevant green CI and the final docs-only head with its own green path-aware CI.

When merging, use an exact expected PR head SHA guard.

**Do not merge unless the user explicitly asks to merge.**

---

## 18. Release packaging rules

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

P8a adds no user-facing executable and no new installer path. Its Python module is imported by the stable `server.py` entrypoint and therefore must be included in the one-file MCP runtime.

---

## 19. Ordered P1-P10 roadmap

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

Status: **DONE**. Merged PR #19.

### P2 - Section-aware Mix Relationships

Status: **DONE**. Merged PR #20.

### P3 - Exact DAW context integration

Status: **BLOCKED** on companion DAW-control capability/contract details.

Exact project metadata wins over audio inference for exact symbolic claims. Stable project identity remains unresolved in the current companion contract, so P5 automatic persistent attachment remains blocked.

### P4 - Transport-anchored range infrastructure

Status: **ACTIVE** — P4a DONE; P4b QUEUED immediately after P8a.

#### P4a - common retained-range resolver + same-range Before/After verification

Status: **DONE**. Merged PR #29.

Merge commit:

```text
c833487c6efbd98206d3f454e0875d4698b1f6af
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

#### P4b - deeper historical retained evidence

Status: **QUEUED — highest-value follow-up after P8a**.

Primary goal: reduce LLM operation/perception latency by allowing direct queries of past sections without forced replay.

Design direction:

```text
reuse common P4 range resolver
retain bounded 32-band Mid detail per canonical bin
retain bounded Side/Mid detail required by historical stereo/P7 evidence
retain only the temporal summaries necessary for supported historical temporal interaction
feature mask + validity + coverage per retained bin
no raw audio by default
```

Before implementation, estimate worst-case RAM per track/project. Preserve one-second retained resolution and explicit coverage; do not fake subsecond/sample-accurate history.

P4b should unlock historical Section follow-up for masking/stereo/mono/temporal evidence and become the basis for historical reference ranges.

### P5 - Persistent project memory + stable external identity

Status: **BLOCKED** until P3 provides trustworthy identity.

Persist candidates: project/track mappings, section maps, Track Stories, relationship summaries, reference profiles, analysis digests, verification/change history, coverage/schema metadata.

Runtime UUID and local epoch must never become permanent project IDs.

### P6 - Dynamics / mastering distributions

Status: **P6a DONE; P6b LATER/QUEUED behind P8a/P4b**.

#### P6a - coverage-aware retained distributions

Status: **DONE**.

Merged PR #33, merge commit:

```text
56b9e0cbfa0a350976beccd594f4d887196f4436
```

Current surface:

```text
audio_dynamics_distribution(...)
mcp/dynamics_tools.py
mcp/dynamics_regression.py
aianalyzer://guide/dynamics-evidence
```

P6a deliberately leaves EBU LRA, arbitrary-range Integrated LUFS, and arbitrary-range PLR unavailable.

#### P6b - authoritative standardized loudness metrics

Status: **LATER / QUEUED**.

Audit current `libebur128` state/modes before implementation. Benchmark added worker state before enabling it broadly. Do not claim whole-song values from incomplete coverage.

### P7 - Energy-aware mono-fold / stereo compatibility

Status: **P7a DONE; P7b QUEUED / OPTIONAL and not next**.

#### P7a - direct recent-window mono-fold energy evidence

Status: **DONE**.

Merged PR #34, merge commit:

```text
a4924b80986d01f622784ec7db6087240f7c34ca
```

Current surface:

```text
audio_mono_compatibility(track, seconds=5.0)
mcp/mono_compatibility_tools.py
mcp/mono_compatibility_regression.py
aianalyzer://guide/mono-compatibility
```

Current limitations remain deliberate:

```text
historical arbitrary DAW-range 32-band mono fold      unavailable
cached Section 32-band mono fold                      unavailable
mono-fold Sample Peak                                 unavailable
mono-fold True Peak                                   unavailable
```

Historical/Section support waits for P4b. Direct peak/true-peak fold-down waits for optional P7b.

#### P7b - optional direct mono-fold peak / True-Peak measurement

Status: **QUEUED / OPTIONAL; lower priority than P8a/P4b/P10**.

If implemented, add only real direct measurements such as `mono_fold_peak_dbfs` and `mono_fold_true_peak_dbtp`. Any real new OSC fields must append after index 149 and justify a protocol bump.

### P8 - Structured reference-track comparison

Status: **ACTIVE**.

#### P8a - session-scoped frozen reference profiles

Status: **IMPLEMENTED ON PR #35 / NOT DONE UNTIL MERGED**.

Current branch surface:

```text
audio_capture_reference(track, label="", seconds=10.0)
audio_list_references()
audio_compare_reference(reference_id, target, seconds=None)
mcp/reference_tools.py
mcp/reference_regression.py
aianalyzer://guide/reference-comparison
```

P8a semantics:

```text
frozen current-session reference profile
recent receive-time window only
no source audio stored
absolute target-minus-reference evidence
explicit RMS-level-normalized spectral-shape view
independent energy / spectrum / stereo / P7 mono evidence
no automatic matching recipe
no quality score
no cross-song section-label assumption
```

Current deliberate limitations:

```text
persistent reference library                  unavailable
historical arbitrary Section 32-band capture  unavailable
whole-song completeness claim                 unavailable
external file fast scan                       unavailable
```

P4b should add historical depth; P5 should own persistence after strong identity; P10 should become the preferred external-file reference producer.

### P9 - Stronger tonal representation

Status: **LATER**.

Candidates: tuning-aware HPCP/log-frequency evidence, bounded register-aware representation, then only later chord/multi-pitch evidence if justified. Exact MIDI/project symbolic data remains authoritative when available.

### P10 - Offline faster-than-realtime scan

Status: **LATER, high value after P4b/P8 schemas stabilize**.

Preferred architecture is a shared C++ analysis core feeding both live Worker and a standalone local scanner. Do not create a drifting unrelated Python DSP stack. File decoding/render orchestration must never enter the realtime callback.

P10 should eventually become the preferred external reference-file producer for P8 and should support complete-file provenance and faster-than-realtime analysis without changing logical DSP timing.

---

## 20. Future system layers

### Mixing Transaction / rollback

Not implemented. Transaction state belongs with the layer that can actually restore DAW/plugin parameters. Analyzer may verify a transaction but must not become a hidden project writer.

### Reference Engine beyond P8a

P8a is active on PR #35. Future layers include historical range/Section reference capture after P4b, persistent project/reference memory after P3/P5, and external-file reference production after P10.

Reference comparison must remain structured context and must never become naive inverse-EQ/master matching.

### Numeric optimizer / learned automix

Not implemented. Stabilize perception-control-verification first. Future optimizers/models should provide bounded proposals/initial guesses and remain external to the realtime Analyzer.

---

## 21. Current genuine limitations

Keep these explicit in code/docs/Skill:

- transport time/PPQ are approximate, not sample-accurate;
- historical tempo-map reconstruction is not implemented;
- stable DAW project identity is unresolved;
- automatic project-switch detection is not implemented;
- runtime UUID is live plugin-instance identity and changes when the same project is reopened;
- current Mixer/Slot binding is MCP-session scoped, not persistent track identity;
- Song Memory is MCP RAM/session-scoped and not partitioned by stable Project ID;
- section maps / Track Stories / relationships / references / range verifications are session-scoped and can outlive a DAW project switch while MCP keeps running;
- strict cross-project isolation currently requires an explicit clean MCP session when authoritative identity is unavailable;
- section detector works at one-second retained-summary scale;
- A/B/C families are neutral recurrence labels;
- exact FL Studio marker/Playlist integration is not implemented;
- epoch IDs are instance-local;
- estimated analysis lag excludes OSC/MCP/LLM/DAW-control latency;
- no exact routing graph until P3;
- detailed masking/stereo/temporal pair tools remain recent-window based;
- P7a mono compatibility is recent-window based; arbitrary historical/Section 32-band Mid/Side fold-down evidence is not retained yet;
- P7a does not directly measure mono-fold Sample Peak or True Peak;
- floor-censored mono-fold loss cannot claim exact cancellation depth below -120 dB;
- same-range P4a uses one-second retained bins, not sample-accurate boundaries;
- arbitrary-range LUFS-I is not implemented;
- P6a distributions are one-second retained-observation statistics, not reconstructed raw-audio distributions;
- standardized EBU LRA is not implemented in P6a;
- arbitrary-range Integrated LUFS and PLR are not implemented in P6a;
- P8a references are recent-window, frozen, MCP-session-only profiles; they are not persistent or whole-song reference truth;
- P8a does not yet provide historical arbitrary Section 32-band reference capture or external-file scanning;
- MCP guide Resources require canonical packaged/repository Skill files for full long-form content; Server instructions + Tool descriptions are the fallback if those files are absent;
- Mixing Transaction / rollback is not implemented;
- numeric optimizer / automix service is not implemented;
- offline fast scan is not implemented.

Never present a roadmap item or an open PR as merged current-main capability.

---

## 22. Final product principle

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
stereo / mono-translation evidence
+
structured reference context
+
DAW/VST control
+
Before/After same-range verification
+
future historical deep recall / rollback / persistent Mix State / offline scan / optimization
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

The current roadmap priority is:

```text
P8a session reference comparison
-> P4b historical retained detail
-> historical deep pair/mono/reference follow-up
-> P10 offline fast scan
-> later P6b / optional P7b / P9 as justified
```

Stabilize that loop first. Future neural models, differentiable DSP, encoders, or specialized audio LLMs should plug into this architecture as optional modules rather than forcing a redesign of the Analyzer core.