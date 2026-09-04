#!/usr/bin/env python3
"""Section-aware per-track story summaries built on cached Song Structure.

Track Story is an MCP reasoning layer, not realtime DSP. It reuses retained
Song Memory and neutral section/family maps to describe how one Analyzer
instance changes across the song. It does not infer a musical role, prescribe
processing, or reinterpret missing coverage as inactivity.
"""

from __future__ import annotations

import math
from itertools import combinations
from typing import Any

import server as core
import section_tools as structure
import song_tools as song

MIN_STORY_COVERAGE = structure.MIN_POINT_COVERAGE
PITCH_CLASSES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
SCALAR_METRICS = (
    "active_ratio",
    "rms_db",
    "lufs_s",
    "crest_db",
    "centroid_hz",
    "stereo_correlation",
    "stereo_width",
    "spectral_flux_mean",
)


def _safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _round_optional(value: Any, digits: int = 4) -> float | None:
    numeric = _safe_float(value)
    return None if numeric is None else round(numeric, digits)


def _stats(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    ordered = [float(value) for value in values]
    minimum = min(ordered)
    maximum = max(ordered)
    return {
        "mean": round(sum(ordered) / len(ordered), 5),
        "min": round(minimum, 5),
        "max": round(maximum, 5),
        "spread": round(maximum - minimum, 5),
    }


def _top_chroma(chroma: Any, count: int = 3) -> list[dict[str, Any]]:
    if not isinstance(chroma, list) or len(chroma) != 12:
        return []
    parsed = [_safe_float(value) for value in chroma]
    if any(value is None or value < 0.0 for value in parsed):
        return []
    total = sum(float(value) for value in parsed)
    if total <= 1.0e-12:
        return []
    ranked = sorted(
        ((index, float(value) / total) for index, value in enumerate(parsed)),
        key=lambda item: item[1],
        reverse=True,
    )
    return [
        {"pitch_class": PITCH_CLASSES[index], "weight": round(weight, 5)}
        for index, weight in ranked[:max(1, min(int(count), 12))]
    ]


def _section_delta(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any] | None:
    if not previous.get("evidence_available") or not current.get("evidence_available"):
        return None

    result: dict[str, Any] = {}
    for key in SCALAR_METRICS:
        before = _safe_float(previous.get(key))
        after = _safe_float(current.get(key))
        result[key] = None if before is None or after is None else round(after - before, 5)

    previous_regions = previous.get("spectral_regions") or {}
    current_regions = current.get("spectral_regions") or {}
    region_delta: dict[str, float | None] = {}
    for name, _lo, _hi in song.SPECTRAL_REGIONS:
        before = _safe_float(previous_regions.get(name))
        after = _safe_float(current_regions.get(name))
        region_delta[name] = None if before is None or after is None else round(after - before, 5)
    result["spectral_regions_db"] = region_delta

    chroma_similarity = structure._cosine_similarity(previous.get("chroma"), current.get("chroma"))
    result["chroma_cosine_similarity"] = (
        None if chroma_similarity is None else round(float(chroma_similarity), 5)
    )
    return result


def _family_consistency(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        grouped.setdefault(str(entry["family_id"]), []).append(entry)

    families: list[dict[str, Any]] = []
    for family_id, members in grouped.items():
        observed = [item for item in members if bool(item.get("evidence_available"))]
        metric_stats: dict[str, dict[str, float] | None] = {}
        for key in SCALAR_METRICS:
            values = [
                float(value)
                for item in observed
                if (value := _safe_float(item.get(key))) is not None
            ]
            metric_stats[key] = _stats(values)

        spectral_stats: dict[str, dict[str, float] | None] = {}
        for name, _lo, _hi in song.SPECTRAL_REGIONS:
            values = [
                float(value)
                for item in observed
                if (value := _safe_float((item.get("spectral_regions") or {}).get(name))) is not None
            ]
            spectral_stats[name] = _stats(values)

        chroma_pairs = []
        for left, right in combinations(observed, 2):
            similarity = structure._cosine_similarity(left.get("chroma"), right.get("chroma"))
            if similarity is not None:
                chroma_pairs.append(float(similarity))

        coverage_values = [
            float(value)
            for item in members
            if (value := _safe_float(item.get("coverage_ratio"))) is not None
        ]
        families.append({
            "family_id": family_id,
            "occurrence_count": len(members),
            "section_ids": [str(item["section_id"]) for item in members],
            "sufficient_coverage_count": len(observed),
            "insufficient_coverage_section_ids": [
                str(item["section_id"]) for item in members if not item.get("evidence_available")
            ],
            "coverage_ratio": _stats(coverage_values),
            "metric_statistics": metric_stats,
            "spectral_region_statistics_db": spectral_stats,
            "chroma_pairwise_cosine": _stats(chroma_pairs),
            "semantics": "Spreads describe observed variation inside this neutral recurring family; they are not a quality or consistency score.",
        })
    return families


def _relative_extrema(entries: list[dict[str, Any]]) -> dict[str, Any]:
    observed = [entry for entry in entries if entry.get("evidence_available")]
    result: dict[str, Any] = {}
    for key in SCALAR_METRICS:
        values = [
            (float(value), entry)
            for entry in observed
            if (value := _safe_float(entry.get(key))) is not None
        ]
        if not values:
            result[key] = None
            continue
        low_value, low_entry = min(values, key=lambda item: item[0])
        high_value, high_entry = max(values, key=lambda item: item[0])
        result[key] = {
            "lowest": {"section_id": low_entry["section_id"], "value": round(low_value, 5)},
            "highest": {"section_id": high_entry["section_id"], "value": round(high_value, 5)},
        }
    return result


def _build_section_entry(section: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    start = float(section["start_seconds"])
    end = float(section["end_seconds"])
    summary = structure._range_summary(selection["rows"], start, end)
    if summary is None:
        return {
            "section_id": section["section_id"],
            "family_id": section["family_id"],
            "family_occurrence": section["family_occurrence"],
            "start_seconds": section["start_seconds"],
            "end_seconds": section["end_seconds"],
            "duration_seconds": section["duration_seconds"],
            "selected_transport_epoch": selection["epoch"],
            "coverage_ratio": 0.0,
            "evidence_available": False,
            "active_ratio": None,
            "rms_db": None,
            "lufs_s": None,
            "crest_db": None,
            "centroid_hz": None,
            "stereo_correlation": None,
            "stereo_width": None,
            "spectral_flux_mean": None,
            "spectral_regions": {},
            "chroma": None,
            "top_pitch_classes": [],
            "data_quality": {"coverage_ratio": 0.0},
        }

    quality = summary.get("data_quality") or {}
    coverage = _safe_float(quality.get("coverage_ratio")) or 0.0
    chroma = summary.get("chroma")
    return {
        "section_id": section["section_id"],
        "family_id": section["family_id"],
        "family_occurrence": section["family_occurrence"],
        "start_seconds": section["start_seconds"],
        "end_seconds": section["end_seconds"],
        "duration_seconds": section["duration_seconds"],
        "selected_transport_epoch": selection["epoch"],
        "coverage_ratio": round(coverage, 4),
        "evidence_available": coverage >= MIN_STORY_COVERAGE,
        "active_ratio": _round_optional(summary.get("active_ratio")),
        "rms_db": _round_optional(summary.get("rms_db")),
        "lufs_s": _round_optional(summary.get("lufs_s")),
        "crest_db": _round_optional(summary.get("crest_db")),
        "centroid_hz": _round_optional(summary.get("centroid_hz"), 2),
        "stereo_correlation": _round_optional(summary.get("stereo_correlation"), 5),
        "stereo_width": _round_optional(summary.get("stereo_width"), 5),
        "spectral_flux_mean": _round_optional(summary.get("spectral_flux_mean"), 6),
        "spectral_regions": summary.get("spectral_regions") or {},
        "chroma": chroma,
        "top_pitch_classes": _top_chroma(chroma),
        "data_quality": quality,
    }


def _cached_map(map_id: str | None) -> tuple[str | None, dict[str, Any] | None]:
    with structure._section_lock:
        if map_id is None:
            return structure._latest_cached_map()
        resolved = str(map_id)
        return resolved, structure._section_maps.get(resolved)


def _build_default_map() -> tuple[str | None, dict[str, Any] | None]:
    reference_runtime_id = structure._resolve_reference(None)
    result = structure._build_map(
        reference_runtime_id,
        None,
        structure.DEFAULT_MIN_SECTION_SECONDS,
        structure.DEFAULT_SENSITIVITY,
        structure.DEFAULT_FAMILY_SIMILARITY,
        48,
        64,
    )
    if result.get("available") is False:
        return None, result
    public = structure._cache_map(result)
    map_id = str(public["map_id"])
    with structure._section_lock:
        return map_id, structure._section_maps.get(map_id)


@core.mcp.tool()
def audio_track_story(track: str, map_id: str | None = None) -> dict[str, Any]:
    """Summarize one Analyzer track across structural sections and recurring families."""
    runtime_id = core._resolve_track(str(track))
    resolved_map_id, cached = _cached_map(map_id)
    generated_map = False

    if cached is None and map_id is None:
        resolved_map_id, cached = _build_default_map()
        generated_map = cached is not None and bool(cached.get("public", {}).get("available"))

    if cached is None or resolved_map_id is None or cached.get("public", {}).get("available") is False:
        reason = "No usable cached section map. Call audio_section_map() after collecting transport-aligned Song Memory."
        if isinstance(cached, dict) and cached.get("reason"):
            reason = str(cached["reason"])
        return {"available": False, "runtime_id": runtime_id, "reason": reason}

    selection = cached.get("track_epochs", {}).get(runtime_id)
    if selection is None and map_id is None:
        resolved_map_id, cached = _build_default_map()
        generated_map = True
        selection = None if cached is None else cached.get("track_epochs", {}).get(runtime_id)

    if selection is None:
        return {
            "available": False,
            "runtime_id": runtime_id,
            "selector": song._binding_selector(runtime_id),
            "display_name": song._display_name(runtime_id),
            "map_id": resolved_map_id,
            "reason": "The requested track has no overlapping retained Song Memory in this section map. Missing coverage is not interpreted as inactivity.",
        }

    entries = [_build_section_entry(section, selection) for section in cached["sections"]]
    for index, entry in enumerate(entries):
        entry["delta_from_previous"] = None if index == 0 else _section_delta(entries[index - 1], entry)

    sufficient = [entry for entry in entries if entry.get("evidence_available")]
    coverage_values = [
        float(value)
        for entry in entries
        if (value := _safe_float(entry.get("coverage_ratio"))) is not None
    ]
    dropped = [
        int((entry.get("data_quality") or {}).get("dropped_blocks_cumulative", 0) or 0)
        for entry in entries
    ]
    warnings: list[str] = []
    insufficient_ids = [entry["section_id"] for entry in entries if not entry.get("evidence_available")]
    if insufficient_ids:
        warnings.append(
            "Some sections have less than 20% retained coverage. Their low/zero activity must not be interpreted as silence or muting."
        )
    if dropped and max(dropped) > 0:
        warnings.append("At least one retained section reports cumulative Analyzer FIFO drops; some audio was not analyzed.")

    return {
        "available": True,
        "map_id": resolved_map_id,
        "generated_section_map": generated_map,
        "runtime_id": runtime_id,
        "selector": song._binding_selector(runtime_id),
        "display_name": song._display_name(runtime_id),
        "is_master": song._is_master(runtime_id),
        "selected_transport_epoch": selection["epoch"],
        "section_count": len(entries),
        "sufficient_coverage_section_count": len(sufficient),
        "coverage_ratio_statistics": _stats(coverage_values),
        "sections": entries,
        "family_consistency": _family_consistency(entries),
        "relative_extrema": _relative_extrema(entries),
        "warnings": warnings,
        "semantics": {
            "activity": "active_ratio is observed signal presence inside retained frames. A low ratio is not automatically a mute state or musical-role label.",
            "coverage": "Missing/low coverage is missing evidence, not silence. Section deltas are withheld unless both adjacent sections meet the minimum coverage threshold.",
            "family": "A/B/C family IDs are neutral recurring-structure labels, not Verse/Chorus/Drop names.",
            "deltas": "delta_from_previous is current minus previous for directly comparable descriptors; it is descriptive evidence, not a processing recommendation.",
            "tonal": "top_pitch_classes/chroma are pitch-class evidence only and do not prove key or chord identity.",
        },
        "note": "Track Story describes how this Analyzer instance changes across the cached section map. Use exact DAW names/markers/project metadata when available, and keep processing decisions with the LLM/user rather than this measurement layer.",
    }


def _self_test() -> dict[str, Any]:
    chroma_c = [1.0] + [0.0] * 11
    chroma_g = [0.0] * 7 + [1.0] + [0.0] * 4

    def fake(section_id: str, family_id: str, rms: float, width: float, coverage: float, chroma: list[float]) -> dict[str, Any]:
        return {
            "section_id": section_id,
            "family_id": family_id,
            "family_occurrence": 1,
            "evidence_available": coverage >= MIN_STORY_COVERAGE,
            "coverage_ratio": coverage,
            "active_ratio": 0.8,
            "rms_db": rms,
            "lufs_s": rms - 2.0,
            "crest_db": 8.0,
            "centroid_hz": 1500.0,
            "stereo_correlation": 0.75,
            "stereo_width": width,
            "spectral_flux_mean": 0.08,
            "spectral_regions": {name: rms - index for index, (name, _lo, _hi) in enumerate(song.SPECTRAL_REGIONS)},
            "chroma": chroma,
        }

    first = fake("S01", "A", -20.0, 0.4, 1.0, chroma_c)
    second = fake("S02", "B", -14.0, 0.7, 1.0, chroma_g)
    third = fake("S03", "A", -18.0, 0.5, 1.0, chroma_c)
    low_coverage = fake("S04", "B", -30.0, 0.2, 0.1, chroma_g)

    delta = _section_delta(first, second)
    if delta is None or delta["rms_db"] != 6.0 or delta["stereo_width"] != 0.3:
        raise RuntimeError(f"Track-story adjacent delta regression failed: {delta}")
    if _section_delta(third, low_coverage) is not None:
        raise RuntimeError("Track-story low-coverage delta must be withheld.")

    families = _family_consistency([first, second, third, low_coverage])
    family_a = next(item for item in families if item["family_id"] == "A")
    family_b = next(item for item in families if item["family_id"] == "B")
    if family_a["occurrence_count"] != 2 or family_a["metric_statistics"]["rms_db"]["spread"] != 2.0:
        raise RuntimeError(f"Track-story family A regression failed: {family_a}")
    if family_b["sufficient_coverage_count"] != 1 or family_b["insufficient_coverage_section_ids"] != ["S04"]:
        raise RuntimeError(f"Track-story family B coverage regression failed: {family_b}")

    return {"adjacent_rms_delta_db": delta["rms_db"], "family_a_rms_spread_db": 2.0, "low_coverage_guard": "ok"}
