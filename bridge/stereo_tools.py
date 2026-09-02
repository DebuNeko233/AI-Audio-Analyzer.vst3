#!/usr/bin/env python3
"""V0.8 Mid/Side and stereo measurement layer.

This module wraps the existing V0.6 append-only frame parser, attaches the V0.8
stereo tail to the same live/history frame objects, and registers measurement-
only stereo profile/comparison tools on the shared MCP server.

The returned values are descriptive evidence. They intentionally keep Side
energy, ordinary L/R correlation, a decorrelation proxy, and negative cross-
spectrum evidence separate instead of collapsing them into a single quality
score or prescribing a mixing action.
"""

from __future__ import annotations

import math
import time
from typing import Any

import server as core
import temporal_tools as temporal

DEFAULT_SECONDS = 5.0
V08_START = temporal.V06_START + temporal.V06_FIELD_COUNT
V08_SCALAR_COUNT = 6
V08_FIELD_COUNT = V08_SCALAR_COUNT + core.NUM_BANDS + core.NUM_STEREO_CORR_BANDS + 1

_ORIGINAL_ON_FRAME = core._on_frame


def on_frame_v08(address: str, *args: Any) -> None:
    """Parse older frame layers first, then attach the append-only V0.8 tail."""
    _ORIGINAL_ON_FRAME(address, *args)

    if len(args) < V08_START + V08_FIELD_COUNT:
        return

    runtime_id = str(args[temporal.V03_START + 3]).strip()
    if not runtime_id:
        return

    try:
        mid_rms_db = float(args[V08_START])
        side_rms_db = float(args[V08_START + 1])
        side_to_mid_db = float(args[V08_START + 2])
        negative_cross_energy_ratio = max(0.0, min(1.0, float(args[V08_START + 3])))
        low_band_correlation = max(-1.0, min(1.0, float(args[V08_START + 4])))
        low_band_side_to_mid_db = float(args[V08_START + 5])
        side_start = V08_START + V08_SCALAR_COUNT
        side_bands_db = [
            float(value) for value in args[side_start : side_start + core.NUM_BANDS]
        ]
        ratio_start = side_start + core.NUM_BANDS
        band_side_to_mid_db = [
            float(value)
            for value in args[ratio_start : ratio_start + core.NUM_STEREO_CORR_BANDS]
        ]
        schema_version = str(args[ratio_start + core.NUM_STEREO_CORR_BANDS]).strip() or "0.8"
    except (TypeError, ValueError):
        return

    with core._lock:
        frame = core._tracks.get(runtime_id)
        if frame is None:
            return

        valid = bool(frame.get("signal_present"))
        frame["schema_version"] = schema_version
        frame["stereo_v08_supported"] = True
        frame["stereo_v08_valid"] = valid
        frame["mid_rms_db"] = mid_rms_db if valid else None
        frame["side_rms_db"] = side_rms_db if valid else None
        frame["side_to_mid_db"] = side_to_mid_db if valid else None
        frame["negative_cross_energy_ratio"] = (
            negative_cross_energy_ratio if valid else None
        )
        frame["low_band_20_120_correlation"] = low_band_correlation if valid else None
        frame["low_band_20_120_side_to_mid_db"] = (
            low_band_side_to_mid_db if valid else None
        )
        frame["side_bands_db"] = side_bands_db if valid else None
        frame["band_side_to_mid_db"] = band_side_to_mid_db if valid else None


def _clamp_seconds(seconds: float) -> float:
    return max(0.5, min(float(seconds), 60.0))


def _history(
    track: str, seconds: float
) -> tuple[str, list[dict[str, Any]], dict[str, Any] | None]:
    runtime_id = core._resolve_track(track)
    cutoff = time.time() - seconds
    with core._lock:
        frames = [
            dict(frame)
            for frame in core._history.get(runtime_id, ())
            if float(frame.get("_received_at", 0.0)) >= cutoff
        ]
        binding = core._binding_public(core._bindings.get(runtime_id))
    return runtime_id, frames, binding


