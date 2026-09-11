---
name: ai-analyzer-flstudio
description: Technical usage skill for AI Audio Analyzer MCP. Teaches identity scope, deterministic Analyzer binding, Analysis Profile control, transport-aware Song Memory, explainable structure, historical P4b retained detail, dynamics, mono compatibility, session reference comparison, validity and closed-loop verification. It does not prescribe a mixing style, fixed target, processing recipe or aesthetic decision.
---

# AI Audio Analyzer MCP Usage Skill

Use this Skill to call **AI Audio Analyzer MCP** correctly and interpret its evidence without overstating it.

The Analyzer measures and remembers audio evidence. The LLM supplies contextual judgment. A real DAW-control MCP performs sound/project writes and actual host readback.

## Self-description layers

```text
Server instructions -> short global hard rules
Tool descriptions   -> discoverable purpose of each tool
MCP Resources       -> long-form guides loaded only when needed
External Skill      -> canonical long-form guidance
```

The packaged/repository `SKILL.md` and `references/*.md` files are the canonical long-form source. Do not load every guide mechanically.

## 1. Start with identity

At a new session or after a possible DAW project switch/reopen:

```text
audio_project_identity_status()
```

Current contract:

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
runtime_id scope                        live_plugin_instance
runtime_id persistent                   false
same-project reopen UUID stable         false
binding scope                           mcp_session
cross-project retained-state isolation  not guaranteed
```

Rules:

- runtime UUID is one live Analyzer instance, not persistent project/track identity;
- reopening the same project recreates UUIDs;
- a new UUID does not prove the project changed;
- retained Song Memory, Sections, references and verification sessions are MCP-session state;
- until exact project identity exists, use a clean MCP session when strict cross-project isolation matters;
- never invent project identity from tempo, names, Mixer indexes, topology, UUIDs or epochs.

Then inspect:

```text
audio_project_status()
audio_song_status()   # for whole-song/past-passage work
```

## 2. Deterministic Analyzer ↔ Mixer binding

Use host parameter `identify` and the Identify event path:

```text
locate real Mixer Track / Slot in DAW control layer
-> toggle Identify
-> audio_last_identify()
-> audio_bind_last_identified(...)
-> audio_instance_map()
```

Preferred selector:

```text
mixer:<index>/slot:<slot>
```

Do not guess instance identity from spectrum, track role or names when Identify is available.

## 3. Analysis Profile

```text
0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

Analyzer-owned write tools:

```text
audio_set_analysis_profile(...)
audio_set_project_analysis_profile(...)
```

These are the only Analyzer-owned writes and change measurement computation only.

Disabled feature families are unavailable, not zero.

## 4. Whole-song hierarchy

Prefer structural compression before raw timeline expansion:

```text
audio_song_status()
-> audio_section_map()
-> choose the smallest follow-up
```

Useful high-level follow-ups:

```text
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
audio_historical_detail(...)
audio_dynamics_distribution(...)
audio_mono_compatibility(...)
audio_capture_reference(...)
audio_compare_reference(...)
```

Use `audio_song_timeline()` only when raw DAW-time evolution is still needed.

Do not mechanically call all **48 tools**.

## 5. Song Memory

```text
canonical bin size   1 second
coverage slot        100 ms
retained bins        up to 1200 / Analyzer instance
scope                current MCP session
```

`transport_epoch` is **instance-local**. Never require equal epoch numbers across tracks. Cross-track retained analysis aligns by overlapping DAW time.

Keep separate:

```text
coverage_ratio
estimated_analysis_lag_ms
data_age_seconds
dropped_blocks
```

Missing coverage is not silence. Transport coordinates are not sample-accurate edit coordinates.

## 6. Structure / Track Story / relationships

```text
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
```

A/B/C families are neutral recurrence labels, not automatic Intro/Verse/Chorus/Drop labels.

`shortlist_priority` is inspection priority only, not masking/audibility/problem probability, quality score or a processing command.

## 7. P4b historical retained detail

For a past DAW range or cached Section, prefer:

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

P4b uses the existing one-second Song Memory and common P4 range resolver. It stores no raw audio.

Possible retained evidence when measured:

```text
32-band Mid/Side summaries
full-band + frequency-dependent stereo
negative-cross / low-band stereo
historical Mid/Side-derived mono-fold energy
one-second temporal summaries
optional same-range ERB masking/stereo/mono/temporal pair evidence
```

Hard boundaries:

```text
historical resolution                  1 second
subsecond historical alignment         unsupported
raw audio                               not retained
missing detail                          unavailable, not silence
equal epoch numbers across tracks       not required
historical mono Sample Peak             unavailable
historical mono True Peak               unavailable
quality score                           none
processing recommendation               none
```

Dedicated `audio_masking_evidence()`, `audio_stereo_profile()` and `audio_temporal_*()` remain **recent-window** tools and can expose finer current-frame context. Do not relabel their recent results as historical Section evidence.

## 8. Coverage-aware dynamics

```text
audio_dynamics_distribution(...)
```

