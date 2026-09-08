#!/usr/bin/env python3
"""P8a session-scoped reference capture and descriptive comparison.

Reference evidence is frozen from recent Analyzer receive-time windows. It is
context for an LLM, not an automatic mastering/EQ recipe. P8a intentionally
stays MCP-side and adds no realtime DSP or OSC fields.
"""

from __future__ import annotations

import copy
import math
import threading
import time
import uuid
from typing import Any

import server as core
import mono_compatibility_tools as mono
import project_tools as project

REFERENCE_SCHEMA_VERSION = 1
REFERENCE_LIMIT = 16
DEFAULT_SECONDS = 10.0
MIN_SECONDS = 0.5
MAX_SECONDS = 60.0

_reference_lock = threading.RLock()
_references: dict[str, dict[str, Any]] = {}


def _clamp_seconds(seconds: float) -> float:
    try:
        value = float(seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError("seconds must be a finite number.") from exc
    if not math.isfinite(value):
        raise ValueError("seconds must be finite.")
    return max(MIN_SECONDS, min(value, MAX_SECONDS))


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _delta(target: Any, reference: Any, digits: int = 4) -> float | None:
    target_value = _safe_float(target)
    reference_value = _safe_float(reference)
    if target_value is None or reference_value is None:
        return None
    return round(target_value - reference_value, digits)


def _bands_from_average(avg: dict[str, Any]) -> list[dict[str, Any]]:
    values = avg.get("bands_db")
    if not isinstance(values, list) or len(values) != core.NUM_BANDS:
        return []
    result: list[dict[str, Any]] = []
    for center, raw in zip(core.BAND_CENTERS, values):
        value = _safe_float(raw)
        result.append(
            {
                "center_hz": round(float(center), 4),
                "db": None if value is None else round(value, 4),
            }
        )
    return result


def _capture_profile(track: str, seconds: float) -> dict[str, Any]:
    seconds = _clamp_seconds(seconds)
    runtime_id = core._resolve_track(str(track))
    avg = project._average_for_runtime(runtime_id, seconds)
    mono_result = mono._build_result(str(track), seconds)

    mono_summary: dict[str, Any]
    if mono_result.get("available"):
        mono_summary = {
            "available": True,
            "full_band": copy.deepcopy(mono_result.get("full_band")),
            "grouped_ranges": copy.deepcopy(
                (mono_result.get("frequency") or {}).get("grouped_ranges") or []
            ),
            "peak_fold_down": copy.deepcopy(mono_result.get("peak_fold_down")),
        }
    else:
        mono_summary = {
            "available": False,
            "reason": mono_result.get("reason") or "Recent mono-fold evidence is unavailable.",
        }

    return {
        "schema_version": REFERENCE_SCHEMA_VERSION,
        "captured_at": time.time(),
        "scope": {
            "kind": "recent_receive_time_window",
            "window_seconds": seconds,
            "session_scoped": True,
            "persistent": False,
            "whole_song_claim_allowed": False,
            "historical_daw_range_supported": False,
            "section_range_supported": False,
        },
        "source": {
            "runtime_id": runtime_id,
            "runtime_id_scope": "live_plugin_instance_session_only",
            "selector": avg.get("selector"),
            "display_name": avg.get("display_name"),
            "analyzer_name": avg.get("track"),
            "binding": copy.deepcopy(avg.get("binding")),
        },
        "coverage": {
            "analysis_valid": bool(avg.get("analysis_valid", avg.get("signal_present"))),
            "signal_present": avg.get("signal_present"),
            "active_ratio": avg.get("active_ratio"),
            "frame_count": avg.get("frames"),
        },
        "energy": {
            "peak_dbfs": _safe_float(avg.get("peak_db")),
            "rms_dbfs": _safe_float(avg.get("rms_db")),
            "crest_db": _safe_float(avg.get("crest_db")),
            "lufs_s": _safe_float(avg.get("lufs_s")),
            "true_peak_dbtp": _safe_float(avg.get("true_peak_dbtp")),
        },
        "spectrum": {
            "representation": "Analyzer 32 logarithmic band-center recent-window averages.",
            "bands": _bands_from_average(avg),
            "regions": copy.deepcopy(avg.get("spectral_regions") or {}),
            "centroid_hz": _safe_float(avg.get("centroid_hz")),
        },
        "stereo": {
            "correlation": _safe_float(avg.get("stereo_correlation")),
            "width": _safe_float(avg.get("stereo_width")),
        },
        "mono_compatibility": mono_summary,
    }


def _band_map(profile: dict[str, Any]) -> dict[float, float | None]:
    result: dict[float, float | None] = {}
    for band in (profile.get("spectrum") or {}).get("bands") or []:
        center = _safe_float(band.get("center_hz"))
        if center is None:
            continue
        result[center] = _safe_float(band.get("db"))
    return result


def _spectral_comparison(reference: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    ref_bands = _band_map(reference)
    target_bands = _band_map(target)
    shared_centers = sorted(set(ref_bands) & set(target_bands))

    ref_rms = _safe_float((reference.get("energy") or {}).get("rms_dbfs"))
    target_rms = _safe_float((target.get("energy") or {}).get("rms_dbfs"))
    gain_to_reference = None
    if ref_rms is not None and target_rms is not None:
        gain_to_reference = ref_rms - target_rms

    absolute_bands: list[dict[str, Any]] = []
    normalized_bands: list[dict[str, Any]] = []
    for center in shared_centers:
        ref_value = ref_bands[center]
        target_value = target_bands[center]
        absolute = _delta(target_value, ref_value)
        normalized = None
        if gain_to_reference is not None and target_value is not None and ref_value is not None:
            normalized = round((target_value + gain_to_reference) - ref_value, 4)
        absolute_bands.append(
            {
                "center_hz": round(center, 4),
                "target_minus_reference_db": absolute,
            }
        )
        normalized_bands.append(
            {
                "center_hz": round(center, 4),
                "level_normalized_target_minus_reference_db": normalized,
            }
        )

    ref_regions = (reference.get("spectrum") or {}).get("regions") or {}
    target_regions = (target.get("spectrum") or {}).get("regions") or {}
    region_names = sorted(set(ref_regions) | set(target_regions))
    absolute_regions: dict[str, float | None] = {}
    normalized_regions: dict[str, float | None] = {}
    for name in region_names:
        ref_value = _safe_float(ref_regions.get(name))
        target_value = _safe_float(target_regions.get(name))
        absolute_regions[name] = _delta(target_value, ref_value)
        if gain_to_reference is None or ref_value is None or target_value is None:
            normalized_regions[name] = None
        else:
            normalized_regions[name] = round((target_value + gain_to_reference) - ref_value, 4)

    return {
        "absolute": {
            "bands": absolute_bands,
            "regions_db": absolute_regions,
            "centroid_hz": _delta(
                (target.get("spectrum") or {}).get("centroid_hz"),
                (reference.get("spectrum") or {}).get("centroid_hz"),
                2,
            ),
        },
        "level_normalized": {
            "available": gain_to_reference is not None,
            "anchor": "RMS dBFS",
            "target_gain_to_reference_db": None if gain_to_reference is None else round(gain_to_reference, 4),
            "bands": normalized_bands,
            "regions_db": normalized_regions,
            "formula": "(target band + reference_rms - target_rms) - reference band",
            "note": "Normalization removes one broad level offset so spectral-shape differences remain visible; it is not a processing instruction.",
        },
    }


def _mono_groups(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mono_profile = profile.get("mono_compatibility") or {}
    if not mono_profile.get("available"):
        return {}
    return {
        str(group.get("range")): group
        for group in mono_profile.get("grouped_ranges") or []
        if group.get("range") is not None
    }


def _mono_comparison(reference: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    ref_mono = reference.get("mono_compatibility") or {}
    target_mono = target.get("mono_compatibility") or {}
    if not (ref_mono.get("available") and target_mono.get("available")):
        return {
            "available": False,
            "reason": "Direct mono-fold evidence is unavailable on one or both sides of this comparison.",
        }

    ref_full = ref_mono.get("full_band") or {}
    target_full = target_mono.get("full_band") or {}
    ref_groups = _mono_groups(reference)
    target_groups = _mono_groups(target)
    shared = sorted(set(ref_groups) & set(target_groups))
    return {
        "available": True,
        "full_band": {
            "mono_fold_rms_delta_db_target_minus_reference": _delta(
                target_full.get("mono_fold_rms_delta_db"),
                ref_full.get("mono_fold_rms_delta_db"),
            ),
            "target_floor_censored": bool(target_full.get("floor_censored")),
            "reference_floor_censored": bool(ref_full.get("floor_censored")),
        },
        "grouped_ranges": [
            {
                "range": name,
                "mono_fold_delta_db_target_minus_reference": _delta(
                    target_groups[name].get("mono_fold_delta_db"),
                    ref_groups[name].get("mono_fold_delta_db"),
                ),
                "target_floor_censored": bool(target_groups[name].get("floor_censored")),
                "reference_floor_censored": bool(ref_groups[name].get("floor_censored")),
            }
            for name in shared
        ],
        "note": "Mono-fold deltas remain independent compatibility evidence, not a stereo-quality score or automatic widening/narrowing instruction.",
    }


def _compare_profiles(reference: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    ref_energy = reference.get("energy") or {}
    target_energy = target.get("energy") or {}
    spectral = _spectral_comparison(reference, target)

    common_features = {
        "energy": any(_safe_float(ref_energy.get(key)) is not None and _safe_float(target_energy.get(key)) is not None for key in ("rms_dbfs", "crest_db", "lufs_s", "peak_dbfs", "true_peak_dbtp")),
        "spectrum": bool((spectral.get("absolute") or {}).get("bands")),
        "stereo": any(
            _safe_float((reference.get("stereo") or {}).get(key)) is not None
            and _safe_float((target.get("stereo") or {}).get(key)) is not None
            for key in ("correlation", "width")
        ),
        "mono_compatibility": bool(
            (reference.get("mono_compatibility") or {}).get("available")
            and (target.get("mono_compatibility") or {}).get("available")
        ),
    }

    return {
        "comparability": {
            "reference_analysis_valid": bool((reference.get("coverage") or {}).get("analysis_valid")),
            "target_analysis_valid": bool((target.get("coverage") or {}).get("analysis_valid")),
            "common_features": common_features,
            "same_section_or_song_assumed": False,
            "note": "P8a compares user-chosen sources descriptively. It never assumes two unrelated songs/sections are semantically equivalent.",
        },
        "energy": {
            "direction": "target_minus_reference",
            "rms_db": _delta(target_energy.get("rms_dbfs"), ref_energy.get("rms_dbfs")),
            "crest_db": _delta(target_energy.get("crest_db"), ref_energy.get("crest_db")),
            "lufs_s_lu": _delta(target_energy.get("lufs_s"), ref_energy.get("lufs_s")),
            "sample_peak_db": _delta(target_energy.get("peak_dbfs"), ref_energy.get("peak_dbfs")),
            "true_peak_db": _delta(target_energy.get("true_peak_dbtp"), ref_energy.get("true_peak_dbtp")),
        },
        "spectrum": spectral,
        "stereo": {
            "direction": "target_minus_reference",
            "correlation": _delta(
                (target.get("stereo") or {}).get("correlation"),
                (reference.get("stereo") or {}).get("correlation"),
            ),
            "width": _delta(
                (target.get("stereo") or {}).get("width"),
                (reference.get("stereo") or {}).get("width"),
            ),
        },
        "mono_compatibility": _mono_comparison(reference, target),
        "interpretation_boundary": {
            "reference_is_context_not_target": True,
            "automatic_eq_match": False,
            "automatic_master_match": False,
            "quality_score": None,
            "processing_recommendation": None,
            "note": "A difference from the reference is not automatically a defect. User intent, musical role, arrangement, translation needs and style remain LLM/context decisions.",
        },
    }


def _reference_summary(reference_id: str, item: dict[str, Any]) -> dict[str, Any]:
    profile = item["profile"]
    return {
        "reference_id": reference_id,
        "label": item["label"],
        "captured_at": profile.get("captured_at"),
        "source": copy.deepcopy(profile.get("source")),
        "scope": copy.deepcopy(profile.get("scope")),
        "analysis_valid": bool((profile.get("coverage") or {}).get("analysis_valid")),
    }


@core.mcp.tool()
def audio_capture_reference(track: str, label: str = "", seconds: float = DEFAULT_SECONDS) -> dict[str, Any]:
    """Freeze one session-scoped recent Analyzer profile as a named reference; this captures evidence only and does not copy audio or change the DAW."""
    profile = _capture_profile(track, seconds)
    clean_label = str(label).strip()
    if len(clean_label) > 96:
        raise ValueError("Reference label must be 96 characters or fewer.")
    if not clean_label:
        clean_label = str((profile.get("source") or {}).get("display_name") or "Reference")

    reference_id = f"ref_{uuid.uuid4().hex[:12]}"
    with _reference_lock:
        _references[reference_id] = {
            "label": clean_label,
            "profile": copy.deepcopy(profile),
        }
        while len(_references) > REFERENCE_LIMIT:
            oldest = next(iter(_references))
            del _references[oldest]

    return {
        "ok": True,
        "reference": _reference_summary(reference_id, {"label": clean_label, "profile": profile}),
        "feature_availability": {
            "spectrum_32_band": bool((profile.get("spectrum") or {}).get("bands")),
            "mono_compatibility": bool((profile.get("mono_compatibility") or {}).get("available")),
            "retained_dynamics_distribution": False,
        },
        "warnings": [
            "P8a references are MCP-session scoped and disappear when the MCP process exits.",
            "P8a recent-window capture does not prove whole-song coverage and does not retain copyrighted source audio.",
            "Historical Section/reference ranges and persistent libraries are future P4b/P5/P10 integration work.",
        ],
    }


@core.mcp.tool()
def audio_list_references() -> dict[str, Any]:
    """List frozen P8a session references and their capture provenance without returning full profile payloads."""
    with _reference_lock:
        items = [
            _reference_summary(reference_id, copy.deepcopy(item))
            for reference_id, item in _references.items()
        ]
    return {
        "schema_version": REFERENCE_SCHEMA_VERSION,
        "session_scoped": True,
        "persistent": False,
        "reference_limit": REFERENCE_LIMIT,
        "count": len(items),
        "references": items,
    }


@core.mcp.tool()
def audio_compare_reference(reference_id: str, target: str, seconds: float | None = None) -> dict[str, Any]:
    """Compare a current target window against one frozen P8a reference using absolute and RMS-level-normalized descriptive evidence; never emit an automatic matching recipe."""
    key = str(reference_id).strip()
    with _reference_lock:
        item = copy.deepcopy(_references.get(key))
    if item is None:
        raise ValueError(f"Unknown reference_id {key!r}. Use audio_list_references() first.")

    reference = item["profile"]
    reference_seconds = float((reference.get("scope") or {}).get("window_seconds") or DEFAULT_SECONDS)
    target_seconds = reference_seconds if seconds is None else _clamp_seconds(seconds)
    target_profile = _capture_profile(target, target_seconds)
    comparison = _compare_profiles(reference, target_profile)

    return {
        "reference": _reference_summary(key, item),
        "target": {
            "captured_at": target_profile.get("captured_at"),
            "source": copy.deepcopy(target_profile.get("source")),
            "scope": copy.deepcopy(target_profile.get("scope")),
            "analysis_valid": bool((target_profile.get("coverage") or {}).get("analysis_valid")),
        },
        **comparison,
        "provenance": {
            "reference_frozen": True,
            "reference_capture_scope": "recent_receive_time_window",
            "target_capture_scope": "recent_receive_time_window",
            "reference_audio_stored": False,
            "session_persistent": False,
        },
        "warnings": [
            "Do not interpret target-minus-reference deltas as automatic defects or parameter changes.",
            "RMS level normalization is an explicit comparison view only; it does not change either source.",
            "P8a does not silently map section labels or musical roles across unrelated songs.",
        ],
    }
