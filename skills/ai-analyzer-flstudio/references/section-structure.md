# Song Section Structure Evidence

Use this reference after transport-aware Song Memory has captured enough of a song or passage to reason about large-scale musical form.

The structure layer is deliberately **evidence-first**:

```text
Song Memory
→ structural boundary novelty
→ section summaries
→ recurring-section similarity
→ neutral A/B/C/... families
→ optional LLM interpretation with DAW/project context
```

It does **not** claim that a family named `A` is an Intro, `B` is a Verse, or `C` is a Chorus. Exact DAW markers, Playlist labels, arrangement metadata, MIDI/project annotations, or explicit user knowledge remain authoritative for exact section names.

## Tools

```text
audio_section_map(
  reference_track=None,
  transport_epoch=None,
  min_section_seconds=8,
  sensitivity=0.55,
  family_similarity=0.78,
  max_sections=48,
  max_tracks=32
)

audio_section_profile(
  section_id,
  map_id=None,
  max_tracks=32,
  max_related=8
)

audio_track_story(
  track,
  map_id=None
)
```

Current MCP 1.2 exposes these reasoning tools without changing the OSC wire format. They consume already-retained protocol-1.2 Song Memory.

`audio_track_story()` is documented in detail in `track-story.md`; this reference focuses on the shared section/family map it consumes.

## Recommended Agent flow

For a whole-song mixing/mastering request:

```text
audio_project_status()
→ establish deterministic Analyzer bindings when needed
→ audio_song_status()
→ ensure enough of the target song/pass has been captured
→ audio_section_map()
→ inspect neutral section boundaries/families
→ audio_track_story() for tracks whose cross-section evolution matters
→ audio_section_profile() for sections that need multi-track context
→ use audio_song_timeline() only if raw time evolution is still needed
→ drill into Temporal / Masking / Stereo / Tonal tools only when a specific relationship needs deeper evidence
```

Do not call every Analyzer tool for every section. The structure layer exists to make later tool selection more selective and context-aware.

## Reference track

By default, `audio_section_map()` prefers the bound Master Analyzer as the structural reference. If no Master can be identified, it falls back to the first available Analyzer instance.

A caller may explicitly provide `reference_track` when another track is a more appropriate structural reference.

The reference provides the main one-second sequence used for boundary detection. Cross-track activity is added as supporting evidence.

## Boundary detection

The current detector compares multi-scale windows before and after each candidate DAW-time boundary.

Default context scales:

```text
2 seconds
4 seconds
8 seconds
```

Evidence families include:

```text
activity   cross-track active/inactive pattern changes
energy     RMS / LUFS-S changes
spectrum   centroid + broad spectral-region changes
chroma     pitch-class distribution change
stereo     correlation / width changes
dynamics   crest changes
temporal   spectral-flux changes
```

Current novelty weights are intentionally transparent rather than learned:

```text
activity   0.25
energy     0.20
spectrum   0.20
chroma     0.15
stereo     0.08
dynamics   0.06
temporal   0.06
```

The detector robust-normalizes scalar features over the analyzed reference pass, combines available evidence, smooths the novelty curve, chooses an adaptive threshold, finds local peaks, and enforces a minimum section spacing.

### `boundary_strength`

Boundary strength is **structural novelty evidence**.

It is not:

```text
a calibrated probability that a human would mark a section boundary
a Verse/Chorus classifier confidence
a musical-quality score
a reason to apply processing
```

Inspect `dominant_evidence`, the individual evidence components, context coverage, and surrounding song context before interpreting a boundary.

## Coverage rules

Missing evidence must remain missing.

The structure detector does not interpret a gap in retained Song Memory as silence or as a musical transition. Returned `coverage_gaps` identify missing DAW-time evidence explicitly.

Boundary contexts require meaningful retained coverage. Low-coverage regions can therefore produce no boundary candidate rather than a fabricated confident result.

Track Story inherits the same rule: a structurally valid Section may remain visible while a particular track has insufficient evidence there. That section must not be treated as silence, muting, absence, or a role change for the target track.

If the reference pass has weak overall coverage, warnings are returned. Replaying the target range is preferable to lowering evidence-quality expectations merely to obtain a boundary.

## Cross-instance epoch alignment

`transport_epoch` is instance-local. Never assume:

```text
Master epoch 7 == Kick epoch 7 == Vocal epoch 7
```

