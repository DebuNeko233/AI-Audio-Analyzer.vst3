---
name: ai-analyzer-flstudio
description: Technical usage skill for Cherry Studio and AI Audio Analyzer MCP. Use it to discover and bind Analyzer instances, choose the correct MCP tools, interpret signal validity, time windows, spectrum, loudness, True Peak, RMS, Crest, spectral descriptors, stereo metrics, V0.6 temporal descriptors, project overview, and A/B snapshots. This Skill does not prescribe a mixing style, LUFS target, EQ/compression/sidechain recipe, or artistic preference.
---

# AI Audio Analyzer MCP Usage Skill

This Skill has two responsibilities:

1. help the model call **AI Audio Analyzer MCP correctly**;
2. help the model interpret the **technical meaning and validity** of MCP measurements correctly.

This Skill does **not** provide style-specific mixing instructions. Do not turn a frequency, loudness, correlation, spectral-overlap, or temporal-overlap measurement directly into an EQ, compression, limiting, sidechain, panning, or mastering action. Artistic decisions should come from the user's goal, musical context, references, and the model's general knowledge—not from a fixed policy embedded in this Skill.

## 1. Check MCP and project readiness first

For project-level tasks, start with:

```text
audio_project_status()
```

Use it to check Bridge/OSC health, Analyzer count, binding completeness, active signal, stale streams, duplicate names, and Master candidates.

Only drill down when needed:

```text
audio_bridge_status()
audio_list_tracks()
audio_instance_map()
```

Do not call every low-level tool unconditionally. Prefer the highest-level tool that already contains enough information for the current question.

## 2. Multiple instances: establish deterministic mapping, never guess

AI Audio Analyzer V0.4+ gives each live instance a runtime UUID and exposes this host parameter:

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

When `audio_instance_map()` reports unbound instances and the FL Studio control MCP can access plugin parameters, process one Analyzer at a time:

1. use the FL Studio MCP to locate the real Mixer Track and Plugin Slot;
2. read the current `Identify` value;
3. set it to the opposite value;
4. immediately call `audio_last_identify()`;
5. confirm the event is fresh and unconsumed;
6. immediately call `audio_bind_last_identified(fl_track_index, fl_track_name, slot)`;
7. verify the result with `audio_instance_map()`.

Each Identify event may be consumed only once. Never reuse an old Identify event for another track.

After binding, prefer selectors in this order:

```text
mixer:<index>/slot:<slot>
→ unique FL Mixer Track name
→ runtime UUID
→ unique Analyzer display name
```

If one Mixer Track contains multiple Analyzer instances, include the `slot`. Runtime UUIDs and bindings are session-scoped.

## 3. Validate measurements before interpreting them

Before content-related analysis, check:

```text
signal_present
analysis_valid
active_ratio
```

Current signal-detector semantics:

```text
close threshold   about -50 dBFS
reopen threshold  about -48 dBFS
hold              about 0.4 s
```

When `signal_present=false`, the Bridge marks content-dependent spectrum/stereo fields as `null` or unavailable. `null` means **no valid measurement**, not numeric zero.

For V0.6 temporal analysis, also check:

```text
temporal_supported
temporal_valid
temporal_window_seconds
```

Older Analyzer versions can still provide legacy measurements, but if `temporal_supported` is false or missing, do not invent V0.6 temporal data.

Always interpret windowed tools together with `active_ratio`. For example, `active_ratio=0.2` over five seconds means only about 20% of sampled frames contained valid input; do not describe that result as continuously present over the full five seconds.

## 4. Tool-selection strategy

### Project readiness

```text
audio_project_status()
```

### Project-level recent-window overview

```text
audio_mix_overview(seconds=10, max_tracks=32)
```

`potential_spectral_conflicts` contains heuristic relative spectral-overlap candidates. It does not prove audible masking.

### Stable single-instance window

```text
audio_average(track, seconds)
```

Use this when the question concerns a stable recent interval rather than one instantaneous frame.

### Latest single-instance frame

```text
audio_snapshot(track)
```

Use for current-state inspection, connection troubleshooting, or explicitly instantaneous measurements.

### Single-instance temporal behavior

```text
audio_temporal_profile(track, seconds=5)
```

Use it to read:

```text
spectral_flux_mean / spectral_flux_peak
rms_rise_peak_db
40-160 Hz temporal energy
onset/change candidate density
```

Candidate events are threshold-based summaries. They are not ground-truth onset labels.

