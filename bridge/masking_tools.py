#!/usr/bin/env python3
"""Masking-evidence tools for AI Audio Analyzer MCP 0.7.

This layer does not claim to implement a validated psychoacoustic masking model.
It re-bins the Analyzer's existing 32 log-spaced FFT features onto equal ERB-rate
regions, combines relative level with V0.6 temporal co-occurrence, and exposes
transparent evidence components for LLM reasoning.

The outputs are measurement/heuristic evidence only. They do not encode mixing
style, quality judgments, or mandatory processing instructions.
"""

from __future__ import annotations

import math
from typing import Any

import project_tools as project
import server as core
import temporal_tools as temporal

ERB_BAND_COUNT = 16
DEFAULT_SECONDS = 5.0
DEFAULT_ALIGNMENT_TOLERANCE_MS = 80.0
DEFAULT_MAX_REGIONS = 8
DEFAULT_MAX_PAIRS = 8
LEVEL_DIRECTION_SCALE_DB = 6.0


def _erb_rate(frequency_hz: float) -> float:
    """Glasberg/Moore ERB-rate scale used only for feature re-binning."""
    return 21.4 * math.log10(1.0 + 0.00437 * max(0.0, frequency_hz))


def _frequency_from_erb_rate(rate: float) -> float:
    return (10.0 ** (rate / 21.4) - 1.0) / 0.00437


def _erb_edges() -> list[float]:
    low = _erb_rate(core.MIN_HZ)
    high = _erb_rate(core.MAX_HZ)
    return [
        _frequency_from_erb_rate(low + (high - low) * index / ERB_BAND_COUNT)
        for index in range(ERB_BAND_COUNT + 1)
    ]


ERB_EDGES_HZ = _erb_edges()


def _clamp_seconds(seconds: float) -> float:
    return max(0.5, min(float(seconds), 60.0))


def _mean_db(values: list[float]) -> float | None:
    finite = [float(value) for value in values if math.isfinite(float(value)) and float(value) > -120.0]
    if not finite:
        return None
    mean_power = sum(10.0 ** (value / 10.0) for value in finite) / len(finite)
    return 10.0 * math.log10(max(mean_power, 1.0e-12))


def _range_db(bands_db: list[float] | None, low_hz: float, high_hz: float) -> float | None:
    if not bands_db:
        return None
    selected = [
        float(value)
        for center, value in zip(core.BAND_CENTERS, bands_db)
        if low_hz <= float(center) < high_hz and math.isfinite(float(value))
    ]
    return _mean_db(selected)


def _auditory_bands(bands_db: list[float] | None) -> list[dict[str, Any]]:
    if not bands_db:
        return []

    result: list[dict[str, Any]] = []
    for index in range(ERB_BAND_COUNT):
        low_hz = ERB_EDGES_HZ[index]
        high_hz = ERB_EDGES_HZ[index + 1]
        centers = [
            float(center)
            for center in core.BAND_CENTERS
            if low_hz <= float(center) < high_hz
        ]
        value = _range_db(bands_db, low_hz, high_hz)
        result.append(
            {
                "index": index,
                "low_hz": round(low_hz, 2),
                "high_hz": round(high_hz, 2),
                "center_hz": round(math.sqrt(max(1.0, low_hz) * high_hz), 2),
                "energy_db": value,
                "source_feature_count": len(centers),
            }
        )
    return result


