# AGENT.md

This file is the working contract and long-term architecture source of truth for AI agents and maintainers modifying **AI Audio Analyzer**.

Read it before changing the repository. Keep implementation, tests, CI, Release packaging, MCP behavior, Skill behavior, roadmap state and public documentation consistent.

## 1. North star

AI Audio Analyzer is the **measurement / memory / structure / comparison / verification** layer of a larger AI-assisted mixing system.

```text
Observe -> Remember -> Understand -> Reason -> external DAW action -> Measure Again -> Verify
```

Analyzer owns factual audio evidence and Analyzer measurement controls. A real DAW-control MCP owns project/plugin inspection, sound-changing writes, actual host readback and future rollback/transactions.

Current FL Studio companion project:

```text
https://github.com/rosasynthesiz/flstudio-mcp
```

Do not build a duplicate DAW-control stack inside Analyzer MCP.

## 2. Current product contract

Current P4b PR #36 branch metadata:

```text
Product version             1.2.0
MCP version                 1.2
OSC analysis protocol       1.2
Analyzer control revision   1
MCP tools                   48
Guide Resources             16
```

Current `main` at the PR #36 branch point:

```text
main head                   79452d30a1d7817dd9bf24fadc3bd34abf35de7c
MCP tools                   47
Guide Resources             16
```

Merged architecture milestones:

- P1 Track Story — PR #19.
- P2 Section-aware Mix Relationships — PR #20.
- P4a retained range resolver + same-range verification — PR #29, merge `c833487c6efbd98206d3f454e0875d4698b1f6af`.
- Project Identity Disclosure — PR #31, merge `70e95f83f2e938cb2bf619c7ffb1e0aabd4b9b9b`.
- MCP Self-Describing API — PR #32, merge `2bcc868413f33737481fcc1704eb641d7042e75e`.
- P6a Dynamics Distribution — PR #33, merge `56b9e0cbfa0a350976beccd594f4d887196f4436`.
- P7a Mono-fold Compatibility — PR #34, merge `a4924b80986d01f622784ec7db6087240f7c34ca`.
- P8a Session Reference Engine — PR #35, merge `79452d30a1d7817dd9bf24fadc3bd34abf35de7c`.

Current open implementation work:

- **PR #36 P4b bounded historical retained detail** — not merged main capability until explicitly merged.

Never present an open PR as merged current-main capability.

## 3. Repository-wide change rule

For every code, protocol, MCP, workflow, packaging or behavior change, inspect and update as appropriate:

```text
README.md
README.zh-CN.md
AGENT.md
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/README-CHERRY-STUDIO.md
skills/ai-analyzer-flstudio/references/*.md
release/README.md
release/common/*.md
.github/workflows/*.yml
mcp/cherry-studio.example.json
release/windows/*
release/macos/*
```

Not every file must change every time, but never knowingly leave stale tool counts, version strings, protocol semantics, control boundaries, roadmap state, packaging lists or Release claims.

All LLM-facing Skill/reference content stays **English-only**.

## 4. Control boundary

Analyzer MCP may change only:

```text
parameter_id = analysis_profile
Eco / Balanced / Mix / Full
```

This exception changes measurement computation only and never changes the audio signal.

Analyzer MCP must not write EQ, compression, gain, pan, routing, synth parameters, automation, arrangement/project state or other artistic/technical DAW parameters.

Keep separate:

```text
control_acknowledged  target Analyzer accepted/applied profile request
telemetry_confirmed   fresh measurement reports requested profile
```

## 5. Realtime architecture

- JUCE 8.0.8, C++20, CMake.
- Visible product: `AI Audio Analyzer`.
- Internal target: `AIAnalyzer`.
- Bundle ID: `com.debuneko.aianalyzer`.
- Measurement OSC default: `127.0.0.1:9855`.
- Audio callback writes only to a preallocated SPSC FIFO plus cheap host/atomic state.
- Background worker owns FFT, loudness, temporal/semantic analysis, reset handling and measurement OSC.
- `libebur128` provides loudness/True-Peak evidence.

Do not put locks, allocation, file/network I/O, FFT, MCP work, Python/model inference, reference comparison or optimizer orchestration in the realtime callback.

Host-visible parameter order remains:

```text
1 Identify
2 Analysis Profile
```

## 6. Adaptive Analysis Profiles

