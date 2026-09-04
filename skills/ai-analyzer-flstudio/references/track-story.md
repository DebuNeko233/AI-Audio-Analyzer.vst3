# Track Story Evidence

`audio_track_story(track, map_id=None)` summarizes how one live Analyzer instance behaves across the neutral structural sections produced from retained Song Memory.

It is a reasoning/read layer. It does not add realtime DSP, does not modify audio, and does not infer a musical role.

## Recommended call order

When a section map already exists:

```text
audio_section_map(...)
-> keep map_id
-> audio_track_story(track, map_id)
```

If `map_id` is omitted, Track Story uses the latest cached section map. If no usable map exists, it may create a default map from the current transport-aware Song Memory.

For deterministic multi-step analysis, prefer passing the exact `map_id` returned by `audio_section_map()`.

## What each section contains

Track Story exposes section-scoped evidence such as:

```text
section_id / family_id / family_occurrence
DAW-time start/end/duration
selected per-instance transport epoch
coverage ratio and data-quality metadata
active_ratio
RMS / LUFS-S / crest
spectral centroid
coarse spectral regions
stereo correlation / width
temporal spectral flux
12-bin chroma + strongest pitch classes
```

The selected transport epoch belongs to the requested Analyzer instance. Do not assume it must equal the reference track's epoch number. Cross-instance alignment is based on overlapping DAW-time coverage.

## Adjacent-section deltas

`delta_from_previous` is current minus previous for directly comparable descriptors.

Examples:

```text
rms_db = +3.2
stereo_width = +0.18
centroid_hz = +740
```

This means the measured descriptor increased from the previous section. It does **not** mean the Agent should automatically apply the opposite processing move.

Track Story also reports chroma cosine similarity between adjacent sections when tonal evidence is available.

Adjacent deltas are withheld when either section has insufficient retained coverage.

## Recurring-family variation

`family_consistency` groups observations by the neutral A/B/C/... recurrence families from the section map.

It reports per-dimension statistics such as:

```text
mean
min
max
spread
```

for activity, energy, spectrum, stereo, temporal evidence, and chroma pairwise similarity where available.

Do not convert those independent dimensions into one universal "consistency score". A recurring section may intentionally change in one dimension while remaining stable in another.

## Relative extrema

`relative_extrema` identifies which observed section is lowest/highest for each descriptor. These are within-track relative observations, not absolute mix-quality judgments.

For example:

```text
stereo_width.highest.section_id = S05
```

means S05 is the widest observed section for this Analyzer instance among adequately covered sections. It does not imply that S05 is too wide.

## Coverage rules

The minimum Track Story evidence threshold follows the section layer's retained coverage guard.

Critical semantics:

```text
missing coverage != silence
low active_ratio != muted
no section row != inactive
```

If a section has insufficient coverage:

- keep it visible as a structural time range;
- mark `evidence_available=false`;
- do not infer silence, muting, absence, or a role change;
- do not create an adjacent delta through that gap.

Cumulative Analyzer drops also reduce confidence in completeness. They do not identify which artistic event was missed.

## Tonal evidence

Track Story exposes chroma and strongest pitch-class weights as evidence only.

Do not silently promote:

```text
strong C chroma -> C major
strong G chroma -> G chord
```

Exact MIDI/project/key/chord metadata wins when available. Audio-derived key/chord interpretation remains a separate uncertain reasoning step.

## Role and arrangement naming

Track Story must not invent a track role from measurements alone.

Do not automatically convert:

```text
low-frequency energy -> Bass
high transient activity -> Drums
mid-forward centered signal -> Vocal
```

Use exact Mixer/project names or explicit user context when available.

Likewise, neutral section families are not semantic arrangement labels:

```text
A != Intro
B != Verse
C != Chorus
```

An LLM may suggest semantic names only when supported by exact DAW metadata or explicit contextual reasoning, and should preserve uncertainty when the evidence is indirect.

## Good uses

Track Story is useful for questions such as:

- Where does this track become more or less active?
- Which section is relatively louder/brighter/wider for this track?
- Does the same recurring family return with similar or different spectral/stereo behavior?
- Which adjacent section transition changes this track most in a particular descriptor?
- Is a suspected change supported by adequate retained coverage?

## Bad uses

Do not use Track Story alone to claim:

- the exact musical role of a track;
- exact Verse/Chorus/Drop names;
- that a low-active section is muted when coverage is incomplete;
- that one section is objectively better because it is louder/brighter/wider;
- a required EQ/compression/stereo move from a descriptor delta;
- persistent project identity across MCP restarts.

Track Story and its section map remain session-scoped until a future persistent project-identity/cache layer is implemented.
