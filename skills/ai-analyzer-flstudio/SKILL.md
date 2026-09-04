---
name: ai-analyzer-flstudio
description: Technical usage skill for Cherry Studio + AI Audio Analyzer MCP. Teaches deterministic Analyzer discovery/binding, adaptive Analysis Profile selection, transport-aware Song Memory, explainable song-section structure, latency/data-quality handling, measurement validity, evidence semantics, performance telemetry, and controlled Before/After verification around externally controlled DAW changes. It does not prescribe a mixing style, LUFS target, EQ/compression/sidechain/stereo recipe, semantic section label, key change, harmony edit, or aesthetic decision.
---

# AI Audio Analyzer MCP Usage Skill

Use this Skill for two things only:

1. call **AI Audio Analyzer MCP** correctly;
2. interpret returned measurements/evidence without overstating them.

It is **not** a mixing, mastering, harmony, arrangement, tuning, or style guide. Measurements, section families, transport memory, and Analysis Profiles do not imply a mandatory processor, parameter value, semantic section name, key change, chord edit, stereo action, or aesthetic choice.

## 1. Start with project state

For a project-level request, begin with:

```text
audio_project_status()
```

Use it to check Bridge/OSC health, live instances, deterministic bindings, active input, stale streams, duplicate names, and Master candidates.

Only descend when needed:

```text
audio_bridge_status()
audio_list_tracks()
audio_instance_map()
```

Do not call every tool mechanically.

For a **whole song, a past passage, section-to-section evolution, or mixing/mastering work where Agent/tool latency matters**, next call:

```text
audio_song_status()
```

The Analyzer observes continuously; the LLM does not need to observe continuously.

If enough of the intended pass has been captured, prefer a structural compression step before requesting raw timeline detail:

```text
audio_section_map()
```

Then inspect only the sections that matter:

```text
audio_section_profile(section_id, map_id)
```

Use `audio_song_timeline()` only when the question still requires raw DAW-time evolution.

If the request involves many Analyzer instances, CPU/load concerns, or a measurement family that may be disabled, also inspect:

```text
audio_project_performance()
audio_analysis_status(track)
```

## 2. Deterministic Analyzer ↔ FL Mixer mapping

The VST3 exposes:

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

When an Analyzer is unbound and the connected FL Studio control MCP can access plugin parameters:

```text
find the real Mixer Track / Plugin Slot
→ read current Identify value
→ toggle Identify
→ audio_last_identify()
→ verify fresh + unconsumed event
→ audio_bind_last_identified(fl_track_index, fl_track_name, slot)
→ audio_instance_map()
```

One Identify event may be consumed only once.

Preferred selector order:

```text
mixer:<index>/slot:<slot>
→ unique FL Mixer track name
→ runtime UUID
→ unique Analyzer display name
```

If multiple Analyzer instances exist on one Mixer Track, include `slot`.

Never guess mapping from track names, spectrum, chroma, or musical content when Identify is available.

## 3. Analysis Profile is a performance control

The VST3 exposes:

```text
Parameter ID: analysis_profile
Display name: Analysis Profile
Choices:
0 Eco
1 Balanced
2 Mix
3 Full
```

Profile groups:

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

`Full` is the default for backward compatibility.

Profiles change **Analyzer computation**, not the audio signal and not artistic quality.

Minimum profile by evidence family:

```text
Transport / Identify / signal / Peak-RMS-Crest   Eco
LUFS / True Peak                                  Balanced
Spectrum / basic masking                          Balanced
Deep Mid/Side / stereo                            Balanced
Temporal profile/compare                          Mix
Masking with temporal interaction                 Mix
Chroma / tonal / single-F0 evidence               Full
```

A section map can use whichever evidence was actually captured. Missing feature families remain unavailable rather than becoming zero-valued structural features.

Analyzer MCP does **not** write DAW parameters. When a different profile is needed:

```text
audio_analysis_status(target)
→ remember current profile
→ use the actual FL Studio control MCP to inspect the real plugin parameters
→ change Analysis Profile through that control MCP
→ read the actual host parameter state back
→ audio_analysis_status(target)
→ verify the expected feature group is enabled
→ collect the required measurement window/pass
→ call the needed Analyzer tool
→ restore the previous profile when appropriate
→ verify the restored Analyzer state
```

Do not invent FL Studio MCP tool names. Do not set every Analyzer to `Full` merely because one track needs tonal analysis.

