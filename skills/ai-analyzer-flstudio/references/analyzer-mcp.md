# AI Audio Analyzer MCP Reference

This reference describes MCP tools, selector rules, Analyzer-owned Analysis Profile control/readback, transport-aware song memory, explainable section structure, call order, validity checks, controlled verification, and OSC compatibility.

Related semantics:

```text
parameters.md
performance-evidence.md
song-memory.md
section-structure.md
masking-evidence.md
stereo-evidence.md
tonal-evidence.md
verification-evidence.md
```

Current MCP 1.2 exposes **36 tools**:

```text
audio_bridge_status()
audio_list_tracks()
audio_last_identify(max_age_seconds=10)
audio_bind_last_identified(fl_track_index, fl_track_name, slot, max_age_seconds=5)
audio_instance_map()
audio_snapshot(track)
audio_average(track, seconds=5)
audio_stereo_bands(track)
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
audio_master_status(track="Master")
audio_project_status()
audio_mix_overview(seconds=10, max_tracks=32)
audio_capture_snapshot(name, seconds=5)
audio_list_snapshots()
audio_compare_snapshots(before, after)
audio_temporal_profile(track, seconds=5)
audio_temporal_compare(track_a, track_b, seconds=5, low_hz=40, high_hz=160, alignment_tolerance_ms=80)
audio_masking_evidence(track_a, track_b, seconds=5, alignment_tolerance_ms=80, max_regions=8)
audio_project_masking_scan(seconds=5, max_pairs=8, alignment_tolerance_ms=80)
audio_stereo_profile(track, seconds=5)
audio_stereo_compare(track_a, track_b, seconds=5)
audio_tonal_profile(track, seconds=8)
audio_tonal_compare(track_a, track_b, seconds=8)
audio_analysis_status(track)
audio_project_performance()
audio_set_analysis_profile(track, profile, timeout_seconds=1.0)
audio_set_project_analysis_profile(profile, tracks=None, timeout_seconds=1.0)
audio_song_status()
audio_song_timeline(track, resolution_seconds=5, transport_epoch=None, start_seconds=None, end_seconds=None, max_bins=240)
audio_song_overview(transport_epoch=None, max_tracks=32)
audio_section_map(reference_track=None, transport_epoch=None, min_section_seconds=8, sensitivity=0.55, family_similarity=0.78, max_sections=48, max_tracks=32)
audio_section_profile(section_id, map_id=None, max_tracks=32, max_related=8)
audio_begin_verification(label, seconds=5, target_selectors=None)
audio_complete_verification(verification_id, seconds=0, change_summary="", host_readback="")
audio_verification_status(verification_id="")
```

## Recommended hierarchy

Do not call all 36 tools by default.

```text
project readiness
→ audio_project_status()

whole-song / delayed Agent context
→ audio_song_status()
→ audio_song_overview()

song structure / recurring arrangement context
→ audio_section_map()
→ audio_section_profile() only for relevant sections
→ audio_song_timeline() only when raw track/time evolution is still needed

many instances / performance concern
→ audio_project_performance()

one instance feature/profile check
→ audio_analysis_status()

minimum evidence unavailable
→ audio_set_analysis_profile() only when needed
→ audio_set_project_analysis_profile() only for intentionally selected/all live instances

recent project state
→ audio_mix_overview()

recent stable single-track measurement
→ audio_average()

then choose only the needed evidence family:
→ temporal
→ masking
→ stereo
→ tonal

external DAW change + measured verification
→ audio_begin_verification()
→ external control MCP write + actual host readback
→ audio_complete_verification()
```

The LLM is not expected to poll the Analyzer continuously. Song Memory exists so the Analyzer can keep observing while the model is thinking or waiting for another tool. The section layer then compresses that remembered evidence into structural boundaries and recurring neutral families before the LLM chooses deeper tools.

## Deterministic Identify mapping

Host-visible parameter:

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

Recommended flow:

1. use the real FL Studio control MCP to locate the Mixer Track / Plugin Slot;
2. inspect the actual plugin parameters and find `Identify`;
3. read current value;
4. toggle it;
5. immediately call `audio_last_identify()`;
6. verify the event is fresh and unconsumed;
7. call `audio_bind_last_identified(fl_track_index, fl_track_name, slot)`;
8. repeat one instance at a time;
9. verify with `audio_instance_map()`.

Do not assume FL Studio MCP tool names. Use the tools it actually exposes.

Runtime UUIDs, Identify events, and bindings are session-scoped.

## Selector rules

