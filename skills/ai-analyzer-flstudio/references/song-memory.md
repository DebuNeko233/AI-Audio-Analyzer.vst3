# Song Timeline Memory and LLM Latency

Use this reference when the request concerns a whole song, a past musical passage, repeated playback, or any workflow where the LLM/tool round trip may be slower than the audio event being analyzed.

The central design rule is:

```text
The Analyzer observes continuously.
The LLM does not need to observe continuously.
```

The VST3 and MCP retain transport-aligned evidence so an Agent may reason several seconds later without pretending that the newest received frame is the sound currently leaving the DAW.

## Available tools

```text
audio_song_status()
audio_song_overview(transport_epoch=None, max_tracks=32)
audio_song_timeline(
  track,
  resolution_seconds=5,
  transport_epoch=None,
  start_seconds=None,
  end_seconds=None,
  max_bins=240
)
```

Use these as high-level context tools. They do not replace detailed Temporal, Masking, Stereo or Tonal tools when a specific relationship requires deeper evidence.

## Recommended whole-song workflow

```text
audio_project_status()
→ resolve/bind Analyzer instances when necessary
→ audio_song_status()
→ let the DAW play the passage/song that needs observation
→ audio_song_overview()
→ audio_song_timeline() only for tracks/time ranges that need detail
→ choose a deeper evidence family only when the question requires it
```

Do not repeatedly poll every Analyzer tool while playback runs. Song memory exists so measurement collection is decoupled from LLM reasoning latency.

## Transport epoch

`transport_epoch` is an **instance-local continuous playback pass**.

The VST3 starts a new epoch when it detects a discontinuity such as:

```text
stopped → playing
seek / playhead jump
loop jump
other substantial transport discontinuity
```

On an epoch change the Analyzer worker:

```text
discards queued pre-jump FIFO audio
resets FFT/temporal continuity state
resets Semantic cache
resets Loudness state when Loudness is enabled
```

This prevents audio from the old DAW position from being labeled as if it belonged to the new position.

### Epoch IDs are not project IDs

Do not assume:

```text
Track A epoch 5 == Track B epoch 5
```

if the instances were loaded or restarted at different times.

Epoch counters are generated independently inside each VST3 instance. Project song tools expose consistency warnings and DAW-time spans. Use those fields instead of inventing a permanent project-wide pass identity.

## DAW-time coordinates

Protocol 1.2 may expose:

```text
transport_time_seconds
transport_ppq_position
transport_bpm
transport_time_signature_numerator
transport_time_signature_denominator
transport_is_playing
transport_is_recording
transport_is_looping
transport_loop_start_ppq
transport_loop_end_ppq
transport_epoch
```

The transport coordinate attached to Analyzer evidence is an estimate for the analyzed FFT window, not merely the latest host playhead read.

The worker approximately compensates for:

```text
current Analyzer FIFO backlog
+
half the 4096-sample FFT window
```

Therefore the coordinate is suitable for:

```text
whole-song reasoning
section-scale comparison
finding approximately where a technical event occurred
comparing energy/spectrum/stereo evolution over song time
```

It is **not** a sample-accurate edit point, onset timestamp, transient-alignment guarantee, automation write position, or phase-alignment coordinate.

## Latency and data quality

Keep these concepts separate:

### `estimated_analysis_lag_ms`

Approximate Analyzer-side backlog/window delay inferred from queued audio plus FFT-window center.

It does not include:

```text
OSC/network delay
MCP execution delay
LLM reasoning delay
external FL Studio MCP delay
human interaction delay
```

### `data_age_seconds`

How old the retained MCP evidence is relative to the MCP process wall clock.

A timeline bin can be old and still be exactly the desired historical song evidence.

Therefore:

```text
old != invalid
```

when the user explicitly asks about a past song range.

### `dropped_blocks`

Cumulative Analyzer FIFO push failures for that live VST3 instance.

Non-zero dropped blocks mean some audio was not measured. Do not silently claim complete fine-grained coverage when drops occurred.

### `coverage_ratio`

How much of the requested/coarse song interval is represented by retained canonical timeline bins.

Low coverage should reduce confidence in statements about the entire requested interval.

## Song memory resolution

The MCP canonical memory uses one-second bins and keeps a bounded history per live Analyzer instance.

Current bound:

```text
1200 bins × 1 second = 20 minutes per instance
```

Queries may aggregate to:

```text
1 s
2 s
5 s
10 s
15 s
30 s
```

Choose the coarsest resolution that answers the question.

Examples:

```text
transient-ish technical change inspection  → 1–2 s, then use Temporal tools
verse/chorus energy evolution               → 5–10 s
whole-song macro balance                    → 10–30 s or audio_song_overview()
```

Do not request hundreds of one-second bins merely because they are available. Compact context is easier for an LLM to reason about reliably.

## What is aggregated

Song-memory summaries may include:

```text
active ratio
RMS
LUFS-S
latest LUFS-I in the pass
Peak / True Peak maxima
Crest
Spectral Centroid
Stereo Correlation / Width
Spectral Flux
coarse spectral regions
weighted 12-bin Chroma when available
BPM / time signature context
analysis lag / dropped-block / age quality
```

Feature availability still follows the Analysis Profile feature mask. A timeline cannot recover Semantic evidence that was never computed.

## Loudness pass semantics

For protocol-1.2 Analyzer instances, Loudness state is reset when the transport epoch changes.

Therefore:

```text
LUFS-I = integrated loudness within the current continuous playback epoch
```

while Loudness remains enabled.

A seek or loop jump intentionally starts a fresh loudness pass. Re-enabling Loudness after it was disabled also starts a fresh state.

Snapshot A/B tools do not independently reset loudness.

Legacy pre-1.2 Analyzer instances retain their historical reset/prepare-scoped LUFS-I behavior.

Do not compare LUFS-I values as if they represent identical song coverage unless the pass/range coverage is comparable.

## Whole-song overview semantics

`audio_song_overview()` summarizes remembered evidence across Analyzer instances.

It does not currently perform automatic musical-form recognition.

Do not claim that it has detected:

```text
Verse
Chorus
Pre-Chorus
Bridge
Drop
Breakdown
Outro
```

unless that structure came from exact DAW/project metadata or another explicit source.

Future section detection can use the same time-aligned memory, but it should expose boundaries/evidence separately from final human/LLM labels.

## Relationship to recent-window tools

Recent tools remain valuable:

```text
audio_average()
audio_temporal_profile()
audio_masking_evidence()
audio_stereo_profile()
audio_tonal_profile()
```

But they answer a different question:

```text
recent-window tool  → what happened in a recent bounded observation window?
song-memory tool    → what happened at this DAW-time region/pass, even if the LLM asks later?
```

For delayed Agent workflows, prefer song memory for context and use recent-window tools after deliberately replaying the target passage when finer evidence is required.

## Current limitations

Song memory is currently:

```text
in-memory
MCP-session scoped
bounded
transport-estimated
not automatically section-labeled
not a persistent project database
```

It is not yet a change ledger, persistent mix history, or transport-anchored Before/After verification database.

Do not infer missing audio, reconstruct dropped frames, or invent section labels to hide those limitations.
