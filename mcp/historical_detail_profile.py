#!/usr/bin/env python3
"""P4b historical range/Section profile builder over bounded Song Memory detail."""

from __future__ import annotations

import math
from typing import Any

import mono_compatibility_tools as mono
import range_tools as ranges
import server as core
import song_tools as song
import temporal_tools as temporal
import historical_detail_store as store

DETAIL_KEY = store.DETAIL_KEY
DETAIL_SCHEMA_VERSION = store.DETAIL_SCHEMA_VERSION
COUNT_MID_RMS = store.COUNT_MID_RMS
COUNT_SIDE_RMS = store.COUNT_SIDE_RMS
COUNT_NEGATIVE_CROSS = store.COUNT_NEGATIVE_CROSS
COUNT_LOW_CORRELATION = store.COUNT_LOW_CORRELATION
COUNT_LOW_SIDE_MID_RATIO = store.COUNT_LOW_SIDE_MID_RATIO
COUNT_LOW_BAND = store.COUNT_LOW_BAND
COUNT_STEREO_VALID = store.COUNT_STEREO_VALID
COUNT_TEMPORAL_VALID = store.COUNT_TEMPORAL_VALID
COUNT_ONSET_CANDIDATE = store.COUNT_ONSET_CANDIDATE
SUM_MID_RMS_POWER = store.SUM_MID_RMS_POWER
SUM_SIDE_RMS_POWER = store.SUM_SIDE_RMS_POWER
SUM_NEGATIVE_CROSS = store.SUM_NEGATIVE_CROSS
SUM_LOW_CORRELATION = store.SUM_LOW_CORRELATION
SUM_LOW_SIDE_MID_RATIO_POWER = store.SUM_LOW_SIDE_MID_RATIO_POWER
SUM_TEMPORAL_FLUX_WEIGHTED = store.SUM_TEMPORAL_FLUX_WEIGHTED
SUM_TEMPORAL_SECONDS = store.SUM_TEMPORAL_SECONDS
SUM_LOW_BAND_POWER = store.SUM_LOW_BAND_POWER
EXT_NEGATIVE_CROSS_MAX = store.EXT_NEGATIVE_CROSS_MAX
EXT_LOW_CORRELATION_MIN = store.EXT_LOW_CORRELATION_MIN
EXT_TEMPORAL_FLUX_PEAK_MAX = store.EXT_TEMPORAL_FLUX_PEAK_MAX
EXT_RMS_RISE_PEAK_MAX = store.EXT_RMS_RISE_PEAK_MAX
_finite = store._finite
_db_to_power = store._db_to_power
_power_to_db = store._power_to_db
_mean_db_array = store._mean_db_array
_mean_linear_array = store._mean_linear_array
_mean_ratio_array = store._mean_ratio_array
_scalar_total = store._scalar_total
_scalar_count = store._scalar_count
_extreme = store._extreme
_estimate_detail_bytes = store._estimate_detail_bytes


def _detail_rows_for_resolved(runtime_id: str, resolved: dict[str, Any]) -> list[dict[str, Any]]:
    if not resolved.get("available"):
        return []
    epoch = resolved.get("selected_transport_epoch")
    effective = resolved.get("effective_range") or {}
    if epoch is None:
        return []
    start = float(effective.get("start_seconds", 0.0))
    end = float(effective.get("end_seconds", 0.0))
    return [
        row for row in song._bins_for(runtime_id, int(epoch))
        if float(row["end_seconds"]) > start and float(row["start_seconds"]) < end
    ]


