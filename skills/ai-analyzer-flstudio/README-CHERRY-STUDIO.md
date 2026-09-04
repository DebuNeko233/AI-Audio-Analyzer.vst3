# AI Audio Analyzer Cherry Studio Skill

This Skill targets:

- Cherry Studio;
- AI Audio Analyzer VST3 1.2.0;
- AI Audio Analyzer MCP 1.2;
- optional FL Studio control MCP: https://github.com/rosasynthesiz/flstudio-mcp

Its purpose is to help an LLM **call Analyzer MCP correctly, interpret measurements correctly, manage multi-instance mapping, choose only the analysis work required by the request, use transport-aware song memory instead of chasing realtime frames, judge latency/data quality, and run auditable Before/After verification around externally controlled DAW changes**.

It does **not** provide fixed mixing style, LUFS targets, EQ/compression/sidechain/stereo recipes, key-change rules, harmony-edit rules, or mastering chains.

## Current capability layers

```text
Signal State / runtime UUID
Identify → FL Mixer Track/Slot deterministic mapping
Project Status / Mix Overview / Snapshot A-B
Adaptive Analysis profiles + worker/FIFO performance telemetry
DAW Transport / continuous playback epochs / latency-aware Song Memory
Spectral Flux / RMS Rise / temporal profile / band-envelope comparison
ERB-rebinned spectral + relative-level + temporal masking evidence
Mid/Side RMS / Side spectrum / frequency-dependent Side-Mid / negative-cross evidence
12-bin chroma / tonal-center candidate ranking / single-F0 harmonic-alignment evidence
controlled closed-loop Before/After verification around external DAW changes
```

The current append-only OSC protocol is **1.2**. Existing indexes `0..134` are unchanged; transport/data-quality metadata is appended at `135..149`.

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

For whole-song or latency-sensitive work, immediately inspect:

```text
audio_song_status()
```

When project performance or feature availability matters, inspect:

```text
audio_project_performance()
audio_analysis_status(track)
```

## Recommended tool path

```text
project readiness               audio_project_status()
whole-song readiness / latency  audio_song_status()
whole-pass compact summary      audio_song_overview()
track / DAW-time history         audio_song_timeline()
project performance             audio_project_performance()
one-instance analysis state     audio_analysis_status()
project recent overview         audio_mix_overview()
project masking candidates      audio_project_masking_scan()
stable recent single track      audio_average()
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

MCP 1.2 exposes **32 tools**. Full signatures are in `references/analyzer-mcp.md`.

## Whole-song memory and Agent latency

Do not build an Agent loop that assumes the LLM must read every frame while playback is happening.

The intended model is:

```text
DAW keeps playing
→ Analyzer keeps measuring
→ DAW-time evidence is retained in one-second bins
→ LLM may think/call other tools for seconds
→ LLM later queries the remembered pass
```

Use:

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(
  "mixer:4/slot:9",
  resolution_seconds=5,
  start_seconds=60,
  end_seconds=90
)
```

Important semantics:

- `transport_epoch` is an **instance-local continuous playback pass**;
- playback start, seek, loop jump, or another detected discontinuity starts a new epoch;
- the worker discards queued pre-jump audio and resets pass-dependent Loudness/Temporal/Semantic state;
- equal epoch numbers across separately loaded instances are not guaranteed to be the same permanent project pass;
- `estimated_analysis_lag_ms` is Analyzer FIFO/window latency, not network or LLM latency;
- `data_age_seconds` is wall-clock age of retained evidence and does not make an explicitly requested historical range invalid;
- non-zero `dropped_blocks` means some input audio was not measured;
- `coverage_ratio` describes how much of a requested/coarse range is actually represented;
- transport coordinates are estimates for song/section reasoning, not sample-accurate edits;
- automatic Verse/Chorus/Bridge labeling is not implemented yet.

Choose the coarsest useful timeline resolution. Prefer a compact `audio_song_overview()` or 10–30 second bins for macro song reasoning; use 1–2 second bins only when the question genuinely needs that detail.

See `references/song-memory.md`.

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
Transport / Identify / signal / core     Eco
LUFS / True Peak                         Balanced
Spectrum / basic masking / stereo        Balanced
Temporal evidence                        Mix
Masking with temporal interaction        Mix
Tonal / chroma / harmonic evidence       Full
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

Runtime telemetry:

```text
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
```

`worker_load_ratio` is background Analyzer-worker busy time, **not DAW realtime audio-thread CPU usage**.

See `references/performance-evidence.md`.

## Closed-loop verification

