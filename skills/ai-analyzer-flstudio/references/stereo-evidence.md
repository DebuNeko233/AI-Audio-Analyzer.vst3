# V0.8 Mid/Side and Stereo Evidence Reference

This reference explains how to interpret AI Audio Analyzer V0.8 stereo measurements. It is a technical measurement guide only. It does **not** prescribe width, panning, mono, EQ, phase rotation, or any other mix action.

## Why V0.8 uses multiple axes

A single stereo-width value cannot distinguish all important cases.

Examples:

```text
high L/R similarity        → correlation near +1
weak linear similarity     → correlation near 0
strong opposition          → correlation near -1
large Side energy          → Side/Mid ratio increases
```

A signal can have large Side energy without being strongly anti-correlated. A signal can also be strongly anti-correlated without being broadly decorrelated.

V0.8 therefore keeps these measurements separate:

```text
L/R correlation
Side/Mid energy ratio
1 - abs(correlation) decorrelation proxy
negative cross-spectrum energy ratio
frequency-dependent Side/Mid ratio
20-120 Hz low-band correlation / Side-Mid ratio
```

Do not collapse them into one hidden "stereo quality" score.

## `mid_rms_db`

RMS level of:

```text
Mid = (L + R) / 2
```

in dBFS-like Analyzer units.

This is the coherent/common component level. It is not the same as total stereo RMS.

## `side_rms_db`

RMS level of:

```text
Side = (L - R) / 2
```

in dBFS-like Analyzer units.

Higher Side RMS only means more difference energy between channels. It does not by itself prove phase problems, better width, or worse mono compatibility.

## `side_to_mid_db`

Current relation:

```text
10 * log10(Side power / Mid power)
```

which is equivalent to:

```text
20 * log10(Side RMS / Mid RMS)
```

Interpretation is relative:

```text
negative dB → Mid energy exceeds Side energy
0 dB        → equal Mid and Side energy
positive dB → Side energy exceeds Mid energy
```

It is not a percentage and has no universal target.

## `stereo_correlation`

Full-band L/R correlation:

```text
+1  strongly similar
 0  weak linear relation
-1  strongly anti-correlated
```

Correlation is signed. It is useful for distinguishing similarity from opposition, but correlation alone does not quantify how much Side energy exists.

## `decorrelation_proxy_mean`

V0.8 profile tools expose the transparent derived quantity:

```text
1 - abs(L/R correlation)
```

Range:

```text
0 → correlation magnitude is near 1
1 → correlation is near 0
```

Important limitation: both `+1` and `-1` correlation produce a decorrelation proxy near `0`. Therefore this proxy must always be read together with the **sign** of correlation and negative-cross evidence.

It is a mathematical proxy, not a perceptual spaciousness score.

## `negative_cross_energy_ratio`

Range:

```text
0..1
```

The VST3 computes the real L/R cross-spectrum for FFT bins. Bins whose real cross term is negative contribute to the numerator. Weight is based on bilateral L/R spectral energy.

Conceptually:

```text
negative-cross bilateral weight
--------------------------------
all bilateral spectral weight
```

This is evidence that a larger portion of bilateral spectral energy has an opposing cross-spectrum sign.

It is **not**:

- a phase-angle histogram;
- a count of samples with opposite sign;
- an audibility probability;
- a mono-cancellation percentage;
- a quality score.

Read it together with correlation, Side/Mid energy, frequency-dependent values, and actual project context.

## `low_band_20_120_correlation`

Aggregate L/R correlation computed from approximately `20-120 Hz` FFT content.

Use it when the question specifically concerns low-frequency channel relation. If the source has little energy in this range, do not overinterpret the number.

There is no universal requirement that every source must be maximally correlated in this band.

## `low_band_20_120_side_to_mid_db`

Integrated Side/Mid power relation over approximately `20-120 Hz`.

This indicates how much low-frequency difference energy exists relative to low-frequency common energy. It is not an automatic mono-compatibility pass/fail threshold.

## `mid_spectrum_db`

The historical Analyzer `bands_db` field is explicitly the 32-band **Mid spectrum**.

V0.8 tools expose it under the clearer name `mid_spectrum_db` when returning a stereo profile.

## `side_spectrum_db`

32 log-spaced Side-spectrum features across the same approximate 20 Hz-20 kHz centers used by the existing Mid spectrum.

Use Mid and Side spectra together to locate the frequency ranges where channel-difference energy is concentrated.

These are FFT-derived machine features, not calibrated SPL.

## `frequency_dependent_stereo[]`

Eight frequency regions are used:

```text
20-60 Hz
60-120 Hz
120-250 Hz
250-500 Hz
500 Hz-1 kHz
1-2 kHz
2-5 kHz
5-20 kHz
```

Each region may contain:

```text
correlation
side_to_mid_db
```

Correlation describes signed L/R relation. Side/Mid dB describes energy distribution. Keep the two meanings separate.

## Distinguishing common cases

Do not turn the following into rigid classification thresholds; use them only as conceptual patterns.

```text
correlation near +1
+ low Side/Mid
→ channels are highly similar and common energy dominates

correlation near 0
+ substantial Side/Mid
+ decorrelation proxy high
→ channels have weak linear similarity with meaningful difference energy

correlation near -1
+ substantial Side/Mid
+ negative-cross ratio high
→ strong opposition evidence is present
```

These patterns describe measurements, not whether the sound is correct for a song.

## `audio_stereo_profile()`

Use:

```text
audio_stereo_profile(track, seconds=5)
```

Prefer it over a single frame when the user asks about stereo behavior across a passage.

Inspect:

```text
active_ratio
stereo_frames
full_band
low_band_20_120_hz
mid_spectrum_db
side_spectrum_db
frequency_dependent_stereo
```

## `audio_stereo_compare()`

Use:

```text
audio_stereo_compare(track_a, track_b, seconds=5)
```

All returned deltas follow:

```text
B - A
```

A positive Side/Mid delta means B measured more Side relative to Mid than A over the compared window. It does not mean B is better or wider in a perceptually universal sense.

## Validity rules

For V0.8 stereo interpretation inspect:

```text
signal_present
stereo_v08_supported
stereo_v08_valid
active_ratio
stereo_frames
```

Older VST3 versions may still provide the legacy correlation/width fields but cannot provide V0.8 Side spectrum or negative-cross evidence.

`null` means unavailable, not zero.

## Output discipline

When reporting stereo evidence, state the actual measurement and scope rather than converting it into an undocumented prescription.

Good technical phrasing:

```text
The 20-120 Hz Side/Mid ratio increased by X dB over this window.
The full-band correlation is near Y while negative-cross evidence is Z.
Side energy is concentrated in these measured frequency regions.
```

Do not claim, based on Analyzer metrics alone:

```text
this must be mono
this is too wide
this phase is wrong
this correlation is bad
apply a specific stereo processor
```

Those are processing/aesthetic decisions outside the measurement scope of this Skill.
