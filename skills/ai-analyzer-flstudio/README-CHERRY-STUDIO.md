# AI Audio Analyzer Cherry Studio Skill

This Skill teaches an Agent how to use AI Audio Analyzer MCP as an evidence, memory and verification layer for mixing/mastering workflows.

P4b PR #36 currently exposes **48 tools** and **16 Guide Resources**.

## Recommended order

```text
audio_project_identity_status()
-> audio_project_status()
-> audio_song_status() for whole-song/past-passage work
-> audio_section_map() when structure helps
-> smallest relevant evidence tool
```

Useful high-level tools:

```text
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
audio_historical_detail(...)
audio_dynamics_distribution(...)
audio_mono_compatibility(...)
audio_capture_reference(...)
audio_compare_reference(...)
audio_begin_range_verification(...)
audio_complete_range_verification(...)
```

Do not mechanically call all 48 tools.

## P4b historical detail

Use `audio_historical_detail()` when the question is about a past DAW range or cached Section and replay should be avoided.

It can expose one-second retained Mid/Side, stereo, historical mono energy, masking and temporal-pair evidence when those measurements existed during capture.

Do not overstate it:

```text
historical resolution       1 second
subsecond alignment         unsupported
raw audio retained          no
missing detail              unavailable, not silence
mono Sample Peak/True Peak  unavailable
quality score               none
```

Dedicated masking/stereo/temporal tools remain recent-window tools with potentially finer current-frame context.

## P7a mono compatibility

Use `audio_mono_compatibility()` for recent direct mono-fold RMS and 32 band-center energy evidence.

For historical one-second mono energy use `audio_historical_detail()` instead. Direct mono-fold Sample Peak/True Peak remain unavailable.

## P8a references

P8a references are frozen recent-window measurement profiles in the current MCP session. They are not copied audio, persistent libraries or whole-song truth.

P4b does not silently turn P8a into historical reference capture.

## Analysis Profile

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

Analyzer-owned Profile control changes measurement computation only and never changes audio.

## Verification

For an external DAW/plugin change on a known passage, prefer transport-anchored same-range verification and provide actual host readback.

`controlled_comparison` means technical comparability only. `closed_loop_complete` additionally requires actual readback. Neither means the change sounds better.

## Hard rules

```text
runtime UUID != persistent project ID
missing coverage != silence
null != zero
recent-window evidence != historical Section evidence
reference difference != defect
relationship shortlist != confirmed problem
Analysis Profile != audio quality
Analyzer Profile ACK != fresh telemetry
```

All sound-changing/project writes remain the responsibility of the external DAW-control MCP.
