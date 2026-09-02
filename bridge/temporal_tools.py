#!/usr/bin/env python3
"""Temporal-analysis compatibility layer for AI Audio Analyzer MCP 0.6.

The stable core bridge remains in ``server.py``. This module wraps its frame
parser so the V0.6 append-only OSC tail is added to the same history objects,
then registers measurement-oriented temporal tools on the existing MCP server.

Temporal outputs are descriptive/heuristic evidence. They do not encode a
mixing style or prescribe processing decisions.
"""

from __future__ import annotations

import math
import time
from typing import Any

import server as core

DEFAULT_SECONDS = 5.0
DEFAULT_BAND_LOW_HZ = 40.0
DEFAULT_BAND_HIGH_HZ = 160.0
DEFAULT_ALIGNMENT_TOLERANCE_MS = 80.0

# These thresholds only define candidate frames for a compact event-density
# summary. They are intentionally exposed in every result and must not be
# interpreted as a universal psychoacoustic onset detector.
ONSET_CANDIDATE_RMS_RISE_DB = 3.0
ONSET_CANDIDATE_SPECTRAL_FLUX = 0.18

V03_START = 11 + core.NUM_BANDS + 4 + core.NUM_STEREO_CORR_BANDS
V06_START = V03_START + 4
V06_FIELD_COUNT = 6

_ORIGINAL_ON_FRAME = core._on_frame


def on_frame_v06(address: str, *args: Any) -> None:
    """Parse the stable frame first, then attach the append-only V0.6 tail."""
    _ORIGINAL_ON_FRAME(address, *args)

    if len(args) < V06_START + V06_FIELD_COUNT:
        return

    runtime_id = str(args[V03_START + 3]).strip()
    if not runtime_id:
        return

    try:
        temporal_window_seconds = max(0.0, float(args[V06_START]))
        spectral_flux_mean = max(0.0, float(args[V06_START + 1]))
        spectral_flux_peak = max(0.0, float(args[V06_START + 2]))
        rms_rise_peak_db = max(0.0, float(args[V06_START + 3]))
        low_band_energy_db = float(args[V06_START + 4])
        schema_version = str(args[V06_START + 5]).strip() or "0.6"
    except (TypeError, ValueError):
        return

    with core._lock:
        frame = core._tracks.get(runtime_id)
        if frame is None:
            return

        signal_present = bool(frame.get("signal_present"))
        temporal_valid = bool(signal_present and temporal_window_seconds > 0.0)
        frame["schema_version"] = schema_version
        frame["temporal_supported"] = True
        frame["temporal_valid"] = temporal_valid
        frame["temporal_window_seconds"] = temporal_window_seconds
        frame["spectral_flux_mean"] = spectral_flux_mean if temporal_valid else None
        frame["spectral_flux_peak"] = spectral_flux_peak if temporal_valid else None
        frame["rms_rise_peak_db"] = rms_rise_peak_db if temporal_valid else None
        frame["low_band_energy_db"] = low_band_energy_db if temporal_valid else None


def _clamp_seconds(seconds: float) -> float:
    return max(0.5, min(float(seconds), 60.0))


def _history(track: str, seconds: float) -> tuple[str, list[dict[str, Any]], dict[str, Any] | None]:
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


def _weighted_mean(values: list[tuple[float, float]]) -> float | None:
    usable = [
        (float(value), max(0.0, float(weight)))
        for value, weight in values
        if math.isfinite(float(value)) and math.isfinite(float(weight)) and float(weight) > 0.0
    ]
    if not usable:
        return None
    total_weight = sum(weight for _, weight in usable)
    if total_weight <= 0.0:
        return None
    return sum(value * weight for value, weight in usable) / total_weight


def _mean_db(values: list[float]) -> float | None:
    finite = [float(value) for value in values if math.isfinite(float(value)) and float(value) > -120.0]
    if not finite:
        return None
    mean_power = sum(10.0 ** (value / 10.0) for value in finite) / len(finite)
    return 10.0 * math.log10(max(mean_power, 1.0e-12))


