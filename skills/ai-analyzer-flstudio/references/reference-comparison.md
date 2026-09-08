# Reference Comparison Evidence

Use P8a when the user wants a **reference direction** for a current mix without turning the Analyzer into an automatic master-matching system.

## Current tools

```text
audio_capture_reference(track, label="", seconds=10.0)
audio_list_references()
audio_compare_reference(reference_id, target, seconds=None)
```

## Scope

P8a references are:

```text
session-scoped
frozen at capture time
recent receive-time windows
measurement profiles only
not stored audio
not persistent across MCP restart
not whole-song claims
```

The source `runtime_id` is retained only as capture provenance for the current live plugin instance. It is not a persistent project/track identity.

Do not present a P8a reference as a persistent reference-library entry. Persistent reference profiles belong to future project-memory work after trustworthy project identity exists.

## What a frozen profile contains

Where the active Analyzer profile and signal support it, the reference stores compact derived evidence such as:

```text
RMS / Peak / Crest
LUFS-S / True Peak
32 Analyzer spectrum band-center averages
coarse spectral regions
centroid
stereo correlation / width
P7a mono-fold RMS delta
grouped mono-fold energy loss
capture scope / source / binding provenance
```

It does **not** store source audio.

## Absolute comparison

`audio_compare_reference()` returns descriptive target-minus-reference deltas.

Examples:

```text
rms_db = +1.8
crest_db = -2.0
presence_2000_5000_db = +1.2
stereo_width = -0.08
```

The direction is always explicit:

```text
target - reference
```

A positive or negative difference is not automatically good or bad.

## RMS-level-normalized spectral comparison

A pure level offset can make every spectral band appear different even when the shape is effectively the same.

P8a therefore also provides an explicit RMS-level-normalized view:

```text
target_gain_to_reference_db = reference_rms - target_rms

normalized spectral delta
= (target_band + target_gain_to_reference_db) - reference_band
```

This is only a comparison view. The Analyzer does not apply the gain and does not alter either source.

Use the two views for different questions:

```text
absolute
  How different are the measured levels as they actually are?

level-normalized
  After removing one broad RMS offset, how different is the spectral shape?
```

Do not use RMS normalization when absolute loudness itself is the question.

## Mono/stereo comparison

P7a mono-fold evidence remains an independent dimension.

A reference may be:

```text
wider
narrower
more positively correlated
less positively correlated
more or less vulnerable to mono-fold energy loss
```

None of those facts implies an automatic widening/narrowing operation.

Do not collapse:

```text
correlation
width
Side/Mid
negative-cross
mono-fold delta
```

into one stereo-quality score.

## No automatic master matching

Never reason like this:

```text
reference has +2 dB at 8 kHz
-> add +2 dB at 8 kHz to the target
```

A spectral difference may come from:

```text
arrangement
instrument choice
register
vocal balance
master level
production style
reference section mismatch
intentional tonal direction
```

Use reference evidence as context for deciding **where to inspect**, not as a direct inverse filter.

## Cross-song / cross-section semantics

P8a never silently assumes that two sections or two songs are semantically equivalent.

Do not infer:

```text
A -> Verse
B -> Chorus
Drop 1 in target == Drop 1 in reference
```

unless the user or an authoritative future structure-mapping layer establishes that relationship.

For current P8a, the user chooses what to capture and compare.

## Current limitations

P8a does not yet provide:

```text
persistent reference libraries
historical arbitrary Section 32-band reference capture
whole-song reference completeness
P6 dynamics distributions embedded into the same frozen recent-window profile
external-file faster-than-realtime scanning
automatic cross-song section matching
processing prescriptions
quality scores
```

These limitations are deliberate.

Historical Section reference depth should reuse P4b retained-detail infrastructure rather than invent another history store. Persistent reference profiles should reuse P5 project memory. External commercial reference files should eventually use the P10 offline scanner so the same evidence schema can be produced without realtime playback.

## Recommended LLM workflow

```text
1. Determine the user's reference direction and the passage/source to capture.
2. Capture the reference with audio_capture_reference().
3. List references if the reference_id is not already in context.
4. Capture/compare the current target with audio_compare_reference().
5. Inspect absolute level differences separately from RMS-normalized shape differences.
6. Keep dynamics, spectrum, stereo and mono compatibility as separate evidence groups.
7. Use detailed masking/stereo/temporal tools only when a difference needs diagnosis.
8. Make DAW/plugin changes through the external DAW-control MCP.
9. Verify the changed passage with Analyzer same-range verification when the comparison is meant to be controlled.
```

## Interpretation boundary

Reference comparison answers:

```text
How is the target different from this chosen reference evidence?
```

It does not answer automatically:

```text
Which difference is wrong?
Which parameter must change?
How much EQ/compression/stereo processing should be applied?
Whether the target should become identical to the reference?
```

Those are context-dependent LLM/user decisions.