def _resolve_section_range(map_id: str | None, section_id: str) -> tuple[float, float, dict[str, Any]]:
    import section_tools as structure
    wanted = str(section_id).strip().upper()
    with structure._section_lock:
        if map_id is None:
            resolved_map_id, cached = structure._latest_cached_map()
        else:
            resolved_map_id = str(map_id)
            cached = structure._section_maps.get(resolved_map_id)
    if cached is None or resolved_map_id is None:
        raise ValueError("No matching cached section map. Call audio_section_map() first and keep its map_id.")
    section = next((item for item in cached.get("sections", []) if item.get("section_id") == wanted), None)
    if section is None:
        available = [str(item.get("section_id")) for item in cached.get("sections", []) if item.get("section_id") is not None]
        raise ValueError(f"section_id {wanted!r} is not present in map {resolved_map_id!r}; available={available}")
    start = float(section["start_seconds"])
    end = float(section["end_seconds"])
    return start, end, {
        "map_id": resolved_map_id,
        "section_id": wanted,
        "family_id": section.get("family_id"),
        "family_occurrence": section.get("family_occurrence"),
        "start_seconds": start,
        "end_seconds": end,
    }


def _resolve_requested_range(start_seconds, end_seconds, map_id, section_id):
    if section_id is not None and str(section_id).strip():
        if start_seconds is not None or end_seconds is not None:
            raise ValueError("Use either section_id/map_id or explicit start_seconds/end_seconds, not both.")
        return _resolve_section_range(map_id, str(section_id))
    if map_id is not None:
        raise ValueError("map_id requires section_id.")
    if start_seconds is None or end_seconds is None:
        raise ValueError("Provide both start_seconds and end_seconds, or provide section_id (optionally map_id).")
    return float(start_seconds), float(end_seconds), None


def _row_mid_spectrum(row: dict[str, Any]) -> list[float | None]:
    return _mean_db_array([row], "mid_power_sum", "mid_count", core.NUM_BANDS)


def _band_energy(spectrum: list[float | None], low_hz: float, high_hz: float) -> float | None:
    values = [
        float(value) for center, value in zip(core.BAND_CENTERS, spectrum)
        if value is not None and low_hz <= float(center) < high_hz
    ]
    return temporal._mean_db(values)


