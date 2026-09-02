---
name: ai-analyzer-flstudio
description: Technical usage skill for Cherry Studio + AI Audio Analyzer MCP. Teaches deterministic Analyzer discovery/binding, tool selection, measurement validity, level/loudness/spectrum/stereo/temporal semantics, project overview, Snapshot A/B, V0.7 masking evidence, V0.8 Mid/Side stereo evidence, V0.9 audio-domain tonal evidence, and V1.0 controlled closed-loop verification around external DAW changes. It does not prescribe a mixing style, LUFS target, EQ/compression/sidechain/stereo recipe, key change, harmony edit, or aesthetic decision.
---

# AI Audio Analyzer MCP Usage Skill

This Skill has two responsibilities only:

1. help the model call **AI Audio Analyzer MCP** correctly;
2. help the model interpret returned measurements and evidence without overstating them.

It is **not a mixing, mastering, harmony, arrangement, or style guide**. Do not infer a mandatory EQ, compressor, limiter, sidechain, panning, stereo, mono, tuning, transposition, chord, harmony, or mastering action merely because a measurement is high, low, overlapping, correlated, anti-correlated, wide, tonal, chromatic, concentrated, ambiguous, or because a V1.0 comparison is technically controlled. Artistic decisions come from the user's goal, musical context, references, DAW state, and the model's own reasoning—not from this Skill.

## 1. Start at project level

For a project-level request, begin with:

```text
audio_project_status()
```

Use it to check Bridge/OSC health, live Analyzer count, deterministic bindings, active input, stale streams, duplicate names, and Master candidates.

Only descend when needed:

```text
audio_bridge_status()
audio_list_tracks()
audio_instance_map()
```

Do not call all tools mechanically. Prefer the highest-level tool that answers the question, then drill down.

## 2. Deterministic multi-instance mapping

AI Audio Analyzer v0.4+ exposes a host-visible Boolean parameter:

```text
Parameter ID: identify
Display name: Identify
```

When an Analyzer is unbound and an FL Studio control MCP can access plugin parameters:

```text
find real Mixer Track / Plugin Slot
→ read current Identify value
→ toggle Identify
→ audio_last_identify()
→ verify fresh + unconsumed event
→ audio_bind_last_identified(fl_track_index, fl_track_name, slot)
→ audio_instance_map()
```

One Identify event may be consumed only once.

Preferred selector order after discovery:

```text
mixer:<index>/slot:<slot>
→ unique FL Mixer track name
→ runtime UUID
→ unique Analyzer display name
```

If multiple Analyzers exist on one Mixer Track, include `slot`.

Do not guess mapping from names, spectrum shape, chroma, tonal evidence, or musical content when Identify is available.

## 3. Validate data before interpreting it

For content-related measurements check:

```text
signal_present
analysis_valid
active_ratio
```

Signal gate semantics are approximately:

```text
close   below -50 dBFS for ~0.4 s
reopen  above -48 dBFS
```

`null` means **unavailable**, not numeric zero.

For V0.6 temporal measurements also inspect:

```text
temporal_supported
temporal_valid
temporal_window_seconds
```

For V0.8 deep stereo measurements inspect:

```text
stereo_v08_supported
stereo_v08_valid
stereo_frames
active_ratio
```

For V0.9 tonal/music-semantic evidence inspect:

```text
semantic_v09_supported
semantic_v09_valid
valid_frames
evidence_quality.mean_chroma_energy_ratio
evidence_quality.normalized_pitch_class_entropy
evidence_quality.tonal_center_top2_margin
evidence_quality.valid_frame_ratio
evidence_quality.active_ratio
```

For V1.0 closed-loop verification inspect both baseline and final comparability state:

```text
ready_for_external_change
baseline_blockers
controlled_comparison
comparability.same_window_seconds
comparability.topology_unchanged
comparability.missing_targets
comparability.invalid_targets
comparability.coverage_mismatch_targets
comparability.active_ratio_tolerance
```

A legacy Analyzer may still provide level/spectrum/stereo data while lacking V0.6 temporal, V0.8 Mid/Side, or V0.9 semantic evidence. V1.0 itself adds no OSC fields; it orchestrates existing measurements in the Bridge.

