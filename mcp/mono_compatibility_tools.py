#!/usr/bin/env python3
"""P7a direct mono-fold compatibility evidence from existing Mid/Side fields.

P7a adds no realtime DSP and no OSC fields. The Analyzer Worker already defines
M = 0.5 * (L + R) and S = 0.5 * (L - R). Therefore Mid RMS is the ordinary
mono-fold RMS, while M/S band-center spectra can be combined into a sampled
stereo-equivalent energy reference via P_stereo ~= P_mid + P_side.

The results are descriptive evidence. They do not define a universal stereo
quality score, pass/fail threshold, audibility probability, or processing
instruction. Direct mono-fold sample-peak / true-peak evidence remains P7b.
"""

from __future__ import annotations

import math
import time
from typing import Any

import server as core
import stereo_tools as stereo

DEFAULT_SECONDS = 5.0
MIN_SECONDS = 0.5
MAX_SECONDS = 60.0
FLOOR_DB = -120.0
_POWER_FLOOR = 1.0e-12

_GROUPS = (
    ("20-120 Hz", 20.0, 120.0),
    ("120-500 Hz", 120.0, 500.0),
    ("500 Hz-2 kHz", 500.0, 2000.0),
    ("2-5 kHz", 2000.0, 5000.0),
    ("5-20 kHz", 5000.0, 20000.0),
)


def _clamp_seconds(seconds: float) -> float:
    return max(MIN_SECONDS, min(float(seconds), MAX_SECONDS))


def _db_to_power(value_db: float) -> float:
    if not math.isfinite(value_db):
        return 0.0
    if value_db <= FLOOR_DB:
        return 0.0
    return 10.0 ** (value_db / 10.0)


def _power_to_db(power: float) -> float | None:
    if not math.isfinite(power) or power <= _POWER_FLOOR:
        return None
    return 10.0 * math.log10(power)


def _power_mean_db(values: list[float]) -> float | None:
    powers = [_db_to_power(float(value)) for value in values if math.isfinite(float(value))]
    powers = [value for value in powers if value > 0.0]
    if not powers:
        return None
    return _power_to_db(sum(powers) / len(powers))


def _delta_from_powers(mono_power: float, stereo_power: float) -> float | None:
    if stereo_power <= _POWER_FLOOR:
        return None
    if mono_power <= _POWER_FLOOR:
        # The Analyzer has a -120 dB display floor. Returning a finite value at
        # that floor is more honest than -inf, while retaining the strong-loss
        # meaning and avoiding fabricated energy below the measurement floor.
        return FLOOR_DB
    return 10.0 * math.log10(mono_power / stereo_power)


def _band_evidence(mid_db: float, side_db: float, center_hz: float) -> dict[str, Any]:
    mid_power = _db_to_power(mid_db)
    side_power = _db_to_power(side_db)
    stereo_power = mid_power + side_power
    if stereo_power <= _POWER_FLOOR:
        return {
            "center_hz": round(float(center_hz), 4),
            "available": False,
            "mid_db": None,
            "side_db": None,
            "stereo_equivalent_energy_db": None,
            "mono_fold_delta_db": None,
            "energy_loss_fraction": None,
            "relative_band_energy": None,
            "inspection_priority": None,
            "reason": "No measurable Mid/Side energy exists at this Analyzer band center.",
        }

    stereo_db = _power_to_db(stereo_power)
    delta_db = _delta_from_powers(mid_power, stereo_power)
    loss_fraction = max(0.0, min(1.0, 1.0 - mid_power / stereo_power))
    return {
        "center_hz": round(float(center_hz), 4),
        "available": True,
        "mid_db": None if mid_power <= _POWER_FLOOR else round(float(mid_db), 4),
        "side_db": None if side_power <= _POWER_FLOOR else round(float(side_db), 4),
        "stereo_equivalent_energy_db": None if stereo_db is None else round(stereo_db, 4),
        "mono_fold_delta_db": None if delta_db is None else round(delta_db, 4),
        "energy_loss_fraction": round(loss_fraction, 6),
        "relative_band_energy": None,
        "inspection_priority": None,
        "_stereo_power": stereo_power,
        "_mid_power": mid_power,
        "_side_power": side_power,
    }