### Two-instance spectral relationship

```text
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
```

The current masking tool remains a heuristic spectral-overlap detector.

### Two-instance temporal relationship

```text
audio_temporal_compare(
  track_a,
  track_b,
  seconds=5,
  low_hz=40,
  high_hz=160,
  alignment_tolerance_ms=80
)
```

Use it to inspect the selected band's:

```text
coactive_ratio
band_envelope_correlation
normalized_band_temporal_overlap
candidate_coincidence_ratio
```

When the question is whether two tracks occupy a frequency region **at the same time**, use this tool in addition to static `spectral_overlap_score`.

### Band-limited stereo correlation

```text
audio_stereo_bands(track)
```

### Master/bus technical summary

```text
audio_master_status(track="Master")
```

This is a measurement summary, not a fixed mastering standard.

## 5. V0.5 Project Snapshot / A-B

To capture two project states:

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

Use `audio_list_snapshots()` to list snapshots stored in the current Bridge session.

For meaningful A/B comparison:

- use the same musical passage when practical;
- use similar window lengths;
- compare `active_ratio`;
- interpret delta as `After - Before`;
- remember that `LUFS-I` is session-integrated, not independently reset for each short snapshot.

## 6. Combining V0.6 temporal evidence with spectral evidence

Static spectral measurements answer:

```text
Do both tracks contain substantial energy in similar frequency regions?
```

V0.6 temporal tools add:

```text
Does that energy appear or change at the same time?
```

Therefore:

```text
high spectral_overlap_score
+
high normalized_band_temporal_overlap
```

means that both spectral and temporal coexistence evidence are relatively strong. It still does not prescribe any processing action.

Likewise:

```text
high band_envelope_correlation
```

means the selected-band envelopes tend to vary in the same direction. It does not identify which track should be changed.

When interpreting `audio_temporal_compare()`, report alignment context as needed:

```text
window_seconds
band_hz
aligned_pairs
usable_band_pairs
alignment_tolerance_ms
mean_abs_alignment_offset_ms
```

If there are too few aligned samples or alignment quality is weak, reduce confidence in correlation/overlap interpretation.

## 7. Parameter interpretation rules

Detailed semantics are in:

```text
references/parameters.md
```

Tool and selector details are in:

```text
references/analyzer-mcp.md
```

Keep these distinctions explicit:

- Sample Peak is not True Peak;
- RMS is not LUFS;
- LUFS-S is not session-integrated LUFS-I;
- Spectrum dB values are machine features, not calibrated SPL;
- Centroid, Rolloff, and Flatness are descriptive statistics, not quality scores;
- Stereo Correlation and Width are measurements, not universal good/bad scores;
- Spectral Flux describes normalized spectral change, not overall level change;
- RMS Rise describes rapid level increase, not Crest Factor;
- temporal overlap/correlation is evidence about timing relationships, not a masking probability;
- `null` means unavailable, not zero;
- windowed statistics must be interpreted with coverage duration, active ratio, and valid-frame count.

## 8. Boundary with the FL Studio control MCP

AI Audio Analyzer MCP is responsible for:

```text
measure / read / compare / verify
```

The FL Studio control MCP is responsible for:

```text
read DAW topology / access plugins / modify host state
```

This Skill may instruct the model to use the FL Studio MCP for deterministic Identify mapping and to read Analyzer measurements after a DAW change, but it must **not** prescribe which parameter to change, by how much, or which mixing style to follow.

If the user asks for project changes, first inspect real tracks, slots, plugins, and parameters. Do not invent host/plugin parameters. Read back the actual host state after changes. Use Analyzer/Snapshot A-B when measurement verification is useful. Keep technical measurement claims separate from artistic judgments.

## 9. Output discipline

When citing Analyzer measurements, include enough context to make the result interpretable, such as:

```text
instance / selector
window length
signal_present / active_ratio
for temporal results: band_hz / temporal coverage / alignment quality
key measurements
measurement validity
```

Do not present the following as facts measured by AI Audio Analyzer:

- "this sound should be warmer/brighter/more modern";
- "this genre must hit a specific LUFS value";
- "this frequency must be cut by a specific number of dB";
- "spectral overlap means EQ or sidechain is mandatory";
- "a particular correlation or temporal-overlap value is inherently good or bad".

Those are musical judgments or processing strategies, not measurements produced by this MCP and not rules that belong in this Skill.