Preferred order:

```text
mixer:<track_index>/slot:<slot>
→ unique FL Mixer track name
→ runtime UUID
→ unique Analyzer display name
```

Examples:

```text
mixer:7
mixer:7/slot:9
fl:7
fl:7/slot:9
```

If multiple Analyzer instances exist on one Mixer Track, include `slot`.

## Analysis Profile control/readback

Host-visible parameter:

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

`Full` is the default for backward compatibility.

Current control-capable Analyzer builds expose:

```text
audio_set_analysis_profile(track, profile, timeout_seconds=1.0)
audio_set_project_analysis_profile(profile, tracks=None, timeout_seconds=1.0)
```

These are deliberately narrow Analyzer-owned write tools. They may change only the Analyzer's own measurement-performance `Analysis Profile`; they do not grant permission to change EQ, gain, pan, compression, routing, synth, automation, project state, or other plugins.

Control flow:

```text
MCP
→ loopback-only UDP command
→ deterministic candidate ports derived from target runtime UUID
→ matching VST3 network receiver
→ queue request
→ JUCE message thread changes host-visible analysis_profile
→ request-scoped loopback ACK
```

Important result fields:

```text
ok
changed
control_acknowledged
telemetry_confirmed
profile
profile_display
profile_index
runtime_id
binding
```

Keep these separate:

```text
control_acknowledged
  target VST3 accepted/applied the host-visible profile request.

telemetry_confirmed
  retained/new Analyzer telemetry reports the requested profile.
```

The control ACK can succeed while playback is stopped. Fresh telemetry normally requires a new measurement frame.

If no ACK is received, do not assume success. The VST3 may be an older build without Analyzer-owned local control. If the connected DAW-control MCP can write the historical `analysis_profile` host parameter, it may be used as a compatibility fallback, then verified through Analyzer telemetry.

Status/readback:

```text
audio_analysis_status(track)
```

Important returned fields:

```text
adaptive_analysis_supported
profile
profile_index
feature_mask
features
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
control_parameter
```

For project-wide profile/load inspection:

```text
audio_project_performance()
```

`worker_load_ratio` is background Analyzer-worker busy time, not DAW realtime audio-thread CPU.

Detailed semantics: `performance-evidence.md`.

## Signal and validity

Approximate signal gate:

```text
close threshold   -50 dBFS
reopen threshold  -48 dBFS
hold              ~0.4 s
```

Rules:

- `null` means unavailable, not zero;
- inspect active/valid coverage for window tools;
- stale streams are not current state;
- when adaptive telemetry exists, `analysis_features` is authoritative about which feature families are actually enabled;
- append-only compatibility positions may exist in the OSC packet even when a profile disabled that family; Bridge parsing invalidates those values before interpretation.

Minimum profiles:

```text
Transport / signal / Core            Eco
LUFS / True Peak                     Balanced
Spectrum / basic masking             Balanced
Deep stereo                          Balanced
Temporal                             Mix
Tonal / chroma / harmonic            Full
```

A section map can use whichever evidence was actually captured. Missing feature families remain missing rather than being converted into zero-valued structure evidence.

## Transport-aware song tools

Protocol 1.2 adds transport and data-quality context so LLM reasoning latency is not confused with audio time.

### `audio_song_status()`

Use for whole-song readiness and latency quality.

Important fields include:

```text
transport_ready
song_memory_ready
max_estimated_analysis_lag_ms
max_dropped_blocks
continuous_passes
instances[].transport_time_seconds
instances[].transport_epoch
instances[].data_age_seconds
instances[].estimated_analysis_lag_ms
instances[].dropped_blocks
warnings
```

`transport_epoch` is an **instance-local continuous playback pass**, not a permanent project-wide revision ID. Playback start, seek, loop jump, or another detected discontinuity begins a new epoch.

### `audio_song_timeline()`

Returns retained DAW-time bins for one track and one continuous pass.

Available resolutions:

```text
1 2 5 10 15 30 seconds
```

Use the coarsest resolution that can answer the question. Do not send a full song as hundreds of one-second bins unless that granularity is truly required.

Returned `data_quality` may include:

```text
mean_estimated_analysis_lag_ms
max_estimated_analysis_lag_ms
dropped_blocks_cumulative
data_age_seconds
coverage_ratio
```

### `audio_song_overview()`

Returns a compact whole-pass summary across Analyzer instances. It does not assign semantic musical-form names.

### Latency semantics

`estimated_analysis_lag_ms` is Analyzer-side FIFO/window latency. It does not include OSC/MCP/LLM/external-control latency.

