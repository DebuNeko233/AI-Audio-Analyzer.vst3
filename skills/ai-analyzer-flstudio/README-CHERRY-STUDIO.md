# AI Audio Analyzer Cherry Studio Skill

This Skill targets:

- Cherry Studio;
- AI Audio Analyzer VST3 0.8.0;
- AI Audio Analyzer MCP 0.8;
- optional FL Studio control MCP: https://github.com/rosasynthesiz/flstudio-mcp

Its purpose is to help an LLM **call Analyzer MCP correctly, interpret measurements correctly, manage multi-instance mapping, and judge evidence quality**.

It does **not** provide fixed mixing style, LUFS targets, EQ/compression/sidechain recipes, stereo recipes, or mastering chains.

## Current capability layers

```text
V0.3  Signal State / runtime UUID
V0.4  Identify → FL Mixer Track/Slot deterministic mapping
V0.5  Project Status / Mix Overview / Snapshot A-B
V0.6  Spectral Flux / RMS Rise / temporal profile / band-envelope comparison
V0.7  ERB-rebinned spectral + relative-level + temporal masking evidence
V0.8  Mid/Side RMS / Side spectrum / frequency-dependent Side-Mid / negative-cross evidence
```

V0.8 extends the VST3 OSC frame append-only; indexes `0..64` remain unchanged.

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
two-track basic spectrum      audio_compare_tracks()
two-track detailed masking    audio_masking_evidence()
custom-band temporal          audio_temporal_compare()
two-track stereo comparison   audio_stereo_compare()
legacy stereo bands           audio_stereo_bands()
Snapshot management           audio_capture_snapshot() / audio_list_snapshots()
Before/After                  audio_compare_snapshots()
```

MCP 0.8 exposes **22 tools**. Full signatures are in `references/analyzer-mcp.md`.

## V0.8 stereo evidence

Single-track recent profile:

```text
audio_stereo_profile("mixer:4/slot:9", seconds=5)
```

Two-track measurement comparison:

```text
audio_stereo_compare(
  "mixer:4/slot:9",
  "mixer:7/slot:9",
  seconds=5
)
```

Keep these axes separate:

```text
signed L/R correlation
Side/Mid energy ratio
1 - abs(correlation) decorrelation proxy
negative cross-spectrum energy ratio
20-120 Hz low-band correlation / Side-Mid
32-band Mid spectrum
32-band Side spectrum
8-band frequency-dependent correlation / Side-Mid
```

Important limitations:

- low correlation is not the same as anti-correlation;
- large Side energy does not prove phase opposition;
- `decorrelation_proxy = 1 - abs(correlation)` must be read with correlation sign;
- negative-cross evidence is not a mono-cancellation percentage or audible-problem probability;
- no universal width, Side/Mid, correlation, or low-band target is defined by this Skill.

See `references/stereo-evidence.md` before making strong claims from V0.8 stereo measurements.

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
audio_project_masking_scan(
  seconds=5,
  max_pairs=8,
  alignment_tolerance_ms=80
)
```

Current model:

```text
existing 32 Analyzer spectrum features
→ 16 equal ERB-rate regions
→ relative spectral occupancy
→ directional relative-level weighting
→ V0.6 temporal overlap
```

Important limitations:

- ERB is used as a **re-binning scale**, not as a gammatone/cochlear filterbank;
- scores are transparent heuristics, not audible-masking probabilities;
- `dominant_direction` indicates stronger measured evidence, not which track should be changed;
- no universal `masking_evidence_score` threshold is defined.

See `references/masking-evidence.md` before making strong claims from V0.7 scores.

## Signal State

The Analyzer gate closes after roughly 0.4 s below about `-50 dBFS` and reopens above about `-48 dBFS`.

When input is invalid:

- spectrum/stereo fields become `null` / unavailable;
- V0.6 temporal fields have `temporal_valid=false`;
- V0.8 deep stereo fields have `stereo_v08_valid=false`;
- `null` is not zero;
- LUFS-I and session max True Peak may remain available because they are session-level state.

Window results must be interpreted with `active_ratio`.

## Snapshot A/B

```text
audio_capture_snapshot("before", 5)
# external control MCP changes the DAW
audio_capture_snapshot("after", 5)
audio_compare_snapshots("before", "after")
```

Use comparable musical passages, similar windows, and similar active coverage. Snapshot state is Bridge-session scoped.

## Suggested Agent instruction

```text
Use the ai-analyzer-flstudio Skill only as a technical MCP usage and measurement-semantics reference.
Start with audio_project_status and establish deterministic Identify bindings for unbound Analyzer instances.
Before interpreting content, inspect signal_present, analysis_valid, active_ratio, temporal validity, and V0.8 stereo validity where relevant.
Use audio_mix_overview for coarse project state, audio_project_masking_scan for ranked V0.7 masking-evidence candidates, audio_masking_evidence for detailed pairwise ERB-region evidence, and audio_stereo_profile for V0.8 Mid/Side and stereo evidence.
Keep correlation, Side/Mid energy, decorrelation proxy, and negative-cross evidence separate. Treat null as unavailable, not zero.
Treat spectral overlap, temporal overlap, onset candidates, masking evidence, and stereo evidence as measurements/evidence rather than automatic processing instructions.
If the DAW is changed through an external control MCP, read back the actual host state and use Analyzer/Snapshot measurements for verification.
```

## References

```text
references/analyzer-mcp.md       MCP tools and selector rules
references/parameters.md         measurement parameter semantics
references/masking-evidence.md   V0.7 evidence model and limitations
references/stereo-evidence.md    V0.8 Mid/Side and stereo evidence semantics
```