P6a uses retained one-second bins with a minimum per-bin coverage floor and covered-seconds weighting.

Keep explicit:

- RMS/LUFS-S/Crest/observed Peak/True-Peak distributions are descriptive;
- LUFS-S P90-P10 is not standardized EBU LRA;
- arbitrary-range Integrated LUFS is unavailable;
- arbitrary-range PLR is unavailable;
- per-bin peak distributions are not reconstructed sample streams;
- section deltas are not quality scores.

## 9. Mono compatibility

Recent-window P7a:

```text
audio_mono_compatibility(track, seconds=5.0)
```

Math:

```text
M = 0.5 * (L + R)
S = 0.5 * (L - R)
(L_power + R_power)/2 = M_power + S_power
```

Keep direct mono loss, correlation, Side/Mid and negative-cross as independent evidence.

Historical one-second mono energy is available separately through P4b `audio_historical_detail()` when retained Mid/Side detail exists.

Still unavailable:

```text
mono-fold Sample Peak
mono-fold True Peak
```

Do not infer them from stereo Peak/True Peak, correlation or Mid/Side.

## 10. Session reference comparison

P8a is merged:

```text
audio_capture_reference(...)
audio_list_references()
audio_compare_reference(...)
```

A reference is a frozen compact **recent-window measurement profile**, not audio.

```text
scope             MCP session
persistent        false
whole-song claim  false
```

Keep two comparison views distinct:

```text
absolute target - reference
RMS-level-normalized spectral-shape delta
```

A difference from the reference is not automatically a defect. Never convert reference deltas mechanically into inverse EQ/master-match processing.

P4b does not silently make P8a historical; historical reference capture requires a future explicit P8 extension.

## 11. Evidence validity

Inspect relevant fields:

```text
analysis_valid
signal_present
analysis_features
coverage_ratio
active_ratio
data_age_seconds
estimated_analysis_lag_ms
dropped_blocks
warnings
```

Current live Profile does not prove what historical features were available. Use retained feature validity from the selected pass.

`null` means unavailable, not zero.

## 12. Choose the smallest evidence tool

```text
Current frame            audio_snapshot
Recent stable track      audio_average
Historical range/Section audio_historical_detail
Temporal                 audio_temporal_profile / compare
Masking                  audio_project_masking_scan / audio_masking_evidence
Stereo                   audio_stereo_profile / compare
Recent mono fold         audio_mono_compatibility
Tonal                    audio_tonal_profile / compare
Dynamics                 audio_dynamics_distribution
Reference                audio_capture_reference / audio_compare_reference
Master summary           audio_master_status
```

These provide evidence, not automatic processing instructions.

## 13. Verification

For a known musical passage around an external DAW/plugin change, prefer transport-anchored same-range verification:

```text
audio_begin_range_verification(...)
-> external DAW write
-> actual host readback
-> replay returned effective range
-> audio_complete_range_verification(...)
```

Rules:

```text
effective range      one-second Song Memory bins
pass selection       coverage first, recency tie-break
After freshness      must be after frozen baseline fence
missing coverage     not silence
host_readback        actual state, not requested value
```

Recent-window verification remains a fallback when explicit range anchoring is unnecessary.

`controlled_comparison=true` means technical comparability only. `closed_loop_complete=true` additionally requires actual host readback. Neither means the result sounds better.

## 14. Critical distinctions

Always keep distinct:

- runtime UUID != persistent project ID / track ID;
- transport epoch != project identity;
- missing coverage != silence;
- Sample Peak != True Peak;
- RMS != LUFS;
- LUFS-S != LUFS-I;
- pass-cumulative LUFS-I != arbitrary-range LUFS-I;
- LUFS-S spread != EBU LRA;
- arbitrary-range level/peak relation != PLR;
- correlation / Side-Mid / negative-cross != direct mono-fold energy;
- P7a recent mono != P4b historical one-second mono;
- historical one-second detail != subsecond recent-frame evidence;
- floor-censored mono loss != exact cancellation below -120 dB;
- reference absolute delta != RMS-normalized shape delta;
- reference difference != defect;
- frozen session reference != persistent whole-song truth;
- section family != semantic section label;
- relationship shortlist != confirmed mix problem;
- Analysis Profile != audio quality;
- Analyzer Profile ACK != fresh telemetry;
- controlled comparison != artistic quality;
- `null` != zero.

## 15. Boundary with DAW control

Analyzer owns measurement, retained evidence, structure, comparison, reference context, verification and Analyzer Profile control.

The external DAW-control layer owns exact project topology/identity when available, markers/Playlist metadata, all sound/project writes, actual host readback and future transaction/rollback.

Never invent identity, control success, readback values, semantic section labels, track roles or processing certainty.

## 16. Output discipline

When relevant include provenance:

```text
identity confidence
selector / runtime context
DAW range + selected epoch
section/map/family IDs
coverage / drops / lag
feature availability
historical vs recent scope
reference_id + frozen/session scope
verification requested/effective range
actual host readback status
measurement value / delta
what the evidence can and cannot establish
```

All LLM-facing Skill/reference content remains English-only.