Transport coordinates are estimates corrected for queued FIFO audio and FFT-window center. They are intended for song/section reasoning, not sample-accurate edits or phase alignment.

Detailed semantics: `song-memory.md`.

## Explainable section structure

The section layer consumes retained Song Memory; it does not add OSC fields or realtime DSP work.

### `audio_section_map()`

Use after enough of the target pass has been captured. It detects section-scale novelty using multi-scale left/right comparisons and groups recurring sections into neutral `A/B/C/...` families.

Default boundary evidence includes:

```text
cross-track activity change
RMS / LUFS-S change
spectral centroid + broad spectral balance change
chroma change
stereo correlation / width change
crest change
spectral-flux change
```

Important fields include:

```text
map_id
reference
boundaries[].time_seconds
boundaries[].strength
boundaries[].dominant_evidence
sections[].section_id
sections[].family_id
sections[].start_seconds
sections[].end_seconds
sections[].reference_summary
sections[].active_tracks
recurring_similarity_pairs
coverage_gaps
warnings
```

`boundary strength` is structural novelty evidence, not a calibrated boundary probability.

`family_id` is a neutral recurrence class. Never silently map `A/B/C` to `Intro/Verse/Chorus/Drop`.

Exact DAW markers, Playlist labels, project metadata, MIDI annotations, or explicit user structure are authoritative for exact names. An LLM may propose a semantic name only when it has additional supporting context and should state uncertainty when the label is inferred.

Supporting Analyzer instances are aligned by overlapping DAW-time coverage. Equal numeric `transport_epoch` values across instances are not required and must not be assumed.

Missing Song Memory is exposed as coverage gaps and must not be interpreted as silence or a structural boundary.

### `audio_section_profile()`

Call after `audio_section_map()` when one section needs deeper context. Keep the returned `map_id` for deterministic follow-up.

The profile returns:

```text
section / family identity
same-family sections
related sections + similarity components
reference summary
per-track section summaries
per-track selected transport epoch
data quality
```

Use it to decide which tracks/relationships deserve deeper Temporal, Masking, Stereo or Tonal queries. It does not prescribe processing.

Section maps are bounded MCP-session memory and are not persistent project identifiers.

Detailed semantics: `section-structure.md`.

## Core / project tools

### `audio_project_status()`

Use first for project readiness. Important fields include:

```text
project_ready
audio_ready
live_count
bound_count
unbound_count
active_count
stale_count
instances
warnings
```

### `audio_mix_overview()`

Returns recent project-level summaries and coarse `potential_spectral_conflicts`. These are candidates, not proof of audible masking.

### `audio_snapshot()`

Latest frame/current state. Do not substitute it for a stable multi-second observation or a historical DAW-time range.

### `audio_average()`

Recent stable window. Content-dependent averages use active frames.

### `audio_master_status()`

Technical summary only; no universal mastering target is defined.

## Temporal tools

Requires Temporal (`Mix` or `Full`).

```text
audio_temporal_profile(track, seconds=5)
audio_temporal_compare(track_a, track_b, seconds=5, low_hz=40, high_hz=160, alignment_tolerance_ms=80)
```

Typical evidence:

```text
spectral_flux_mean
spectral_flux_peak
rms_rise_peak_db
low_band_40_160_energy_db
onset/change candidates
aligned pairs
band-envelope correlation
normalized band temporal overlap
alignment offset
```

Change candidates are heuristic, not annotated onset ground truth.

## Masking tools

Spectrum requires `Balanced` or higher; temporal interaction evidence requires `Mix`/`Full`.

```text
audio_masking_evidence(...)
audio_project_masking_scan(...)
```

Current model:

```text
32 Analyzer Mid-spectrum features
→ 16 equal ERB-rate regions
→ relative spectral occupancy
→ directional relative-level weighting
→ temporal overlap when available
```

`auditory_band_model.filterbank=false`: this is re-binning, not a gammatone/cochlear filterbank.

`masking_evidence_score` is not an audible-masking probability.

Legacy spectrum-only tools remain:

```text
audio_compare_tracks()
audio_detect_masking()
```

## Stereo tools

Requires Stereo (`Balanced` or higher).

```text
audio_stereo_profile(track, seconds=5)
audio_stereo_compare(track_a, track_b, seconds=5)
```

Keep these independent:

```text
signed L/R correlation
Mid/Side energy
Side/Mid dB
1 - abs(correlation) decorrelation proxy
negative-cross evidence
20–120 Hz stereo relation
frequency-dependent stereo relation
```