def _finalize_relative_energy(bands: list[dict[str, Any]]) -> None:
    maximum = max(
        (float(band.get("_stereo_power", 0.0)) for band in bands if band.get("available")),
        default=0.0,
    )
    for band in bands:
        if not band.get("available") or maximum <= _POWER_FLOOR:
            band.pop("_stereo_power", None)
            band.pop("_mid_power", None)
            band.pop("_side_power", None)
            continue
        relative = max(0.0, min(1.0, float(band["_stereo_power"]) / maximum))
        loss = float(band["energy_loss_fraction"])
        band["relative_band_energy"] = round(relative, 6)
        band["inspection_priority"] = round(relative * loss, 6)


def _group_summary(bands: list[dict[str, Any]], label: str, lo: float, hi: float) -> dict[str, Any]:
    selected = [
        band for band in bands
        if band.get("available")
        and lo <= float(band["center_hz"]) < hi
        and "_stereo_power" in band
    ]
    if not selected:
        return {
            "range": label,
            "available": False,
            "mono_fold_delta_db": None,
            "energy_loss_fraction": None,
            "relative_group_energy": None,
            "inspection_priority": None,
        }

    mid_power = sum(float(band["_mid_power"]) for band in selected)
    side_power = sum(float(band["_side_power"]) for band in selected)
    stereo_power = mid_power + side_power
    delta = _delta_from_powers(mid_power, stereo_power)
    loss = max(0.0, min(1.0, 1.0 - mid_power / max(stereo_power, _POWER_FLOOR)))
    return {
        "range": label,
        "available": True,
        "sampled_band_centers": len(selected),
        "mono_fold_delta_db": None if delta is None else round(delta, 4),
        "energy_loss_fraction": round(loss, 6),
        "relative_group_energy": None,
        "inspection_priority": None,
        "_stereo_power": stereo_power,
    }


def _finalize_group_relative_energy(groups: list[dict[str, Any]]) -> None:
    maximum = max(
        (float(group.get("_stereo_power", 0.0)) for group in groups if group.get("available")),
        default=0.0,
    )
    for group in groups:
        if group.get("available") and maximum > _POWER_FLOOR:
            relative = max(0.0, min(1.0, float(group["_stereo_power"]) / maximum))
            loss = float(group["energy_loss_fraction"])
            group["relative_group_energy"] = round(relative, 6)
            group["inspection_priority"] = round(relative * loss, 6)
        group.pop("_stereo_power", None)


def _recent_frames(track: str, seconds: float) -> tuple[str, list[dict[str, Any]], dict[str, Any] | None]:
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


def _mean_band_db(frames: list[dict[str, Any]], key: str, index: int) -> float:
    powers: list[float] = []
    for frame in frames:
        values = frame.get(key)
        if not isinstance(values, list) or len(values) != core.NUM_BANDS:
            continue
        value = float(values[index])
        power = _db_to_power(value)
        powers.append(power)
    if not powers:
        return FLOOR_DB
    mean_power = sum(powers) / len(powers)
    value = _power_to_db(mean_power)
    return FLOOR_DB if value is None else value