```text
0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

`Full` is compatibility default. Disabled families are unavailable, never placeholder zero measurements. When re-enabled, rebuild/reset state rather than pretending uninterrupted measurement.

## 7. Identity and retained-state boundary

Always expose current limitations through:

```text
audio_project_identity_status()
```

Current contract:

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
runtime_id.scope                        live_plugin_instance
runtime_id.persistent                   false
runtime_id.stable_when_same_project_is_reopened  false
binding.scope                           mcp_session
retained_state.scope                    mcp_session
retained_state.cross_project_isolation_guaranteed  false
```

Rules:

- reopening the same project recreates Analyzer runtime UUIDs;
- runtime UUID is not project ID or persistent track ID;
- a new UUID does not prove a project switch;
- equal transport epoch numbers across tracks are not required and are not identity;
- until P3 supplies authoritative project identity, strict isolation after a suspected switch/reopen requires a clean Analyzer MCP session;
- never manufacture project identity from tempo, names, topology, Mixer indexes, runtime UUIDs, epochs or audio fingerprints.

## 8. Measurement invariants

### `null` is not zero

Unavailable evidence remains unavailable.

### Missing coverage is not silence

Never convert missing/sparse Song Memory into inactivity, mute state, a section boundary, relationship disappearance or a zero-valued feature.

### Evidence is not a quality score

Do not invent universal mix/master/stereo/dynamics scores or hardcoded genre-independent targets.

### Exact DAW data wins

If external project/MIDI tooling exposes exact names, routing, markers, plugin state or notes, that exact symbolic evidence outranks audio inference for exact claims.

## 9. OSC analysis protocol 1.2

Analysis address:

```text
/aianalyzer/frame
```

Existing indexes `0..149` are append-only and must never be repurposed. New real measurements must append after 149 and justify a protocol bump.

Current 1.1/1.2 tail:

```text
128 analysis_profile
129 analysis_feature_mask
130 worker_load_ratio
131 fifo_fill_ratio
132 fft_runs_per_second
133 semantic_runs_per_second
134 schema marker "1.1"
135 transport_supported
136 transport_time_seconds
137 transport_ppq_position
138 transport_bpm
139 time-signature numerator
140 time-signature denominator
141 transport_is_playing
142 transport_is_recording
143 transport_is_looping
144 loop_start_ppq
145 loop_end_ppq
146 transport_epoch
147 estimated_analysis_lag_ms
148 dropped_blocks
149 schema marker "1.2"
```

P4b is MCP-side retained-detail work only. It adds no VST3 DSP, GUI field or OSC index.

## 10. Song Memory

```text
canonical bin size       1 second
coverage slot            100 ms
max retained bins        1200 / Analyzer instance
max retained span        about 20 minutes / instance
query resolutions        1 / 2 / 5 / 10 / 15 / 30 seconds
scope                    running MCP session
```

A `transport_epoch` is one instance-local continuous playback pass. Cross-track retained analysis aligns by overlapping DAW time, not numeric epoch equality.

Transport coordinates are for song/section/range reasoning, not sample-accurate edits.

## 11. P4a retained-range infrastructure

P4a is merged and owns the common range resolver plus same-range Before/After verification.

Core invariants:

- requested fractional boundaries are explicit;
- effective ranges normalize to canonical one-second bins;
- each Analyzer independently chooses the best local epoch;
- pass selection is coverage-first, recency only breaks ties;
- After cannot silently reuse pre-change retained evidence;
- missing coverage is not silence;
- higher dropped-block evidence may block technical comparability;
- pass-cumulative LUFS-I is not arbitrary-range LUFS-I;
- actual host readback is required for `closed_loop_complete=true`;
- `controlled_comparison=true` means technical comparability, not artistic improvement.

## 12. P4b bounded historical retained detail — PR #36

Goal: let an LLM inspect a past DAW range/Section without forcing replay when the needed deep evidence was already measured.

High-level tool:

```text
audio_historical_detail(
  track,
  start_seconds=None,
  end_seconds=None,
  map_id=None,
  section_id=None,
  compare_track=None,
  minimum_coverage=0.8,
  max_masking_regions=8,
  temporal_low_hz=40,
  temporal_high_hz=160
)
```

Architecture:

- reuse the same canonical one-second Song Memory bins;
- reuse the P4a range resolver;
- store no raw audio;
- retain bounded derived detail only when source feature families were actually available;
- preserve coverage, feature validity and selected-pass provenance;
- align optional pair evidence by common one-second DAW-time bins;
- do not require equal epoch numbers across tracks.

Historical evidence may include:

