# AI Audio Analyzer Cherry Studio Skill

This Skill targets:

- Cherry Studio;
- AI Audio Analyzer VST3 1.2.0;
- AI Audio Analyzer MCP 1.2;
- optional FL Studio control MCP: https://github.com/rosasynthesiz/flstudio-mcp

Its purpose is to help an LLM **call Analyzer MCP correctly, interpret measurements correctly, manage multi-instance mapping, choose only the analysis work required by the request, use Analyzer-owned Analysis Profile control, use transport-aware Song Memory, explainable section structure, Track Story and bounded section-aware relationship shortlisting instead of chasing realtime frames, judge latency/data quality, and run auditable Before/After verification around externally controlled DAW changes**.

It does **not** provide fixed mixing style, LUFS targets, EQ/compression/sidechain/stereo recipes, forced Verse/Chorus/Drop labels, inferred track roles, key-change rules, harmony-edit rules, or mastering chains.

## Current capability layers

```text
Signal State / runtime UUID
Identify -> FL Mixer Track/Slot deterministic mapping
Project Status / Mix Overview / Snapshot A-B
Adaptive Analysis profiles + worker/FIFO performance telemetry
Analyzer-owned loopback Analysis Profile control + ACK
DAW Transport / continuous playback epochs / latency-aware Song Memory
Explainable section boundaries / neutral recurring A-B-C families / section profiles
Track Story: one Analyzer instance across sections / recurring families
Section-aware Mix Relationships: bounded pair shortlist across sections/families
Spectral Flux / RMS Rise / temporal profile / band-envelope comparison
ERB-rebinned spectral + relative-level + temporal masking evidence
Mid/Side RMS / Side spectrum / frequency-dependent Side-Mid / negative-cross evidence
12-bin chroma / tonal-center candidate ranking / single-F0 harmonic-alignment evidence
controlled closed-loop Before/After verification around external DAW changes
```

The current append-only OSC **analysis-frame** protocol is **1.2**. Existing indexes `0..149` remain unchanged. Analyzer-owned Analysis Profile control uses a separate loopback-only local control revision 1; the section, Track Story and section-relationship layers add no analysis-frame fields and consume retained Song Memory in MCP.

## Recommended initialization

Start with:

```text
audio_project_status()
```

If Analyzer instances are unbound:

```text
FL Studio control MCP finds real Mixer Track / Slot
-> read target Analyzer Identify value
-> toggle Identify
-> audio_last_identify()
-> audio_bind_last_identified(...)
-> audio_instance_map()
```

After binding, prefer:

```text
mixer:<index>/slot:<slot>
```

For whole-song or latency-sensitive work:

```text
audio_song_status()
```

After enough of the intended pass is captured, prefer:

```text
audio_section_map()
```

Then choose the smallest section-aware query:

```text
audio_track_story(track, map_id)          # one track across sections
audio_section_profile(section_id, map_id) # many tracks inside one section
audio_section_relationships(map_id)       # bounded pair shortlist across sections/families
```

When project performance or feature availability matters:

```text
audio_project_performance()
audio_analysis_status(track)
```

When the required feature family is disabled, use the minimum necessary Analyzer-owned profile control:

```text
audio_set_analysis_profile(track, profile)
```

For an intentionally selected group/all live Analyzers:

```text
audio_set_project_analysis_profile(profile, tracks=[...])
```

## Recommended tool path