The structure layer uses the requested/reference epoch only for the reference Analyzer. Supporting Analyzer instances are selected using the retained pass with the strongest overlap over the same DAW-time range.

Therefore a valid analysis may intentionally use:

```text
Master epoch 7
Kick epoch 3
Vocal epoch 11
```

as long as those passes cover the same song-time region.

Track Story follows the same principle for its target track. If the target was not one of the map's original supporting tracks, it can still select that track's best-overlapping retained epoch over the map range.

This is evidence alignment by DAW time, not a persistent project-wide pass identity.

## Recurring section families

After boundaries are selected, each section receives a descriptive fingerprint using evidence such as:

```text
cross-track activity profile
RMS / LUFS-S
broad spectral balance
spectral centroid
chroma
stereo relation
dynamics / temporal character
duration
```

Section-to-section similarity keeps these components explicit. Current family grouping is deterministic, lightweight, and heuristic rather than a trained musical-form model.

Current recurrence-similarity weights:

```text
activity   0.30
spectrum   0.22
energy     0.18
chroma     0.15
stereo     0.07
dynamics   0.05
duration   0.03
```

Sections that pass the family-similarity threshold are assigned the same neutral family ID:

```text
S01  A
S02  B
S03  C
S04  B
S05  C
```

### Family IDs are neutral

Never automatically translate:

```text
A → Intro
B → Verse
C → Chorus
```

A family only means that the Analyzer found substantial structural recurrence under the current evidence model.

An LLM may propose semantic names later when additional evidence supports them, for example:

```text
exact DAW markers
Playlist/pattern names
track names and arrangement metadata
user-provided structure
lyrics/vocal context
other explicit project information
```

When exact project metadata conflicts with audio inference, prefer the exact metadata for naming.

## `audio_section_map()` output

Important fields include:

```text
map_id
reference
boundaries[]
section_count
family_count
family_counts
sections[]
recurring_similarity_pairs[]
coverage_gaps[]
track_activity_source_count
warnings
```

Each section exposes:

```text
section_id
family_id
family_occurrence
start_seconds
end_seconds
duration_seconds
reference_summary
active_tracks
```

`recurring_similarity_pairs` exposes strong section-to-section recurrence evidence instead of hiding it behind the family label.

## `audio_section_profile()`

Use after `audio_section_map()` when one section needs deeper project context.

It returns:

```text
section/family identity
section DAW-time range
reference summary
same-family sections
related sections + similarity components
per-track section profiles
selected transport epoch for every supporting Analyzer
per-track data quality
```

This is the preferred bridge from large-scale song structure into **multi-track reasoning inside one section**.

## `audio_track_story()` relationship

Use Track Story for the orthogonal question: **how one Analyzer instance changes across the section map**.

It reuses the same `section_id`, `family_id`, DAW-time ranges, and coverage semantics, then adds per-track section observations, adjacent-section deltas, recurring-family per-dimension variation, and relative extrema.

Example conceptual use:

```text
Family B returns as S02 and S04.
→ inspect one target track with audio_track_story()
→ compare that track's measured energy/spectrum/stereo/temporal dimensions across S02/S04
→ if a specific cross-track relationship matters, inspect the relevant section profile
→ only then call detailed masking/stereo/temporal tools for that relationship
```

Do not infer a musical role from Track Story measurements alone. Exact Mixer/project names or explicit user context are the proper source for exact track roles.

## Map lifetime

`map_id` identifies a recently generated structure map inside the running MCP process. Maps are bounded session memory, not persistent project IDs.

Track Story based on that map is likewise session-scoped reasoning, not persistent project history.

If the MCP process restarts, call `audio_section_map()` again.

If the song arrangement or captured pass changes materially, regenerate the map instead of assuming the cached map represents the new project state.

## Limitations

The current structure layer is intentionally lightweight and explainable. It is not:

```text
a neural music-structure model
a source separator
a beat/downbeat tracker
a semantic Verse/Chorus/Drop classifier
a lyric structure model
a persistent arrangement database
a sample-accurate segmentation system
```

The current one-second Song Memory sets the practical structural time resolution. The detector is intended for section-scale reasoning, not transient slicing.

No structure or Track Story output implies a mixing/mastering action. Use structure to determine **where**, **when**, and **which recurring context** should be measured more deeply; use Track Story to describe **how one observed track changes across those contexts**.