```text
32-band Mid / Side summaries
full-band + frequency-dependent stereo context
negative-cross / low-band stereo summaries
Mid/Side-derived mono-fold energy evidence
bounded one-second temporal summaries
optional ERB masking/overlap pair evidence
optional stereo / mono / temporal pair deltas
```

Hard boundaries:

```text
historical resolution                  1 second
subsecond historical alignment         unsupported
raw audio                               not retained
missing P4b fields                      unavailable, not silence
recent-window tools                     remain distinct/finer current context
historical mono Sample Peak             unavailable
historical mono True Peak               unavailable
quality score                           none
processing recommendation               none
```

CI regression on Python 3.12 reports a shallow container/array estimate around `1918 B` per detail bin, about `2.20 MiB` at 1200 bins/track. Treat this as a bounded implementation estimate, not exact process RSS.

P4b does **not** automatically convert P8a recent-window references into historical reference profiles. A future P8 extension may consume P4b explicitly.

## 13. P6a dynamics distributions

P6a is merged. `audio_dynamics_distribution()` provides coverage-aware retained RMS/LUFS-S/Crest/observed Peak/True-Peak distributions and section deltas.

Keep explicit:

- weighted retained observations are descriptive;
- dB percentiles are not power-domain means;
- LUFS-S P90-P10 is not standardized EBU LRA;
- arbitrary-range Integrated LUFS is unavailable;
- arbitrary-range PLR is unavailable;
- missing bins are missing;
- no universal loudness/dynamics quality score.

P6b standardized LRA/pass-scope loudness remains later work.

## 14. P7 mono compatibility

P7a is merged. `audio_mono_compatibility()` is a **recent receive-time** tool using existing Mid/Side evidence.

```text
M = 0.5 * (L + R)
S = 0.5 * (L - R)
(L_power + R_power)/2 = M_power + S_power
```

Keep direct mono-fold loss, correlation, Side/Mid and negative-cross as independent evidence.

P4b adds a separate historical one-second Mid/Side-derived mono energy path through `audio_historical_detail()`.

Still unavailable:

```text
direct mono-fold Sample Peak
direct mono-fold True Peak
```

Optional P7b owns any future direct mono peak/True-Peak Worker/OSC extension.

## 15. P8a Reference Engine

P8a is merged via PR #35. Current tools:

```text
audio_capture_reference(track, label="", seconds=10.0)
audio_list_references()
audio_compare_reference(reference_id, target, seconds=None)
```

Current references are frozen compact measurement profiles:

```text
recent receive-time window
MCP-session scoped
not persistent
not whole-song truth
no source audio stored
```

Comparison is structured context, not matching. Keep absolute and RMS-level-normalized spectral-shape views explicit. Do not emit inverse-EQ/master-match recipes, quality scores or cross-song section equivalence assumptions.

P4b supplies historical deep evidence but P8a does not yet expose historical reference capture. P5 should own persistence after trustworthy identity. P10 should become the preferred external-file producer.

## 16. Structure, Track Story and relationships

```text
audio_section_map()
audio_section_profile()
audio_track_story()
audio_section_relationships()
```

A/B/C are neutral recurrence labels, never automatic Intro/Verse/Chorus/Drop labels.

`shortlist_priority` is inspection priority only, not masking probability, audibility probability, problem probability, quality score or a processing command.

For historical deep follow-up use `audio_historical_detail()`; dedicated masking/stereo/temporal tools remain recent-window APIs and may expose finer current-frame context.

## 17. High-level API strategy

Prefer:

```text
identity/project status
-> song/section summary
-> smallest relevant historical/recent evidence tool
-> external DAW action when needed
-> actual host readback
-> same-range verification
```

Do not force the LLM to mechanically call all 48 tools.

Important high-level tools on PR #36:

```text
audio_project_identity_status()
audio_project_status()
audio_song_status()
audio_song_overview()
audio_section_map()
audio_section_profile()
audio_track_story()
audio_section_relationships()
audio_historical_detail()
audio_dynamics_distribution()
audio_mono_compatibility()
audio_capture_reference()
audio_list_references()
audio_compare_reference()
audio_begin_range_verification()
audio_complete_range_verification()
```

## 18. MCP source layout

Stable source/PyInstaller entrypoint:

```text
mcp/server.py
```

Do not create version-numbered startup files or a parallel `bridge/` tree.

P4b runtime modules:

```text
mcp/historical_detail_store.py
mcp/historical_detail_profile.py
mcp/historical_detail_pair.py
mcp/historical_detail_tools.py
```

Repository-only regression:

