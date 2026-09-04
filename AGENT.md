# AGENT.md

This file is the working contract for AI agents and maintainers modifying **AI Audio Analyzer**.

Read it before changing the repository. Keep implementation, tests, CI, Release packaging, installers, MCP behavior, Skill behavior, history, and public documentation consistent.

## 1. Project purpose and control boundary

AI Audio Analyzer is a machine-readable audio measurement/perception/memory/verification layer for AI/LLM-assisted music-production workflows.

```text
AI Audio Analyzer
├─ VST3    measures audio + DAW transport context inside the DAW
├─ MCP     measures / remembers / structures / compares / verifies
│          + may control Analyzer-owned measurement-performance settings only
└─ Skill   teaches correct MCP use, latency handling and evidence semantics
```

The current companion DAW-control project is:

```text
https://github.com/rosasynthesiz/flstudio-mcp
```

### Hard write boundary

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

Those writes, exact project inspection, markers/Playlist metadata, and actual host readback remain the responsibility of the real DAW-control MCP.

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

Not every file must change every time, but every relevant file must be **considered**. Never leave known stale tool counts, version strings, semantics, control boundaries, or packaging lists.

All LLM-facing Skill content stays **English-only**.

The plugin GUI may be bilingual. Do not localize stable technical identifiers such as host parameter IDs, OSC field names, MCP tool names, or protocol keys.

## 3. Current metadata

```text
Product version             1.2.0
MCP_VERSION                 1.2
OSC analysis protocol       1.2
Analyzer control revision   1
MCP tool count              37
```

Do not invent a new product/MCP/OSC version merely because an MCP-derived feature or a local Analyzer-owned control helper is added. Version bumps require a real compatibility/release reason.

There is no predefined next numbered stage/version.

## 4. VST3 architecture

- JUCE 8.0.8, C++20, CMake.
- Visible product name: `AI Audio Analyzer`.
- Internal target: `AIAnalyzer`.
- Bundle ID: `com.debuneko.aianalyzer`.
- Manufacturer/plugin IDs remain stable for DAW-project compatibility.
- Default measurement OSC endpoint: `127.0.0.1:9855`.
- Audio callback writes to a preallocated SPSC FIFO.
- Audio callback does **not** run FFT, loudness, semantic analysis, structure analysis, OSC/network control, MCP, file I/O, or verification orchestration.
- Audio callback may read host Analysis Profile and DAW transport, then hand fixed-size scalar state to the worker using realtime-safe atomics/FIFO only.
- Background worker owns FFT/analysis/state resets/latency estimation/measurement OSC.
- `libebur128` provides LUFS / True Peak.

Historical host-visible parameter order must remain:

```text
1  Identify
2  Analysis Profile
```

Do not casually change host/plugin identity fields or reorder historical host parameters.

### GUI

Current editor behavior:

- built-in `English / 中文` presentation;
- language stored as non-automatable `uiLanguage` in `AIAnalyzerState`;
- older project state defaults to English;
- four visible `Eco / Balanced / Mix / Full` buttons use the real `analysis_profile` host parameter;
- DAW automation/state restore/GUI clicks/Analyzer-owned MCP profile control converge on the same parameter;
- Instance / OSC Host / Port live under collapsible Settings;
- status area exposes DAW transport, pass/epoch, signal validity, worker load, FIFO fill, estimated analysis lag, drops, and configured OSC TX target.

`OSC TX -> host:port` means the configured **measurement-frame destination**. It is not a generic “MCP connected” indicator.

## 5. Adaptive Analysis Profiles

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

### Profile transitions

When a disabled family is re-enabled:

- Loudness state is rebuilt;
- Temporal previous-spectrum/RMS and aggregate state are cleared;
- Semantic cache is cleared.

Do not bridge unmeasured gaps as if the feature had remained continuously active.

## 6. Analyzer-owned local control protocol

Current control revision:

```text
1
```

This is intentionally **separate** from OSC analysis-frame protocol 1.2.

Purpose:

```text
Analyzer MCP
-> request Eco / Balanced / Mix / Full
-> target live Analyzer runtime UUID
-> VST3 applies host-visible analysis_profile
-> explicit ACK
```

