#!/usr/bin/env python3
"""Coverage-aware retained dynamics distributions for AI Audio Analyzer MCP.

P6a is intentionally MCP-side. It reuses transport-aligned one-second Song
Memory and the P4 range resolver; no percentile work belongs in the realtime
VST3 callback and no new OSC fields are required.

These statistics are descriptive distributions over retained observations.
They are not standardized EBU LRA, arbitrary-range integrated LUFS, or PLR.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import server as core
import range_tools as ranges
import section_tools as structure
import song_tools as song

DEFAULT_MINIMUM_RANGE_COVERAGE = ranges.DEFAULT_MINIMUM_COVERAGE
DEFAULT_MINIMUM_BIN_COVERAGE = 0.5


def _safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _clamp_coverage(value: float, *, name: str, minimum: float = 0.1) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number.") from exc
    if not math.isfinite(numeric):
        raise ValueError(f"{name} must be finite.")
    return max(minimum, min(numeric, 1.0))


def _weighted_percentile(observations: list[tuple[float, float]], q: float) -> float | None:
    """Weighted percentile using interpolation between weighted bin midpoints."""
    pairs = sorted(
        (float(value), float(weight))
        for value, weight in observations
        if math.isfinite(float(value)) and math.isfinite(float(weight)) and float(weight) > 0.0
    )
    if not pairs:
        return None
    if len(pairs) == 1:
        return pairs[0][0]

    total = sum(weight for _value, weight in pairs)
    if total <= 0.0:
        return None
    target = max(0.0, min(float(q), 1.0))
    points: list[tuple[float, float]] = []
    cumulative = 0.0
    for value, weight in pairs:
        points.append(((cumulative + 0.5 * weight) / total, value))
        cumulative += weight

    if target <= points[0][0]:
        return points[0][1]
    if target >= points[-1][0]:
        return points[-1][1]
    for (left_pos, left_value), (right_pos, right_value) in zip(points, points[1:]):
        if left_pos <= target <= right_pos:
            if right_pos <= left_pos:
                return right_value
            fraction = (target - left_pos) / (right_pos - left_pos)
            return left_value * (1.0 - fraction) + right_value * fraction
    return points[-1][1]


def _weighted_arithmetic_mean(observations: list[tuple[float, float]]) -> float | None:
    total_weight = sum(weight for _value, weight in observations if weight > 0.0)
    if total_weight <= 0.0:
        return None
    return sum(value * weight for value, weight in observations if weight > 0.0) / total_weight


def _weighted_power_mean_db(observations: list[tuple[float, float]]) -> float | None:
    total_weight = sum(weight for _value, weight in observations if weight > 0.0)
    if total_weight <= 0.0:
        return None
    power = sum((10.0 ** (value / 10.0)) * weight for value, weight in observations if weight > 0.0)
    if power <= 0.0:
        return None
    return 10.0 * math.log10(max(power / total_weight, 1.0e-12))


def _distribution(
    observations: list[tuple[float, float]],
    *,
    unit: str,
    include_power_mean: bool = False,
) -> dict[str, Any]:
    clean = [
        (float(value), float(weight))
        for value, weight in observations
        if math.isfinite(float(value)) and math.isfinite(float(weight)) and float(weight) > 0.0
    ]
    if not clean:
        return {
            "available": False,
            "unit": unit,
            "observation_count": 0,
            "covered_seconds_weight": 0.0,
            "reason": "No accepted retained bin contains this measurement family.",
        }

    values = [value for value, _weight in clean]
    percentiles = {
        name: _weighted_percentile(clean, q)
        for name, q in (("p10", 0.10), ("p25", 0.25), ("p50", 0.50), ("p75", 0.75), ("p90", 0.90))
    }
    rounded = {key: None if value is None else round(float(value), 4) for key, value in percentiles.items()}
    p25 = percentiles["p25"]
    p75 = percentiles["p75"]
    p10 = percentiles["p10"]
    p90 = percentiles["p90"]
    result: dict[str, Any] = {
        "available": True,
        "unit": unit,
        "observation_count": len(clean),
        "covered_seconds_weight": round(sum(weight for _value, weight in clean), 3),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        **rounded,
        "iqr": None if p25 is None or p75 is None else round(float(p75 - p25), 4),
        "p90_minus_p10": None if p10 is None or p90 is None else round(float(p90 - p10), 4),
        "weighted_arithmetic_mean": None,
    }
    arithmetic = _weighted_arithmetic_mean(clean)
    result["weighted_arithmetic_mean"] = None if arithmetic is None else round(arithmetic, 4)
    if include_power_mean:
        power_mean = _weighted_power_mean_db(clean)
        result["covered_seconds_power_mean_db"] = None if power_mean is None else round(power_mean, 4)
    return result


def _exact_epoch_range(
    runtime_id: str,
    transport_epoch: int,
    start_seconds: float,
    end_seconds: float,
    minimum_range_coverage: float,
) -> dict[str, Any]:
    """Honor a caller-specified local epoch without inventing another selector."""
    normalized = ranges.normalize_range(start_seconds, end_seconds)
    effective = normalized["effective_range"]
    start = float(effective["start_seconds"])
    end = float(effective["end_seconds"])
    rows = [
        row
        for row in song._bins_for(runtime_id, int(transport_epoch))
        if float(row["end_seconds"]) > start and float(row["start_seconds"]) < end
    ]
    if not rows:
        return {
            "available": False,
            "runtime_id": runtime_id,
            **normalized,
            "requested_transport_epoch": int(transport_epoch),
            "reason": "The requested instance-local transport epoch has no retained bins overlapping the effective range.",
        }
    expected = end - start
    summary = song._finalize_rows(rows, start_seconds=start, end_seconds=end, expected_seconds=expected)
    coverage = float((summary.get("data_quality") or {}).get("coverage_ratio") or 0.0)
    return {
        "available": True,
        "adequate_coverage": coverage >= minimum_range_coverage,
        "runtime_id": runtime_id,
        **normalized,
        "minimum_coverage": minimum_range_coverage,
        "selected_transport_epoch": int(transport_epoch),
        "coverage_ratio": round(coverage, 4),
        "first_received_at": min(float(row["first_received_at"]) for row in rows),
        "last_received_at": max(float(row["last_received_at"]) for row in rows),
        "summary": summary,
        "warnings": [] if coverage >= minimum_range_coverage else [
            f"Requested transport epoch covers only {coverage:.3f} of the effective range; minimum requested coverage is {minimum_range_coverage:.3f}."
        ],
        "selection_semantics": "Caller supplied one instance-local transport epoch explicitly; no cross-track epoch identity is implied.",
    }


def _section_range(section_id: str, map_id: str | None) -> dict[str, Any]:
    section_key = str(section_id).strip().upper()
    with structure._section_lock:
        if map_id is None:
            resolved_map_id, cached = structure._latest_cached_map()
        else:
            resolved_map_id = str(map_id)
            cached = structure._section_maps.get(resolved_map_id)
        cached_copy = None if cached is None else copy.deepcopy(cached)
    if cached_copy is None or resolved_map_id is None:
        return {
            "available": False,
            "reason": "No matching cached Section Map. Call audio_section_map() first and keep its map_id for deterministic follow-up.",
        }
    section = next(
        (item for item in cached_copy.get("sections", []) if str(item.get("section_id", "")).upper() == section_key),
        None,
    )
    if section is None:
        return {
            "available": False,
            "map_id": resolved_map_id,
            "requested_section_id": section_key,
            "available_section_ids": [item.get("section_id") for item in cached_copy.get("sections", [])],
            "reason": "Requested section_id is not present in the cached Section Map.",
        }
    return {
        "available": True,
        "map_id": resolved_map_id,
        "section_id": section_key,
        "family_id": section.get("family_id"),
        "start_seconds": float(section["start_seconds"]),
        "end_seconds": float(section["end_seconds"]),
    }


def _scope_request(
    runtime_id: str,
    *,
    transport_epoch: int | None,
    start_seconds: float | None,
    end_seconds: float | None,
    map_id: str | None,
    section_id: str | None,
    minimum_range_coverage: float,
) -> dict[str, Any]:
    if section_id is not None and str(section_id).strip():
        if start_seconds is not None or end_seconds is not None:
            raise ValueError("section_id cannot be combined with start_seconds/end_seconds.")
        section = _section_range(str(section_id), map_id)
        if not section.get("available"):
            return section
        start = float(section["start_seconds"])
        end = float(section["end_seconds"])
        scope_kind = "section_range"
        section_meta = {
            "map_id": section["map_id"],
            "section_id": section["section_id"],
            "family_id": section.get("family_id"),
        }
    elif start_seconds is not None or end_seconds is not None:
        if start_seconds is None or end_seconds is None:
            raise ValueError("start_seconds and end_seconds must be supplied together.")
        start = float(start_seconds)
        end = float(end_seconds)
        scope_kind = "explicit_range"
        section_meta = {}
    else:
        epochs = song._available_epochs(runtime_id)
        if not epochs:
            return {
                "available": False,
                "reason": "No transport-aligned Song Memory is retained for this Analyzer instance.",
            }
        selected_epoch = epochs[-1] if transport_epoch is None else int(transport_epoch)
        rows = song._bins_for(runtime_id, selected_epoch)
        if not rows:
            return {
                "available": False,
                "requested_transport_epoch": selected_epoch,
                "available_epochs": epochs[-12:],
                "reason": "The requested instance-local transport epoch is not retained.",
            }
        start = min(float(row["start_seconds"]) for row in rows)
        end = max(float(row["end_seconds"]) for row in rows)
        scope_kind = "selected_pass_span"
        section_meta = {}
        transport_epoch = selected_epoch

    if transport_epoch is None:
        resolved = ranges.resolve_track_range(
            runtime_id,
            start,
            end,
            minimum_coverage=minimum_range_coverage,
        )
    else:
        resolved = _exact_epoch_range(
            runtime_id,
            int(transport_epoch),
            start,
            end,
            minimum_range_coverage,
        )
    return {
        "available": bool(resolved.get("available")),
        "scope_kind": scope_kind,
        "section_meta": section_meta,
        "resolved": resolved,
        "reason": resolved.get("reason"),
    }


def _row_observation(row: dict[str, Any]) -> dict[str, Any]:
    summary = song._finalize_rows(
        [row],
        start_seconds=float(row["start_seconds"]),
        end_seconds=float(row["end_seconds"]),
        expected_seconds=song.TIMELINE_BIN_SECONDS,
    )
    covered_seconds = song._covered_seconds(row)
    return {
        "bin_index": int(row["bin_index"]),
        "start_seconds": float(row["start_seconds"]),
        "end_seconds": float(row["end_seconds"]),
        "covered_seconds": covered_seconds,
        "coverage_ratio": covered_seconds / song.TIMELINE_BIN_SECONDS,
        "rms_db": _safe_float(summary.get("rms_db")),
        "lufs_s": _safe_float(summary.get("lufs_s")),
        "crest_db": _safe_float(summary.get("crest_db")),
        "peak_db": _safe_float(summary.get("peak_db")),
        "true_peak_dbtp": _safe_float(summary.get("true_peak_dbtp")),
    }


def _metric_observations(rows: list[dict[str, Any]], field: str) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for item in rows:
        value = _safe_float(item.get(field))
        weight = _safe_float(item.get("covered_seconds"))
        if value is not None and weight is not None and weight > 0.0:
            result.append((value, weight))
    return result


def _build_distribution(
    track: str,
    *,
    transport_epoch: int | None,
    start_seconds: float | None,
    end_seconds: float | None,
    map_id: str | None,
    section_id: str | None,
    minimum_range_coverage: float,
    minimum_bin_coverage: float,
) -> dict[str, Any]:
    runtime_id = core._resolve_track(str(track))
    request = _scope_request(
        runtime_id,
        transport_epoch=transport_epoch,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        map_id=map_id,
        section_id=section_id,
        minimum_range_coverage=minimum_range_coverage,
    )
    if not request.get("available"):
        return {
            "available": False,
            "runtime_id": runtime_id,
            "selector": song._binding_selector(runtime_id),
            "display_name": song._display_name(runtime_id),
            "reason": request.get("reason") or "Requested retained dynamics scope is unavailable.",
            **{key: value for key, value in request.items() if key not in {"available", "resolved", "reason"}},
        }

    resolved = request["resolved"]
    effective = resolved["effective_range"]
    effective_start = float(effective["start_seconds"])
    effective_end = float(effective["end_seconds"])
    epoch = int(resolved["selected_transport_epoch"])
    raw_rows = [
        row
        for row in song._bins_for(runtime_id, epoch)
        if float(row["end_seconds"]) > effective_start and float(row["start_seconds"]) < effective_end
    ]
    observations = [_row_observation(row) for row in raw_rows]
    accepted = [item for item in observations if float(item["coverage_ratio"]) >= minimum_bin_coverage]
    rejected = [item for item in observations if float(item["coverage_ratio"]) < minimum_bin_coverage]

    expected_bins = max(1, int(round((effective_end - effective_start) / song.TIMELINE_BIN_SECONDS)))
    missing_bins = max(0, expected_bins - len(observations))
    covered_seconds = sum(float(item["covered_seconds"]) for item in observations)
    accepted_covered_seconds = sum(float(item["covered_seconds"]) for item in accepted)

    rms = _distribution(_metric_observations(accepted, "rms_db"), unit="dBFS", include_power_mean=True)
    lufs_s = _distribution(_metric_observations(accepted, "lufs_s"), unit="LUFS")
    crest = _distribution(_metric_observations(accepted, "crest_db"), unit="dB")
    peak = _distribution(_metric_observations(accepted, "peak_db"), unit="dBFS")
    true_peak = _distribution(_metric_observations(accepted, "true_peak_dbtp"), unit="dBTP")

    range_coverage = float(resolved.get("coverage_ratio") or 0.0)
    scope_kind = str(request["scope_kind"])
    if scope_kind == "selected_pass_span":
        completeness = "full_pass_coverage" if range_coverage >= minimum_range_coverage else "partial_pass_coverage"
    elif scope_kind == "section_range":
        completeness = "section_range_only"
    else:
        completeness = "explicit_range_only"

    warnings = list(resolved.get("warnings") or [])
    if rejected:
        warnings.append(
            f"Rejected {len(rejected)} retained one-second bin(s) below the per-bin coverage floor {minimum_bin_coverage:.2f}."
        )
    if missing_bins:
        warnings.append(f"{missing_bins} expected retained one-second bin(s) are missing; missing coverage is not treated as silence or zero.")
    if not lufs_s.get("available"):
        warnings.append("No accepted retained LUFS-S observations are available; the historical Loudness feature may have been unavailable/disabled for this scope.")
    if scope_kind == "selected_pass_span":
        warnings.append("full_pass_coverage refers only to the retained selected-pass span; it does not prove authoritative whole-song coverage.")

    return {
        "available": True,
        "runtime_id": runtime_id,
        "selector": song._binding_selector(runtime_id),
        "display_name": song._display_name(runtime_id),
        "scope": {
            "kind": scope_kind,
            "completeness": completeness,
            "historical_distribution": True,
            "whole_song_claim_allowed": False,
            "requested_range": resolved.get("requested_range"),
            "effective_range": resolved.get("effective_range"),
            "range_resolution_seconds": resolved.get("resolution_seconds"),
            "range_normalized": resolved.get("normalized"),
            "selected_transport_epoch": epoch,
            **request.get("section_meta", {}),
        },
        "coverage": {
            "minimum_range_coverage": minimum_range_coverage,
            "range_coverage_ratio": round(range_coverage, 4),
            "covered_seconds": round(covered_seconds, 3),
            "minimum_bin_coverage": minimum_bin_coverage,
            "accepted_bin_count": len(accepted),
            "accepted_covered_seconds": round(accepted_covered_seconds, 3),
            "rejected_low_coverage_bin_count": len(rejected),
            "missing_bin_count": missing_bins,
            "expected_bin_count": expected_bins,
            "weighting_policy": "Accept retained one-second bins at or above minimum_bin_coverage; weight accepted observations by observed covered seconds from 100 ms coverage slots.",
        },
        "energy_distribution": {
            "rms_db": rms,
            "note": "Percentiles operate on retained per-bin RMS dB observations. covered_seconds_power_mean_db is a separate energy-domain mean and is not the same statistic as a dB percentile.",
        },
        "loudness_short_term_distribution": {
            "lufs_s": lufs_s,
            "lufs_s_interpercentile_range_lu": lufs_s.get("p90_minus_p10") if lufs_s.get("available") else None,
            "interpercentile_definition": "P90(LUFS-S) - P10(LUFS-S) over accepted retained one-second observations.",
            "note": "This is descriptive LUFS-S distribution evidence, not EBU Loudness Range and not arbitrary-range integrated loudness.",
        },
        "dynamics_distribution": {
            "crest_db": crest,
        },
        "peak_distribution": {
            "sample_peak_dbfs": peak,
            "true_peak_dbtp": true_peak,
            "note": "These are distributions of observed per-bin maxima, not a reconstructed sample stream.",
        },
        "standardized_metrics": {
            "ebu_lra_lu": {
                "available": False,
                "value": None,
                "reason": "P6a does not implement the standardized gated EBU Loudness Range algorithm. LUFS-S interpercentile spread is kept separate.",
            },
            "range_integrated_lufs": {
                "available": False,
                "value": None,
                "reason": "Retained protocol-1.2 LUFS-I is transport-pass cumulative, not isolated to an arbitrary retained range.",
            },
            "plr_db": {
                "available": False,
                "value": None,
                "reason": "A scope-compatible peak-to-loudness relation is not derived for arbitrary retained ranges in P6a.",
            },
        },
        "warnings": warnings,
        "semantics": {
            "percentiles": "Coverage-weighted descriptive percentiles over accepted one-second retained observations; values are not inserted for missing bins.",
            "db_weighting": "Covered seconds are statistical weights. dB-valued percentiles remain dB percentiles; power-domain means are explicitly separate fields.",
            "transport_epoch": "Instance-local playback pass. Equal epoch numbers across Analyzer instances do not imply the same project/pass identity.",
            "quality": "No universal dynamics/mastering quality score or fixed genre/loudness target is produced.",
        },
    }


def _delta(compare_value: Any, primary_value: Any) -> float | None:
    a = _safe_float(compare_value)
    b = _safe_float(primary_value)
    return None if a is None or b is None else round(a - b, 4)


def _section_comparison(primary: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    p_rms = primary.get("energy_distribution", {}).get("rms_db", {})
    c_rms = comparison.get("energy_distribution", {}).get("rms_db", {})
    p_lufs = primary.get("loudness_short_term_distribution", {}).get("lufs_s", {})
    c_lufs = comparison.get("loudness_short_term_distribution", {}).get("lufs_s", {})
    p_crest = primary.get("dynamics_distribution", {}).get("crest_db", {})
    c_crest = comparison.get("dynamics_distribution", {}).get("crest_db", {})
    p_peak = primary.get("peak_distribution", {}).get("sample_peak_dbfs", {})
    c_peak = comparison.get("peak_distribution", {}).get("sample_peak_dbfs", {})
    return {
        "available": bool(primary.get("available") and comparison.get("available")),
        "direction": "comparison_minus_primary",
        "primary_section_id": primary.get("scope", {}).get("section_id"),
        "comparison_section_id": comparison.get("scope", {}).get("section_id"),
        "deltas": {
            "median_rms_db": _delta(c_rms.get("p50"), p_rms.get("p50")),
            "median_lufs_s_lu": _delta(c_lufs.get("p50"), p_lufs.get("p50")),
            "crest_p50_db": _delta(c_crest.get("p50"), p_crest.get("p50")),
            "crest_p90_db": _delta(c_crest.get("p90"), p_crest.get("p90")),
            "sample_peak_p50_db": _delta(c_peak.get("p50"), p_peak.get("p50")),
            "rms_p90_p10_spread_db": _delta(c_rms.get("p90_minus_p10"), p_rms.get("p90_minus_p10")),
            "lufs_s_p90_p10_spread_lu": _delta(c_lufs.get("p90_minus_p10"), p_lufs.get("p90_minus_p10")),
        },
        "note": "Descriptive section-to-section distribution shifts only. Positive/negative deltas are not a dynamics quality score or processing recommendation.",
    }


@core.mcp.tool()
def audio_dynamics_distribution(
    track: str,
    transport_epoch: int | None = None,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    map_id: str | None = None,
    section_id: str | None = None,
    compare_section_id: str | None = None,
    minimum_range_coverage: float = DEFAULT_MINIMUM_RANGE_COVERAGE,
    minimum_bin_coverage: float = DEFAULT_MINIMUM_BIN_COVERAGE,
) -> dict[str, Any]:
    """Return coverage-weighted retained dynamics distributions for a pass, DAW range or cached section; optionally compare two sections without claiming standardized LRA/PLR."""
    minimum_range = _clamp_coverage(
        minimum_range_coverage,
        name="minimum_range_coverage",
        minimum=0.1,
    )
    minimum_bin = _clamp_coverage(
        minimum_bin_coverage,
        name="minimum_bin_coverage",
        minimum=0.1,
    )
    if compare_section_id is not None and str(compare_section_id).strip() and not (section_id is not None and str(section_id).strip()):
        raise ValueError("compare_section_id requires section_id so the comparison scope is unambiguous.")

    primary = _build_distribution(
        track,
        transport_epoch=transport_epoch,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        map_id=map_id,
        section_id=section_id,
        minimum_range_coverage=minimum_range,
        minimum_bin_coverage=minimum_bin,
    )
    if not primary.get("available") or compare_section_id is None or not str(compare_section_id).strip():
        return primary

    resolved_map_id = primary.get("scope", {}).get("map_id") or map_id
    comparison = _build_distribution(
        track,
        transport_epoch=transport_epoch,
        start_seconds=None,
        end_seconds=None,
        map_id=resolved_map_id,
        section_id=str(compare_section_id),
        minimum_range_coverage=minimum_range,
        minimum_bin_coverage=minimum_bin,
    )
    return {
        **primary,
        "comparison_scope": comparison,
        "section_comparison": _section_comparison(primary, comparison),
    }