Detailed rules: `references/performance-evidence.md`.

## 4. Whole-song memory and Agent latency

Do **not** assume the newest Analyzer frame corresponds to the audio the user hears at the instant the LLM reads it.

The chain can contain:

```text
Analyzer worker backlog
OSC/MCP transport
LLM reasoning
external control tool calls
human/host interaction
```

Protocol 1.2 addresses this by attaching DAW transport context and keeping bounded song-time memory.

Use:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(track, resolution_seconds=5, ...)
```

Recommended whole-song flow:

```text
audio_project_status()
→ fix mapping/readiness if necessary
→ audio_song_status()
→ play/capture the song or target passage
→ allow Analyzer to keep collecting while the Agent reasons/works
→ audio_section_map()
→ audio_section_profile() for relevant sections
→ audio_song_overview() when a compact pass-level summary helps
→ audio_song_timeline() only when raw time evolution is still required
→ drill into Temporal / Masking / Stereo / Tonal evidence only as needed
```

Do not repeatedly poll all Analyzer tools during playback just to avoid missing an event.

### Transport epoch

`transport_epoch` means one **instance-local continuous playback pass**.

A new epoch can begin on:

```text
stopped → playing
seek / playhead jump
loop jump
other detected transport discontinuity
```

The worker discards queued pre-jump FIFO audio and resets pass-dependent Loudness/Temporal/Semantic state before measuring the new epoch.

Never assume equal epoch numbers from independently loaded Analyzer instances are a permanent project-wide pass identity.

### Data quality

Keep these distinct:

```text
estimated_analysis_lag_ms
  Analyzer FIFO + FFT-window estimate only.
  Not network latency and not LLM latency.

data_age_seconds
  Wall-clock age of retained MCP evidence.
  Old evidence can still be exactly the requested historical song range.

dropped_blocks
  Cumulative Analyzer FIFO push failures.
  Non-zero means some input audio was not measured.

coverage_ratio
  Fraction of a requested/coarse interval represented by retained 100 ms coverage slots.
```

Transport coordinates are useful for song/section reasoning, not sample-accurate edits, transient placement, or phase alignment.

Current Song Memory resolutions:

```text
1 2 5 10 15 30 seconds
```

Prefer the coarsest resolution that answers the question.

Detailed rules: `references/song-memory.md`.

## 5. Explainable song structure

Use the structure layer to compress a captured song into boundaries and recurring contexts before doing detailed mix analysis.

```text
audio_section_map(
  reference_track=None,
  transport_epoch=None,
  min_section_seconds=8,
  sensitivity=0.55,
  family_similarity=0.78,
  max_sections=48,
  max_tracks=32
)
```

The detector compares multi-scale left/right contexts using available evidence from:

```text
cross-track activity
energy / loudness
spectral balance
chroma
stereo
dynamics
temporal change
```

Returned `boundary strength` is structural novelty evidence, not a calibrated probability.

Sections are assigned neutral recurring families:

```text
S01 A
S02 B
S03 C
S04 B
S05 C
```

Never automatically translate those families into:

```text
A = Intro
B = Verse
C = Chorus
```

`family_id` only means substantial structural recurrence under the current explainable model.

Prefer exact DAW/project structure sources for exact names:

```text
markers
Playlist/arrangement labels
pattern names
MIDI/project annotations
explicit user-provided structure
```

If exact project metadata conflicts with Analyzer audio inference, exact project metadata wins for semantic naming.

### Epoch alignment across tracks

The section reference uses one requested/latest reference epoch. Supporting tracks are selected by **DAW-time coverage overlap**, not by equal numeric epoch IDs.

A legitimate map may use:

```text
Master epoch 7
Kick epoch 3
Vocal epoch 11
```

when those passes cover the same song-time range.

### Missing evidence

A coverage gap is not silence and not a transition. Inspect:

```text
coverage_gaps
reference.coverage_ratio
warnings
```

If coverage is weak, prefer replaying the target range over lowering quality expectations merely to force a section map.

### Section drill-down

After a map is generated:

```text
audio_section_profile("S02", map_id)
```

Use it to inspect:

```text
same-family sections
related section similarities
per-track activity / levels / spectral / stereo / tonal summaries
selected transport epoch for each track
per-track data quality
```

Then choose only the deeper evidence that the question needs.

`map_id` is bounded MCP-session memory, not a persistent project ID.

Detailed rules: `references/section-structure.md`.

## 6. Validate data before interpretation

For content-related measurements inspect:

```text
signal_present
analysis_valid
active_ratio
analysis_features
```

Signal gate is approximately:

```text
close   below -50 dBFS for ~0.4 s
reopen  above -48 dBFS
```

`null` means **unavailable**, not numeric zero.

Feature-specific validity includes:

```text
Temporal:
  temporal_supported
  temporal_valid
  temporal_window_seconds

