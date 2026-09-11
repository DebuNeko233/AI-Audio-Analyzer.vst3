# Mono Compatibility Evidence

Use this guide for mono fold-down, stereo translation and direct Mid/Side energy loss.

## Recent-window P7a tool

```text
audio_mono_compatibility(track, seconds=5.0)
```

P7a uses existing Analyzer Mid/Side math:

```text
M = 0.5 * (L + R)
S = 0.5 * (L - R)
(L_power + R_power)/2 = M_power + S_power
```

Full-band evidence includes:

```text
stereo_rms_db
mono_fold_rms_db
mono_fold_rms_delta_db
floor_censored
```

At the existing 32 Analyzer band centers:

```text
stereo_equivalent_power = mid_power + side_power
mono_fold_band_power     = mid_power
mono_fold_delta_db       = 10*log10(mid_power / stereo_equivalent_power)
```

Returned band fields include energy loss, relative band energy and `inspection_priority`.

`inspection_priority` is an energy-aware shortlist aid only. It is not audibility probability, phase-problem probability, quality score, pass/fail result or processing recommendation.

When Mid reaches the Analyzer `-120 dB` measurement floor, cancellation depth is floor-censored. Do not claim exact deeper cancellation.

## Historical scope after P4b

`audio_mono_compatibility()` itself remains a **recent receive-time** tool and still reports no direct historical/Section support.

For a retained historical DAW range or cached Section use:

```text
audio_historical_detail(...)
```

P4b reuses the common P4 range resolver and retained one-second Song Memory. When spectrum/stereo features were actually measured during capture, it can reconstruct one-second historical Mid/Side energy and derived mono-fold energy evidence without replay.

Keep scopes distinct:

```text
audio_mono_compatibility()  recent frames / finer current context
audio_historical_detail()  one-second retained historical context
```

Missing historical detail remains unavailable, never silence.

## Direct peak fold-down remains unavailable

Current Analyzer does not directly measure:

```text
mono_fold_sample_peak_dbfs
mono_fold_true_peak_dbtp
```

Do not infer either from stereo Sample Peak/True Peak, correlation, Mid RMS or Side/Mid.

Direct mono Peak/True-Peak measurement belongs to optional P7b and would require deliberate Worker/protocol work.

## Keep stereo evidence dimensions separate

Do not collapse:

```text
mono-fold energy loss
L/R correlation
frequency-dependent correlation
Side/Mid ratio
low-band correlation
negative-cross energy ratio
```

Direct fold-down energy measures the energy consequence. Other stereo descriptors help explain context but are not universal quality rules.

## Interpretation discipline

Never hard-code rules such as:

```text
all low frequencies must be mono
correlation < 0 means bad
mono_fold_delta < -X dB means fail
wide masters are wrong
```

Use arrangement, musical role, playback target, reference context and user intent.

## Calling order

Recent mono question:

```text
audio_project_identity_status()
-> audio_project_status()
-> identify target Analyzer
-> audio_mono_compatibility(...)
```

Historical Section/range question:

```text
audio_section_map() if needed
-> audio_historical_detail(...)
```

If P4b retained detail is unavailable, say so. Do not present a current recent-window result as evidence for a past Section.