def _direction_weight(level_delta_db: float) -> float:
    """Bounded level-direction weight; not a masking threshold or probability."""
    x = float(level_delta_db) / LEVEL_DIRECTION_SCALE_DB
    if x >= 0.0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _aligned_temporal_band(
    pairs: list[tuple[dict[str, Any], dict[str, Any], float]],
    low_hz: float,
    high_hz: float,
) -> dict[str, Any]:
    values_a: list[float] = []
    values_b: list[float] = []
    both_active = 0

    for frame_a, frame_b, _offset in pairs:
        if bool(frame_a.get("signal_present")) and bool(frame_b.get("signal_present")):
            both_active += 1
        energy_a = temporal._band_energy_db(frame_a, low_hz, high_hz)
        energy_b = temporal._band_energy_db(frame_b, low_hz, high_hz)
        if energy_a is None or energy_b is None:
            continue
        values_a.append(float(energy_a))
        values_b.append(float(energy_b))

    correlation = temporal._pearson(values_a, values_b)
    overlap = temporal._normalized_overlap(values_a, values_b)
    return {
        "usable_pairs": len(values_a),
        "coactive_ratio": 0.0 if not pairs else both_active / len(pairs),
        "band_envelope_correlation": correlation,
        "normalized_band_temporal_overlap": overlap,
    }