```text
mcp/p4b_regression.py
```

Regression sources must not ship in beginner Releases.

## 19. Self-describing API

Three layers:

```text
Server instructions
Tool descriptions
MCP Resources under aianalyzer://guide/*
```

The packaged/repository Skill remains the canonical long-form source. MCP Resources read those same files on demand.

PR #36 still exposes **16 Guide Resources**. P4b guidance is integrated into existing core/Song Memory/mono guides rather than creating a redundant guide count bump.

## 20. CI and merge rules

Never merge while latest relevant head has pending/failing CI.

For MCP changes verify at least:

```text
py_compile
AI_ANALYZER_SELF_TEST=1 python mcp/server.py
mcp/ci_regression.py
feature-specific regressions
exact tool registry
packaged runtime self-test with Guide files
```

P4b additionally requires `mcp/p4b_regression.py` and must prove:

- independent per-track epoch selection;
- explicit range/Section resolution;
- retained 32-band Mid/Side availability;
- one-second pair alignment;
- masking/stereo/mono/temporal evidence boundaries;
- legacy/missing detail remains unavailable;
- disabled Analysis Profile families remain unavailable;
- no raw audio, quality score or processing recommendation;
- mono Sample Peak/True Peak remain unavailable;
- bounded memory estimate remains guarded.

Build #411 / run `34309872712` on head `7bcc399d0d35c46795d2cdad1e250137aadadecd` passed source self-test, 48-tool registry, all existing MCP regressions, P4b regression and development package validation.

Path-aware docs-only follow-up commits may skip expensive plugin jobs legitimately. Record the last implementation head with full relevant green CI and the final docs head with its own green relevant checks.

When merging, use an exact expected head SHA guard.

**Do not merge unless the user explicitly asks to merge in the current turn.**

## 21. Beginner Release rules

Supported user packages:

```text
Windows x64
macOS Apple Silicon arm64
```

Requirements:

- one final ZIP per platform;
- no nested ZIP;
- no MCP Python source;
- no `requirements.txt`, venv or PyInstaller `_internal`;
- MCP runtime built with PyInstaller `-F` / onefile;
- package contains VST3, one-file MCP runtime, canonical `skill/`, setup/install docs, VERSION and LICENSE;
- final package self-test must resolve canonical Guide files.

Canonical runtime build:

```text
python -m PyInstaller -F \
  --name ai-audio-analyzer-mcp \
  --paths mcp \
  --collect-all mcp \
  --collect-all pythonosc \
  mcp/server.py
```

P4b adds no user-facing executable or installer path.

## 22. Roadmap

Status vocabulary:

```text
ACTIVE   implementation in progress
QUEUED   near-term dependency-following candidate
LATER    useful but not near-term
BLOCKED  requires unresolved external/design capability
DONE     merged, documented and regression-covered on main
```

### P1 Track Story — DONE
### P2 Section-aware Mix Relationships — DONE
### P3 Exact DAW context integration — BLOCKED on authoritative companion contract/project identity
### P4 Transport range/history — ACTIVE: P4a DONE; P4b ACTIVE on PR #36
### P5 Persistent project memory — BLOCKED until P3 provides trustworthy identity
### P6 Dynamics — P6a DONE; P6b LATER/QUEUED
### P7 Mono compatibility — P7a DONE; P7b OPTIONAL/LATER
### P8 Reference Engine — P8a DONE; historical/persistent/file-backed extensions later
### P9 Stronger tuning-aware tonal representation — LATER
### P10 Offline faster-than-realtime scan — next major high-value stage after P4b schema stabilizes

Recommended post-P4b direction:

```text
P4b merge/stabilize
-> P10 shared-core offline scanner architecture
-> P8 external-file reference producer integration
-> P6b standardized loudness when justified
-> P7b mono peak/TP only if practical value warrants DSP/protocol cost
-> P9 tonal upgrades as needed
```

P10 must share a deterministic C++ analysis core with live Worker. Do not create a drifting unrelated Python DSP implementation.

## 23. Final product principle

```text
professional mixing knowledge
+ realtime and retained audio perception
+ whole-song structure
+ historical deep recall
+ multi-track relationship evidence
+ stereo/mono translation evidence
+ structured reference context
+ DAW control with actual readback
+ same-range verification
+ future offline scan / persistence / optimization
```

Priority remains:

```text
LLM -> perception -> reasoning -> real operation -> re-perception -> verification
```

Evidence and provenance first. Missing data stays missing. Artistic judgment stays contextual.