def _mean(values: list[float]) -> float | None:
    usable = [float(value) for value in values if math.isfinite(float(value))]
    if not usable:
        return None
    return sum(usable) / len(usable)


def _mean_db(values: list[float]) -> float | None:
    usable = [
        float(value)
        for value in values
        if math.isfinite(float(value)) and float(value) > -120.0
    ]
    if not usable:
        return None
    mean_power = sum(10.0 ** (value / 10.0) for value in usable) / len(usable)
    return 10.0 * math.log10(max(mean_power, 1.0e-12))


def _mean_ratio_db(values: list[float]) -> float | None:
    usable = [float(value) for value in values if math.isfinite(float(value))]
    if not usable:
        return None
    mean_ratio = sum(10.0 ** (value / 10.0) for value in usable) / len(usable)
    return 10.0 * math.log10(max(mean_ratio, 1.0e-12))


def _mean_spectrum(frames: list[dict[str, Any]], key: str) -> list[float | None]:
    result: list[float | None] = []
    for index in range(core.NUM_BANDS):
        values: list[float] = []
        for frame in frames:
            bands = frame.get(key)
            if isinstance(bands, list) and len(bands) == core.NUM_BANDS:
                values.append(float(bands[index]))
        value = _mean_db(values)
        result.append(None if value is None else round(value, 4))
    return result


def _mean_band_ratio(frames: list[dict[str, Any]]) -> list[float | None]:
    result: list[float | None] = []
    for index in range(core.NUM_STEREO_CORR_BANDS):
        values: list[float] = []
        for frame in frames:
            ratios = frame.get("band_side_to_mid_db")
            if isinstance(ratios, list) and len(ratios) == core.NUM_STEREO_CORR_BANDS:
                values.append(float(ratios[index]))
        value = _mean_ratio_db(values)
        result.append(None if value is None else round(value, 4))
    return result


def _mean_band_correlation(frames: list[dict[str, Any]]) -> list[float | None]:
    result: list[float | None] = []
    for index in range(core.NUM_STEREO_CORR_BANDS):
        values: list[float] = []
        for frame in frames:
            correlations = frame.get("band_stereo_correlation")
            if isinstance(correlations, list) and len(correlations) == core.NUM_STEREO_CORR_BANDS:
                values.append(float(correlations[index]))
        value = _mean(values)
        result.append(None if value is None else round(value, 6))
    return result