def _candidate(frame: dict[str, Any]) -> bool:
    if not bool(frame.get("temporal_valid")):
        return False
    rise = frame.get("rms_rise_peak_db")
    flux = frame.get("spectral_flux_peak")
    rise_hit = rise is not None and float(rise) >= ONSET_CANDIDATE_RMS_RISE_DB
    flux_hit = flux is not None and float(flux) >= ONSET_CANDIDATE_SPECTRAL_FLUX
    return bool(rise_hit or flux_hit)


def _band_energy_db(frame: dict[str, Any], low_hz: float, high_hz: float) -> float | None:
    if not bool(frame.get("signal_present", True)):
        return None
    bands = frame.get("bands_db")
    if not bands:
        return None

    selected = [
        float(value)
        for center, value in zip(core.BAND_CENTERS, bands)
        if low_hz <= float(center) < high_hz and math.isfinite(float(value))
    ]
    return _mean_db(selected)


def _clock(frame: dict[str, Any]) -> float:
    value = frame.get("plugin_timestamp")
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float("nan")
    if math.isfinite(numeric):
        return numeric
    return float(frame.get("_received_at", 0.0))


def _align_frames(
    frames_a: list[dict[str, Any]],
    frames_b: list[dict[str, Any]],
    tolerance_seconds: float,
) -> list[tuple[dict[str, Any], dict[str, Any], float]]:
    a = sorted(frames_a, key=_clock)
    b = sorted(frames_b, key=_clock)
    pairs: list[tuple[dict[str, Any], dict[str, Any], float]] = []
    i = 0
    j = 0

    while i < len(a) and j < len(b):
        ta = _clock(a[i])
        tb = _clock(b[j])
        delta = ta - tb
        if abs(delta) <= tolerance_seconds:
            pairs.append((a[i], b[j], delta))
            i += 1
            j += 1
        elif delta < 0.0:
            i += 1
        else:
            j += 1

    return pairs


def _pearson(values_a: list[float], values_b: list[float]) -> float | None:
    if len(values_a) != len(values_b) or len(values_a) < 3:
        return None
    mean_a = sum(values_a) / len(values_a)
    mean_b = sum(values_b) / len(values_b)
    centered_a = [value - mean_a for value in values_a]
    centered_b = [value - mean_b for value in values_b]
    denom_a = sum(value * value for value in centered_a)
    denom_b = sum(value * value for value in centered_b)
    denom = math.sqrt(max(0.0, denom_a * denom_b))
    if denom <= 1.0e-12:
        return None
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(centered_a, centered_b)) / denom))


def _normalized_overlap(values_a_db: list[float], values_b_db: list[float]) -> float | None:
    if len(values_a_db) != len(values_b_db) or not values_a_db:
        return None
    max_a = max(values_a_db)
    max_b = max(values_b_db)
    overlaps = []
    for a_db, b_db in zip(values_a_db, values_b_db):
        rel_a = 10.0 ** ((a_db - max_a) / 10.0)
        rel_b = 10.0 ** ((b_db - max_b) / 10.0)
        overlaps.append(min(rel_a, rel_b))
    return sum(overlaps) / len(overlaps)