## 4. Tool selection

### Project readiness

```text
audio_project_status()
```

### Project-wide recent overview

```text
audio_mix_overview(seconds=10, max_tracks=32)
```

Its `potential_spectral_conflicts` are coarse spectral candidates only.

### Project-wide stronger masking candidates — V0.7

```text
audio_project_masking_scan(seconds=5, max_pairs=8, alignment_tolerance_ms=80)
```

Use this when the user wants likely interaction candidates across the project. It ranks candidates with spectral/relative-level/temporal evidence. It is not an automatic list of mix problems.

### Stable single-track window

```text
audio_average(track, seconds)
```

Prefer this to a single frame for observations that should represent several seconds.

### Current single frame

```text
audio_snapshot(track)
```

Use for current-state/connection inspection, not as a stable-window substitute.

### Single-track temporal profile — V0.6

```text
audio_temporal_profile(track, seconds=5)
```

Use for normalized spectral flux, RMS-rise evidence, low-band temporal energy, and threshold-based onset/change candidate density.

### Deep single-track stereo profile — V0.8

```text
audio_stereo_profile(track, seconds=5)
```

Use when the question depends on Mid/Side energy, Side spectrum, signed L/R correlation, low-frequency stereo relation, or negative cross-spectrum evidence.

Keep these axes separate:

```text
correlation
side_to_mid_db
decorrelation_proxy_mean
negative_cross_energy_ratio_mean
```

### Two-track stereo measurement comparison — V0.8

```text
audio_stereo_compare(track_a, track_b, seconds=5)
```

Deltas are `B - A` and are not labelled better/worse.

### Single-track audio-domain tonal profile — V0.9

```text
audio_tonal_profile(track, seconds=8)
```

Use when the question requires audio-derived pitch-class distribution, tonal-center candidate evidence, or single-F0 harmonic-alignment evidence over a passage.

Important output groups:

```text
chroma
tonal_center_evidence
harmonic_alignment
evidence_quality
```

Do not use this tool to replace exact symbolic project data. If the DAW/MIDI control MCP can provide exact note events, key metadata, chord data, or tuning metadata and the question asks for those exact facts, prefer that data.

### Two-track tonal measurement comparison — V0.9

```text
audio_tonal_compare(track_a, track_b, seconds=8)
```

Use when the user asks how two measured pitch-class distributions differ.

Important outputs:

```text
pitch_class_comparison.cosine_similarity
pitch_class_comparison.jensen_shannon_divergence
pitch_class_comparison.normalized_power_delta_b_minus_a[12]
harmonic_alignment_delta_b_minus_a
```

These do not establish harmonic compatibility, consonance, correctness, arrangement quality, or a required musical action.

### Two-track spectral comparison

```text
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
```

`audio_detect_masking()` is the older spectral-overlap heuristic. Do not describe it as a validated psychoacoustic masking result.

### Two-track temporal comparison — V0.6

```text
audio_temporal_compare(
  track_a,
  track_b,
  seconds=5,
  low_hz=40,
  high_hz=160,
  alignment_tolerance_ms=80
)
```

Use when the question depends on whether energy in a selected frequency range actually co-occurs or co-varies over time.

### Two-track masking evidence — V0.7

```text
audio_masking_evidence(
  track_a,
  track_b,
  seconds=5,
  alignment_tolerance_ms=80,
  max_regions=8
)
```

It combines:

```text
existing 32-band Analyzer spectrum
→ 16 equal ERB-rate regions
→ relative spectral occupancy
→ directional relative-level weighting
→ V0.6 selected-band temporal overlap
```

The ERB stage is re-binning, not a gammatone/cochlear filterbank. The score is heuristic evidence, not an audible-masking probability.

### Legacy stereo bands

```text
audio_stereo_bands(track)
```

Use for the existing eight correlation bands when V0.8 detail is unnecessary or unavailable.

### Master technical summary

```text
audio_master_status(track="Master")
```

It summarizes measurements; it does not define a universal mastering target.

### Snapshot A/B

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

