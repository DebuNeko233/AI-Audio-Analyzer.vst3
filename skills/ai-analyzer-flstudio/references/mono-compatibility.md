# Mono Compatibility Evidence

Use this guide when the task is specifically about mono fold-down, stereo translation, phase-cancellation risk, or deciding where to inspect stereo energy more closely.

P7a adds **direct recent-window mono-fold energy evidence** from measurements the Analyzer already computes. It does not add realtime DSP, new OSC fields, a quality score, or a processing command.

## Measurement identity

The Analyzer Worker defines:

```text
M = 0.5 * (L + R)
S = 0.5 * (L - R)
```

Therefore current `mid_rms_db` is already the RMS of the ordinary equal-weight mono fold `(L+R)/2`.

The stereo-equivalent RMS reference is based on:

```text
P_stereo = (L_power + R_power) / 2
```

and the Mid/Side identity is:

```text
P_stereo = P_mid + P_side
```

This lets the MCP expose direct fold-down energy change without pretending that correlation alone measures mono compatibility.

## Tool

```text
audio_mono_compatibility(track, seconds=5.0)
```

The current P7a scope is a **recent receive-time window** from 0.5 to 60 seconds.

Use it after selecting/binding the target Analyzer when you need direct mono fold-down evidence. Do not call it mechanically for every mixing question.

## Full-band result

The tool returns:

```text
stereo_rms_db
mono_fold_rms_db
mono_fold_rms_delta_db
```

with:

```text
mono_fold_rms_db       = Mid RMS
mono_fold_rms_delta_db = mono-fold RMS energy relative to stereo-equivalent RMS
```

Typical mathematical reference cases:

```text
identical L/R                  -> about 0 dB fold-down RMS delta
left-only or right-only        -> about -3.01 dB
hard equal anti-phase L/R      -> Mid approaches the Analyzer floor / very strong loss
```

These are mathematical reference cases, **not universal pass/fail thresholds**.

## 32-band energy evidence

Current `bands_db` is the Analyzer Mid spectrum and `side_bands_db` is the Side spectrum. At each Analyzer logarithmic band center, P7a derives:

```text
mid_power
side_power
stereo_equivalent_power = mid_power + side_power
mono_fold_band_power     = mid_power
mono_fold_delta_db       = 10*log10(mid_power / stereo_equivalent_power)
```

The returned fields include:

```text
center_hz
mid_db
side_db
stereo_equivalent_energy_db
mono_fold_delta_db
energy_loss_fraction
relative_band_energy
inspection_priority
```

These are **band-center sampled energy descriptors**. They are not a perfect integrated-band transfer function and must not be described as one.

If both Mid and Side energy are below the Analyzer measurement floor at a band center, that band is unavailable rather than being converted into an artificial extreme cancellation result.

## Energy-aware inspection priority

A large raw loss in a nearly silent region should not outrank a smaller loss in a dominant region.

P7a therefore keeps these fields separate:

```text
mono_fold_delta_db
relative_band_energy
energy_loss_fraction
inspection_priority
```

Current shortlist heuristic:

```text
inspection_priority = relative_band_energy * energy_loss_fraction
```

`relative_band_energy` is normalized to the strongest sampled stereo-equivalent band in the current result.

`inspection_priority` means only:

```text
where direct fold-down energy evidence may deserve inspection first
```

It is **not**:

```text
audibility probability
phase-problem probability
mix-quality score
mastering score
pass/fail result
processing recommendation
```

## Grouped regions

For quicker high-level inspection, the same sampled band evidence is also grouped into:

```text
20-120 Hz
120-500 Hz
500 Hz-2 kHz
2-5 kHz
5-20 kHz
```

Grouped values are summaries of the same sampled Mid/Side powers. Keep the raw 32-band evidence available when exact frequency context matters.

## Keep independent stereo evidence separate

P7a also exposes existing stereo context where available, but do not collapse these dimensions:

```text
mono-fold RMS delta
bandwise mono-fold energy loss
L/R correlation
frequency-dependent correlation
Side/Mid ratio
low-band correlation
negative-cross energy ratio
```

For example, correlation below zero can be relevant phase-opposition evidence, but it is not itself a universal proof that the fold-down is unacceptable. Direct fold-down energy tells you what energy actually changes; the other descriptors help explain why.

## Historical limitation

Current Song Memory does **not** retain the full recent-window 32-band Mid/Side detail needed to reconstruct this P7a analysis for arbitrary historical DAW ranges or cached Sections.

Therefore current P7a reports:

```text
historical_daw_range_supported = false
section_range_supported        = false
```

Do not silently substitute a recent window for a requested historical section.

Historical/Section mono-fold analysis should wait for a deliberate retained-detail extension that reuses the common P4 range resolver.

## Peak fold-down limitation

Current Analyzer exposes stereo Sample Peak / True Peak, but does not directly measure mono-fold Sample Peak or mono-fold True Peak.

P7a therefore returns direct peak fold-down evidence as unavailable:

```text
mono_fold_sample_peak_dbfs = null
mono_fold_true_peak_dbtp    = null
```

Do not infer either from:

```text
stereo peak
stereo True Peak
correlation
Mid RMS
Side/Mid
```

Direct peak/true-peak fold-down measurement belongs to the optional P7b worker/protocol extension.

## Interpretation discipline

Never hard-code rules such as:

```text
all low frequencies must be mono
correlation < 0 means bad
mono_fold_delta < -X dB means fail
wide masters are wrong
Side energy must be minimized
```

Use musical role, arrangement, playback target, reference direction and user intent. The Analyzer reports the measurable fold-down consequence; the LLM decides whether that consequence matters.

## Recommended calling order

For a mono-translation question:

```text
audio_project_identity_status()
-> audio_project_status()
-> identify the target Analyzer
-> audio_mono_compatibility(target, seconds=...)
-> inspect existing_stereo_context only where useful
-> if a sound-changing action is made through the external DAW-control MCP,
   replay the same passage and use the appropriate verification path
```

For a historical Section request, explicitly state that P7a retained-detail support is unavailable rather than presenting recent-window evidence as that Section.