```text
project readiness               audio_project_status()
whole-song readiness / latency  audio_song_status()
structural map / recurrence      audio_section_map()
one-track section evolution     audio_track_story()
selected-section detail         audio_section_profile()
section-aware pair shortlist    audio_section_relationships()
whole-pass compact summary      audio_song_overview()
raw track / DAW-time history    audio_song_timeline()
project performance             audio_project_performance()
one-instance analysis state     audio_analysis_status()
one-instance profile control    audio_set_analysis_profile()
project/group profile control   audio_set_project_analysis_profile()
project recent overview         audio_mix_overview()
project masking candidates      audio_project_masking_scan()
stable recent single track      audio_average()
current single frame            audio_snapshot()
single-track temporal           audio_temporal_profile()
deep single-track stereo        audio_stereo_profile()
single-track tonal evidence     audio_tonal_profile()
two-track detailed masking      audio_masking_evidence()
custom-band temporal            audio_temporal_compare()
two-track stereo comparison     audio_stereo_compare()
two-track tonal comparison      audio_tonal_compare()
Snapshot management             audio_capture_snapshot() / audio_list_snapshots()
manual Snapshot A/B             audio_compare_snapshots()
controlled change verification  audio_begin_verification() / audio_complete_verification()
verification recovery/status    audio_verification_status()
```

MCP 1.2 exposes **38 tools**. Full signatures are in `references/analyzer-mcp.md`.

## Whole-song memory and Agent latency

Do not build an Agent loop that assumes the LLM must read every frame while playback is happening.

```text
DAW keeps playing
-> Analyzer keeps measuring
-> DAW-time evidence is retained in one-second bins
-> LLM may think/call other tools for seconds
-> LLM later queries the remembered pass
-> section map compresses the pass into relevant structural contexts
-> Track Story compresses one track's evolution across those contexts
-> section-aware relationships shortlist which track pairs merit deeper inspection in each context
```

Important semantics:

- `transport_epoch` is an **instance-local continuous playback pass**;
- playback start, seek, loop jump, or another detected discontinuity starts a new epoch;
- the worker discards queued pre-jump audio and resets pass-dependent Loudness/Temporal/Semantic state;
- equal epoch numbers across separately loaded instances are not guaranteed to be the same permanent project pass;
- `estimated_analysis_lag_ms` is Analyzer FIFO/window latency, not network or LLM latency;
- `data_age_seconds` is wall-clock age of retained evidence and does not make an explicitly requested historical range invalid;
- non-zero `dropped_blocks` means some input audio was not measured;
- `coverage_ratio` describes how much of a requested/coarse range is actually represented;
- transport coordinates are estimates for song/section reasoning, not sample-accurate edits.

Choose the coarsest useful timeline resolution. Prefer structure/Track Story/relationship/overview tools for macro reasoning; use 1–2 second bins only when genuinely necessary.

See `references/song-memory.md`.

## Explainable song structure, Track Story, and relationships

The structure layer is intentionally lightweight and interpretable. It uses multi-scale changes in available evidence such as:

```text
cross-track activity
RMS / LUFS-S
spectral centroid / broad spectral balance
chroma
stereo relation
crest / spectral flux
```

Use:

```text
audio_section_map()
```

to obtain:

```text
structural boundary candidates
boundary strength + dominant evidence
S01/S02/... ranges
neutral A/B/C/... recurring families
strong section-to-section similarity pairs
coverage gaps / warnings
```

For one track across the map:

```text
audio_track_story(track, map_id)
```

returns section-scoped activity/energy/spectrum/stereo/temporal/tonal evidence, coverage/data quality, adjacent-section current-minus-previous deltas, recurring-family per-dimension variation, and relative per-metric extrema.

For many tracks inside one section:

```text
audio_section_profile("S02", map_id)
```

returns section-level per-track evidence and related/same-family sections.

For a bounded project-level shortlist of track pairs whose measured relationship changes across sections/families:

```text
audio_section_relationships(map_id)
```

The relationship layer uses common activity plus coarse spectral-shape, relative-level and stereo-width evidence to rank **inspection priority**. Master is excluded by default, candidates and returned pairs are bounded, and insufficient coverage blocks pair evidence.

Critical relationship rules:

- `shortlist_priority` is not a masking probability, audibility probability, mix-problem probability, quality score, or processing recommendation;
- `B - A` descriptors preserve direction only; they do not imply which track should be processed;
- a pair appearing in one family and disappearing in another is a measured context change, not proof that one context is wrong;
- current deep masking/stereo/temporal pair tools remain recent-window based;
- therefore replay/select the relevant section before using those recent-window pair tools as deeper evidence for a historical section;
- missing or insufficient pair coverage must not create a false conflict.