def _build_profile(track: str, seconds: float) -> dict[str, Any]:
    seconds = _clamp_seconds(seconds)
    runtime_id, frames, binding = _history(track, seconds)

    if not frames:
        return {
            "available": False,
            "id": runtime_id,
            "binding": binding,
            "window_seconds": seconds,
            "reason": "No Analyzer frames are available in the requested window.",
        }

    supported = [frame for frame in frames if bool(frame.get("stereo_v08_supported"))]
    if not supported:
        return {
            "available": False,
            "id": runtime_id,
            "track": frames[-1].get("track"),
            "binding": binding,
            "window_seconds": seconds,
            "reason": "Deep Mid/Side stereo descriptors require AI Audio Analyzer VST3 0.8+ frames.",
        }

    valid = [frame for frame in supported if bool(frame.get("stereo_v08_valid"))]
    if not valid:
        return {
            "available": False,
            "id": runtime_id,
            "track": frames[-1].get("track"),
            "binding": binding,
            "window_seconds": seconds,
            "stereo_v08_supported": True,
            "signal_present": bool(frames[-1].get("signal_present")),
            "active_ratio": round(
                sum(bool(frame.get("signal_present")) for frame in frames) / len(frames), 4
            ),
            "reason": "No stereo-valid active frames occurred in the requested window.",
        }

    correlations = [
        float(frame["stereo_correlation"])
        for frame in valid
        if frame.get("stereo_correlation") is not None
    ]
    decorrelation = [1.0 - abs(value) for value in correlations]
    mid_rms = [float(frame["mid_rms_db"]) for frame in valid if frame.get("mid_rms_db") is not None]
    side_rms = [float(frame["side_rms_db"]) for frame in valid if frame.get("side_rms_db") is not None]
    side_mid = [
        float(frame["side_to_mid_db"])
        for frame in valid
        if frame.get("side_to_mid_db") is not None
    ]
    negative_cross = [
        float(frame["negative_cross_energy_ratio"])
        for frame in valid
        if frame.get("negative_cross_energy_ratio") is not None
    ]
    low_corr = [
        float(frame["low_band_20_120_correlation"])
        for frame in valid
        if frame.get("low_band_20_120_correlation") is not None
    ]
    low_side_mid = [
        float(frame["low_band_20_120_side_to_mid_db"])
        for frame in valid
        if frame.get("low_band_20_120_side_to_mid_db") is not None
    ]

    corr_mean = _mean(correlations)
    decorrelation_mean = _mean(decorrelation)
    mid_mean = _mean_db(mid_rms)
    side_mean = _mean_db(side_rms)
    side_mid_mean = _mean_ratio_db(side_mid)
    negative_mean = _mean(negative_cross)
    low_corr_mean = _mean(low_corr)
    low_side_mid_mean = _mean_ratio_db(low_side_mid)

    mid_spectrum = _mean_spectrum(valid, "bands_db")
    side_spectrum = _mean_spectrum(valid, "side_bands_db")
    band_side_mid = _mean_band_ratio(valid)
    band_corr = _mean_band_correlation(valid)
    ranges = core._stereo_corr_ranges()

    return {
        "available": True,
        "id": runtime_id,
        "track": frames[-1].get("track"),
        "binding": binding,
        "window_seconds": seconds,
        "frames": len(frames),
        "stereo_frames": len(valid),
        "active_ratio": round(
            sum(bool(frame.get("signal_present")) for frame in frames) / len(frames), 4
        ),
        "full_band": {
            "mid_rms_db": None if mid_mean is None else round(mid_mean, 4),
            "side_rms_db": None if side_mean is None else round(side_mean, 4),
            "side_to_mid_db": None if side_mid_mean is None else round(side_mid_mean, 4),
            "stereo_correlation_mean": None if corr_mean is None else round(corr_mean, 6),
            "stereo_correlation_min": None if not correlations else round(min(correlations), 6),
            "decorrelation_proxy_mean": (
                None if decorrelation_mean is None else round(decorrelation_mean, 6)
            ),
            "negative_cross_energy_ratio_mean": (
                None if negative_mean is None else round(negative_mean, 6)
            ),
            "negative_cross_energy_ratio_max": (
                None if not negative_cross else round(max(negative_cross), 6)
            ),
        },
        "low_band_20_120_hz": {
            "correlation_mean": None if low_corr_mean is None else round(low_corr_mean, 6),
            "correlation_min": None if not low_corr else round(min(low_corr), 6),
            "side_to_mid_db": (
                None if low_side_mid_mean is None else round(low_side_mid_mean, 4)
            ),
            "side_to_mid_db_max": (
                None if not low_side_mid else round(max(low_side_mid), 4)
            ),
        },
        "spectrum_band_centers_hz": list(core.BAND_CENTERS),
        "mid_spectrum_db": mid_spectrum,
        "side_spectrum_db": side_spectrum,
        "frequency_dependent_stereo": [
            {
                "range": ranges[index],
                "correlation": band_corr[index],
                "side_to_mid_db": band_side_mid[index],
            }
            for index in range(core.NUM_STEREO_CORR_BANDS)
        ],
        "evidence_semantics": {
            "decorrelation_proxy_formula": "1 - abs(L/R correlation)",
            "negative_cross_energy_ratio": (
                "Fraction of bilateral FFT-bin weight whose real L/R cross-spectrum is negative. "
                "It is phase-opposition evidence, not a phase-angle histogram or audibility score."
            ),
            "bands_db": "Historical 32-band Analyzer spectrum is the Mid spectrum.",
            "side_bands_db": "V0.8 adds a separate 32-band Side spectrum.",
            "side_to_mid_db": "10*log10(Side power / Mid power), equivalently 20*log10(Side RMS / Mid RMS).",
        },
        "note": (
            "Keep correlation, Side/Mid energy, decorrelation proxy, and negative-cross evidence separate. "
            "No field is a universal stereo-quality score or processing instruction."
        ),
    }