def _profile(track: str, start_seconds: float, end_seconds: float, minimum_coverage: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    runtime_id = core._resolve_track(str(track))
    resolved = ranges.resolve_track_range(runtime_id, start_seconds, end_seconds, minimum_coverage=minimum_coverage)
    rows = _detail_rows_for_resolved(runtime_id, resolved)
    deep_rows = [row for row in rows if isinstance(row.get(DETAIL_KEY), dict)]
    base = {
        "available": bool(resolved.get("available")),
        "detail_available": bool(deep_rows),
        "runtime_id": runtime_id,
        "selector": resolved.get("selector"),
        "display_name": resolved.get("display_name"),
        "requested_range": resolved.get("requested_range"),
        "effective_range": resolved.get("effective_range"),
        "selected_transport_epoch": resolved.get("selected_transport_epoch"),
        "coverage_ratio": resolved.get("coverage_ratio"),
        "adequate_coverage": resolved.get("adequate_coverage"),
        "minimum_coverage": resolved.get("minimum_coverage"),
        "first_received_at": resolved.get("first_received_at"),
        "last_received_at": resolved.get("last_received_at"),
        "warnings": list(resolved.get("warnings") or []),
    }
    if not resolved.get("available"):
        base["reason"] = resolved.get("reason")
        return base, rows
    if not deep_rows:
        base["reason"] = "The selected Song Memory pass has no P4b retained-detail fields. Missing deep history is unavailable, not silence."
        return base, rows

    summary = resolved.get("summary") or {}
    mid_spectrum = _mean_db_array(deep_rows, "mid_power_sum", "mid_count", core.NUM_BANDS)
    side_spectrum = _mean_db_array(deep_rows, "side_power_sum", "side_count", core.NUM_BANDS)
    band_corr = _mean_linear_array(deep_rows, "band_corr_sum", "band_corr_count", core.NUM_STEREO_CORR_BANDS)
    band_side_mid = _mean_ratio_array(
        deep_rows, "band_side_mid_ratio_power_sum", "band_side_mid_ratio_count", core.NUM_STEREO_CORR_BANDS
    )

    mid_count = _scalar_count(deep_rows, COUNT_MID_RMS)
    side_count = _scalar_count(deep_rows, COUNT_SIDE_RMS)
    mid_rms_db = _power_to_db(_scalar_total(deep_rows, SUM_MID_RMS_POWER), mid_count)
    side_rms_db = _power_to_db(_scalar_total(deep_rows, SUM_SIDE_RMS_POWER), side_count)
    neg_count = _scalar_count(deep_rows, COUNT_NEGATIVE_CROSS)
    low_corr_count = _scalar_count(deep_rows, COUNT_LOW_CORRELATION)
    low_ratio_count = _scalar_count(deep_rows, COUNT_LOW_SIDE_MID_RATIO)
    negative_mean = None if neg_count <= 0 else _scalar_total(deep_rows, SUM_NEGATIVE_CROSS) / neg_count
    low_corr_mean = None if low_corr_count <= 0 else _scalar_total(deep_rows, SUM_LOW_CORRELATION) / low_corr_count
    low_ratio_db = None
    if low_ratio_count > 0:
        ratio = _scalar_total(deep_rows, SUM_LOW_SIDE_MID_RATIO_POWER) / low_ratio_count
        if ratio > 0:
            low_ratio_db = 10.0 * math.log10(ratio)

    mono_bands = []
    for center, mid_db, side_db in zip(core.BAND_CENTERS, mid_spectrum, side_spectrum):
        if mid_db is None or side_db is None:
            mono_bands.append({
                "center_hz": round(float(center), 4), "available": False,
                "mid_db": mid_db, "side_db": side_db, "mono_fold_delta_db": None,
                "floor_censored": False, "energy_loss_fraction": None,
                "relative_band_energy": None, "inspection_priority": None,
            })
        else:
            mono_bands.append(mono._band_evidence(mid_db, side_db, center))
    mono_groups = [mono._group_summary(mono_bands, label, lo, hi) for label, lo, hi in mono._GROUPS]
    mono._finalize_group_relative_energy(mono_groups)
    mono._finalize_relative_energy(mono_bands)
    mono_shortlist = sorted(
        [{
            "center_hz": b["center_hz"], "mono_fold_delta_db": b["mono_fold_delta_db"],
            "floor_censored": b["floor_censored"], "relative_band_energy": b["relative_band_energy"],
            "energy_loss_fraction": b["energy_loss_fraction"], "inspection_priority": b["inspection_priority"],
        } for b in mono_bands if b.get("available") and b.get("inspection_priority") is not None],
        key=lambda item: float(item["inspection_priority"]), reverse=True,
    )[:8]

    stereo_power = _db_to_power(summary.get("rms_db"))
    mono_power = None if mid_rms_db is None else _db_to_power(mid_rms_db)
    full_delta = None
    floor_censored = False
    if stereo_power is not None and stereo_power > mono._POWER_FLOOR:
        mp = 0.0 if mono_power is None else mono_power
        full_delta = mono._delta_from_powers(mp, stereo_power)
        floor_censored = mp <= mono._POWER_FLOOR

    temporal_valid = _scalar_count(deep_rows, COUNT_TEMPORAL_VALID)
    temporal_seconds = _scalar_total(deep_rows, SUM_TEMPORAL_SECONDS)
    temporal_flux_mean = None if temporal_seconds <= 0 else _scalar_total(deep_rows, SUM_TEMPORAL_FLUX_WEIGHTED) / temporal_seconds
    low_band_count = _scalar_count(deep_rows, COUNT_LOW_BAND)
    low_band_db = _power_to_db(_scalar_total(deep_rows, SUM_LOW_BAND_POWER), low_band_count)
    onset_count = _scalar_count(deep_rows, COUNT_ONSET_CANDIDATE)
    deep_bytes = _estimate_detail_bytes()

    result = {
        **base,
        "detail_schema_version": DETAIL_SCHEMA_VERSION,
        "detail_row_count": len(deep_rows),
        "summary": {
            "active_ratio": summary.get("active_ratio"), "rms_db": summary.get("rms_db"),
            "lufs_s": summary.get("lufs_s"), "peak_db": summary.get("peak_db"),
            "true_peak_dbtp": summary.get("true_peak_dbtp"), "crest_db": summary.get("crest_db"),
            "centroid_hz": summary.get("centroid_hz"), "spectral_regions": summary.get("spectral_regions"),
        },
        "spectrum": {
            "representation": "Retained Analyzer 32 logarithmic Mid/Side band-center power means over observed frames in selected one-second Song Memory bins.",
            "band_centers_hz": [round(float(x), 4) for x in core.BAND_CENTERS],
            "mid_spectrum_db": mid_spectrum, "side_spectrum_db": side_spectrum,
        },
        "stereo": {
            "full_band": {
                "mid_rms_db": None if mid_rms_db is None else round(mid_rms_db, 4),
                "side_rms_db": None if side_rms_db is None else round(side_rms_db, 4),
                "side_to_mid_db": None if mid_rms_db is None or side_rms_db is None else round(side_rms_db - mid_rms_db, 4),
                "stereo_correlation_mean": summary.get("stereo_correlation"),
                "stereo_width_mean": summary.get("stereo_width"),
                "negative_cross_energy_ratio_mean": None if negative_mean is None else round(negative_mean, 6),
                "negative_cross_energy_ratio_max": _extreme(deep_rows, EXT_NEGATIVE_CROSS_MAX, "max"),
            },
            "low_band_20_120_hz": {
                "correlation_mean": None if low_corr_mean is None else round(low_corr_mean, 6),
                "correlation_min": _extreme(deep_rows, EXT_LOW_CORRELATION_MIN, "min"),
                "side_to_mid_db": None if low_ratio_db is None else round(low_ratio_db, 4),
            },
            "frequency_dependent_stereo": [
                {"range": core._stereo_corr_ranges()[i], "correlation": band_corr[i], "side_to_mid_db": band_side_mid[i]}
                for i in range(core.NUM_STEREO_CORR_BANDS)
            ],
        },
        "mono_compatibility": {
            "available": any(b.get("available") for b in mono_bands),
            "full_band": {
                "stereo_rms_db": summary.get("rms_db"),
                "mono_fold_rms_db": None if mid_rms_db is None else round(mid_rms_db, 4),
                "mono_fold_rms_delta_db": None if full_delta is None else round(full_delta, 4),
                "floor_censored": floor_censored,
            },
            "bands": mono_bands, "grouped_ranges": mono_groups, "inspection_shortlist": mono_shortlist,
            "peak_fold_down": {
                "available": False, "mono_fold_sample_peak_dbfs": None, "mono_fold_true_peak_dbtp": None,
                "reason": "P4b retains Mid/Side energy summaries, not direct historical mono-fold peak/True-Peak measurements.",
            },
        },
        "temporal": {
            "available": temporal_valid > 0,
            "resolution_boundary": "Historical temporal detail is retained per canonical one-second bin; it is not subsecond frame alignment.",
            "temporal_valid_frames": temporal_valid,
            "temporal_observed_seconds_sum": round(temporal_seconds, 4),
            "spectral_flux_mean": None if temporal_flux_mean is None else round(temporal_flux_mean, 6),
            "spectral_flux_peak": _extreme(deep_rows, EXT_TEMPORAL_FLUX_PEAK_MAX, "max"),
            "rms_rise_peak_db": _extreme(deep_rows, EXT_RMS_RISE_PEAK_MAX, "max"),
            "low_band_40_160_energy_db": None if low_band_db is None else round(low_band_db, 4),
            "onset_candidate_frames": onset_count,
            "onset_candidate_density_hz": None if temporal_seconds <= 0 else round(onset_count / temporal_seconds, 4),
        },
        "retention": {
            "same_canonical_song_memory_bins": True, "raw_audio_retained": False,
            "detail_schema_version": DETAIL_SCHEMA_VERSION,
            "estimated_container_plus_array_bytes_per_bin": deep_bytes,
            "max_bins_per_instance": song.MAX_TIMELINE_BINS_PER_INSTANCE,
            "estimated_max_detail_bytes_per_track": deep_bytes * song.MAX_TIMELINE_BINS_PER_INSTANCE,
            "note": "Interpreter-local shallow container+array estimate; allocator/key-sharing overhead varies.",
        },
    }
    return result, rows