General structure/Track Story rules:

- boundary strength is novelty evidence, not calibrated probability;
- A/B/C are recurrence families, **not** automatic Intro/Verse/Chorus/Drop labels;
- exact DAW markers, Playlist labels, project metadata or explicit user structure are authoritative for exact naming;
- missing Song Memory is not silence and is not automatically a boundary;
- Track Story low activity is not automatically muting or a track-role change;
- Track Story measurements do not prove Bass/Vocal/Drums role from audio alone;
- adjacent deltas are descriptive evidence, not automatic inverse processing instructions;
- same-family variation remains separate by dimension, not one universal consistency/quality score;
- supporting tracks are aligned by overlapping DAW time, not equal instance-local epoch numbers;
- a Track Story target may select its own best-overlapping retained epoch even if it was not part of the map's original `max_tracks` set;
- `map_id` is MCP-session memory, not a persistent project ID;
- no structure, Track Story, or relationship shortlist result implies a processing action.

See `references/section-structure.md`, `references/track-story.md`, and `references/section-relationships.md`.

## Adaptive Analysis and performance control

The VST3 exposes:

```text
Parameter ID: analysis_profile
Display name: Analysis Profile
0 Eco
1 Balanced
2 Mix
3 Full
```

Profiles control Analyzer computation only:

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

`Full` remains the default for backward compatibility.

Current control-capable Analyzer builds can change this Analyzer-owned performance parameter directly through:

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

These tools **do not** grant general DAW write access. EQ, compression, gain, pan, routing, synth, automation, arrangement and other sound/project writes remain the responsibility of the actual DAW-control MCP.

Keep two confirmations separate:

```text
control_acknowledged  VST3 accepted/applied the profile request
telemetry_confirmed   a measurement frame also reports the target profile
```

The control ACK can work while playback is stopped. Fresh telemetry normally requires new audio processing.

If a control request receives no ACK, do not assume success. An older VST3 may lack the local control receiver. A DAW-control MCP that can write the historical `analysis_profile` parameter may be used as a compatibility fallback, followed by `audio_analysis_status()` verification.

Runtime telemetry:

```text
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
```

`worker_load_ratio` is background Analyzer-worker busy time, **not DAW realtime audio-thread CPU usage**.

See `references/performance-evidence.md`.

## Closed-loop verification

Use verification when the user asks the Agent to **change the DAW and verify the measured result**.

```text
audio_project_status()
-> deterministic Identify binding if needed
-> ensure required evidence is enabled
-> play the intended comparison passage
-> audio_begin_verification(...)
-> inspect ready_for_external_change / baseline_blockers
-> external FL Studio control MCP makes the intended sound/project change
-> external control MCP reads back actual host state
-> replay a comparable passage
-> audio_complete_verification(...)
```

`controlled_comparison=true` means only that technical A/B guardrails passed. `closed_loop_complete=true` additionally requires caller-supplied actual host readback. Neither means the change is better or should be kept.

Analyzer Profile control ACK is only an Analyzer configuration acknowledgement. It does not replace actual host readback for unrelated DAW/plugin changes.

Current verification remains recent-window based, not yet transport-anchored to an exact DAW-time range.

See `references/verification-evidence.md`.

## Evidence layers

Tonal:

```text
audio_tonal_profile()
audio_tonal_compare()
```

Keep chroma, tonal-center ranking, entropy, coverage and single-F0 evidence separate. Prefer exact DAW/MIDI symbolic data for exact facts.

Stereo:

```text
audio_stereo_profile()
audio_stereo_compare()
```

Keep signed L/R correlation, Side/Mid energy, decorrelation proxy, negative-cross evidence and frequency-dependent relation separate.

Masking:

```text
audio_masking_evidence()
audio_project_masking_scan()
```

ERB is feature re-binning, not a gammatone/cochlear filterbank. Scores are heuristic evidence, not audible-masking probabilities or processing instructions.