def _build_result(track: str, seconds: float) -> dict[str, Any]:
    seconds = _clamp_seconds(seconds)
    runtime_id, frames, binding = _recent_frames(track, seconds)
    if not frames:
        return {
            "available": False,
            "id": runtime_id,
            "binding": binding,
            "scope": {"kind": "recent_receive_time_window", "window_seconds": seconds},
            "reason": "No Analyzer frames are available in the requested recent window.",
        }

    supported = [frame for frame in frames if bool(frame.get("stereo_v08_supported"))]
    valid = [frame for frame in supported if bool(frame.get("stereo_v08_valid"))]
    if not valid:
        return {
            "available": False,
            "id": runtime_id,
            "track": frames[-1].get("track"),
            "binding": binding,
            "scope": {"kind": "recent_receive_time_window", "window_seconds": seconds},
            "frames": len(frames),
            "supported_frames": len(supported),
            "reason": (
                "P7a requires active V0.8+ Mid/Side stereo evidence in the requested recent window."
            ),
        }

    stereo_rms_values = [
        float(frame["rms_db"])
        for frame in valid
        if frame.get("rms_db") is not None and math.isfinite(float(frame["rms_db"]))
    ]
    mono_rms_values = [
        float(frame["mid_rms_db"])
        for frame in valid
        if frame.get("mid_rms_db") is not None and math.isfinite(float(frame["mid_rms_db"]))
    ]
    stereo_rms_db = _power_mean_db(stereo_rms_values)
    mono_rms_db = _power_mean_db(mono_rms_values)
    stereo_power = 0.0 if stereo_rms_db is None else _db_to_power(stereo_rms_db)
    mono_power = 0.0 if mono_rms_db is None else _db_to_power(mono_rms_db)
    full_delta = _delta_from_powers(mono_power, stereo_power)

    bands = [
        _band_evidence(
            _mean_band_db(valid, "bands_db", index),
            _mean_band_db(valid, "side_bands_db", index),
            float(core.BAND_CENTERS[index]),
        )
        for index in range(core.NUM_BANDS)
    ]
    groups = [_group_summary(bands, label, lo, hi) for label, lo, hi in _GROUPS]
    _finalize_group_relative_energy(groups)
    _finalize_relative_energy(bands)

    shortlist = sorted(
        [
            {
                "center_hz": band["center_hz"],
                "mono_fold_delta_db": band["mono_fold_delta_db"],
                "relative_band_energy": band["relative_band_energy"],
                "energy_loss_fraction": band["energy_loss_fraction"],
                "inspection_priority": band["inspection_priority"],
            }
            for band in bands
            if band.get("available") and band.get("inspection_priority") is not None
        ],
        key=lambda item: float(item["inspection_priority"]),
        reverse=True,
    )[:8]

    context = stereo._build_profile(track, seconds)
    existing_context = None
    if context.get("available"):
        existing_context = {
            "full_band": context.get("full_band"),
            "low_band_20_120_hz": context.get("low_band_20_120_hz"),
            "frequency_dependent_stereo": context.get("frequency_dependent_stereo"),
        }

    return {
        "available": True,
        "id": runtime_id,
        "track": frames[-1].get("track"),
        "binding": binding,
        "scope": {
            "kind": "recent_receive_time_window",
            "window_seconds": seconds,
            "historical_daw_range_supported": False,
            "section_range_supported": False,
        },
        "coverage": {
            "frames": len(frames),
            "stereo_supported_frames": len(supported),
            "stereo_valid_frames": len(valid),
            "active_ratio": round(
                sum(bool(frame.get("signal_present")) for frame in frames) / len(frames), 4
            ),
            "note": (
                "This is recent receive-time evidence, not canonical Song Memory range coverage. "
                "Historical 32-band Mid/Side detail is not retained yet."
            ),
        },
        "full_band": {
            "stereo_rms_db": None if stereo_rms_db is None else round(stereo_rms_db, 4),
            "mono_fold_rms_db": None if mono_rms_db is None else round(mono_rms_db, 4),
            "mono_fold_rms_delta_db": None if full_delta is None else round(full_delta, 4),
            "formula": "10*log10(P_mid / P_stereo), where P_mid is M=(L+R)/2 and P_stereo=(L^2+R^2)/2",
        },
        "frequency": {
            "representation": "Analyzer 32 logarithmic band-center samples; not integrated-band transfer functions.",
            "bands": bands,
            "grouped_ranges": groups,
            "inspection_shortlist": shortlist,
            "inspection_priority_semantics": (
                "relative sampled stereo-equivalent energy * mono-fold energy-loss fraction; "
                "shortlist aid only, not audibility probability, quality score, or fail threshold."
            ),
        },
        "existing_stereo_context": existing_context,
        "peak_fold_down": {
            "available": False,
            "mono_fold_sample_peak_dbfs": None,
            "mono_fold_true_peak_dbtp": None,
            "reason": (
                "P7a adds no new OSC/DSP fields. Current Analyzer does not retain direct mono-fold "
                "sample peak or true peak; do not infer either from stereo peak, correlation, or RMS."
            ),
            "planned_scope": "P7b",
        },
        "evidence_semantics": {
            "mid_definition": "M = 0.5 * (L + R)",
            "side_definition": "S = 0.5 * (L - R)",
            "stereo_energy_identity": "(L_power + R_power)/2 = M_power + S_power",
            "mono_fold_band_delta": "10*log10(M_power / (M_power + S_power))",
            "missing_or_unmeasurable_energy": "unavailable/null, never silence invented from absent data",
        },
        "warnings": [
            "Do not treat correlation, Side/Mid, negative-cross evidence, or mono-fold delta as one universal stereo-quality score.",
            "Do not assume all low frequencies must be mono or apply a fixed mono-fold-loss pass/fail threshold.",
            "Arbitrary historical/Section 32-band mono-fold analysis is unavailable until retained-detail support exists.",
        ],
    }


@core.mcp.tool()
def audio_mono_compatibility(track: str, seconds: float = DEFAULT_SECONDS) -> dict[str, Any]:
    """Measure recent direct mono-fold RMS and energy-aware 32-band compatibility evidence without a quality score."""
    return _build_result(track, seconds)