Deep stereo:
  stereo_v08_supported
  stereo_v08_valid
  stereo_frames

Tonal / semantic:
  semantic_v09_supported
  semantic_v09_valid
  valid_frames
  evidence_quality.mean_chroma_energy_ratio
  evidence_quality.normalized_pitch_class_entropy
  evidence_quality.tonal_center_top2_margin
  evidence_quality.valid_frame_ratio

Transport / Song Memory:
  transport_v12_supported
  transport_epoch
  estimated_analysis_lag_ms
  dropped_blocks
  data_quality.coverage_ratio

Section structure:
  reference.coverage_ratio
  boundaries[].context_coverage
  coverage_gaps
  warnings
```

The **feature mask is authoritative**; disabled measurements are unavailable even if append-only compatibility positions physically exist.

## 7. Performance telemetry

Use:

```text
audio_analysis_status(track)
audio_project_performance()
```

Important fields:

```text
analysis_profile
analysis_features
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
```

`worker_load_ratio` is the Analyzer background-worker busy ratio, not DAW realtime CPU. Sustained FIFO growth can indicate measurement lag. Do not convert performance telemetry into audio-quality judgments.

## 8. Choose the smallest tool that answers the question

Project readiness:

```text
audio_project_status()
```

Whole-song context:

```text
audio_song_status()
audio_song_overview()
```

Structural compression:

```text
audio_section_map()
audio_section_profile()
```

Raw historical timeline only when needed:

```text
audio_song_timeline(...)
```

Project performance:

```text
audio_project_performance()
audio_analysis_status(track)
```

Recent project overview:

```text
audio_mix_overview(seconds=10, max_tracks=32)
```

Stable recent single track:

```text
audio_average(track, seconds=5)
```

Current frame / connection state:

```text
audio_snapshot(track)
```

### Temporal evidence

Requires Temporal (`Mix` or `Full`):

```text
audio_temporal_profile(track, seconds=5)
audio_temporal_compare(track_a, track_b, seconds=5, low_hz=40, high_hz=160, alignment_tolerance_ms=80)
```

Spectral Flux and RMS Rise are change evidence, not ground-truth onset labels.

### Masking evidence

Spectrum requires `Balanced` or higher. Temporal interaction requires `Mix` or `Full`.

```text
audio_project_masking_scan(...)
audio_masking_evidence(...)
```

ERB handling is re-binning, not a gammatone/cochlear filterbank. Scores are heuristic evidence, not audible-masking probabilities.

Legacy spectrum-only paths remain:

```text
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
```

### Deep stereo evidence

Requires Stereo (`Balanced` or higher):

```text
audio_stereo_profile(track, seconds=5)
audio_stereo_compare(track_a, track_b, seconds=5)
```

Keep signed correlation, Side/Mid energy, decorrelation proxy, negative-cross evidence, and frequency-dependent stereo relation independent.

### Tonal / music-semantic evidence

Requires Semantic (`Full`):

```text
audio_tonal_profile(track, seconds=8)
audio_tonal_compare(track_a, track_b, seconds=8)
```

Do not use audio inference to replace exact symbolic project data. Tonal-center correlation is not key probability; single-F0 evidence is not note transcription.

### Master technical summary

```text
audio_master_status(track="Master")
```

It summarizes measurements; it does not define universal mastering targets.

## 9. Snapshot A/B

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

Use comparable passages, similar windows, comparable active coverage, and the same relevant feature availability.

Deltas are `After - Before`.

Snapshot tools do not independently reset Loudness. For protocol-1.2 instances, LUFS-I / pass-max True Peak accumulate inside the current transport epoch; playback start/seek/loop discontinuity creates a new epoch and Loudness state.

## 10. Controlled external-change verification

Use when the Agent coordinates a real DAW modification through an external control MCP and the user wants measured verification.

```text
audio_begin_verification(...)
→ inspect ready_for_external_change / baseline_blockers
→ external control MCP performs the real write
→ external control MCP reads actual host state back
→ replay the intended passage
→ audio_complete_verification(...)
```

`host_readback` must represent actual state returned by the external control MCP, not the intended value.

`controlled_comparison=true` is a technical comparability gate only.

`closed_loop_complete=true` additionally requires supplied host readback.

Neither means After is better, the change should be kept, or the processor setting is correct.

Current verification remains recent-window based; do not claim it is already transport-anchored to an exact DAW-time range.

Detailed rules: `references/verification-evidence.md`.

## 11. Critical distinctions

Always keep these distinctions:

- Sample Peak ≠ True Peak.
- RMS ≠ LUFS.
- LUFS-S ≠ LUFS-I.
- Protocol-1.2 LUFS-I pass scope ≠ permanent project loudness history.
- Analyzer spectrum dB is not calibrated SPL.
- Stereo Correlation ≠ Side/Mid energy.
- Low correlation ≠ anti-correlation.
- Spectral overlap / temporal overlap / masking evidence are not audible-masking probabilities.
- Chroma is not note probability or MIDI transcription.
- Tonal-center correlation is not key probability.
- Harmonic F0 candidate is not a detected musical note.
- `transport_epoch` is instance-local pass identity, not a persistent project hash.
- `estimated_analysis_lag_ms` is Analyzer backlog/window latency, not total Agent latency.
- `data_age_seconds` is not the same thing as invalid historical evidence.
- section `boundary strength` is novelty evidence, not formal-boundary probability.
- section `family_id` is recurrence evidence, not Verse/Chorus/Drop identity.
- a Song Memory coverage gap is not silence or a section boundary.
- `map_id` is session memory, not a persistent project/arrangement ID.
- topology fingerprint is not a persistent DAW-project hash.
- `host_readback` is caller-supplied control-MCP evidence, not Analyzer-verified host state.
- `controlled_comparison` is technical comparability, not artistic quality.
- `worker_load_ratio` is background Analyzer-worker load, not realtime DAW CPU.
- Analysis Profile is computation scope, not audio quality.
- `null` is unavailable, not zero.

Detailed references:

```text
references/parameters.md
references/performance-evidence.md
references/song-memory.md
references/section-structure.md
references/masking-evidence.md
references/stereo-evidence.md
references/tonal-evidence.md
references/verification-evidence.md
references/analyzer-mcp.md
```

## 12. Boundary with FL Studio control MCP

AI Audio Analyzer MCP owns:

```text
measure
read Analyzer state
remember transport-aligned evidence
infer explainable structural boundaries / neutral recurrence families
compare
identity/binding evidence
performance/profile readback
verification measurement conditions
```

FL Studio control MCP owns:

```text
DAW topology / project data
exact markers / Playlist / arrangement metadata when exposed
plugin access
Analysis Profile writes
artistic/technical parameter writes
actual host state readback
```

Never invent control tools, controls, notes, write success, profile state, semantic section labels, or readback values.

## 13. Output discipline

When citing Analyzer evidence, include enough context to make it auditable:

```text
instance / selector
DAW-time range / transport epoch when Song Memory is used
section_id / family_id / map_id when structure evidence is used
Analysis Profile / enabled feature group when relevant
measurement window or timeline resolution
signal validity / active ratio
data age / estimated Analyzer lag / dropped blocks / coverage when relevant
boundary evidence / recurrence components when relevant
evidence-quality fields
frequency / stereo band / ERB region / pitch-class context when relevant
alignment quality for temporal evidence
verification topology / coverage / readback context when relevant
measurement/evidence value
what the metric can and cannot establish
```

Do not present these as Analyzer-measured facts:

- a sound should be warmer/brighter/wider/louder/narrower;
- a genre must hit a fixed LUFS number;
- a frequency must be cut/boosted by a specific amount;
- masking evidence automatically requires EQ/sidechain;
- stereo evidence automatically requires mono/narrowing/widening/phase rotation;
- the top tonal-center candidate is certainly the song key;
- an F0 candidate is certainly the played note;
- `A/B/C` section families are certainly Intro/Verse/Chorus/Drop;
- a structure boundary necessarily requires a processing change;
- `controlled_comparison=true` means After is better;
- `Full` means higher audio quality than `Eco`;
- `worker_load_ratio` is the DAW audio-thread CPU percentage.

Those are artistic, symbolic, processing, or external-host-state judgments outside the measurement scope of this MCP and Skill.