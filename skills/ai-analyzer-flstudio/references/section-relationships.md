# Section-aware Mix Relationship Evidence

Use this reference after Song Memory and an explainable Section Map exist and the Agent needs to know **which track pairs deserve deeper inspection in which song contexts**.

The relationship layer is a bounded routing/shortlisting layer:

```text
Song Memory
→ Section Map / neutral A-B-C families
→ per-track section summaries
→ bounded pair shortlist
→ choose one relevant section/family
→ replay/select that passage when deeper recent-window evidence is needed
→ masking / stereo / temporal pair tools
```

It is not an automatic mix-problem detector and it does not prescribe processing.

## Tool

```text
audio_section_relationships(
  map_id=None,
  max_pairs=12,
  max_tracks=32,
  include_master=False,
  min_activity_overlap=0.15,
  min_shortlist_priority=0.18
)
```

The tool consumes retained MCP evidence only. It adds no realtime DSP and no OSC analysis-frame fields.

## Why this layer exists

A project with many Analyzer instances can create a large number of possible pairs. Returning every pair for every section would waste computation, tokens and Agent attention.

The tool therefore keeps work bounded:

```text
eligible tracks
→ per-section coverage/activity filter
→ at most 24 active/covered section candidates
→ pair shortlist heuristic
→ globally ranked bounded pair list
```

Default returned pair limit is 12; the hard `max_pairs` limit is 32. `max_tracks` defaults to 32 and is hard-limited to 64.

Master is excluded by default because Master-vs-every-track relationships are usually structurally trivial and would dominate a project shortlist. Set `include_master=true` only when the question genuinely requires those relationships.

## Shortlist evidence

A pair needs adequate retained coverage and overlapping observed activity before it can be shortlisted.

Current coarse routing evidence includes:

```text
activity_overlap
coarse_spectral_shape_overlap
level_proximity
stereo_width_proximity
```

The current ranking heuristic is intentionally transparent:

```text
shape_proximity = weighted available evidence
  spectral shape     0.50
  RMS proximity      0.30
  width proximity    0.20

shortlist_priority = activity_overlap × shape_proximity
```

### `shortlist_priority` is not a problem score

Never interpret `shortlist_priority` as:

```text
masking probability
audibility probability
mix-problem probability
quality score
importance score
a reason to EQ / sidechain / compress / pan / widen
```

It only answers:

> Is this pair in this measured section sufficiently co-active and similar in coarse observable dimensions that a deeper look may be worth the Agent's attention?

A high value can be musically intentional. A low value does not prove the pair is harmless or irrelevant.

## Coverage and activity rules

Keep these separate:

```text
coverage_ratio_min
  retained evidence coverage for the weaker-covered member of the pair.

activity_overlap
  min(active_ratio_a, active_ratio_b) within the observed section.
```

Rules:

- missing coverage != silence;
- low activity != mute state;
- one track being inactive in a section means the pair cannot have strong simultaneous activity evidence there, not that the track is absent from the arrangement;
- insufficient coverage must produce unavailable relationship evidence rather than a false low conflict score.

Current minimum relationship coverage follows the Track Story/structure evidence floor (20%).

## Section and family context

For each returned pair inspect:

```text
shortlisted_section_ids
present_family_ids
observed_but_not_shortlisted_family_ids
family_presence[]
adjacent_changes[]
section_evidence[]
```

This can show patterns such as:

```text
Pair A/B
  family A: shortlisted
  family B: observed but not shortlisted

Pair A/C
  family A: observed but not shortlisted
  family B: shortlisted
```

This is the intended P2 use: identify **where a relationship appears, disappears or materially changes**.

`A/B/C` remain neutral recurrence-family labels. Never convert them automatically to Intro/Verse/Chorus/Drop.

## Adjacent relationship changes

`adjacent_changes` may report:

```text
entered_shortlist
left_shortlist
relationship_evidence_changed
evidence_availability_changed
```

When both adjacent sections remain shortlisted, deltas may include changes in:

```text
shortlist_priority
activity_overlap
coarse_spectral_shape_overlap
```

These changes are descriptive. They do not mean the later section is better/worse or that processing should change at the boundary.

## Directional evidence

Some returned fields preserve a stable A/B direction:

```text
rms_db_b_minus_a
stereo_width_b_minus_a
spectral_region_b_minus_a_db
strongest_directional_regions
louder_runtime_id
```

`B - A` means exactly that arithmetic direction. It does not mean B is the problem, A should be protected, or either track should be processed.

## Deep follow-up tools and the historical-range limitation

The section relationship tool is based on retained DAW-time Song Memory.

Current detailed pair tools such as:

```text
audio_masking_evidence()
audio_temporal_compare()
audio_stereo_compare()
```

still use recent-window evidence. They are **not yet transport-anchored historical section queries**.

Therefore the safe flow is:

```text
audio_section_relationships(map_id)
→ choose the relevant pair + section
→ use DAW control / user playback to select or replay that section
→ confirm the measurement window is now on that passage
→ call the detailed recent-window pair tool
```

Do not call a current/recent pair tool seconds later and claim its result came from historical `S02` merely because `audio_section_relationships()` mentioned `S02`.

Transport-anchored exact same-range pair/verification evidence is a later roadmap capability.

## Cross-instance epoch semantics

Every Analyzer instance has its own local `transport_epoch` counter.

The relationship layer inherits Track Story/Section Structure alignment rules and selects retained passes by overlapping DAW time. It does not require:

```text
Track A epoch 7 == Track B epoch 7
```

A valid relationship analysis may use different local epoch numbers for different tracks if they cover the same DAW-time section.

## Bounded-output warnings

Inspect `warnings` and the project-count fields:

```text
eligible_project_track_count
evaluated_track_count
section_track_candidate_cap
candidate_pair_count_before_limit
returned_pair_count
```

Warnings can indicate:

- more project tracks existed than `max_tracks` allowed;
- a section exceeded the active-track candidate cap;
- more candidate pairs passed the threshold than `max_pairs` returned;
- no pair passed the current thresholds.

`no pair passed` does **not** prove there are no audible interactions or masking issues.

## Recommended Agent flow

```text
audio_project_status()
→ audio_song_status()
→ capture enough Song Memory
→ audio_section_map()
→ audio_track_story() when one track's evolution matters
→ audio_section_relationships() when cross-track changes matter
→ inspect section/family/coverage context
→ select one relevant pair + passage
→ replay/select that passage if deeper pair evidence is required
→ call only the necessary masking/stereo/temporal tool
```

Do not mechanically expand every returned pair into every detailed pair tool.

## Interpretation boundary

Never convert relationship evidence directly into:

```text
"cut Track A at 250 Hz"
"sidechain B to A"
"compress B"
"pan A left"
"make B narrower"
"this pair is bad"
```

Those are processing/aesthetic decisions. The Analyzer layer identifies measured context and evidence; the LLM/user reasons about artistic intent and, when a real change is requested, the external DAW-control MCP performs it and supplies actual host readback.
