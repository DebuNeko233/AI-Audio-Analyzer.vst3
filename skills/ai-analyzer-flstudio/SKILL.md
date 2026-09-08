---
name: ai-analyzer-flstudio
description: Technical usage skill for Cherry Studio + AI Audio Analyzer MCP. Teaches explicit project/runtime identity scope, deterministic Analyzer binding, adaptive Analysis Profile control, transport-aware Song Memory, explainable song structure, Track Story, bounded section-aware relationships, coverage-aware retained dynamics distributions, direct mono-fold compatibility, frozen session reference comparison, measurement validity, performance telemetry, recent-window verification, and transport-anchored same-range verification around externally controlled DAW changes. It does not prescribe a mixing style, LUFS target, EQ/compression/sidechain/stereo recipe, semantic section label, key change, harmony edit, reference-matching recipe, or aesthetic decision.
---

# AI Audio Analyzer MCP Usage Skill

Use this Skill to:

1. call **AI Audio Analyzer MCP** correctly;
2. interpret its evidence without overstating it.

It is not a mixing/mastering style guide. Analyzer measurements do not imply a mandatory processor, parameter value, section name, track role, chord/key edit, stereo action, reference match, or aesthetic choice.

## MCP self-description and this Skill

AI Audio Analyzer MCP remains minimally safe to use even when a client does not import this external Skill.

```text
Server instructions
  -> short startup order + cross-cutting hard rules

Tool descriptions
  -> purpose and intended use visible through tools/list

MCP Resources
  -> detailed long-form guidance loaded only when needed

External Skill
  -> canonical long-form guidance for clients that support Skills
```

This `SKILL.md` and its `references/*.md` files are the canonical long-form source. MCP Resources read the same packaged/repository Markdown on demand.

Useful Resource URIs include:

```text
aianalyzer://guide/index
aianalyzer://guide/core
aianalyzer://guide/analyzer-mcp
aianalyzer://guide/parameters
aianalyzer://guide/performance-evidence
aianalyzer://guide/song-memory
aianalyzer://guide/section-structure
aianalyzer://guide/track-story
aianalyzer://guide/section-relationships
aianalyzer://guide/dynamics-evidence
aianalyzer://guide/mono-compatibility
aianalyzer://guide/reference-comparison
aianalyzer://guide/masking-evidence
aianalyzer://guide/stereo-evidence
aianalyzer://guide/tonal-evidence
aianalyzer://guide/verification-evidence
```

Read only the guide relevant to the task. Do not load every Resource mechanically.

## 1. Start with identity scope and project status

At a new Agent/MCP session, and whenever the user may have switched or reopened a DAW project, first inspect:

```text
audio_project_identity_status()
```

Current expected semantics:

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
runtime_id scope                        live_plugin_instance
runtime_id persistent                   false
runtime_id serialized with project      false
same-project reopen UUID stable         false
binding scope                           mcp_session
cross-project retained-state isolation  not guaranteed
```

Rules:

- `runtime_id` identifies one live Analyzer plugin instance only;
- reopening the same project recreates runtime UUIDs;
- a new runtime UUID does not prove the project changed;
- MCP bindings are session-scoped, not persistent track identity;
- retained Song Memory, Section Maps, snapshots, relationships, references and verification sessions may remain in MCP RAM while the user switches/reopens projects;
- until exact project identity is integrated, do not assume retained state belongs to the current project after a switch/reopen;
- when strict isolation matters, restart Analyzer MCP before analyzing the reopened/new project;
- do not invent a project ID from UUIDs, tempo, track count, names, topology fingerprints, transport epochs, or Mixer indexes.

Then inspect:

```text
audio_project_status()
```

For whole-song/past-passage work next use:

```text
audio_song_status()
```

If enough of the pass is retained, prefer structural compression:

```text
audio_section_map()
```

Then choose the smallest follow-up:

```text
audio_track_story(track, map_id)
audio_section_profile(section_id, map_id)
audio_section_relationships(map_id)
audio_dynamics_distribution(...)
audio_mono_compatibility(track, seconds)
audio_capture_reference(...)
audio_compare_reference(...)
```

Use `audio_song_timeline()` only when raw DAW-time evolution is still required.

Do not call all 47 tools mechanically.

## 2. Deterministic Analyzer ↔ FL Mixer mapping

Host-visible parameter:

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

Preferred discovery flow:

```text
locate real Mixer Track / Plugin Slot with DAW-control MCP
-> toggle Identify
-> audio_last_identify()
-> verify fresh + unconsumed event
-> audio_bind_last_identified(fl_track_index, fl_track_name, slot)
-> audio_instance_map()
```

Preferred selectors:

```text
mixer:<index>/slot:<slot>
-> unique FL Mixer track name
-> runtime UUID
-> unique Analyzer display name
```

Never guess instance mapping from spectrum, chroma, or musical role when Identify is available.

## 3. Analysis Profile is measurement-performance control

```text
0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

