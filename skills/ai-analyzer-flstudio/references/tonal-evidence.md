# V0.9 Tonal and Music-Semantic Evidence

This reference explains how to call and interpret AI Audio Analyzer V0.9 music-semantic measurements. It does **not** prescribe a key change, tuning edit, chord edit, arrangement decision, EQ move, mix process, or production style.

## Scope

V0.9 adds audio-domain evidence for questions that cannot be answered from level/spectrum/stereo data alone:

```text
12-bin pitch-class distribution (chroma)
→ tonal-center candidate ranking
→ evidence-quality context

single-F0 spectral harmonic alignment
→ harmonic-alignment evidence
→ candidate fundamental frequency
```

Use these measurements only when the audio itself is the relevant source of evidence.

If an available DAW/MIDI/project source provides exact note events, written key metadata, chord data, tuning metadata, or other symbolic information, prefer that source for exact symbolic claims. Analyzer V0.9 is an audio inference layer, not a replacement for exact project data.

## Tools

### `audio_tonal_profile(track, seconds=8)`

Use for a stable recent-window tonal profile of one Analyzer instance.

Main output groups:

```text
chroma
tonal_center_evidence
harmonic_alignment
evidence_quality
```

### `audio_tonal_compare(track_a, track_b, seconds=8)`

Use when the question is how two measured audio-domain pitch-class distributions differ.

Important outputs:

```text
pitch_class_comparison.cosine_similarity
pitch_class_comparison.jensen_shannon_divergence
pitch_class_comparison.normalized_power_delta_b_minus_a[12]
harmonic_alignment_delta_b_minus_a
evidence_quality.track_a
evidence_quality.track_b
```

These outputs do not establish harmonic correctness, consonance, compatibility, arrangement quality, or a required production action.

## Chroma

### `chroma.normalized_power`

Twelve normalized pitch-class power values in this fixed order:

```text
C, C#, D, D#, E, F, F#, G, G#, A, A#, B
```

The VST3 derives them from the **Mid spectrum** over approximately:

```text
80 Hz – 5 kHz
```

Each eligible FFT bin is assigned to the nearest 12-TET pitch class and accumulated in the power domain. The twelve values are then normalized to sum approximately to `1.0`.

Interpret them as a relative audio-domain pitch-class distribution.

Do **not** interpret a chroma value as:

- probability that a note is playing;
- MIDI note velocity;
- note count;
- chord-membership probability;
- note transcription confidence;
- proof that a pitch class is musically important.

Octave information is intentionally collapsed.

### `chroma.top_pitch_classes`

The same chroma values ranked from largest to smallest. This is a convenience view of relative pitch-class power, not note detection.

### `chroma.analysis_range_hz`

Currently approximately:

```text
80 – 5000 Hz
```

Energy outside this range can still matter musically but does not contribute to the V0.9 chroma vector.

## Chroma evidence quality

### `chroma_energy_ratio`

Per-frame ratio:

```text
power used for chroma analysis (80 Hz–5 kHz)
------------------------------------------------
Analyzer Mid-spectrum power in the analysis range
```

The windowed profile exposes its mean as:

```text
evidence_quality.mean_chroma_energy_ratio
```

Use this as **coverage context**, not a probability that the chroma is correct.

A low value means much of the measured spectral power lies outside the chroma-analysis range. A high value means more of the measured power lies inside it. Neither is inherently good or bad.

### `chroma.normalized_entropy`

Normalized Shannon entropy of the twelve-bin chroma distribution:

```text
approximately 0 → power concentrated in fewer pitch classes
approximately 1 → power distributed more uniformly across pitch classes
```

Entropy describes distribution concentration. It is not tonal quality, musical complexity, consonance, or confidence by itself.

## Tonal-center evidence

V0.9 compares the aggregated chroma vector with explicit Krumhansl-Kessler major/minor key profiles using Pearson correlation.

For each of 12 tonics × 2 modes:

```text
tonal_center_evidence.top_candidates[].tonic
tonal_center_evidence.top_candidates[].mode
tonal_center_evidence.top_candidates[].profile_correlation
```

The highest candidate means only:

> among the tested major/minor profile templates, this template currently correlates most strongly with the measured aggregate chroma.