@core.mcp.tool()
def audio_temporal_profile(track: str, seconds: float = DEFAULT_SECONDS) -> dict[str, Any]:
    """Summarize V0.6 temporal descriptors for one analyzer over a recent window."""
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

    supported = [frame for frame in frames if bool(frame.get("temporal_supported"))]
    if not supported:
        return {
            "available": False,
            "id": runtime_id,
            "track": frames[-1].get("track"),
            "binding": binding,
            "window_seconds": seconds,
            "reason": "Temporal descriptors require AI Audio Analyzer V0.6+ frames.",
        }

    valid = [frame for frame in supported if bool(frame.get("temporal_valid"))]
    observed_seconds = sum(max(0.0, float(frame.get("temporal_window_seconds") or 0.0)) for frame in valid)
    candidates = [frame for frame in valid if _candidate(frame)]

    if not valid:
        return {
            "available": False,
            "id": runtime_id,
            "track": frames[-1].get("track"),
            "binding": binding,
            "window_seconds": seconds,
            "temporal_supported": True,
            "signal_present": bool(frames[-1].get("signal_present")),
            "active_ratio": round(sum(bool(frame.get("signal_present")) for frame in frames) / len(frames), 4),
            "reason": "No temporally valid active frames occurred in the requested window.",
        }

    weights = [max(1.0e-6, float(frame.get("temporal_window_seconds") or 0.0)) for frame in valid]
    flux_mean = _weighted_mean([
        (float(frame["spectral_flux_mean"]), weight)
        for frame, weight in zip(valid, weights)
        if frame.get("spectral_flux_mean") is not None
    ])
    flux_peaks = [float(frame["spectral_flux_peak"]) for frame in valid if frame.get("spectral_flux_peak") is not None]
    rms_rises = [float(frame["rms_rise_peak_db"]) for frame in valid if frame.get("rms_rise_peak_db") is not None]
    low_band_values = [float(frame["low_band_energy_db"]) for frame in valid if frame.get("low_band_energy_db") is not None]

    return {
        "available": True,
        "id": runtime_id,
        "track": frames[-1].get("track"),
        "binding": binding,
        "window_seconds": seconds,
        "frames": len(frames),
        "temporal_frames": len(valid),
        "temporal_observed_seconds": round(observed_seconds, 4),
        "active_ratio": round(sum(bool(frame.get("signal_present")) for frame in frames) / len(frames), 4),
        "spectral_flux_mean": None if flux_mean is None else round(flux_mean, 6),
        "spectral_flux_peak": None if not flux_peaks else round(max(flux_peaks), 6),
        "rms_rise_peak_db": None if not rms_rises else round(max(rms_rises), 4),
        "low_band_40_160_energy_db": None if not low_band_values else round(_mean_db(low_band_values) or -120.0, 4),
        "low_band_40_160_min_db": None if not low_band_values else round(min(low_band_values), 4),
        "low_band_40_160_max_db": None if not low_band_values else round(max(low_band_values), 4),
        "onset_candidate_frames": len(candidates),
        "onset_candidate_density_hz": (
            None if observed_seconds <= 0.0 else round(len(candidates) / observed_seconds, 4)
        ),
        "onset_candidate_thresholds": {
            "rms_rise_peak_db_gte": ONSET_CANDIDATE_RMS_RISE_DB,
            "spectral_flux_peak_gte": ONSET_CANDIDATE_SPECTRAL_FLUX,
            "logic": "OR",
        },
        "note": (
            "Spectral flux is normalized positive spectral redistribution. RMS-rise peak is the largest positive "
            "window-to-window RMS change inside each OSC aggregate. Onset candidates are threshold-based evidence, "
            "not ground-truth musical onset labels."
        ),
    }


