# Closed-loop Verification Evidence

This reference explains both verification paths exposed by AI Audio Analyzer MCP 1.2.

Neither path decides what DAW change should be made, and neither path labels an artistic result better or worse.

AI Audio Analyzer never performs the sound-changing DAW operation. The external DAW-control MCP owns the real write and actual host readback. Analyzer owns measurement evidence and comparability checks.

## Which verification path to use

Prefer **transport-anchored same-range verification** whenever a specific DAW-time passage is known or can be replayed:

```text
audio_begin_range_verification(label, start_seconds, end_seconds, ...)
→ inspect ready_for_external_change / baseline_blockers
→ external DAW-control MCP performs the real write
→ external DAW-control MCP reads actual host state back
→ replay the returned effective_range
→ audio_complete_range_verification(..., host_readback="...")
```

Use the older **recent-window verification** only when an explicit retained DAW-time range is not practical:

```text
audio_begin_verification(label, seconds=5, ...)
→ inspect ready_for_external_change / baseline_blockers
→ external DAW-control MCP performs the real write
→ external DAW-control MCP reads actual host state back
→ replay a comparable passage
→ audio_complete_verification(..., host_readback="...")
```

Do not silently describe the recent-window path as exact same-range verification.

## Shared rules

### `verification_id`

A Bridge-session identifier for one verification experiment. It is not a permanent project ID, DAW undo ID, plugin runtime UUID, or persistent database key.

Both verification stores disappear when the Analyzer MCP process exits.

### `ready_for_external_change`

`true` means the current Before baseline passed that verification mode's technical pre-change guards. It does not mean the proposed processing move is appropriate.

If false, inspect `baseline_blockers` and establish a clean baseline before changing the DAW.

### Target selectors

Prefer deterministic selectors:

```text
mixer:<track_index>/slot:<slot>
```

Do not use equal numeric transport epochs as cross-track identity. Epochs are instance-local.

### `controlled_comparison`

This is a technical comparability gate only.

It does **not** mean:

- After is better;
- the change should be kept;
- a processor setting is correct;
- the mix is more professional;
- masking/stereo/tonal evidence perceptually improved.

### `closed_loop_complete`

`true` additionally requires caller-supplied actual host readback from the external DAW-control layer.

`host_readback` must describe what the host actually returned after the write, not the intended value.

Analyzer stores this text for auditability but does not independently validate the DAW/plugin parameter state.

### Delta convention

```text
Delta = After - Before
```

A positive delta only means the After measurement is numerically higher on that axis.

## Transport-anchored same-range verification

Tools:

```text
audio_begin_range_verification(...)
audio_complete_range_verification(...)
audio_range_verification_status(...)
```

This path freezes a retained Song Memory range before the external change and requires a clean replay of the same normalized DAW-time range after the change.

### Requested vs effective range

Song Memory is retained in canonical one-second bins. Therefore fractional requests are made explicit rather than pretending sub-second precision exists.

Example:

```text
requested_range  2.25 .. 4.20 s
effective_range  2.00 .. 5.00 s
resolution       1.0 s
```

Use the returned `effective_range` for replay and reporting.

Transport coordinates remain approximate Analyzer/host context, not sample-accurate edit coordinates.

### Coverage-first pass selection

For each Analyzer independently, the range resolver selects the retained transport epoch using:

```text
1. best DAW-time coverage
2. newest pass only as a tie-breaker
```

A newer sparse pass must not displace an older complete pass merely because it is newer.

Different tracks may legitimately select different local epoch numbers for the same musical range.

### After freshness fence

`audio_begin_range_verification()` freezes a wall-clock `receive_fence`.

The After resolver must select a retained pass whose requested range was first observed **after** that fence. Pre-change Song Memory cannot be silently reused as the After measurement.

If the same range has not been replayed cleanly after the change, `stale_after_targets` prevents a controlled comparison.

### Coverage

The default minimum retained coverage is a technical evidence threshold, not an artistic threshold.

Missing coverage is not silence. Sparse coverage must not be interpreted as inactivity, muting, or a successful change.

### Historical feature availability

Same-range comparison uses the measurement families actually present in the retained Before and After evidence.

Do not substitute the Analyzer's current live Analysis Profile for historical availability. A Profile may have changed after the passage was captured.

Current live feature-mask values may still be useful audit context, but retained field availability determines whether a historical dimension can be compared.

### Dropped blocks

A higher cumulative dropped-block count in the selected After evidence is treated as a data-quality regression and blocks `controlled_comparison=true`.

This is a measurement integrity guard, not an audio-quality judgment.

### Active ratio

In same-range mode, `active_ratio` is descriptive evidence. It is **not** used as a proxy for passage identity, because DAW-time anchoring already defines the passage.

### Range LUFS-I limitation

The same-range result intentionally does **not** expose a fake range-integrated LUFS-I delta.

Current retained `lufs_i_latest` is cumulative within a transport pass, not a mathematically isolated integrated loudness for an arbitrary sub-range. Until a true range-integrated loudness representation exists, do not label it as section/range LUFS-I.

Use retained LUFS-S/RMS/peak/crest and other supported range evidence instead.

### Same-range comparability fields

Important fields include:

```text
same_effective_range
topology_unchanged
missing_targets
invalid_targets
feature_availability_mismatch_targets
dropped_block_regression_targets
stale_after_targets
warnings
```

When reporting a result, include:

```text
verification_id
requested_range
effective_range
resolution_seconds
selected transport epoch per target for Before and After
coverage per target
post-baseline freshness status
controlled_comparison
external host-readback status
measurement deltas actually used
```

## Recent-window verification

Tools:

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

This older path captures recent measurement windows rather than an explicit retained DAW-time range.

Its strict comparability guards include:

```text
same Before/After window duration
Analyzer topology unchanged
no requested target missing
valid active analysis in both windows
active-ratio absolute difference within 0.15
```

The `0.15` active-ratio tolerance is a transparent recent-passage comparability guardrail. It is not a psychoacoustic threshold or mix-quality threshold.

Use this mode only when explicit same-range anchoring is unavailable or unnecessary. Do not claim it proves the Before and After came from the same DAW-time coordinates.

## Topology fingerprint

Both paths use a short SHA-256-derived consistency fingerprint over Analyzer identity/binding metadata.

It is not:

- a persistent FL Studio project hash;
- an audio fingerprint;
- proof that every DAW setting is unchanged;
- a replacement for external host readback.

## Session status and idempotence

The corresponding status tool can list recent in-memory sessions or retrieve one by ID.

Completing an already completed verification returns the stored result rather than silently replacing the After measurement.

## Output discipline

If `controlled_comparison=false`, state why before making a strong A/B claim.

Never convert comparability flags, topology fingerprints, coverage thresholds, freshness checks, dropped-block checks, or numeric deltas into automatic processing instructions or artistic conclusions.