It is **not** a ground-truth key label.

The method can be ambiguous for short windows, modal music, chromatic material, changing harmony, drones, percussion-heavy passages, atonal material, sparse notes, borrowed harmony, or mixtures of multiple tonal sources.

### `profile_correlation`

Pearson correlation between the measured chroma shape and one rotated major/minor template.

It is a template-similarity statistic, not a probability.

Do not convert it into a percentage such as “82% chance of C major”.

### `top2_margin`

Difference between the first and second ranked profile correlations:

```text
best correlation - second-best correlation
```

A larger margin means the best candidate is more separated **within this 24-template comparison**. A smaller margin means the top candidates are closer.

It is not a calibrated confidence probability and has no universal pass/fail threshold.

Read it together with:

```text
mean_chroma_energy_ratio
normalized_pitch_class_entropy
valid_frame_ratio
active_ratio
window_seconds
```

## Single-F0 harmonic-alignment evidence

### `single_f0_harmonic_energy_ratio`

The VST3 searches a candidate fundamental approximately within:

```text
55 – 1000 Hz
```

and evaluates spectral energy near up to eight integer harmonics. The chosen candidate is the one that best supports a single-harmonic-series explanation under the current heuristic.

The resulting ratio describes how much semantic-range spectral energy is near that candidate's harmonic locations.

It is **not**:

- probability that the source is harmonic;
- percentage of “good harmonics”;
- harmonic/percussive source separation;
- a calibrated harmonic-to-noise ratio;
- fundamental-frequency confidence;
- pitch-tracker confidence;
- chord confidence;
- a quality score.

Polyphonic, noisy, percussive, inharmonic, distorted, detuned, weak-fundamental, or octave-rich signals can produce misleading or unstable candidates.

### `harmonic_f0_candidate_hz`

The candidate fundamental used by the single-F0 heuristic.

Do not directly convert this to a note label and report it as detected pitch. The candidate can jump by an octave or subharmonic and can represent a common divisor of multiple spectral components rather than a played fundamental.

Windowed profile fields:

```text
harmonic_alignment.f0_candidate_hz_median
harmonic_alignment.f0_candidate_hz_min
harmonic_alignment.f0_candidate_hz_max
```

A wide min/max spread is useful evidence that the candidate is unstable over the measured passage.

## Validity

Before interpretation inspect:

```text
semantic_v09_supported
semantic_v09_valid
signal_present
active_ratio
valid_frames
frames
window_seconds
```

For `audio_tonal_profile()`, also inspect:

```text
evidence_quality.mean_chroma_energy_ratio
evidence_quality.normalized_pitch_class_entropy
evidence_quality.tonal_center_top2_margin
evidence_quality.valid_frame_ratio
evidence_quality.active_ratio
```

`null` means unavailable, not zero.

A V0.8-or-earlier plugin can still provide normal Analyzer measurements while lacking V0.9 semantic evidence.

## Comparing two tracks

### `cosine_similarity`

Cosine similarity of the two normalized 12-bin chroma vectors.

Higher means the two distributions point in a more similar pitch-class direction. It does not establish harmonic compatibility or consonance.

### `jensen_shannon_divergence`

Symmetric divergence between the two normalized pitch-class distributions, bounded approximately to `0..1` by the implementation.

Lower means the distributions are more similar; higher means they differ more. This is a distribution-distance statistic, not a music-theory correctness score.

### `normalized_power_delta_b_minus_a`

For each pitch class:

```text
B - A
```

Positive means the normalized pitch-class share is larger in B; negative means larger in A.

Do not turn these deltas into mandatory note, harmony, arrangement, EQ, or tuning edits.

## LLM interpretation rules

Keep these distinctions explicit:

```text
chroma != note probability
pitch-class power != MIDI notes
tonal-center candidate != ground-truth key
profile correlation != key probability
top2 margin != calibrated confidence
entropy != quality
chroma coverage != correctness probability
single-F0 harmonic ratio != harmonic-content probability
F0 candidate != detected musical note
chroma similarity != harmonic compatibility
```

When making a factual statement from V0.9, state the evidence type and its limitation. Use exact symbolic DAW/MIDI data instead whenever that data is available and the question asks for exact notes, chords, or key metadata.
