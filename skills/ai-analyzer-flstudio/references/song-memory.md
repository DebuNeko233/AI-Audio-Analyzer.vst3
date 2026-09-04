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

The explainable structure layer consumes this retained memory:

```text
audio_section_map(...)
audio_section_profile(...)
```

Use section tools before raw timeline expansion when a whole-song request can be answered in structural units.

## Recommended whole-song workflow

```text
audio_project_status()
→ resolve/bind Analyzer instances when necessary
→ audio_song_status()
→ let the DAW play the passage/song that needs observation
→ audio_section_map()
→ audio_section_profile() only for relevant sections
→ audio_song_overview() when a pass-level compact summary helps
→ audio_song_timeline() only for tracks/time ranges that still need raw detail
→ choose a deeper evidence family only when the question requires it
```

Do not repeatedly poll every Analyzer tool while playback runs. Song Memory exists so measurement collection is decoupled from LLM reasoning latency.

## Transport epoch

`transport_epoch` is an **instance-local continuous playback pass**.

The VST3 starts a new epoch when it detects:

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
acknowledges the new epoch before transport-tagged publication resumes
```

This prevents audio from the old DAW position from being labeled as if it belonged to the new position.

### Epoch IDs are not project IDs

Do not assume:

```text
Track A epoch 5 == Track B epoch 5
```

Epoch counters are generated independently inside each VST3 instance. Project/song tools expose consistency warnings and DAW-time spans. Section tools deliberately select supporting passes by **overlapping DAW-time coverage**, not numeric epoch equality.

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

Suitable for:

```text
whole-song reasoning
section-scale comparison
approximately locating technical events
comparing energy/spectrum/stereo evolution over song time
```

Not suitable for:

```text
sample-accurate edits
exact onset timestamps
transient alignment guarantees
automation write positions
phase-alignment coordinates
```

## Latency and data quality

### `estimated_analysis_lag_ms`

Approximate Analyzer-side backlog/window delay. It does not include OSC/network delay, MCP execution, LLM reasoning, external control MCP delay, or human interaction.

### `data_age_seconds`

Wall-clock age of retained MCP evidence.

```text
old != invalid
```

when the user explicitly asks about a past DAW-time range.

### `dropped_blocks`

Cumulative Analyzer FIFO push failures. Non-zero means some audio was not measured.

### `coverage_ratio`

Fraction of the requested/coarse interval represented by retained observations.

Coverage is tracked with 100 ms slots inside each canonical one-second bin. Coarse aggregation must preserve partial coverage; sparse 1-second bins must not become false 100% coverage merely because they span the requested range.

Low coverage should reduce confidence in claims about the whole interval.

## Song Memory resolution

```text
canonical storage    1 second
coverage slot        100 ms
retention            1200 bins / about 20 minutes per instance
query resolutions    1 / 2 / 5 / 10 / 15 / 30 seconds
```

Choose the coarsest resolution that answers the question.

```text
transient-ish inspection         → 1–2 s, then Temporal tools
section evolution                → prefer section map/profile; 5–10 s when timeline detail is needed
whole-song macro balance         → section map + overview, or 10–30 s timeline bins
```

Do not request hundreds of one-second bins merely because they are available.

## What is aggregated

Song Memory summaries may include:

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
analysis lag / dropped-block / age / coverage quality
```

Feature availability still follows the Analysis Profile feature mask. A timeline cannot recover evidence that was never computed.

## Loudness pass semantics

For protocol-1.2 instances:

```text
LUFS-I = integrated loudness within the current continuous playback epoch
```

while Loudness remains enabled.

A playback start, seek or loop jump starts a fresh epoch/loudness pass. Re-enabling Loudness after it was disabled also starts a fresh state. Snapshot A/B tools do not independently reset Loudness.

Legacy pre-1.2 Analyzer instances retain historical reset/prepare-scoped LUFS-I behavior.

Do not compare LUFS-I values as if they represent identical song coverage unless pass/range coverage is comparable.

## Relationship to section structure

`audio_song_overview()` remains a compact pass summary. It does not itself assign musical-form labels.

For structural reasoning, use:

```text
audio_section_map()
```

which exposes section-scale novelty boundaries and neutral recurrence families such as A/B/C. Then use:

```text
audio_section_profile()
```

for per-track evidence inside a selected section.

These tools still do **not** make exact semantic claims such as Verse/Chorus/Bridge/Drop. Exact DAW markers/project labels remain authoritative; an LLM may interpret neutral families only with additional context and appropriate uncertainty.

Detailed rules: `section-structure.md`.

## Relationship to recent-window tools

Recent tools remain valuable:

```text
audio_average()
audio_temporal_profile()
audio_masking_evidence()
audio_stereo_profile()
audio_tonal_profile()
```

They answer a different question:

```text
recent-window tool  → what happened in a recent bounded observation window?
Song Memory         → what happened at this DAW-time region/pass, even if the LLM asks later?
section tool        → which song-scale ranges differ or recur, and which range should be inspected next?
```

For delayed Agent workflows, prefer Song Memory/structure for context and use recent-window tools after deliberately replaying a target passage when finer evidence is required.

## Current limitations

Song Memory is currently:

```text
in-memory
MCP-session scoped
bounded
transport-estimated
not a persistent project database
```

The structure layer built on it is explainable/heuristic and neutral-label only. Neither Song Memory nor section maps are a change ledger, persistent mix history, exact semantic arrangement database, or transport-anchored Before/After verification store.

Do not infer missing audio, reconstruct dropped frames, or invent semantic section names to hide those limitations.