@core.mcp.tool()
def audio_temporal_compare(
    track_a: str,
    track_b: str,
    seconds: float = DEFAULT_SECONDS,
    low_hz: float = DEFAULT_BAND_LOW_HZ,
    high_hz: float = DEFAULT_BAND_HIGH_HZ,
    alignment_tolerance_ms: float = DEFAULT_ALIGNMENT_TOLERANCE_MS,
) -> dict[str, Any]:
    """Compare time-aligned band envelopes and V0.6 change candidates for two analyzers."""
    seconds = _clamp_seconds(seconds)
    low_hz = max(core.MIN_HZ, float(low_hz))
    high_hz = min(core.MAX_HZ, float(high_hz))
    if high_hz <= low_hz:
        raise ValueError("high_hz must be greater than low_hz within the Analyzer 20 Hz-20 kHz range.")

    tolerance_ms = max(10.0, min(float(alignment_tolerance_ms), 250.0))
    tolerance_seconds = tolerance_ms / 1000.0

    id_a, frames_a, binding_a = _history(track_a, seconds)
    id_b, frames_b, binding_b = _history(track_b, seconds)
    pairs = _align_frames(frames_a, frames_b, tolerance_seconds)

    if not pairs:
        return {
            "available": False,
            "track_a_id": id_a,
            "track_b_id": id_b,
            "binding_a": binding_a,
            "binding_b": binding_b,
            "window_seconds": seconds,
            "reason": "No time-aligned Analyzer frames were found within the requested tolerance.",
        }

    energy_a: list[float] = []
    energy_b: list[float] = []
    usable_pairs = 0
    both_active_pairs = 0
    offsets_ms: list[float] = []
    temporal_pair_count = 0
    candidate_a = 0
    candidate_b = 0
    coincident_candidates = 0

    for frame_a, frame_b, offset in pairs:
        offsets_ms.append(abs(offset) * 1000.0)
        active_a = bool(frame_a.get("signal_present"))
        active_b = bool(frame_b.get("signal_present"))
        if active_a and active_b:
            both_active_pairs += 1

        band_a = _band_energy_db(frame_a, low_hz, high_hz)
        band_b = _band_energy_db(frame_b, low_hz, high_hz)
        if band_a is not None and band_b is not None:
            energy_a.append(band_a)
            energy_b.append(band_b)
            usable_pairs += 1

        if bool(frame_a.get("temporal_supported")) and bool(frame_b.get("temporal_supported")):
            temporal_pair_count += 1
            hit_a = _candidate(frame_a)
            hit_b = _candidate(frame_b)
            candidate_a += int(hit_a)
            candidate_b += int(hit_b)
            coincident_candidates += int(hit_a and hit_b)

    correlation = _pearson(energy_a, energy_b)
    overlap = _normalized_overlap(energy_a, energy_b)
    smaller_candidate_count = min(candidate_a, candidate_b)

    return {
        "available": usable_pairs > 0,
        "track_a_id": id_a,
        "track_b_id": id_b,
        "track_a": frames_a[-1].get("track") if frames_a else None,
        "track_b": frames_b[-1].get("track") if frames_b else None,
        "binding_a": binding_a,
        "binding_b": binding_b,
        "window_seconds": seconds,
        "band_hz": [round(low_hz, 3), round(high_hz, 3)],
        "alignment_tolerance_ms": tolerance_ms,
        "aligned_pairs": len(pairs),
        "usable_band_pairs": usable_pairs,
        "mean_abs_alignment_offset_ms": None if not offsets_ms else round(sum(offsets_ms) / len(offsets_ms), 3),
        "coactive_ratio": round(both_active_pairs / len(pairs), 4),
        "band_envelope_correlation": None if correlation is None else round(correlation, 6),
        "normalized_band_temporal_overlap": None if overlap is None else round(overlap, 6),
        "temporal_descriptor_pairs": temporal_pair_count,
        "onset_candidate_frames_a": candidate_a,
        "onset_candidate_frames_b": candidate_b,
        "coincident_onset_candidate_frames": coincident_candidates,
        "candidate_coincidence_ratio": (
            None
            if smaller_candidate_count == 0
            else round(coincident_candidates / smaller_candidate_count, 4)
        ),
        "onset_candidate_thresholds": {
            "rms_rise_peak_db_gte": ONSET_CANDIDATE_RMS_RISE_DB,
            "spectral_flux_peak_gte": ONSET_CANDIDATE_SPECTRAL_FLUX,
            "logic": "OR",
        },
        "note": (
            "Envelope correlation measures co-variation, while normalized temporal overlap measures simultaneous relative "
            "band occupancy. Neither proves audible masking. Candidate coincidence is a thresholded V0.6 change-event summary."
        ),
    }
