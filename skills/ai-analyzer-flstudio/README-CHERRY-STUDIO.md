# AI Audio Analyzer Cherry Studio Skill

This Skill is intended for:

- Cherry Studio;
- AI Audio Analyzer.vst3 0.6+;
- AI Audio Analyzer MCP 0.6;
- optional FL Studio control MCP: https://github.com/rosasynthesiz/flstudio-mcp

Its purpose is to help the model **call Analyzer MCP correctly, interpret returned measurements, handle multi-instance mapping, and respect data validity**. It does not provide fixed mixing styles, LUFS targets, EQ/compression/sidechain recipes, or artistic presets.

## Current capabilities

```text
V0.3  Signal State / runtime UUID
V0.4  Identify → deterministic FL Mixer Track/Slot mapping
V0.5  Project Status / Mix Overview / Snapshot A-B
V0.6  Spectral Flux / RMS Rise / temporal profile / band-envelope comparison
```

## Recommended initialization flow

Start with:

```text
audio_project_status()
```

If Analyzer instances are unbound:

```text
Use FL Studio MCP to locate the real Mixer Track / Slot
→ read the target Analyzer's current Identify value
→ toggle Identify
→ audio_last_identify()
→ audio_bind_last_identified(...)
→ audio_instance_map()
```

After binding, prefer:

```text
mixer:<index>/slot:<slot>
```

## Tool selection

```text
Project readiness         audio_project_status()
Project recent window     audio_mix_overview()
Stable single track       audio_average()
Latest single frame       audio_snapshot()
Single-track timing       audio_temporal_profile()
Two-track spectrum        audio_compare_tracks()
Two-track timing          audio_temporal_compare()
Band stereo               audio_stereo_bands()
Snapshot management       audio_capture_snapshot() / audio_list_snapshots()
Before/After              audio_compare_snapshots()
```

MCP 0.6 currently exposes 18 tools. See `references/analyzer-mcp.md` for the complete list.

## V0.6 temporal analysis

VST3 0.6 appends these fields to the existing OSC frame:

```text
temporal_window_seconds
spectral_flux_mean
spectral_flux_peak
rms_rise_peak_db
low_band_energy_db   # FFT-derived 40-160 Hz energy
frame_schema_version
```

Single track:

```text
audio_temporal_profile("mixer:7/slot:9", 5)
```

Two tracks:

```text
audio_temporal_compare(
  "mixer:4/slot:9",
  "mixer:7/slot:9",
  5,
  40,
  160,
  80
)
```

`band_envelope_correlation` describes how similarly the selected-band envelopes vary. `normalized_band_temporal_overlap` describes how often both tracks are simultaneously strong relative to their own selected-band peaks. Both are measurement evidence, not automatic processing instructions.

`onset_candidate_*` fields use explicit thresholds returned by the MCP. They are compressed change-event heuristics, not ground-truth onset labels.

## Signal State

The Analyzer closes its signal gate after input remains below roughly `-50 dBFS` for about 0.4 seconds, and reopens above roughly `-48 dBFS`.

Without valid input:

- spectrum/stereo content fields become `null` or unavailable;
- V0.6 temporal fields report `temporal_valid=false`;
- `null` does not mean zero;
- LUFS-I and session maximum True Peak may remain available as session-level values.

Always interpret windowed results together with `active_ratio`.

## Snapshot A/B

```text
audio_capture_snapshot("before", 5)
# external control MCP changes the project
audio_capture_snapshot("after", 5)
audio_compare_snapshots("before", "after")
```

Use the same musical passage, similar window lengths, and comparable `active_ratio` when practical. Snapshots exist only in the current Bridge session.

## Recommended Agent instruction

```text
Use the ai-analyzer-flstudio Skill only as technical guidance for AI Audio Analyzer MCP usage and measurement semantics.
Start with audio_project_status to check project readiness. Use Identify to establish deterministic FL Mixer Track/Slot bindings for unbound instances.
Before content analysis, check signal_present, analysis_valid, and active_ratio. For temporal analysis, also check temporal_supported and temporal_valid.
Use audio_average for stable single-track windows, audio_temporal_profile for single-track temporal behavior, and audio_temporal_compare when determining whether two tracks occupy or vary within a frequency region at the same time.
Do not treat null as zero. Do not convert spectral overlap, temporal overlap, correlation, or onset candidates directly into fixed mixing actions.
If the FL Studio control MCP changes the project, read back the host state and use Analyzer/Snapshot A-B when measurement verification is useful.
```

## References

```text
references/analyzer-mcp.md   MCP tools, calling flow, selectors
references/parameters.md     technical parameter semantics and validity
```
