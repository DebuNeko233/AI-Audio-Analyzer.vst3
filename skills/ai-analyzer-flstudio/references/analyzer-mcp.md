# AI Audio Analyzer MCP Reference

Use this guide for the MCP 1.2 surface, selector/identity rules, Song Memory, P4b historical detail, dynamics, mono/reference comparison and verification boundaries.

## Current surface

P4b PR #36 exposes **48 tools** and **16 Guide Resources**. Product/OSC/control versions remain 1.2.0 / 1.2 / revision 1.

High-level tools:

```text
audio_project_identity_status()
audio_project_status()
audio_song_status()
audio_song_overview()
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
audio_historical_detail(...)
audio_dynamics_distribution(...)
audio_mono_compatibility(...)
audio_capture_reference(...)
audio_list_references()
audio_compare_reference(...)
audio_begin_range_verification(...)
audio_complete_range_verification(...)
```

Do not call all 48 tools by default.

## Identity and selectors

`runtime_id` is live plugin-instance identity only. It is not persistent project or track identity and changes when the same DAW project is reopened.

Use `audio_project_identity_status()` before assuming continuity across a switch/reopen.

Preferred selector order:

```text
mixer:<track_index>/slot:<slot>
-> unique FL Mixer track name
-> runtime UUID
-> unique Analyzer display name
```

Use the VST3 Identify parameter and `audio_bind_last_identified()` to create deterministic current-session Mixer bindings.

## Analysis Profile

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

Analyzer-owned write tools may change only `analysis_profile`. `control_acknowledged` and `telemetry_confirmed` are separate states.

Disabled feature families are unavailable, not zero.

## Song Memory

```text
canonical bin        1 second
coverage slot        100 ms
max bins             1200 / Analyzer instance
query resolutions    1 / 2 / 5 / 10 / 15 / 30 seconds
scope                MCP session
```

`transport_epoch` is instance-local. Cross-track retained analysis aligns by DAW-time overlap, not numeric epoch equality.

Missing coverage is not silence.

## Structure and relationship layer

`audio_section_map()` provides explainable novelty boundaries and neutral recurrence families.

`audio_section_profile()` returns per-track evidence in one selected Section.

`audio_track_story()` summarizes one track across sections/families without inventing role or one quality score.

`audio_section_relationships()` returns a bounded pair shortlist. `shortlist_priority` is inspection priority only.

## P4b historical retained detail

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

P4b reuses the common P4 range resolver and the existing canonical one-second Song Memory. It does not create a second history database and does not retain raw audio.

When feature families were actually measured, one-track historical evidence may include:

```text
32-band Mid spectrum
32-band Side spectrum
full-band stereo context
8-range frequency-dependent stereo
negative-cross / low-band stereo
Mid/Side-derived mono-fold energy
one-second temporal summaries
```

With `compare_track`, each track independently selects its best local transport epoch by coverage. Pair evidence then aligns common one-second DAW bins and may include:

```text
ERB-rebinned masking/overlap
stereo deltas
mono-fold energy deltas
one-second band-envelope correlation/overlap
one-second onset-candidate coincidence
```

Hard boundaries:

```text
subsecond historical alignment       false
raw audio retained                   false
missing detail                       unavailable, not silence
equal epoch numbers required         false
historical mono Sample Peak          unavailable
historical mono True Peak            unavailable
quality score                        none
processing recommendation            none
```

Dedicated masking/stereo/temporal tools remain recent-window APIs and may provide finer current-frame context.

## P6a retained dynamics

`audio_dynamics_distribution()` supports retained pass spans, explicit ranges, cached Sections and optional Section-to-Section deltas.

Coverage policy is a per-bin minimum plus covered-seconds weighting.

Keep explicit:

- LUFS-S P90-P10 != EBU LRA;
- arbitrary-range Integrated LUFS unavailable;
- arbitrary-range PLR unavailable;
- observed per-bin peaks != reconstructed sample stream;
- section deltas != quality score.

## P7 mono compatibility

`audio_mono_compatibility()` is a recent receive-time tool using direct Mid/Side energy math.

P4b provides a separate one-second historical Mid/Side-derived mono energy path through `audio_historical_detail()`.

Direct mono-fold Sample Peak / True Peak remain unavailable and must not be inferred from stereo metrics.

## P8a session reference comparison

```text
audio_capture_reference(...)
audio_list_references()
audio_compare_reference(...)
```

Reference profiles are frozen recent-window MCP-session evidence and contain no copied audio. They are not persistent and are not whole-song truth.

Absolute and RMS-level-normalized spectral-shape comparisons must remain separate. A reference difference is context, not a defect or automatic processing instruction.

P4b does not silently make P8a historical; future historical reference capture must explicitly consume retained history.

## Verification

Recent-window verification and transport-anchored same-range verification coexist.

Same-range flow:

```text
capture retained Before
-> freeze receive-time fence
-> external DAW write
-> actual host readback
-> replay same effective DAW range
-> choose clean post-fence After pass
-> compare
```

`controlled_comparison` is technical comparability only. `closed_loop_complete` additionally requires actual host readback. Neither means better sound.

## Core validity rules

- `null` != zero;
- missing retained coverage != silence;
- current live Profile != proof of historical availability;
- recent-window result != historical Section result;
- runtime UUID != project identity;
- equal epoch numbers across tracks are unnecessary;
- quality/aesthetic judgment belongs to the LLM/user context, not MCP core heuristics.
