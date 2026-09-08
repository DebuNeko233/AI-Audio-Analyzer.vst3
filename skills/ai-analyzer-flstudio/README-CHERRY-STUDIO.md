# AI Audio Analyzer Cherry Studio Skill

This Skill targets:

- Cherry Studio;
- AI Audio Analyzer VST3 1.2.0;
- AI Audio Analyzer MCP 1.2;
- optional FL Studio control MCP: https://github.com/rosasynthesiz/flstudio-mcp

Its purpose is to help an LLM call Analyzer MCP correctly, understand project/runtime identity limits, manage deterministic Analyzer bindings, choose only the required Analysis Profile, use transport-aware Song Memory, explainable structure, Track Story, bounded section-aware relationships, coverage-aware dynamics distributions, direct mono-fold compatibility, frozen session reference comparison, and auditable Before/After verification around externally controlled DAW changes.

It does **not** prescribe a mixing style, LUFS target, EQ/compression/sidechain/stereo recipe, semantic section label, track role, key/harmony edit, reference-matching recipe, or mastering chain.

## Current capability layers

```text
Project/runtime identity-scope disclosure
Signal State / runtime UUID
Identify -> FL Mixer Track/Slot deterministic mapping
Project Status / Mix Overview / Snapshot A-B
Adaptive Analysis + worker/FIFO telemetry
Analyzer-owned loopback Analysis Profile control + ACK
DAW Transport / instance-local playback epochs / Song Memory
Explainable section boundaries / neutral A-B-C recurrence families
Track Story across sections/families
Bounded Section-aware Mix Relationships
Coverage-aware retained Dynamics Distribution
Direct recent-window Mono-fold RMS / energy-aware compatibility evidence
Frozen session Reference Capture / Comparison
Temporal / Masking / Mid-Side / Stereo / Tonal evidence
Recent-window verification
Transport-anchored same-range verification
```

OSC analysis protocol remains append-only **1.2**, indexes `0..149` unchanged. Analyzer-owned Profile control remains separate local revision 1.

MCP 1.2 exposes **47 tools** and **16 Guide Resources**.

## MCP self-description and Skill relationship

The MCP remains understandable even when the client has not imported this Skill:

```text
Server instructions
-> startup order + hard semantic/control rules

Tool descriptions
-> purpose and critical limitation for every tool

MCP Resources
-> on-demand long-form guides under aianalyzer://guide/*
```

`SKILL.md` and `references/*.md` remain the canonical long-form content source. MCP Resources read the same files.

Useful specialized guides:

```text
aianalyzer://guide/dynamics-evidence
aianalyzer://guide/mono-compatibility
aianalyzer://guide/reference-comparison
aianalyzer://guide/verification-evidence
```

Do not load every guide mechanically. Importing the Skill into Cherry Studio is optional for basic MCP correctness but remains useful for clients that do not expose MCP Resources directly.

## Recommended initialization

First inspect identity guarantees:

```text
audio_project_identity_status()
```

Current identity is intentionally unresolved:

```text
stable_project_id = null
project_identity_confidence = UNRESOLVED
runtime_id = live plugin-instance session identity
binding = MCP-session scoped
```

Then inspect:

```text
audio_project_status()
audio_song_status()
```

If the intended pass is sufficiently retained, prefer:

```text
audio_section_map()
```

and then drill down with only what is needed:

```text
audio_track_story(...)
audio_section_profile(...)
audio_section_relationships(...)
audio_dynamics_distribution(...)
audio_mono_compatibility(...)
audio_capture_reference(...)
audio_compare_reference(...)
```

Do not mechanically call all 47 tools.

## Analysis Profile

```text
0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

Use the lowest Profile that supplies the evidence needed for the task.

Analyzer may modify only its own `analysis_profile`. All sound/project/plugin writes remain with the external DAW-control MCP.

## Song Memory and structure

Song Memory uses one-second canonical bins with 100 ms coverage accounting and instance-local transport epochs.

Missing coverage is not silence. Equal epoch numbers across tracks are not required.

A/B/C section families are neutral recurrence labels, not automatic Intro/Verse/Chorus/Drop names.

## P6a dynamics

Use `audio_dynamics_distribution()` for retained pass/range/Section descriptive distributions.

Do not relabel LUFS-S P90-P10 as EBU LRA. Arbitrary-range Integrated LUFS and PLR remain unavailable in P6a.

## P7a mono compatibility

Use `audio_mono_compatibility()` for recent direct mono-fold RMS and 32 band-center energy evidence.

Keep direct fold-down loss separate from correlation, Side/Mid and negative-cross evidence.

Historical Section 32-band mono evidence and mono-fold Sample Peak/True Peak are not available in P7a.

## P8a reference comparison

Typical flow:

```text
choose/cue the intended reference source or passage
-> audio_capture_reference(track, label, seconds)
-> keep returned reference_id
-> cue/measure the current target
-> audio_compare_reference(reference_id, target, seconds)
```

A P8a reference is:

```text
frozen measurement evidence
recent-window
MCP-session scoped
not copied audio
not persistent
not a whole-song claim
```

The comparison exposes both absolute `target - reference` evidence and an explicit RMS-level-normalized spectral-shape view.

Do **not** convert the reference spectral delta directly into inverse EQ. A difference from the reference is context, not automatically a defect or required change.

P8a does not emit an automatic EQ/master match, quality score or processing recommendation and does not assume Section labels across unrelated songs are semantically equivalent.

## Verification around real DAW changes

When a known passage matters, prefer:

```text
audio_begin_range_verification(...)
-> external DAW-control MCP performs real write
-> external MCP returns actual host readback
-> replay effective_range
-> audio_complete_range_verification(...)
```

Use recent-window verification only when explicit retained range anchoring is unnecessary/unavailable.

`controlled_comparison=true` means technical comparability only. `closed_loop_complete=true` additionally requires actual host readback. Neither means the result is artistically better.

## Critical safety/meaning rules

```text
null != zero
missing coverage != silence
runtime UUID != persistent Project/Track ID
current binding != persistent identity
P6 LUFS-S spread != standardized LRA
P7 mono-fold evidence != universal stereo quality
reference difference != defect
RMS-normalized reference view != applied gain
P8a reference != persistent/whole-song reference truth
reference comparison != automatic master matching
controlled comparison != artistic quality
Analyzer Profile control != sound/project control
```

When a real mix change is desired, reason from user intent + musical context + Analyzer evidence, apply the change through the external DAW-control MCP, read back actual host state, then use Analyzer to measure again.