def _build_pair_evidence(
    track_a: str,
    track_b: str,
    seconds: float,
    alignment_tolerance_ms: float,
    max_regions: int,
) -> dict[str, Any]:
    seconds = _clamp_seconds(seconds)
    tolerance_ms = max(10.0, min(float(alignment_tolerance_ms), 250.0))
    max_regions = max(1, min(int(max_regions), ERB_BAND_COUNT))

    runtime_a = core._resolve_track(track_a)
    runtime_b = core._resolve_track(track_b)
    avg_a = core.audio_average(runtime_a, seconds)
    avg_b = core.audio_average(runtime_b, seconds)

    if not bool(avg_a.get("analysis_valid", avg_a.get("signal_present"))):
        return {
            "available": False,
            "track_a_id": runtime_a,
            "track_b_id": runtime_b,
            "reason": f"{avg_a.get('track', track_a)} has no valid active-frame analysis in the requested window.",
        }
    if not bool(avg_b.get("analysis_valid", avg_b.get("signal_present"))):
        return {
            "available": False,
            "track_a_id": runtime_a,
            "track_b_id": runtime_b,
            "reason": f"{avg_b.get('track', track_b)} has no valid active-frame analysis in the requested window.",
        }

    auditory_a = _auditory_bands(avg_a.get("bands_db"))
    auditory_b = _auditory_bands(avg_b.get("bands_db"))
    if not auditory_a or not auditory_b:
        return {
            "available": False,
            "track_a_id": runtime_a,
            "track_b_id": runtime_b,
            "reason": "Auditory-band evidence requires valid 32-band spectrum data for both analyzers.",
        }

    finite_a = [float(item["energy_db"]) for item in auditory_a if item.get("energy_db") is not None]
    finite_b = [float(item["energy_db"]) for item in auditory_b if item.get("energy_db") is not None]
    if not finite_a or not finite_b:
        return {
            "available": False,
            "track_a_id": runtime_a,
            "track_b_id": runtime_b,
            "reason": "No usable auditory-band energy values were available.",
        }

    max_a = max(finite_a)
    max_b = max(finite_b)

    _id_a, frames_a, binding_a = temporal._history(runtime_a, seconds)
    _id_b, frames_b, binding_b = temporal._history(runtime_b, seconds)
    aligned = temporal._align_frames(frames_a, frames_b, tolerance_ms / 1000.0)
    offsets_ms = [abs(offset) * 1000.0 for _a, _b, offset in aligned]

    regions: list[dict[str, Any]] = []
    for band_a, band_b in zip(auditory_a, auditory_b):
        energy_a = band_a.get("energy_db")
        energy_b = band_b.get("energy_db")
        if energy_a is None or energy_b is None:
            continue

        energy_a = float(energy_a)
        energy_b = float(energy_b)
        relative_a = 10.0 ** ((energy_a - max_a) / 10.0)
        relative_b = 10.0 ** ((energy_b - max_b) / 10.0)
        spectral_overlap = min(relative_a, relative_b)
        level_delta_db = energy_a - energy_b
        direction_a_over_b = _direction_weight(level_delta_db)
        direction_b_over_a = 1.0 - direction_a_over_b

        temporal_band = _aligned_temporal_band(
            aligned,
            float(band_a["low_hz"]),
            float(band_a["high_hz"]),
        )
        temporal_overlap = temporal_band["normalized_band_temporal_overlap"]

        spectral_level_a_over_b = spectral_overlap * direction_a_over_b
        spectral_level_b_over_a = spectral_overlap * direction_b_over_a
        combined_a_over_b = (
            None
            if temporal_overlap is None
            else spectral_level_a_over_b * (0.25 + 0.75 * float(temporal_overlap))
        )
        combined_b_over_a = (
            None
            if temporal_overlap is None
            else spectral_level_b_over_a * (0.25 + 0.75 * float(temporal_overlap))
        )
        rank_score = max(
            spectral_level_a_over_b if combined_a_over_b is None else combined_a_over_b,
            spectral_level_b_over_a if combined_b_over_a is None else combined_b_over_a,
        )

        if combined_a_over_b is not None and combined_b_over_a is not None:
            dominant_direction = "a_over_b" if combined_a_over_b >= combined_b_over_a else "b_over_a"
        else:
            dominant_direction = "a_over_b" if spectral_level_a_over_b >= spectral_level_b_over_a else "b_over_a"

        regions.append(
            {
                "index": int(band_a["index"]),
                "low_hz": band_a["low_hz"],
                "high_hz": band_a["high_hz"],
                "center_hz": band_a["center_hz"],
                "source_feature_count": band_a["source_feature_count"],
                "a_db": round(energy_a, 4),
                "b_db": round(energy_b, 4),
                "level_delta_a_minus_b_db": round(level_delta_db, 4),
                "relative_spectral_overlap": round(spectral_overlap, 6),
                "level_direction_weight_a_over_b": round(direction_a_over_b, 6),
                "level_direction_weight_b_over_a": round(direction_b_over_a, 6),
                "spectral_level_evidence_a_over_b": round(spectral_level_a_over_b, 6),
                "spectral_level_evidence_b_over_a": round(spectral_level_b_over_a, 6),
                "temporal_usable_pairs": temporal_band["usable_pairs"],
                "coactive_ratio": round(float(temporal_band["coactive_ratio"]), 6),
                "band_envelope_correlation": (
                    None
                    if temporal_band["band_envelope_correlation"] is None
                    else round(float(temporal_band["band_envelope_correlation"]), 6)
                ),
                "normalized_band_temporal_overlap": (
                    None if temporal_overlap is None else round(float(temporal_overlap), 6)
                ),
                "combined_evidence_a_over_b": (
                    None if combined_a_over_b is None else round(combined_a_over_b, 6)
                ),
                "combined_evidence_b_over_a": (
                    None if combined_b_over_a is None else round(combined_b_over_a, 6)
                ),
                "dominant_direction": dominant_direction,
                "_rank_score": rank_score,
            }
        )

    regions.sort(key=lambda item: float(item["_rank_score"]), reverse=True)
    strongest = regions[:max_regions]
    for item in strongest:
        item.pop("_rank_score", None)

    top = strongest[0] if strongest else None
    summary_score = None
    if top is not None:
        values = [
            max(
                float(item.get("combined_evidence_a_over_b") or item["spectral_level_evidence_a_over_b"]),
                float(item.get("combined_evidence_b_over_a") or item["spectral_level_evidence_b_over_a"]),
            )
            for item in strongest[: min(4, len(strongest))]
        ]
        summary_score = sum(values) / len(values) if values else None

    return {
        "available": bool(strongest),
        "track_a": avg_a.get("track"),
        "track_a_id": runtime_a,
        "binding_a": binding_a,
        "track_b": avg_b.get("track"),
        "track_b_id": runtime_b,
        "binding_b": binding_b,
        "window_seconds": seconds,
        "active_ratio_a": avg_a.get("active_ratio"),
        "active_ratio_b": avg_b.get("active_ratio"),
        "auditory_band_model": {
            "type": "equal-erb-rate-rebinning",
            "band_count": ERB_BAND_COUNT,
            "source": "existing 32 log-spaced Analyzer FFT features",
            "filterbank": False,
            "note": "This is not a gammatone/cochlear filterbank and not a calibrated auditory threshold model.",
        },
        "alignment": {
            "tolerance_ms": tolerance_ms,
            "aligned_pairs": len(aligned),
            "mean_abs_offset_ms": None if not offsets_ms else round(sum(offsets_ms) / len(offsets_ms), 4),
        },
        "direction_level_scale_db": LEVEL_DIRECTION_SCALE_DB,
        "masking_evidence_score": None if summary_score is None else round(summary_score, 6),
        "strongest_regions": strongest,
        "evidence_formula": {
            "spectral_overlap": "min(relative_a_power, relative_b_power) after each track is normalized to its own strongest ERB region",
            "direction_weight": "logistic(level_delta_db / 6 dB); descriptive directional weighting, not a masking threshold",
            "spectral_level_evidence": "spectral_overlap * direction_weight",
            "combined_evidence": "spectral_level_evidence * (0.25 + 0.75 * normalized_band_temporal_overlap) when temporal overlap is available",
        },
        "note": (
            "Scores are transparent heuristic evidence, not probabilities of audible masking. "
            "Use arrangement, source role, listening context, routing, and user intent separately."
        ),
    }


