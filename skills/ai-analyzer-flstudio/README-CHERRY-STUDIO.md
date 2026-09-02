# AI Audio Analyzer Cherry Studio Skill

This Skill targets:

- Cherry Studio;
- AI Audio Analyzer VST3 1.1.0;
- AI Audio Analyzer MCP 1.1;
- optional FL Studio control MCP: https://github.com/rosasynthesiz/flstudio-mcp

Its purpose is to help an LLM **call Analyzer MCP correctly, interpret measurements correctly, manage multi-instance mapping, choose only the analysis work required by the request, judge evidence quality, and run auditable Before/After verification around externally controlled DAW changes**.

It does **not** provide fixed mixing style, LUFS targets, EQ/compression/sidechain/stereo recipes, key-change rules, harmony-edit rules, or mastering chains.

## Current capability layers

```text
Signal State / runtime UUID
Identify → FL Mixer Track/Slot deterministic mapping
Project Status / Mix Overview / Snapshot A-B
Spectral Flux / RMS Rise / temporal profile / band-envelope comparison
ERB-rebinned spectral + relative-level + temporal masking evidence
Mid/Side RMS / Side spectrum / frequency-dependent Side-Mid / negative-cross evidence
12-bin chroma / tonal-center candidate ranking / single-F0 harmonic-alignment evidence
controlled closed-loop Before/After verification around external DAW changes
Adaptive Analysis profiles + worker/FIFO performance telemetry
```

The current append-only OSC protocol is **1.1**. Existing indexes `0..127` are unchanged; adaptive runtime metadata is appended at `128..134`.

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

When project performance or feature availability matters, inspect:

```text
audio_project_performance()
audio_analysis_status(track)
```

## Recommended tool path

```text
project readiness               audio_project_status()
project performance             audio_project_performance()
one-instance analysis state     audio_analysis_status()
project recent overview         audio_mix_overview()
project masking candidates      audio_project_masking_scan()
stable single track             audio_average()
current single frame            audio_snapshot()
single-track temporal           audio_temporal_profile()
deep single-track stereo        audio_stereo_profile()
single-track tonal evidence     audio_tonal_profile()
two-track basic spectrum        audio_compare_tracks()
two-track detailed masking      audio_masking_evidence()
custom-band temporal            audio_temporal_compare()
two-track stereo comparison     audio_stereo_compare()
two-track tonal comparison      audio_tonal_compare()
legacy stereo bands             audio_stereo_bands()
Snapshot management             audio_capture_snapshot() / audio_list_snapshots()
manual Snapshot A/B             audio_compare_snapshots()
controlled change verification  audio_begin_verification() / audio_complete_verification()
verification recovery/status    audio_verification_status()
```

MCP 1.1 exposes **29 tools**. Full signatures are in `references/analyzer-mcp.md`.

## Adaptive Analysis and performance control

The VST3 exposes a real host parameter:

```text
Parameter ID: analysis_profile
Display name: Analysis Profile

0 Eco
1 Balanced
2 Mix
3 Full
```

Profiles control Analyzer computation only; they do not alter the audio signal or define an artistic mode.

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

`Full` remains the default for backward compatibility.

Minimum profiles for common evidence families:

```text
Identify / signal / core state        Eco
LUFS / True Peak                      Balanced
Spectrum / basic masking / stereo     Balanced
Temporal evidence                     Mix
Masking with temporal interaction     Mix
Tonal / chroma / harmonic evidence    Full
```

Analyzer MCP does **not** change `Analysis Profile`. If a lower/higher profile is needed:

```text
audio_analysis_status(target)
→ remember current profile
→ use the actual FL Studio control MCP to find and change Analysis Profile
→ read back the actual host parameter state
→ audio_analysis_status(target)
→ verify the required feature group is really enabled
→ collect the required measurement window
→ call only the needed Analyzer evidence tool
→ restore the previous profile through the control MCP when appropriate
→ verify the restored status
```

Do not invent FL Studio MCP tool names and do not switch every Analyzer to Full for a single-track question.

Runtime telemetry:

```text
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
```

`worker_load_ratio` is background Analyzer-worker busy time, **not DAW realtime audio-thread CPU usage**. Sustained FIFO growth is evidence that the analysis worker may be falling behind and measurement timing may become stale.

Disabled feature families are unavailable, not numeric zero. The append-only frame still contains compatibility positions, but the feature mask is authoritative and the Bridge invalidates disabled values before downstream interpretation.

See `references/performance-evidence.md`.

## Closed-loop verification

Use the verification session when a user asks the agent to **change the DAW and verify the measured result**.

Canonical flow:

```text
audio_project_status()
→ deterministic Identify binding if needed
→ ensure the target Analysis Profile exposes the required evidence
→ play the intended comparison passage
→ audio_begin_verification(
     "short factual label",
     seconds=5,
     target_selectors=["mixer:4/slot:9"]
   )
→ inspect ready_for_external_change / baseline_blockers
→ external FL Studio control MCP makes the intended artistic/technical change
→ external FL Studio control MCP reads back the actual host value/state
→ replay the same intended passage
→ audio_complete_verification(
     verification_id,
     change_summary="what was actually changed",
     host_readback="actual host state reported after the write"
   )
→ inspect controlled_comparison / closed_loop_complete and comparability fields
→ call specialized temporal/masking/stereo/tonal tools only if deeper evidence is needed
```