### Security/scope invariants

- loopback only (`127.0.0.1`);
- no remote-network control;
- only Analysis Profile is accepted;
- target runtime UUID must match;
- invalid profile/request/reply port is rejected;
- no control processing on audio thread;
- network callback only validates/queues;
- actual host parameter mutation occurs through JUCE `AsyncUpdater` on the message thread;
- ACK is request-scoped and sent to a temporary MCP loopback reply port;
- stopped transport must not prevent control ACK;
- old VST3 builds without the receiver must fail by timeout, never by optimistic success.

### Deterministic candidate ports

Each live VST3 binds the first available port from a deterministic list derived from runtime UUID.

Current constants:

```text
base                 20000
span                 40000
candidate count      16
step modulo          997
profile address      /aianalyzer/control/profile
ACK address          /aianalyzer/control/ack
```

MCP sends the request to all candidate ports. Only the matching runtime UUID accepts it. This avoids requiring every Analyzer instance to bind one global shared control port.

C++ and Python port derivation must remain protocol-identical. Regression vector:

```text
runtime UUID:
00000000-0000-0000-0000-000000000001

ports:
43038 43415 43792 44169
44546 44923 45300 45677
46054 46431 46808 47185
47562 47939 48316 48693
```

If this derivation changes intentionally, update C++ tests, MCP self-test, docs, and control revision together.

### ACK vs telemetry

Keep separate:

```text
control_acknowledged
  VST3 accepted/applied the host-visible profile request.

telemetry_confirmed
  a retained/new measurement frame reports the target profile.
```

ACK can succeed while playback is stopped. Fresh telemetry normally requires new audio processing.

## 7. Realtime/performance rules

Any change to profiles, scheduling, FIFO behavior, transport handling, local control, timeline memory or telemetry must review:

```text
1. realtime callback work
2. network/message-thread boundaries
3. host parameter compatibility/state restoration
4. actual feature computation skipped, not merely hidden
5. MCP validity/null behavior for disabled families
6. profile-transition state reset semantics
7. transport-discontinuity / epoch reset semantics
8. FIFO backlog / staleness / data-age behavior
9. Windows x64 + macOS arm64 compilation
10. C++ and MCP synthetic regressions
11. Skill / README / Release impact
```

Realtime callback rules:

```text
allowed:
  cheap host parameter/transport reads
  atomic scalar handoff
  FIFO push

forbidden:
  locks
  allocation
  Thread::notify()
  FFT
  loudness
  semantic analysis
  structure analysis
  OSC/network/control parsing
  file I/O
  MCP work
```

The audio callback does not wake the worker.

Current scheduling/measurement invariants:

```text
hop size                    1024 samples
FFT                         4096 samples
measurement OSC update      about 10 Hz
worker short-FIFO wait      bounded 1-20 ms
true peak read              every loudness-enabled hop
LUFS-S / LUFS-I polling     about every 100 ms
```

`tests/WorkerSchedulingTests.cpp` protects scheduling, True Peak accumulation, and local-control candidate-port derivation.

### Telemetry semantics

- `worker_load_ratio` = background Analyzer worker busy ratio, not DAW audio-thread CPU.
- `fifo_fill_ratio` = queued Analyzer input capacity; sustained growth can indicate lag.
- `estimated_analysis_lag_ms` = FIFO + half-window estimate, not total Agent latency.
- `dropped_blocks` = cumulative FIFO push failures; nonzero means some audio was not analyzed.
- `data_age_seconds` = wall-clock age of retained evidence; old historical evidence may still be exactly requested.
- `coverage_ratio` = observed retained time coverage, not confidence probability.
- `fft_runs_per_second` / `semantic_runs_per_second` are observed scheduler rates, not guarantees.

## 8. OSC analysis protocol 1.2

Analysis address:

```text
/aianalyzer/frame
```

Protocol is append-only. Existing indexes must never be silently repurposed.

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

Indexes `0..149` remain unchanged by the local profile-control feature.

If a future measurement field is needed, append after 149. Do not overload the local control protocol into analysis-frame indexes.