Temporal:

```text
audio_temporal_profile()
audio_temporal_compare()
```

Spectral Flux and RMS Rise are change evidence, not annotated onset ground truth.

## Signal, feature and timeline validity

When relevant, inspect:

```text
signal_present
analysis_valid
active_ratio
analysis_features
temporal_supported / temporal_valid
stereo_v08_supported / stereo_v08_valid
semantic_v09_supported / semantic_v09_valid
transport_v12_supported
transport_epoch
estimated_analysis_lag_ms
dropped_blocks
data_quality.coverage_ratio
section reference.coverage_ratio
section coverage_gaps / warnings
Track Story sections[].coverage_ratio / evidence_available / warnings
Section Relationships section_evidence[].coverage_ratio_a / coverage_ratio_b / evidence_available
Section Relationships selected_transport_epochs
```

`null` means unavailable, not zero.

## Suggested Agent instruction

```text
Use the ai-analyzer-flstudio Skill only as a technical MCP usage and measurement-semantics reference.
Start with audio_project_status and establish deterministic Identify bindings for unbound Analyzer instances.
For whole-song, past-passage, or latency-sensitive work, call audio_song_status. After sufficient Song Memory exists, prefer audio_section_map. Use audio_track_story when the question is how one track evolves across sections; use audio_section_profile when the question is what multiple tracks do inside one section; use audio_section_relationships when the question is which bounded track pairs change across sections/families and merit deeper inspection. Request raw timeline bins or specialized evidence only when still needed.
Treat audio_section_relationships shortlist_priority only as an inspection-ranking heuristic. It is not a masking/mix-problem probability or processing instruction. Preserve B-minus-A directionality without assuming which track should change. Before using current recent-window masking/stereo/temporal pair tools as evidence for a historical section, replay/select that section first.
Treat A/B/C section families only as neutral structural recurrence evidence. Never invent Verse/Chorus/Drop labels when exact DAW/project structure is unavailable; prefer exact markers/project metadata when available.
Treat Track Story activity/deltas/family spreads as descriptive evidence only. Missing coverage is not silence, low activity is not automatically muting, and measurements alone do not prove a track role or required processing move.
Treat transport_epoch as an instance-local continuous playback pass. For cross-track structure, align by DAW-time coverage rather than numeric epoch equality.
Inspect data age, estimated Analyzer lag, dropped blocks, coverage gaps, and coverage ratios before song-wide claims. Missing evidence is not silence.
Use the minimum Analysis Profile that exposes the required evidence. Prefer audio_set_analysis_profile or audio_set_project_analysis_profile for the Analyzer's own profile on control-capable builds, require a valid control ACK for a requested change, and verify fresh telemetry when available. Never generalize this narrow exception into DAW/plugin writes; real sound/project writes and host readback belong to the actual FL Studio control MCP.
Treat null as unavailable, not zero. Prefer exact DAW/MIDI/project metadata for exact symbolic facts.
When the task changes the DAW and asks for verification, call audio_begin_verification before the external write, read actual host state back, replay a comparable passage, and then call audio_complete_verification.
Never turn Analyzer measurements, section families, Track Story, relationship shortlists, transport memory, or performance profiles into automatic mixing, mastering, harmony, tuning, semantic section, or processing instructions.
```

## References

```text
references/analyzer-mcp.md          MCP tools and selector rules
references/parameters.md            measurement parameter semantics
references/performance-evidence.md  adaptive profiles and performance/control telemetry
references/song-memory.md           transport timeline, pass and latency semantics
references/section-structure.md      boundary / recurrence / section-profile semantics
references/track-story.md            one-track-across-sections evidence semantics
references/section-relationships.md  bounded pair shortlist across sections/families
references/masking-evidence.md      masking evidence and limitations
references/stereo-evidence.md       Mid/Side/stereo evidence semantics
references/tonal-evidence.md        chroma/tonal/harmonic evidence semantics
references/verification-evidence.md closed-loop verification semantics
```