Use the verification session when a user asks the agent to **change the DAW and verify the measured result**.

Canonical flow:

```text
audio_project_status()
→ deterministic Identify binding if needed
→ ensure the target Analysis Profile exposes the required evidence
→ play the intended comparison passage
→ audio_begin_verification(...)
→ inspect ready_for_external_change / baseline_blockers
→ external FL Studio control MCP makes the intended change
→ external FL Studio control MCP reads back the actual host value/state
→ replay the same intended passage
→ audio_complete_verification(...)
→ inspect controlled_comparison / closed_loop_complete
```

Important semantics:

- Analyzer MCP does not perform the DAW change;
- `host_readback` is supplied from the external control MCP and stored for auditability;
- `controlled_comparison=true` means only that the stated technical A/B guardrails passed;
- `closed_loop_complete=true` additionally requires caller-supplied actual host readback;
- neither Boolean means the change is better, correct, or worth keeping;
- current verification is still recent-window based, not yet transport-anchored to an exact DAW-time range;
- verification state is Bridge-session memory only.

See `references/verification-evidence.md`.

## Evidence layers

Tonal:

```text
audio_tonal_profile()
audio_tonal_compare()
```

Keep chroma, tonal-center ranking, entropy, coverage and single-F0 evidence separate. Exact DAW/MIDI note/key/chord metadata should be preferred for exact symbolic facts.

Stereo:

```text
audio_stereo_profile()
audio_stereo_compare()
```

Keep signed L/R correlation, Side/Mid energy, decorrelation proxy, negative-cross evidence and frequency-dependent relation separate.

Masking:

```text
audio_masking_evidence()
audio_project_masking_scan()
```

ERB is feature re-binning, not a gammatone/cochlear filterbank. Scores are heuristic evidence, not audible-masking probabilities or processing instructions.

Temporal:

```text
audio_temporal_profile()
audio_temporal_compare()
```

Spectral Flux and RMS Rise are change evidence, not annotated onset ground truth.

## Signal, feature and timeline validity

When relevant, inspect:

```text
signal_present
analysis_valid
active_ratio
analysis_features
temporal_supported / temporal_valid
stereo_v08_supported / stereo_v08_valid
semantic_v09_supported / semantic_v09_valid
transport_v12_supported
transport_epoch
estimated_analysis_lag_ms
dropped_blocks
data_quality.coverage_ratio
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

Snapshot tools do not independently reset Loudness. For protocol-1.2 instances, LUFS-I and pass-max True Peak accumulate inside the current transport epoch; a playback start/seek/loop discontinuity creates a new epoch and loudness state. Legacy instances retain historical reset/prepare scope.

When the agent coordinates a real DAW change through an external control MCP, prefer verification because it records technical comparability and host readback context.

## Suggested Agent instruction

```text
Use the ai-analyzer-flstudio Skill only as a technical MCP usage and measurement-semantics reference.
Start with audio_project_status and establish deterministic Identify bindings for unbound Analyzer instances.
For whole-song, past-passage, or latency-sensitive work, call audio_song_status and prefer audio_song_overview/audio_song_timeline over chasing the latest frame. The Analyzer observes continuously while the LLM may reason later.
Treat transport_epoch as an instance-local continuous playback pass. Inspect DAW-time spans, data age, estimated Analyzer lag, dropped blocks, and coverage before making timeline-wide claims.
Use the minimum Analysis Profile that exposes the required evidence. Analyzer MCP does not write DAW parameters; real writes and host readback belong to the actual FL Studio control MCP.
Treat null as unavailable, not zero. Prefer exact DAW/MIDI/project metadata for exact symbolic facts.
When the task changes the DAW and asks for verification, call audio_begin_verification before the external write, read actual host state back, replay a comparable passage, and then call audio_complete_verification.
Treat controlled_comparison only as a technical comparability guardrail and closed_loop_complete only as comparability plus supplied host readback. Neither is an artistic quality judgment.
Never turn Analyzer measurements, transport memory, or performance profiles into automatic mixing, mastering, key-change, harmony-edit, tuning, or processing instructions.
```

## References

```text
references/analyzer-mcp.md          MCP tools and selector rules
references/parameters.md            measurement parameter semantics
references/performance-evidence.md  adaptive profiles and performance telemetry
references/song-memory.md           transport timeline, pass and latency semantics
references/masking-evidence.md      masking evidence and limitations
references/stereo-evidence.md       Mid/Side/stereo evidence semantics
references/tonal-evidence.md        chroma/tonal/harmonic evidence semantics
references/verification-evidence.md closed-loop verification semantics
```