Deltas from `audio_stereo_compare()` are `B - A`, not better/worse labels.

Legacy eight correlation bands:

```text
audio_stereo_bands(track)
```

## Tonal / semantic tools

Requires Semantic (`Full`).

```text
audio_tonal_profile(track, seconds=8)
audio_tonal_compare(track_a, track_b, seconds=8)
```

Main groups:

```text
chroma.normalized_power[12]
chroma.normalized_entropy
tonal_center_evidence.top_candidates[]
tonal_center_evidence.top2_margin
harmonic_alignment
evidence_quality
```

Chroma order:

```text
C C# D D# E F F# G G# A A# B
```

Tonal-center candidates are Krumhansl-Kessler major/minor profile correlations, not key probabilities.

Single-F0 fields are spectral-alignment evidence, not note transcription or pitch-confidence probability.

When exact MIDI/DAW notes, key, chords, or tuning metadata are available, use the exact project data for exact symbolic facts.

## Snapshot A/B

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

Use comparable passages, windows, active coverage, and relevant Analysis Profile/feature availability.

Delta convention:

```text
After - Before
```

Snapshot tools do not independently reset Loudness. For protocol-1.2 instances, LUFS-I accumulates within the current continuous transport epoch; a playback start/seek/loop discontinuity creates a fresh epoch and loudness state. Legacy instances retain reset/prepare-scoped LUFS-I behavior.

## Controlled verification

For a DAW modification that should be measured before/after:

```text
audio_begin_verification(
  label,
  seconds=5,
  target_selectors=[...]
)
```

Call it **before** the external artistic/technical write.

Then:

```text
external DAW-control MCP performs the real write
→ external DAW-control MCP reads actual host state back
→ replay comparable passage
→ audio_complete_verification(...)
```

`controlled_comparison` = measurement comparability guardrail only.

`closed_loop_complete` = controlled comparison plus supplied actual host readback.

Neither means the artistic change is better/correct/preferred.

Analyzer-owned Profile control ACK is not a substitute for actual host readback of unrelated DAW/plugin writes.

Current verification remains recent-window based. Transport-anchored same-DAW-range verification is not yet implemented.

Verification sessions are Bridge-session memory only.

## OSC compatibility

Analysis address:

```text
/aianalyzer/frame
```

Identify address:

```text
/aianalyzer/identify
```

The frame remains append-only:

```text
0..58      historical core / loudness / stereo / identity prefix
59..64     Temporal fields + "0.6" marker
65..111    Mid/Side + deeper stereo fields + "0.8" marker
112..123   12 chroma bins C..B
124        chroma_energy_ratio
125        single_f0_harmonic_energy_ratio
126        harmonic_f0_candidate_hz
127        "0.9" marker
128        analysis_profile index
129        analysis_feature_mask
130        worker_load_ratio
131        fifo_fill_ratio
132        fft_runs_per_second
133        semantic_runs_per_second
134        "1.1" marker
135        transport_supported
136        transport_time_seconds
137        transport_ppq_position
138        transport_bpm
139        transport_time_signature_numerator
140        transport_time_signature_denominator
141        transport_is_playing
142        transport_is_recording
143        transport_is_looping
144        transport_loop_start_ppq
145        transport_loop_end_ppq
146        transport_epoch
147        estimated_analysis_lag_ms
148        dropped_blocks
149        "1.2" marker
```

Existing indexes `0..149` are unchanged by Analyzer-owned Profile control.

Feature-mask bits:

```text
1   Core
2   Loudness
4   Spectrum
8   Stereo
16  Temporal
32  Semantic
```

Historical `bands_db` remains the 32-band Mid spectrum.

### Separate local Analyzer control revision 1

Analyzer-owned Profile control intentionally does not append a measurement field.

```text
transport        UDP loopback only
profile address  /aianalyzer/control/profile
ACK address      /aianalyzer/control/ack
scope            Analysis Profile only
revision         1
```

The VST3 chooses the first available port from 16 deterministic candidates derived from runtime UUID. MCP sends to all candidates; only the matching runtime accepts the command. The candidate range is local ports `20000..59999`.

## Multiple instances and OSC

All VST3 instances normally send measurement frames to:

```text
127.0.0.1:9855
```

Only the Bridge binds UDP 9855. VST3 instances are measurement senders, so multiple Analyzer instances do not require separate measurement ports.

Profile control is different: each live instance binds one loopback-only deterministic candidate control port. No manual user port configuration is required.