Use comparable musical passages, similar window lengths, and comparable `active_ratio`. Snapshot deltas are `After - Before`. LUFS-I is session cumulative, not reset per snapshot.

### Controlled external-change verification — V1.0

Use this when the agent is coordinating a real DAW modification through an external control MCP and the user wants measurement verification.

```text
audio_begin_verification(
  label="short factual label",
  seconds=5,
  target_selectors=["mixer:4/slot:9"]
)
```

Do **not** make the DAW change first. Establish the Before baseline first and inspect:

```text
ready_for_external_change
baseline_blockers
verification_id
```

If the baseline is ready:

```text
external FL Studio control MCP writes the intended change
→ external FL Studio control MCP reads the actual host state back
→ replay the same intended passage
→ audio_complete_verification(
     verification_id,
     seconds=0,
     change_summary="factual change actually attempted",
     host_readback="actual host state reported after the write"
   )
```

`seconds=0` means use the baseline measurement duration again.

Then inspect:

```text
result.comparison.controlled_comparison
result.comparison.comparability
result.topology
result.external_change.readback_supplied
result.audit
result.comparison.targets[].delta
```

Use:

```text
audio_verification_status()
audio_verification_status(verification_id)
```

for current-session listing/recovery.

V1.0 verification is session-scoped. It does not persist across Bridge restarts.

## 5. How to read V1.0 verification evidence

### `ready_for_external_change`

This means the Before baseline passed the current measurement-workflow checks. It does not mean the proposed DAW change is appropriate.

If false, resolve `baseline_blockers` and begin a new verification before changing the DAW.

### Host readback is not a plan

`host_readback` should contain the external control MCP's **actual post-write host state**. Do not fill it with the intended value merely because the write was requested.

Analyzer stores caller-supplied readback text for auditability. Analyzer does not independently query FL Studio or validate that text.

### Topology fingerprint

The topology fingerprint summarizes sorted live Analyzer identity/binding metadata for Before/After consistency checking.

It is not a persistent project ID, audio fingerprint, or proof that every DAW parameter is unchanged.

### `controlled_comparison`

Current V1.0 requires:

```text
at least one compared target
same Before/After window duration
topology unchanged
no missing targets
valid active analysis for all compared requested targets
absolute active_ratio difference <= 0.15 for all compared requested targets
```

The `0.15` active-ratio tolerance is a transparent passage-coverage guardrail, not an audible or quality threshold.

`controlled_comparison=true` means only that the current A/B measurement conditions satisfy these guardrails. It does **not** mean:

```text
After is better
change should be kept
processor setting is correct
mix is more professional
masking/stereo/tonal quality improved
```

If false, report the failed guardrail before making a strong A/B claim.

### Verification delta convention

Basic V1.0 deltas use:

```text
After - Before
```

Positive means numerically higher in After, not better.

For deeper analysis after a controlled change, call only the relevant specialized tool family rather than pretending the basic verification deltas contain all temporal, masking, stereo, or tonal information.

Detailed semantics:

```text
references/verification-evidence.md
```

## 6. How to read V0.9 tonal evidence

### Chroma is a pitch-class power distribution

V0.9 exposes twelve normalized bins in this fixed order:

```text
C C# D D# E F F# G G# A A# B
```

The plugin accumulates Mid-spectrum power approximately over `80 Hz–5 kHz`, maps FFT bins to the nearest 12-TET pitch class, and collapses octave information.

Therefore:

```text
chroma != note probability
chroma != MIDI note list
chroma != note count
chroma != chord-membership probability
```

### `chroma_energy_ratio`

This describes how much measured Mid-spectrum power falls inside the chroma-analysis frequency range. Use it as coverage context, not correctness probability.

### `normalized_pitch_class_entropy`

Approximately:

```text
0 → pitch-class power more concentrated
1 → pitch-class power more uniformly distributed
```

It is distribution concentration, not quality, consonance, complexity, or certainty.

### Tonal-center candidates

V0.9 ranks 24 major/minor tonal-center templates using Pearson correlation against Krumhansl-Kessler key profiles.

`profile_correlation` means template similarity, not key probability.

`top2_margin` means:

```text
best profile correlation - second-best profile correlation
```