`Full` is the compatibility default.

Profiles change Analyzer computation only. They do not change audio quality or the audio signal.

Minimum-profile examples:

```text
Transport / signal / Peak-RMS-Crest   Eco
LUFS / True Peak                      Balanced
Spectrum / basic masking              Balanced
Deep Mid/Side / stereo                Balanced
P7a mono-fold energy evidence         Balanced
P8a reference spectrum/stereo/mono    Balanced
Temporal                              Mix
Tonal / chroma / harmonic             Full
```

Analyzer-owned write tools:

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

These are the **only** Analyzer-owned write tools.

Keep separate:

```text
control_acknowledged = target VST3 accepted/applied the request
telemetry_confirmed  = a fresh frame reports the Profile
```

## 4. Song Memory and transport epochs

Use:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
```

A `transport_epoch` is one **instance-local continuous playback pass**. Playback start, seek, loop jump, or another discontinuity may create a new epoch.

Never require equal numeric epochs across Analyzer instances. Cross-track retained analysis aligns by overlapping DAW-time coverage.

```text
canonical bin size   1 second
coverage slot        100 ms
retained bins        up to 1200 / instance
scope                current MCP session
```

Keep data-quality concepts separate:

```text
estimated_analysis_lag_ms  Analyzer FIFO + analysis-window estimate only
data_age_seconds           wall-clock age of evidence
dropped_blocks             cumulative FIFO push failures
coverage_ratio             retained coverage fraction
```

Missing coverage is not silence. Transport coordinates are not sample-accurate editing coordinates.

## 5. Explainable structure, Track Story and relationships

```text
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
```

A/B/C/... are neutral recurrence-family labels. Never automatically translate them to Intro/Verse/Chorus/Drop.

Track Story summarizes one track across sections using activity, levels, spectrum, stereo, temporal, chroma, coverage/lag/drop, adjacent deltas, same-family variation and relative extrema.

Do not invent one overall Track Story quality/consistency score.

`shortlist_priority` from section relationships is inspection priority only. It is not masking probability, audibility probability, mix-problem probability, quality score, or a processing recommendation.

Detailed masking/stereo/temporal tools remain recent-window based until deeper retained detail exists.

## 6. Coverage-aware retained dynamics distributions

Use:

```text
audio_dynamics_distribution(
  track,
  transport_epoch=None,
  start_seconds=None,
  end_seconds=None,
  map_id=None,
  section_id=None,
  compare_section_id=None,
  minimum_range_coverage=...,
  minimum_bin_coverage=...
)
```

Supported scopes:

```text
selected retained transport-pass span
explicit DAW-time range
cached Section Map section
optional section-to-section comparison
```

P6a is MCP-side and uses one-second Song Memory.

Coverage policy:

```text
minimum per-bin coverage floor
+
covered-seconds weighting for accepted bins
```

Metric groups include RMS, LUFS-S, Crest, observed per-bin Sample Peak maxima and observed per-bin True Peak maxima.

Critical terminology boundaries:

- `lufs_s_interpercentile_range_lu` is descriptive P90-P10 LUFS-S, **not EBU Loudness Range**;
- standardized EBU LRA is unavailable in P6a;
- retained `lufs_i_latest` is pass-cumulative, so arbitrary-range Integrated LUFS is unavailable;
- arbitrary-range PLR is unavailable without scope-compatible peak + integrated loudness;
- a per-bin peak distribution is not a reconstructed sample stream;
- section deltas are descriptive only;
- never invent a universal dynamics/mastering quality score or fixed genre target.

Detailed rules: `references/dynamics-evidence.md`.

## 7. Direct energy-aware mono-fold compatibility

Use:

```text
audio_mono_compatibility(track, seconds=5.0)
```

P7a reuses existing Analyzer Mid/Side math:

```text
M = 0.5 * (L + R)
S = 0.5 * (L - R)
(L_power + R_power)/2 = M_power + S_power
```

Current scope is a recent receive-time window from 0.5 to 60 seconds.

Full-band evidence includes:

```text
stereo_rms_db
mono_fold_rms_db
mono_fold_rms_delta_db
floor_censored
```

32 band-center evidence includes:

```text
stereo_equivalent_energy_db
mono_fold_delta_db
energy_loss_fraction
relative_band_energy
inspection_priority
```

`inspection_priority` is an energy-aware shortlist aid only, not audibility probability, phase-problem probability, quality score, pass/fail status, or processing advice.

When Mid reaches the Analyzer `-120 dB` measurement floor, `floor_censored=true`. Do not claim precise cancellation depth below the floor.

Keep correlation, Side/Mid, negative-cross and direct mono-fold loss as separate evidence dimensions.

Current P7a limits:

```text
historical arbitrary DAW-range 32-band mono fold   unavailable
cached Section 32-band mono fold                   unavailable
mono-fold Sample Peak                              unavailable
mono-fold True Peak                                unavailable
```

Do not infer mono peak/True Peak from stereo metrics. Direct peak/True-Peak fold-down belongs to optional P7b.

Detailed rules: `references/mono-compatibility.md`.

## 8. Frozen session reference comparison

Use:

```text
audio_capture_reference(track, label="", seconds=10.0)
audio_list_references()
audio_compare_reference(reference_id, target, seconds=None)
```

P8a freezes compact **measurement profiles**, not audio.

Current reference scope:

```text
recent receive-time window
MCP-session scoped
frozen at capture time
not persistent
not a whole-song claim
```

A captured profile can include available evidence such as:

```text
RMS / Peak / Crest / LUFS-S / True Peak
32 Analyzer spectrum bands + coarse regions
centroid
stereo correlation / width
P7a mono-fold full-band + grouped evidence
source/binding/scope provenance
```

### Absolute view

All deltas are explicitly:

```text
target - reference
```

A positive/negative delta is not automatically good/bad.

### RMS-level-normalized spectral-shape view

P8a also exposes:

```text
target_gain_to_reference_db = reference_rms - target_rms
normalized_delta = (target_band + target_gain_to_reference_db) - reference_band
```

This removes one broad RMS offset from the **comparison view only**. It does not change either source.

Use absolute evidence when actual level is the question. Use level-normalized evidence when broad gain should not masquerade as spectral-shape difference.

### Interpretation boundary

Never reason mechanically like:

```text
reference is +2 dB at 8 kHz
-> add +2 dB at 8 kHz to target
```

A reference difference may come from arrangement, instrumentation, register, vocal balance, intended production style, source level, or section mismatch.

P8a does not emit:

```text
automatic_eq_match
automatic_master_match
quality_score
processing_recommendation
```

and does not silently assume A/B/C or named sections in unrelated songs are semantically equivalent.

Current deliberate limits:

```text
persistent reference library                  unavailable
historical arbitrary Section 32-band capture  unavailable
whole-song completeness claim                 unavailable
external-file faster-than-realtime scan       unavailable
```

Detailed rules: `references/reference-comparison.md`.

## 9. Validate evidence before interpreting it

Inspect relevant validity/coverage fields:

```text
signal_present
analysis_valid
active_ratio
analysis_features
coverage_ratio
data_age_seconds
estimated_analysis_lag_ms
dropped_blocks
warnings
```

Disabled/unmeasured feature families are unavailable, not zero.

For historical evidence, use what was actually retained in that pass. Do not use the current live Analysis Profile as proof of what was measured earlier.

For P7a/P8a recent-window evidence, do not turn the current result into a historical Section claim.

Before reusing project-level retained state after a project reopen/switch, inspect `audio_project_identity_status()` and require trustworthy external identity or a clean MCP session boundary.

## 10. Choose the smallest evidence tool

```text
Current frame                 audio_snapshot(...)
Recent stable track           audio_average(...)
Temporal                      audio_temporal_profile / compare
Masking                       audio_project_masking_scan / audio_masking_evidence
Stereo                        audio_stereo_profile / compare
Direct mono fold              audio_mono_compatibility
Tonal                         audio_tonal_profile / compare
Dynamics                      audio_dynamics_distribution
Reference                     audio_capture_reference / audio_compare_reference
Master technical summary      audio_master_status
```

These provide evidence, not automatic processing instructions.

## 11. Snapshot A/B

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

Snapshot deltas are `After - Before`.

Snapshots are session memory and are not tagged with a stable project identity. Do not compare across a suspected project switch/reopen without authoritative identity.

Snapshot A/B is not a substitute for same-range verification when the exact passage matters.

## 12. Closed-loop verification

When coordinating a real DAW/plugin modification through an external control MCP, prefer same-range verification whenever an explicit passage is known.

### Same-range verification

```text
audio_begin_range_verification(...)
-> inspect ready_for_external_change / blockers
-> external DAW-control MCP performs write
-> external DAW-control MCP reads actual host state back
-> replay returned effective_range
-> audio_complete_range_verification(..., host_readback="actual readback")
```

Rules:

```text
requested fractional range != fake sub-second precision
effective range = one-second Song Memory bins
pass selection = coverage first, recency second
epoch IDs remain instance-local
After must be first-observed after frozen receive-time fence
pre-change retained bins cannot silently become After
missing coverage != silence
active_ratio is descriptive, not passage identity
```

Do not report arbitrary-range LUFS-I delta from pass-cumulative retained LUFS-I.

### Recent-window fallback

```text
audio_begin_verification(...)
-> external write + actual host readback
-> replay comparable passage
-> audio_complete_verification(...)
```

`controlled_comparison=true` means technical comparability only.

`closed_loop_complete=true` additionally requires supplied actual host readback.

Neither means After is better.

Detailed rules: `references/verification-evidence.md`.

## 13. Critical distinctions

Always keep these distinct:

- runtime UUID != persistent project ID / track ID.
- a new runtime UUID != proof of another project.
- current Mixer/Slot binding != persistent identity.
- MCP session memory != project-isolated persistent memory.
- Sample Peak != True Peak.
- RMS != LUFS.
- LUFS-S != LUFS-I.
- pass-cumulative LUFS-I != arbitrary-range LUFS-I.
- LUFS-S interpercentile spread != standardized EBU LRA.
- arbitrary-range peak/LUFS-S relation != PLR.
- dB percentile != power-domain mean.
- observed per-bin peak maxima != reconstructed sample stream.
- stereo correlation != Side/Mid energy.
- correlation / Side-Mid / negative-cross != direct mono-fold energy change.
- mono-fold band-center evidence != integrated-band transfer function.
- floor-censored mono-fold delta != exact cancellation depth below -120 dB.
- P7a mono RMS/energy != mono Sample Peak/True Peak.
- recent P7a mono compatibility != historical/Section mono compatibility.
- reference absolute delta != normalized spectral-shape delta.
- reference difference != defect.
- RMS normalization view != an applied gain change.
- frozen P8a session reference != persistent/whole-song reference truth.
- reference comparison != automatic master match.
- overlap/masking heuristics != audible-masking probability.
- chroma != MIDI note probability.
- tonal-center correlation != key probability.
- section family != semantic section name.
- Track Story activity != mute/role state.
- relationship shortlist != confirmed mix problem.
- coverage gap != silence.
- topology fingerprint != DAW project hash.
- host_readback != requested setting.
- controlled_comparison != artistic quality.
- worker_load_ratio != DAW realtime CPU.
- Analysis Profile != audio quality.
- Analyzer Profile ACK != fresh telemetry.
- `null` != zero.

## 14. Boundary with DAW control

AI Audio Analyzer MCP owns:

```text
measure
read Analyzer state
disclose current identity guarantees
remember transport-aligned evidence
infer explainable structure
summarize Track Story
shortlist bounded relationships
compute retained dynamics distributions
compute recent mono-fold compatibility
freeze/compare session reference measurement profiles
compare measurements
resolve retained DAW-time ranges
verify Before/After measurement conditions
control Analyzer Analysis Profile only
```

The DAW-control MCP owns:

```text
DAW topology / exact project data
stable project identity when available
markers / Playlist / arrangement metadata when exposed
plugin access
all non-Analyzer artistic/technical writes
actual host-state readback
transaction / rollback when implemented by that layer
```

Never invent identity, control success, readback values, track roles, semantic section labels, or processing certainty.

## 15. Output discipline

Include enough provenance to audit a claim:

```text
identity confidence when continuity matters
selector / runtime context
DAW-time range + selected epoch for retained evidence
section_id / family_id / map_id for structure
coverage / accepted-rejected-missing bins for distributions
recent receive-time window + floor_censored for P7a
reference_id + frozen/session scope + absolute/normalized mode for P8a
data age / lag / drops when relevant
Analysis Profile / feature availability when relevant
verification requested/effective range + freshness
actual external host-readback status
measurement value / delta
what the metric can and cannot establish
```

All LLM-facing Skill/reference content remains English-only.