## 9. Transport-aware Song Memory

The VST3 reads `AudioPlayHead::PositionInfo` in `processBlock()` and hands transport state to the worker through atomics only.

The worker estimates analyzed-window DAW time using approximately:

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
-> publishes requested epoch atomically
-> transport temporarily unavailable
-> worker acknowledges epoch
-> worker discards old queued FIFO content
-> FFT/Temporal/Semantic/Loudness pass state resets as appropriate
-> new epoch coordinates become valid
```

Prefer a short coverage gap over `old audio + new DAW position` mislabeling.

Epoch counters are generated independently in every VST3 instance. Never treat equal numeric epochs across instances as a permanent project-wide pass identity.

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

## 10. Explainable song structure and Track Story

The structure/reasoning layer lives entirely in MCP and consumes retained Song Memory. It adds **no realtime DSP** and **no analysis-frame OSC fields**.

Current tools:

```text
audio_section_map()
audio_section_profile()
audio_track_story()
```

Current section detector:

```text
one-second reference Song Memory
-> robust feature normalization
-> multi-scale 2/4/8-second left/right comparison
-> explainable novelty components
-> adaptive threshold
-> local novelty peaks
-> minimum-section spacing
-> sections S01/S02/...
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

Recurring structure:

```text
section summaries
-> transparent weighted similarity
-> neutral A/B/C/... families
```

Track Story then summarizes one Analyzer instance across those sections:

```text
section-level activity / RMS / LUFS-S / crest
spectral centroid + coarse spectral regions
stereo correlation / width
temporal flux
chroma / top pitch-class evidence
coverage / lag / drops
adjacent-section deltas
same-family per-dimension variation
relative per-metric extrema
```

Track Story must not collapse those independent dimensions into one quality/consistency score.

A/B/C are **not** semantic arrangement labels. Never automatically map:

```text
A = Intro
B = Verse
C = Chorus
```

Exact DAW markers, Playlist labels, pattern/arrangement metadata, MIDI/project annotations, or explicit user structure win for exact naming.

Supporting tracks are aligned to the reference DAW-time range by the retained pass with the strongest overlapping coverage. Do **not** require equal instance-local epoch numbers.

Missing Song Memory is missing evidence. A coverage gap is **not silence** and must **not** become a structural boundary or an inactive Track Story section merely because data disappeared.

`map_id` is bounded MCP-session state, not a persistent project identifier.

## 11. MCP source layout

There is exactly one supported source/PyInstaller entrypoint:

```text
mcp/server.py
```

Do not create version-named startup files.

Current layout:

```text
mcp/server.py             startup / self-test / version metadata / tool registration
mcp/analyzer_core.py      OSC/runtime state, identity/binding, base tools
mcp/project_tools.py      project overview / Snapshot A-B
mcp/temporal_tools.py     temporal parsing/tools
mcp/masking_tools.py      masking evidence
mcp/stereo_tools.py       Mid/Side and stereo evidence
mcp/semantic_tools.py     chroma / tonal-center / harmonic evidence
mcp/performance_tools.py  adaptive-profile / worker-performance telemetry
mcp/control_tools.py      loopback-only Analyzer Analysis Profile control
mcp/song_tools.py         transport parser / song-pass memory / summaries
mcp/section_tools.py      explainable boundaries / recurrence / section profiles
mcp/track_story_tools.py  per-track section/family evolution summaries
mcp/verification_tools.py controlled closed-loop verification sessions
mcp/ci_regression.py      repository-only synthetic MCP regression suite
```

The source directory is `mcp/`. Do not reintroduce a parallel `bridge/` source tree. “Bridge” may remain as a conceptual/runtime term and in historical tool names such as `audio_bridge_status`.

### Current 37-tool registry

The exact registry is enforced by `mcp/server.py` self-test. The two Analyzer-owned write tools are:

```text
audio_set_analysis_profile
audio_set_project_analysis_profile
```

Do not add a write tool without explicitly checking the hard control boundary in Section 1.

## 12. Skill rules

Skill directory:

```text
skills/ai-analyzer-flstudio/
```

All LLM-facing files are English-only:

```text
SKILL.md
README-CHERRY-STUDIO.md
references/*.md
```

Skill scope includes:

- MCP calling strategy;
- selector/mapping rules;
- Analyzer-owned profile control and ACK semantics;
- profile selection;
- measurement validity;
- transport/Song Memory semantics;
- structure boundary/recurrence semantics;
- Track Story and section-to-section evolution semantics;
- latency/data quality;
- worker performance telemetry;
- temporal/masking/stereo/tonal evidence;
- verification;
- limitations.

Do not add fixed genre EQ recipes, LUFS targets, mandatory sidechain rules, stereo recipes, mastering chains, forced Verse/Chorus/Drop labels, key-change rules, harmony-edit rules, tuning recipes, or “metric X always means processor/action Y”.

## 13. Measurement/interpretation invariants

### `null` is not zero

Unavailable evidence remains unavailable.

### Feature mask is authoritative

Append-only compatibility fields can physically remain in a packet when a profile disables their computation. MCP parsing must invalidate disabled families.

```text
Loudness off  -> LUFS / True Peak unavailable
Spectrum off  -> spectrum validity false / arrays unavailable
Stereo off    -> stereo validity false / deep stereo unavailable
Temporal off  -> temporal validity false / temporal descriptors unavailable
Semantic off  -> semantic validity false / chroma/harmonic unavailable
```

Transport/Core context may remain available under Eco.

### Keep independent concepts independent

Do not collapse:

```text
correlation + Side/Mid + negative-cross -> one stereo score
chroma + entropy + tonal ranking + F0 -> one music confidence score
verification topology + coverage + readback -> one change-quality score
worker load + FIFO + lag + drops + age -> one performance score
structure boundary + recurrence + semantic naming -> one form-confidence score
Track Story activity + energy + spectrum + stereo + temporal -> one track-quality score
control ACK + telemetry readback -> one undifferentiated success flag
```

### Heuristics/estimates must be labelled

Spectral overlap, temporal overlap, ERB evidence, negative-cross evidence, tonal-center ranking, harmonic alignment, transport-window alignment, FIFO-derived lag, section boundary strength, recurrence similarity and Track Story relative comparisons are evidence/heuristics/estimates unless replaced by validated stronger models.

### Prefer exact project data for exact symbolic facts

If DAW/MIDI/project tooling exposes exact notes, chords, key metadata, tuning, markers, arrangement labels, routing or other symbolic state, use it for exact claims. Audio inference may complement it but must not silently override exact project data.

## 14. Verification boundary

Controlled Before/After verification for real project/plugin changes remains external-control-oriented:

```text
Before baseline
-> external DAW-control MCP write
-> actual host readback
-> comparable After capture
-> comparability guardrails
-> After-minus-Before deltas
```

The Analyzer-owned Analysis Profile control ACK is **not** a substitute for host readback of unrelated DAW/plugin changes.

For artistic A/B verification, avoid changing Analysis Profile between Before and After unless the measurement procedure explicitly accounts for the feature-set difference.

Current verification remains recent-window based, not exact transport-anchored same-range verification.

## 15. CI and merge rules

Never merge a PR while its latest relevant head has pending or failing CI.