It is separation within this template set, not calibrated confidence.

Short, modal, chromatic, changing, sparse, percussion-heavy, atonal, or mixed-source passages can be ambiguous. Do not report the top candidate as a ground-truth key without appropriate qualification.

### Single-F0 harmonic alignment

```text
single_f0_harmonic_energy_ratio
harmonic_f0_candidate_hz
```

These come from a transparent single-harmonic-series spectral heuristic. They are not pitch-tracker confidence, note detection, harmonic/percussive source separation, or probability that the source is harmonic.

The F0 candidate can jump by octave/subharmonic, especially for polyphonic, noisy, distorted, weak-fundamental, or percussive material. Do not convert it directly into a note label and claim that note was detected.

Detailed semantics:

```text
references/tonal-evidence.md
```

## 7. How to read V0.8 stereo evidence

### Correlation is signed

```text
+1 → strongly similar L/R
 0 → weak linear relation
-1 → strongly anti-correlated
```

Correlation does not by itself quantify Side energy.

### `side_to_mid_db`

```text
10 * log10(Side power / Mid power)
```

Negative means Mid energy exceeds Side; positive means Side exceeds Mid. There is no universal target.

### `decorrelation_proxy_mean`

```text
1 - abs(L/R correlation)
```

It is a mathematical proxy, not perceptual spaciousness. Read it with correlation sign.

### `negative_cross_energy_ratio`

Weighted fraction of bilateral FFT-bin evidence with negative real L/R cross-spectrum. It is phase-opposition evidence, not a phase-angle histogram, mono-cancellation percentage, audibility probability, or quality score.

### Mid/Side spectra and low-band evidence

Historical `bands_db` is the Mid spectrum. V0.8 adds Side spectrum and 20–120 Hz stereo relations. Very low-energy bands should not be overinterpreted.

Detailed semantics:

```text
references/stereo-evidence.md
```

## 8. How to read V0.7 masking evidence

`audio_masking_evidence()` reports transparent components rather than an opaque conclusion:

```text
relative_spectral_overlap
level_delta_a_minus_b_db
level_direction_weight_*
spectral_level_evidence_*
normalized_band_temporal_overlap
combined_evidence_*
masking_evidence_score
```

The scores are heuristic evidence for relative ranking in comparable contexts. They are not probabilities of audible masking and do not automatically require EQ or sidechain.

Detailed semantics:

```text
references/masking-evidence.md
```

## 9. Evidence quality matters

When interpreting window/pair/verification evidence, inspect the relevant context:

```text
window_seconds
active_ratio
valid_frames / valid_frame_ratio
mean_chroma_energy_ratio for V0.9
normalized_pitch_class_entropy for V0.9
tonal_center_top2_margin for V0.9
stereo_frames for V0.8
aligned_pairs / tolerance / mean offset for temporal and masking evidence
frequency / stereo band / ERB region when relevant
verification topology/window/target/active-coverage comparability for V1.0
```

Sparse, stale, mostly silent, poorly aligned, weakly covered, or technically non-comparable data should reduce certainty in the interpretation.

## 10. Relationship between tools

Use tools progressively rather than mechanically:

```text
audio_project_status()
    project readiness
        ↓
audio_mix_overview()
    coarse project state
        ↓
choose evidence family only when needed:
    audio_project_masking_scan() / audio_masking_evidence()
    audio_stereo_profile() / audio_stereo_compare()
    audio_tonal_profile() / audio_tonal_compare()
    audio_temporal_profile() / audio_temporal_compare()
```

Do not call every layer if the user's question is already answered.

For a requested DAW modification with verification:

```text
project ready + deterministic mapping
→ audio_begin_verification()
→ external control MCP change
→ external control MCP host readback
→ audio_complete_verification()
→ inspect controlled_comparison
→ specialized Analyzer evidence only if the question requires deeper detail
```

For exact symbolic music facts:

```text
exact DAW/MIDI/project data available
→ prefer that data

audio-only evidence needed or symbolic data unavailable
→ use V0.9 tonal tools with validity/uncertainty context
```

## 11. Parameter interpretation rules

Detailed semantics:

```text
references/parameters.md
references/masking-evidence.md
references/stereo-evidence.md
references/tonal-evidence.md
references/verification-evidence.md
```

Tool/selector details:

```text
references/analyzer-mcp.md
```

Always keep these distinctions:

- Sample Peak ≠ True Peak.
- RMS ≠ LUFS.
- LUFS-S ≠ cumulative LUFS-I.
- Analyzer spectrum dB is not calibrated SPL.
- Centroid/Rolloff/Flatness are descriptive statistics, not quality scores.
- Stereo Correlation ≠ Side/Mid energy.
- Low correlation ≠ anti-correlation.
- High Side energy ≠ proof of phase opposition.
- `decorrelation_proxy = 1 - abs(correlation)` must be read with correlation sign.
- Negative-cross evidence is not an audible mono-cancellation percentage.
- Spectral Flux is normalized spectral redistribution, not simple gain change.
- RMS Rise is rapid level-increase evidence, not Crest Factor or attack time.
- Spectral overlap, temporal overlap, and V0.7 masking evidence are not probabilities of audible masking.
- Onset candidates are threshold-based change candidates, not ground-truth labels.
- Chroma is not note probability or MIDI transcription.
- Tonal-center profile correlation is not key probability.
- Tonal-center top-2 margin is not calibrated confidence.
- Pitch-class entropy is not musical quality.
- Chroma energy coverage is not correctness probability.
- Single-F0 harmonic ratio is not probability of harmonic content.
- Harmonic F0 candidate is not a detected musical note.
- Chroma similarity is not harmonic compatibility.
- V1.0 topology fingerprint is not a persistent DAW-project hash.
- `host_readback` is caller-supplied external control-MCP evidence, not an Analyzer-verified host query.
- `controlled_comparison` is a technical comparability gate, not an artistic quality score.
- `null` is unavailable, not zero.

## 12. Boundary with FL Studio control MCP

AI Audio Analyzer MCP is responsible for:

```text
measure / read / compare / verify measurement conditions
```

FL Studio control MCP is responsible for:

```text
DAW topology / project data / plugin access / host changes / host readback
```

This Skill may guide deterministic Identify mapping and V1.0 measurement verification around an external DAW change. It must **not** prescribe what parameter to change, by how much, what key to use, what chord to replace, or which artistic style to follow.

If the user asks to modify the project:

1. inspect the actual DAW tracks/slots/plugins/parameters and relevant symbolic project data;
2. establish `audio_begin_verification()` before the write when measured Before/After verification is desired;
3. use the real control MCP to perform the write;
4. read the actual host state back through that control MCP;
5. pass a factual summary/readback to `audio_complete_verification()`;
6. inspect measurement comparability before interpreting the A/B strongly.

Do not invent controls, notes, write success, or readback values.

## 13. Output discipline

When citing Analyzer evidence, include enough context to make it auditable:

```text
instance / selector
measurement window
signal validity / active ratio
evidence-quality fields when relevant
frequency / stereo band / ERB region / pitch-class context
alignment quality for temporal evidence
verification_id / topology / coverage / readback context for V1.0 when relevant
measurement/evidence value
what the metric can and cannot establish
```

Do not present these as Analyzer-measured facts:

- a sound "should" be warmer, brighter, wider, louder, narrower, or more modern;
- a genre must hit a fixed LUFS number;
- a frequency must be cut/boosted by a specific amount;
- spectral/masking evidence automatically requires EQ or sidechain;
- one correlation/Side-Mid/negative-cross score is inherently good or bad;
- stereo evidence automatically requires mono, narrowing, widening, phase rotation, or a stereo processor;
- the top tonal-center candidate is certainly the song key;
- an F0 candidate is certainly the played note;
- similar/different chroma automatically means two sources are harmonically compatible/incompatible;
- V0.9 evidence automatically requires transposition, tuning, chord replacement, harmony editing, arrangement changes, or any processing action;
- `controlled_comparison=true` means the After state is better, correct, or preferred;
- caller-supplied `host_readback` was independently verified by Analyzer.

Those are symbolic/artistic/processing or external-host-state judgments outside the measurement scope of this MCP and Skill.