@core.mcp.tool()
def audio_masking_evidence(
    track_a: str,
    track_b: str,
    seconds: float = DEFAULT_SECONDS,
    alignment_tolerance_ms: float = DEFAULT_ALIGNMENT_TOLERANCE_MS,
    max_regions: int = DEFAULT_MAX_REGIONS,
) -> dict[str, Any]:
    """Return ERB-rebinned spectral/level/temporal masking evidence for two analyzers."""
    return _build_pair_evidence(track_a, track_b, seconds, alignment_tolerance_ms, max_regions)


@core.mcp.tool()
def audio_project_masking_scan(
    seconds: float = DEFAULT_SECONDS,
    max_pairs: int = DEFAULT_MAX_PAIRS,
    alignment_tolerance_ms: float = DEFAULT_ALIGNMENT_TOLERANCE_MS,
) -> dict[str, Any]:
    """Rank project-level masking-evidence candidates from overview spectral pairs."""
    seconds = _clamp_seconds(seconds)
    max_pairs = max(1, min(int(max_pairs), 16))
    overview = project.audio_mix_overview(seconds=seconds, max_tracks=32)
    candidates = overview.get("potential_spectral_conflicts", [])[: max_pairs * 2]

    reports: list[dict[str, Any]] = []
    for candidate in candidates:
        selector_a = str(candidate["selector_a"])
        selector_b = str(candidate["selector_b"])
        report = _build_pair_evidence(
            selector_a,
            selector_b,
            seconds,
            alignment_tolerance_ms,
            max_regions=4,
        )
        if not report.get("available"):
            continue
        top = report.get("strongest_regions", [None])[0]
        reports.append(
            {
                "track_a": report.get("track_a"),
                "selector_a": selector_a,
                "track_b": report.get("track_b"),
                "selector_b": selector_b,
                "overview_spectral_overlap_score": candidate.get("spectral_overlap_score"),
                "masking_evidence_score": report.get("masking_evidence_score"),
                "top_region": top,
                "alignment": report.get("alignment"),
            }
        )

    reports.sort(
        key=lambda item: (
            -1.0 if item.get("masking_evidence_score") is None else float(item["masking_evidence_score"])
        ),
        reverse=True,
    )
    reports = reports[:max_pairs]

    return {
        "window_seconds": seconds,
        "candidate_pair_count": len(reports),
        "pairs": reports,
        "source_candidate_count": len(candidates),
        "auditory_band_model": "16 equal ERB-rate regions re-binned from the existing 32 Analyzer spectrum features",
        "note": (
            "This scan ranks evidence candidates only. It intentionally excludes a universal 'problem' threshold and "
            "does not prescribe EQ, sidechain, compression, gain, panning, or any other processing action."
        ),
    }