Important semantics:

- Analyzer MCP does not perform the DAW change;
- `host_readback` is supplied from the external control MCP and stored for auditability; Analyzer does not independently validate that text;
- After uses the same measurement-window duration as Before by default;
- the topology fingerprint is a live-session consistency marker, not a permanent FL Studio project ID;
- current active-ratio comparability tolerance is `0.15` absolute difference;
- topology drift, missing targets, invalid targets, window mismatch, baseline blockers, or excessive active-coverage mismatch make `controlled_comparison=false`;
- `controlled_comparison=true` means only that the stated technical A/B guardrails passed;
- `closed_loop_complete=true` additionally requires caller-supplied actual host readback;
- neither Boolean means the change is better, correct, or worth keeping;
- verification state is Bridge-session memory only.

See `references/verification-evidence.md`.

## Tonal evidence

Single-track recent profile:

```text
audio_tonal_profile("mixer:4/slot:9", seconds=8)
```

This requires Semantic analysis, therefore the target must currently expose the `semantic` feature group (normally `Full`).

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

See `references/tonal-evidence.md`.

## Stereo evidence

```text
audio_stereo_profile("mixer:4/slot:9", seconds=5)
```

Requires the Stereo feature group (`Balanced` or higher). Keep signed L/R correlation, Side/Mid energy, decorrelation proxy, negative-cross evidence, and frequency-dependent stereo relation separate. None defines a universal stereo target.

See `references/stereo-evidence.md`.

## Masking evidence

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

Spectrum evidence requires `Balanced` or higher. Temporal interaction evidence requires `Mix` or `Full`. ERB is used as a re-binning scale, not a gammatone/cochlear filterbank. Scores are transparent heuristics, not audible-masking probabilities or processing instructions.

See `references/masking-evidence.md`.

## Signal and feature validity

The Analyzer gate closes after roughly 0.4 s below about `-50 dBFS` and reopens above about `-48 dBFS`.

When relevant, inspect:

```text
signal_present
analysis_valid
active_ratio
analysis_features
temporal_supported / temporal_valid
stereo_v08_supported / stereo_v08_valid
semantic_v09_supported / semantic_v09_valid
```

For performance-sensitive workflows also inspect:

```text
analysis_profile
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
```

For tonal evidence also inspect:

```text
mean_chroma_energy_ratio
normalized_pitch_class_entropy
tonal_center_top2_margin
valid_frame_ratio
active_ratio
```

For verification also inspect:

```text
ready_for_external_change
baseline_blockers
controlled_comparison
closed_loop_complete
same_window_seconds
topology_unchanged
missing_targets
invalid_targets
coverage_mismatch_targets
active_ratio_tolerance
```

`null` means unavailable, not zero.

## Snapshot A/B versus verification

Manual Snapshot A/B remains useful for simple measurement comparisons:

```text
audio_capture_snapshot("before", 5)
# some external event/change
audio_capture_snapshot("after", 5)
audio_compare_snapshots("before", "after")
```

Use comparable passages, similar windows, similar active coverage, and the same relevant Analysis Profile/feature availability.

When the agent itself coordinates a DAW change through an external control MCP, prefer verification because it additionally records baseline blockers, target selectors, topology consistency, active-coverage comparability, external change summary, and host readback.

## Suggested Agent instruction

```text
Use the ai-analyzer-flstudio Skill only as a technical MCP usage and measurement-semantics reference.
Start with audio_project_status and establish deterministic Identify bindings for unbound Analyzer instances.
If performance or feature availability matters, inspect audio_project_performance and audio_analysis_status. Analysis Profile is a performance control, not an artistic mode.
Use the minimum profile that exposes the required evidence. If profile escalation is needed, change the real host Analysis Profile through the actual FL Studio control MCP, read it back, verify with audio_analysis_status, collect the measurement, and restore the prior profile when appropriate.
Before interpreting content, inspect signal/feature validity and evidence-quality fields relevant to the selected tool. Treat null as unavailable, not zero.
For exact note/key/chord facts, prefer exact DAW/MIDI/project data when available; use audio-domain tonal evidence only with uncertainty context.
When the task changes the DAW and asks for verification, call audio_begin_verification before the external artistic/technical control write, read the actual host state back, replay a comparable passage, then call audio_complete_verification.
Treat controlled_comparison only as a measurement-comparability guardrail and closed_loop_complete only as comparability plus supplied host readback. Neither is an artistic quality judgment.
Never turn Analyzer measurements or performance profiles into automatic mixing, mastering, key-change, harmony-edit, tuning, or processing instructions.
```

## References

```text
references/analyzer-mcp.md          MCP tools and selector rules
references/parameters.md            measurement parameter semantics
references/performance-evidence.md  adaptive profiles and performance telemetry
references/masking-evidence.md      masking evidence and limitations
references/stereo-evidence.md       Mid/Side/stereo evidence semantics
references/tonal-evidence.md        chroma/tonal/harmonic evidence semantics
references/verification-evidence.md closed-loop verification semantics
```
