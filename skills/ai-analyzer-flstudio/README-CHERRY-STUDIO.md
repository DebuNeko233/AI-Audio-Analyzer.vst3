# AI Audio Analyzer Cherry Studio Skill

This Skill targets:

- Cherry Studio;
- AI Audio Analyzer VST3 1.0.0;
- AI Audio Analyzer MCP 1.0;
- optional FL Studio control MCP: https://github.com/rosasynthesiz/flstudio-mcp

Its purpose is to help an LLM **call Analyzer MCP correctly, interpret measurements correctly, manage multi-instance mapping, judge evidence quality, and run auditable Before/After verification around externally controlled DAW changes**.

It does **not** provide fixed mixing style, LUFS targets, EQ/compression/sidechain/stereo recipes, key-change rules, harmony-edit rules, or mastering chains.

## Current capability layers

```text
V0.3  Signal State / runtime UUID
V0.4  Identify → FL Mixer Track/Slot deterministic mapping
V0.5  Project Status / Mix Overview / Snapshot A-B
V0.6  Spectral Flux / RMS Rise / temporal profile / band-envelope comparison
V0.7  ERB-rebinned spectral + relative-level + temporal masking evidence
V0.8  Mid/Side RMS / Side spectrum / frequency-dependent Side-Mid / negative-cross evidence
V0.9  12-bin chroma / tonal-center candidate ranking / single-F0 harmonic-alignment evidence
V1.0  controlled closed-loop Before/After verification around external DAW changes
```

V1.0 adds no new VST3 OSC fields. The current OSC protocol remains **0.9**, with append-only indexes `0..127`.

## Recommended initialization

Start with:

```text
audio_project_status()
```

If Analyzer instances are unbound:

```text
FL Studio control MCP finds real Mixer Track / Slot
→ read target Analyzer Identify value
→ toggle Identify
→ audio_last_identify()
→ audio_bind_last_identified(...)
→ audio_instance_map()
```

After binding, prefer:

```text
mixer:<index>/slot:<slot>
```

## Recommended tool path

```text
project readiness             audio_project_status()
project recent overview       audio_mix_overview()
project masking candidates    audio_project_masking_scan()
stable single track           audio_average()
current single frame          audio_snapshot()
single-track temporal         audio_temporal_profile()
deep single-track stereo      audio_stereo_profile()
single-track tonal evidence   audio_tonal_profile()
two-track basic spectrum      audio_compare_tracks()
two-track detailed masking    audio_masking_evidence()
custom-band temporal          audio_temporal_compare()
two-track stereo comparison   audio_stereo_compare()
two-track tonal comparison    audio_tonal_compare()
legacy stereo bands           audio_stereo_bands()
Snapshot management           audio_capture_snapshot() / audio_list_snapshots()
manual Snapshot A/B           audio_compare_snapshots()
controlled change verification audio_begin_verification() / audio_complete_verification()
verification recovery/status  audio_verification_status()
```

MCP 1.0 exposes **27 tools**. Full signatures are in `references/analyzer-mcp.md`.

## V1.0 closed-loop verification

Use the verification session when a user asks the agent to **change the DAW and verify the measured result**.

Canonical flow:

```text
audio_project_status()
→ deterministic Identify binding if needed
→ play the intended comparison passage
→ audio_begin_verification(
     "short factual label",
     seconds=5,
     target_selectors=["mixer:4/slot:9"]
   )
→ inspect ready_for_external_change / baseline_blockers
→ external FL Studio control MCP makes the intended change
→ external FL Studio control MCP reads back the actual host value/state
→ replay the same intended passage
→ audio_complete_verification(
     verification_id,
     change_summary="what was actually changed",
     host_readback="actual host state reported after the write"
   )
→ inspect controlled_comparison and its comparability fields
→ call specialized temporal/masking/stereo/tonal tools only if deeper evidence is needed
```

Important semantics:

- Analyzer MCP does not perform the DAW change;
- `host_readback` is supplied from the external control MCP and stored for auditability; Analyzer does not independently validate that text;
- After uses the same measurement-window duration as Before by default;
- the topology fingerprint is a live-session consistency marker, not a permanent FL Studio project ID;
- current active-ratio comparability tolerance is `0.15` absolute difference;
- topology drift, missing targets, invalid targets, window mismatch, or excessive active-coverage mismatch make `controlled_comparison=false`;
- `controlled_comparison=true` means only that the stated technical A/B guardrails passed; it does **not** mean the change is better, correct, or worth keeping;
- verification state is Bridge-session memory only.

See `references/verification-evidence.md` before making strong Before/After claims from V1.0 verification.

## V0.9 tonal evidence

Single-track recent profile:

```text
audio_tonal_profile("mixer:4/slot:9", seconds=8)
```

Two-track pitch-class distribution comparison:

```text
audio_tonal_compare(
  "mixer:4/slot:9",
  "mixer:7/slot:9",
  seconds=8
)
```

Read these as separate evidence axes:

```text
12-bin normalized chroma (C..B)
chroma analysis energy coverage
pitch-class entropy
24 major/minor profile correlations
top-2 tonal-center separation
single-F0 harmonic-alignment ratio
single-F0 candidate frequency stability
```

Important limitations:

- chroma is normalized audio-domain pitch-class power, not note probability or MIDI transcription;
- tonal-center candidates are template correlations, not ground-truth key labels;
- `top2_margin` is candidate separation, not calibrated confidence probability;
- pitch-class entropy is distribution concentration, not musical quality;
- chroma energy coverage is not correctness probability;
- single-F0 harmonic evidence is not harmonic/percussive source separation or a probability of harmonic content;
- `harmonic_f0_candidate_hz` can octave/subharmonic-jump and is not a detected note;
- exact DAW/MIDI note/key/chord metadata should be preferred when the request asks for exact symbolic facts.

See `references/tonal-evidence.md` before making strong claims from V0.9 semantic evidence.

## V0.8 stereo evidence

Single-track recent profile:

```text
audio_stereo_profile("mixer:4/slot:9", seconds=5)
```

Keep signed L/R correlation, Side/Mid energy, decorrelation proxy, negative-cross evidence, and frequency-dependent stereo relation separate. None defines a universal stereo target.

See `references/stereo-evidence.md`.

## V0.7 masking evidence

Detailed pair query:

```text
audio_masking_evidence(
  "mixer:4/slot:9",
  "mixer:7/slot:9",
  seconds=5,
  alignment_tolerance_ms=80,
  max_regions=8
)
```

Project-level scan:

```text
audio_project_masking_scan(seconds=5, max_pairs=8, alignment_tolerance_ms=80)
```

ERB is used as a re-binning scale, not a gammatone/cochlear filterbank. Scores are transparent heuristics, not audible-masking probabilities or processing instructions.

See `references/masking-evidence.md`.

## Signal and feature validity

The Analyzer gate closes after roughly 0.4 s below about `-50 dBFS` and reopens above about `-48 dBFS`.

When relevant, inspect:

```text
signal_present
analysis_valid
active_ratio
temporal_supported / temporal_valid
stereo_v08_supported / stereo_v08_valid
semantic_v09_supported / semantic_v09_valid
```

For V0.9 also inspect evidence quality:

```text
mean_chroma_energy_ratio
normalized_pitch_class_entropy
tonal_center_top2_margin
valid_frame_ratio
active_ratio
```

For V1.0 verification also inspect:

```text
ready_for_external_change
baseline_blockers
controlled_comparison
same_window_seconds
topology_unchanged
missing_targets
invalid_targets
coverage_mismatch_targets
active_ratio_tolerance
```

`null` means unavailable, not zero.

## Snapshot A/B versus V1.0 verification

Manual Snapshot A/B remains useful for simple measurement comparisons:

```text
audio_capture_snapshot("before", 5)
# some external event/change
audio_capture_snapshot("after", 5)
audio_compare_snapshots("before", "after")
```

Use comparable passages, similar windows, and similar active coverage. Snapshot state is Bridge-session scoped.

When the agent itself is coordinating a DAW change through an external control MCP, prefer V1.0 verification because it additionally records baseline blockers, target selectors, topology consistency, active-coverage comparability, external change summary, and host readback.

## Suggested Agent instruction

```text
Use the ai-analyzer-flstudio Skill only as a technical MCP usage and measurement-semantics reference.
Start with audio_project_status and establish deterministic Identify bindings for unbound Analyzer instances.
Before interpreting content, inspect signal/feature validity and evidence-quality fields relevant to the selected tool.
Use only the measurement family needed for the request: temporal, masking, stereo, or V0.9 tonal evidence.
For exact note/key/chord facts, prefer exact DAW/MIDI/project data when available; use V0.9 as audio-domain inference evidence and report its uncertainty context.
When the task changes the DAW and asks for verification, call audio_begin_verification before the external control write, make the change through the actual FL Studio control MCP, read the host state back, replay a comparable passage, then call audio_complete_verification with the factual change summary and host readback.
Treat controlled_comparison only as a measurement-comparability guardrail. If it is false, report the reason before making a strong A/B claim.
Keep correlation, Side/Mid energy, negative-cross evidence, chroma, tonal-center ranking, harmonic-alignment evidence, and verification comparability conceptually separate. Treat null as unavailable, not zero.
Never turn Analyzer measurements into automatic mixing, mastering, key-change, harmony-edit, tuning, or processing instructions.
```

## References

```text
references/analyzer-mcp.md          MCP tools and selector rules
references/parameters.md            measurement parameter semantics
references/masking-evidence.md      V0.7 masking evidence and limitations
references/stereo-evidence.md       V0.8 Mid/Side/stereo evidence semantics
references/tonal-evidence.md        V0.9 chroma/tonal/harmonic evidence semantics
references/verification-evidence.md V1.0 closed-loop verification semantics
```
