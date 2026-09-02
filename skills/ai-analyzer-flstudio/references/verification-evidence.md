# V1.0 Closed-loop Verification Evidence

This reference explains the V1.0 verification-session semantics used to measure a DAW change made through an external control MCP.

It does **not** decide what change should be made and does not label an artistic result better or worse.

## Canonical flow

```text
audio_project_status()
→ establish deterministic Analyzer bindings if needed
→ play the intended comparison passage
→ audio_begin_verification(...)
→ external DAW-control MCP performs the intended change
→ external DAW-control MCP reads back the actual host state
→ play the same intended comparison passage
→ audio_complete_verification(..., host_readback="...")
→ use specialized temporal/masking/stereo/tonal tools only if deeper evidence is needed
```

AI Audio Analyzer never performs the DAW change in this flow. It owns the measurement baseline, the After measurement, and the comparability evidence.

## `verification_id`

A Bridge-session identifier for one verification experiment.

It is not:

- a permanent project identifier;
- a DAW undo identifier;
- a plugin-instance UUID;
- a persistent database key.

Verification sessions disappear when the Analyzer MCP Bridge exits.

## `ready_for_external_change`

Returned by `audio_begin_verification()`.

`true` means the baseline passed the current pre-change checks, including usable Analyzer state, deterministic project readiness, requested target presence, and valid active measurements for the selected targets.

It does not mean the proposed DAW change is appropriate.

If false, inspect `baseline_blockers` and establish a clean baseline before changing the DAW.

## `baseline_blockers`

Human-readable reasons why the current Before measurement should not be treated as a clean controlled baseline.

Examples include:

- no Analyzer tracks captured;
- incomplete/stale Analyzer mapping;
- requested selectors missing;
- requested targets without valid active analysis.

These are measurement-workflow blockers, not artistic problems.

## Target selectors

When `target_selectors` are supplied, V1.0 evaluates comparability specifically for those Analyzer identities.

Preferred deterministic form:

```text
mixer:<track_index>/slot:<slot>
```

If targets are omitted, the comparison can include the shared Analyzer identities captured in both states.

## Topology fingerprint

Each Before/After state receives a short SHA-256-derived fingerprint over sorted Analyzer identity/binding metadata, including runtime/binding context.

It is a **consistency marker for this live measurement session**.

It is not:

- a persistent FL Studio project hash;
- an audio-content fingerprint;
- a cryptographic guarantee that every DAW setting is unchanged;
- a replacement for external host-state readback.

If topology changes intentionally, the returned measurement deltas can still be inspected, but V1.0 does not call the result a controlled comparison.

## `controlled_comparison`

This Boolean is intentionally strict.

It becomes true only when the current implementation can establish all of the following:

```text
at least one requested/shared target was compared
same Before/After measurement-window duration
Analyzer topology unchanged
no requested target missing
valid active analysis for all compared requested targets
active-ratio difference within tolerance for all compared requested targets
```

Current active-ratio tolerance:

```text
0.15 absolute difference
```

Example:

```text
Before active_ratio = 0.92
After  active_ratio = 0.86
absolute difference = 0.06 → within tolerance
```

The 0.15 value is a transparent passage-coverage guardrail. It is not a psychoacoustic threshold or mix-quality threshold.

Most importantly:

```text
controlled_comparison = true
```

means only:

> the current A/B measurement conditions satisfy the stated technical guardrails.

It does **not** mean:

- After is better;
- the user should keep the change;
- a processor setting is correct;
- the mix is more professional;
- a tonal/stereo/masking condition improved perceptually.

## Comparability fields

### `same_window_seconds`

Whether the requested Before and After measurement-window durations are equal.

`audio_complete_verification()` uses the baseline duration by default when its `seconds` argument is `0` or negative.

### `topology_unchanged`

Whether the Before/After topology fingerprint and captured Analyzer identity set remained unchanged.

### `missing_targets`

Requested targets absent from either Before or After.

### `invalid_targets`

Requested targets that lack valid active analysis in Before or After.

### `coverage_mismatch_targets`

Requested targets whose absolute Before/After `active_ratio` difference exceeds the current `0.15` tolerance, or whose active coverage cannot be compared.

### `warnings`

Human-readable explanations for failed comparability guards. Treat them as audit context, not processing instructions.

## Delta convention

V1.0 basic verification deltas use:

```text
Delta = After - Before
```

The result currently includes basic project-state deltas such as:

```text
peak_db
rms_db
crest_db
lufs_s
lufs_i
true_peak_dbtp
centroid_hz
rolloff_hz
flatness
stereo_correlation
stereo_width
broad spectral-region dB features
```

A positive delta only means the After measurement is numerically higher on that axis. It does not mean better.

For deeper evidence, call the dedicated temporal, masking, V0.8 stereo, or V0.9 tonal tools after the verification session when the user's question actually requires them.

## `change_summary`

Caller-supplied description of the DAW change that was attempted.

It is audit metadata. Analyzer MCP does not independently prove that the described change occurred.

Keep it factual, for example describing the real parameter/control that the external control MCP changed.

## `host_readback`

Caller-supplied report of the **actual host state read back after the DAW change**.

This should come from the external DAW-control MCP after writing the change, not from the original plan or intended value.

Analyzer MCP stores this text beside the measurement result for auditability, but it does not independently validate the text against FL Studio.

Therefore:

```text
readback_supplied = true
```

means readback evidence was supplied by the caller. It does not mean Analyzer itself queried or verified the DAW control state.

## Why host readback and Analyzer measurement are separate

They answer different questions:

```text
external DAW-control MCP readback
→ what state did the host actually report after the write?

AI Audio Analyzer verification
→ what changed in measured audio, and were Before/After conditions technically comparable?
```

A reliable closed loop needs both when the user asks to modify and verify a project.

## Session status

`audio_verification_status()` can:

- list recent in-memory verification sessions;
- retrieve one session by `verification_id`;
- recover a completed result during the same Bridge session.

A completed verification is idempotent: calling `audio_complete_verification()` again for the same completed ID returns the stored result instead of silently replacing the After measurement.

## Output discipline

When reporting a V1.0 verification result, include the relevant audit context:

```text
verification_id
selected targets
Before/After window duration
controlled_comparison
topology_unchanged
active-ratio comparability
missing/invalid targets if any
external host readback status
measurement deltas used in the conclusion
```

If `controlled_comparison=false`, say why before making a strong A/B claim.

Never convert `controlled_comparison`, topology fingerprints, coverage tolerance, or a numeric delta into an automatic artistic recommendation.