@core.mcp.tool()
def audio_stereo_profile(track: str, seconds: float = DEFAULT_SECONDS) -> dict[str, Any]:
    """Summarize V0.8 Mid/Side, correlation, low-band, and Side-spectrum evidence."""
    return _build_profile(track, seconds)


@core.mcp.tool()
def audio_stereo_compare(
    track_a: str,
    track_b: str,
    seconds: float = DEFAULT_SECONDS,
) -> dict[str, Any]:
    """Compare V0.8 stereo measurements for two analyzer instances without judging quality."""
    a = _build_profile(track_a, seconds)
    b = _build_profile(track_b, seconds)
    if not a.get("available") or not b.get("available"):
        return {
            "available": False,
            "track_a": a,
            "track_b": b,
            "reason": "Both tracks need stereo-valid V0.8 frames in the requested window.",
        }

    full_a = a["full_band"]
    full_b = b["full_band"]
    low_a = a["low_band_20_120_hz"]
    low_b = b["low_band_20_120_hz"]

    def delta(value_a: Any, value_b: Any, digits: int = 4) -> float | None:
        if value_a is None or value_b is None:
            return None
        return round(float(value_b) - float(value_a), digits)

    band_deltas = []
    for band_a, band_b in zip(
        a["frequency_dependent_stereo"], b["frequency_dependent_stereo"]
    ):
        band_deltas.append(
            {
                "range": band_a["range"],
                "correlation_delta_b_minus_a": delta(
                    band_a.get("correlation"), band_b.get("correlation"), 6
                ),
                "side_to_mid_db_delta_b_minus_a": delta(
                    band_a.get("side_to_mid_db"), band_b.get("side_to_mid_db")
                ),
            }
        )

    return {
        "available": True,
        "window_seconds": _clamp_seconds(seconds),
        "track_a": {"id": a["id"], "track": a["track"], "binding": a["binding"]},
        "track_b": {"id": b["id"], "track": b["track"], "binding": b["binding"]},
        "deltas_b_minus_a": {
            "mid_rms_db": delta(full_a.get("mid_rms_db"), full_b.get("mid_rms_db")),
            "side_rms_db": delta(full_a.get("side_rms_db"), full_b.get("side_rms_db")),
            "side_to_mid_db": delta(full_a.get("side_to_mid_db"), full_b.get("side_to_mid_db")),
            "stereo_correlation_mean": delta(
                full_a.get("stereo_correlation_mean"),
                full_b.get("stereo_correlation_mean"),
                6,
            ),
            "decorrelation_proxy_mean": delta(
                full_a.get("decorrelation_proxy_mean"),
                full_b.get("decorrelation_proxy_mean"),
                6,
            ),
            "negative_cross_energy_ratio_mean": delta(
                full_a.get("negative_cross_energy_ratio_mean"),
                full_b.get("negative_cross_energy_ratio_mean"),
                6,
            ),
            "low_band_20_120_correlation": delta(
                low_a.get("correlation_mean"), low_b.get("correlation_mean"), 6
            ),
            "low_band_20_120_side_to_mid_db": delta(
                low_a.get("side_to_mid_db"), low_b.get("side_to_mid_db")
            ),
        },
        "frequency_dependent_deltas": band_deltas,
        "note": (
            "Deltas are B minus A measurements. Positive or negative values are not labelled better/worse; "
            "interpret them only in the user's musical/project context."
        ),
    }
