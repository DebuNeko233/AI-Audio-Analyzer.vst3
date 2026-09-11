# Song Timeline Memory and LLM Latency

Use this guide for whole-song work, past passages and any workflow where Agent/tool latency is slower than the audio event.

Central rule:

```text
The Analyzer observes continuously.
The LLM does not need to observe continuously.
```

## Song Memory

```text
canonical storage    1 second
coverage slot        100 ms
retention            1200 bins / about 20 minutes per instance
query resolutions    1 / 2 / 5 / 10 / 15 / 30 seconds
scope                current MCP session
```

Available high-level tools:

```text
audio_song_status()
audio_song_overview(...)
audio_song_timeline(...)
audio_section_map(...)
audio_section_profile(...)
audio_historical_detail(...)
```

Prefer Section Map/Profile before expanding raw timeline when a structural answer is enough.

## Transport epoch

A `transport_epoch` is one **instance-local continuous playback pass**.

Playback start, seek, loop jump or another detected discontinuity starts a new epoch and resets pass-dependent measurement continuity.

Do not assume:

```text
Track A epoch 5 == Track B epoch 5
```

Cross-track retained analysis aligns by overlapping DAW-time coverage.

## Data quality

Keep separate:

```text
coverage_ratio
estimated_analysis_lag_ms
data_age_seconds
dropped_blocks
```

Coverage is represented by 100 ms slots inside each canonical one-second bin. Sparse bins must not become false 100% coverage after aggregation.

Missing coverage is not silence.

## Transport coordinates

Transport timestamps are suitable for:

```text
whole-song reasoning
section/range comparison
approximately locating technical events
```

They are not suitable for:

```text
sample-accurate edits
exact onset timestamps
phase-alignment coordinates
automation write positions
```

## What base Song Memory retains

Depending on enabled Analysis Profile features, one-second summaries may include:

```text
activity / RMS / Crest
LUFS-S and pass-cumulative LUFS-I
observed Peak / True Peak maxima
coarse spectrum and centroid
stereo correlation / width
spectral flux
weighted chroma
transport context
lag / drops / age / coverage
```

A timeline cannot recover a feature family that was disabled or never measured.

## P4b bounded historical detail

P4b attaches deeper bounded summaries to the **same canonical one-second bins**. It does not create a second history store and does not retain raw audio.

Use:

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

Single-track retained detail may include:

```text
32-band Mid / Side
full-band + 8-range stereo
negative-cross / low-band stereo
historical Mid/Side-derived mono-fold energy
one-second temporal descriptors
```

With `compare_track`, the common P4 range resolver chooses an appropriate pass independently for each Analyzer, then aligns common one-second DAW bins for optional masking/stereo/mono/temporal pair evidence.

Boundaries:

```text
resolution                       1 second
subsecond historical alignment  unsupported
raw audio                        not retained
missing detail                   unavailable, not silence
equal epoch numbers              not required
mono Sample Peak / True Peak     unavailable
quality score                    none
```

The Python regression tracks a shallow container/array estimate around 1918 B/detail-bin in the current CI environment. This is a bounded implementation guard, not exact process RSS.

## Recent-window tools remain useful

```text
audio_average()
audio_temporal_profile()
audio_masking_evidence()
audio_stereo_profile()
audio_tonal_profile()
audio_mono_compatibility()
```

These answer a different question: what happened in a recent bounded observation window, often with finer current-frame context.

For delayed Agent workflows, use Song Memory/structure first. Use `audio_historical_detail()` when a past range needs deep retained evidence. Replay only when the task requires finer evidence that historical memory does not preserve.

Do not silently substitute a recent-window result for a requested historical Section.

## Loudness semantics

LUFS-I remains pass-cumulative within the relevant continuous playback/loudness state. Do not relabel it as arbitrary-range Integrated LUFS.

P6a retained distributions deliberately keep standardized EBU LRA and arbitrary-range PLR unavailable rather than fabricating them.

## Current limitations

Song Memory is:

```text
in-memory
MCP-session scoped
bounded
transport-estimated
not a persistent project database
not partitioned by a stable project ID
```

Section families are neutral labels. Missing audio is never reconstructed. Project persistence waits for authoritative external identity.