For every implementation head that changes VST3/control code, verify:

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
exact tool registry count
control protocol self-test when relevant
```

Path-aware synchronize behavior may legitimately skip expensive jobs on later docs-only commits. In that case, record both:

```text
latest implementation head with full relevant green CI
final docs-only head with its own green path-aware CI
```

When merging, use the exact expected PR head SHA guard.

## 16. Release packaging rules

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

Stable MCP source/PyInstaller entrypoint:

```text
mcp/server.py
```

Canonical PyInstaller shape:

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

The local Analyzer control protocol requires no additional user configuration or exposed network port; it is loopback-only and derived per live runtime UUID.

## 17. Implemented evolution / history

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
- explainable section-scale novelty detection, neutral recurrence families and section-level project profiles built on Song Memory;
- bilingual English/Chinese plugin GUI with transport/health visibility;
- direct four-button Eco/Balanced/Mix/Full GUI synchronized to the real host parameter;
- Analyzer-owned loopback Analysis Profile control with explicit ACK and a strict no-general-DAW-write boundary;
- section-aware Track Story that exposes per-section observations, adjacent deltas, recurring-family per-dimension variation and coverage guardrails without assigning artistic roles.

## 18. Long-term roadmap / ordered genuine gaps

This roadmap is the persistent development order for the current architecture. Do not invent artificial stage numbers or version bumps to advance it. Reorder only when a concrete reliability/workflow dependency justifies the change, and record the reason here.

Status vocabulary:

```text
ACTIVE       implementation is currently being developed/validated
QUEUED       intended next work after earlier dependencies
LATER        useful but not yet a near-term dependency
BLOCKED      requires external DAW/project capability or unresolved design work
DONE         implemented, documented and regression-covered on main
```

### P1 - Track Story across sections

Status: **ACTIVE** on the current development branch; mark **DONE** only after merge and exact-head MCP CI passes.

Goal:

```text
one Analyzer instance
+ cached section map
-> per-section behavior
-> adjacent-section deltas
-> recurring-family variation
-> coverage-aware whole-track narrative evidence
```

Required evidence:

- active ratio;
- RMS / LUFS-S;
- crest;
- centroid + coarse spectral regions;
- stereo correlation / width;
- temporal flux;
- chroma / pitch-class evidence;
- selected per-instance transport epoch;
- coverage / lag / drops;
- adjacent deltas only when both sections have adequate coverage;
- same-family per-dimension min/max/mean/spread rather than a single score.

Completion criteria:

- `audio_track_story(track, map_id=None)` exists;
- no realtime/VST3/OSC changes;
- missing coverage never becomes inactivity;
- no inferred track role or Verse/Chorus/Drop naming;
- synthetic test covers different instance-local epochs and low-coverage guards;
- README/Skill/Release docs and tool counts agree;
- MCP self-test and `mcp/ci_regression.py` pass on the exact implementation head.

### P2 - Section-aware Mix Relationships

Status: **QUEUED**.

Goal: explain where relationships between relevant tracks change across sections/families, instead of doing only isolated pair comparisons.

Design constraints:

- avoid O(N^2) all-pairs output explosion;
- shortlist pairs using overlapping activity + coarse spectral/stereo evidence;
- then reuse deeper masking/stereo/temporal tools only for relevant pairs;
- preserve directionality where the evidence has direction;
- return section/family context and coverage for every relationship;
- do not turn overlap into an automatic EQ/sidechain recommendation.

Completion criteria:

- project-level shortlist remains bounded on large track counts;
- output identifies which section/family changed and which evidence dimension changed;
- sparse/missing track coverage cannot create false conflicts;
- synthetic project regression includes at least one relationship that appears in one family and disappears in another.

### P3 - Exact DAW context integration

Status: **BLOCKED** on companion DAW-control capability/contract details.

Target exact context:

```text
project identity
Mixer track names and stable IDs
plugin chain and slot identity
routing/sends
Playlist markers/labels
clips/patterns where available
MIDI/symbolic notes where available
actual plugin parameter readback
```

Rules:

- exact project metadata wins over audio inference for exact symbolic claims;
- Analyzer runtime UUID remains runtime identity, not project identity;
- do not duplicate a general DAW-control layer inside Analyzer MCP.

Completion criteria:

- stable external project + track identifiers can be joined to Analyzer runtime mappings;
- exact section names/markers can annotate neutral A/B/C evidence without overwriting the evidence itself;
- reconnect/reload behavior is deterministic and documented.

### P4 - Transport-anchored same-range verification

Status: **QUEUED** after stable section/time-range selection is mature.

Goal:

```text
Before DAW range X..Y
-> external change + actual host readback
-> After exact same DAW range X..Y
-> comparable deltas
```

Completion criteria:

- exact requested DAW range is retained separately from recent-window history;
- Before/After coverage/profile/topology compatibility is explicit;
- loop/seek/replay epochs cannot silently mix;
- failed range recapture returns incomplete verification rather than optimistic success.

### P5 - Persistent project memory and stable external identity

Status: **BLOCKED** until P3 provides a trustworthy project identity.

Goal: preserve useful Song Memory derivatives across MCP/DAW restarts without confusing different projects or stale audio.

Persist candidates:

```text
project_id / track_id mappings
section maps
Track Stories
analysis digests
verification/change history
coverage metadata
schema/version metadata
```

Rules:

- raw long-term audio is not required;
- stale cache must be detectable;
- runtime UUID and instance-local epoch are never used as permanent project IDs;
- cache schema must be migratable or safely discardable.

### P6 - Dynamics/mastering distributions

Status: **QUEUED**.

Target evidence:

```text
RMS/LUFS percentiles
peak/crest distributions
LRA
PLR-like evidence where semantics are valid
section-aware dynamic range
transient density/distribution
```

Rules:

- distinguish complete-song coverage from partial playback;
- do not expose a whole-song Integrated LUFS claim from an incomplete pass;
- keep descriptive distribution evidence separate from loudness-target advice.

### P7 - Energy-aware mono-fold / stereo compatibility evidence

Status: **QUEUED**.

Target evidence:

```text
mono-fold RMS delta
bandwise mono-fold energy loss
mono-fold peak delta
spectral delta after L+R fold
```

This complements, not replaces:

```text
correlation
Side/Mid
negative-cross energy
frequency-dependent stereo
```

Do not compress them into one stereo-quality score.

### P8 - Reference-track comparison

Status: **LATER**.

Goal: level-aware, section-aware comparison against a user-selected reference without copying the reference as a processing recipe.

Required guardrails:

- explicit reference identity/source;
- loudness/level matching where appropriate;
- comparable section/range selection;
- distributions rather than only one average;
- observed difference != required correction.

### P9 - Stronger tonal representation

Status: **LATER**.

Candidates:

```text
HPCP/CQT-style tonal evidence
better tuning-offset handling
multi-pitch evidence
tonal-centroid/Tonnetz-like relationships
key/chord likelihood with explicit uncertainty
```

Rules:

- exact MIDI/project symbolic data wins when available;
- audio-derived key/chord remains probabilistic evidence;
- do not add a learned model merely because it is fashionable; require measured improvement over explainable evidence.

### P10 - Offline fast scan

Status: **LATER / BLOCKED** on input/render workflow design.

Goal: analyze rendered songs/stems faster than realtime while preserving a compatible evidence schema.

Possible implementation surfaces:

```text
standalone CLI/file analyzer
DAW offline-render integration
rendered stem ingestion
```

Do not put file I/O or offline scanning onto the realtime audio callback.

### Cross-cutting reliability gaps

These are not separate product milestones, but every relevant milestone should improve them when possible:

- transport time/PPQ are approximate, not sample-accurate;
- PPQ correction uses current BPM, not full historical tempo-map reconstruction;
- Song Memory and section maps are currently MCP-session scoped;
- section detection operates at one-second retained-summary scale, not beat/transient segmentation;
- structure is explainable/heuristic, not learned;
- epoch IDs are instance-local, not project-global pass IDs;
- estimated analysis lag excludes OSC/MCP/LLM/DAW-control latency;
- no routing graph until exact DAW context supplies one;
- semantic arrangement naming remains intentionally external/contextual.

### Optional future candidates after P1-P10 dependencies

Only pursue these when evidence shows they solve a real workflow gap:

- change ledger / Agent cursor-digest for avoiding repeated edits;
- more explicit spectral tilt/balance summaries derived from existing 32 bands;
- beat-aware structure refinement;
- learned music embeddings if explainable structure/tonal features prove insufficient;
- richer offline/project interchange.

## 19. Roadmap maintenance rule

Whenever a roadmap item changes state:

1. update its status in this file;
2. move durable completed behavior into Section 17 history/current architecture sections;
3. update tool counts/source layout if applicable;
4. update README/Skill/Release docs as required by Section 2;
5. add or update a regression that proves the completion criterion;
6. do not mark **DONE** until the implementation head has the required green CI and the change is on `main`.

Do not use conversation memory alone as the project roadmap. `AGENT.md` is the repository source of truth for planned architectural work.
