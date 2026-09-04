#!/usr/bin/env python3
"""Explainable song-structure layer built on transport-aware Song Memory.

This module deliberately avoids forcing musical-form names such as Verse or
Chorus. It detects structural boundaries from multi-scale changes, groups
recurring sections into neutral A/B/C families, and exposes the evidence to an
LLM. Exact DAW markers/project metadata remain authoritative when available.
"""

from __future__ import annotations

import hashlib
import math
import statistics
import threading
from collections import OrderedDict
from typing import Any

import server as core
import song_tools as song

DEFAULT_SCALES_SECONDS = (2, 4, 8)
DEFAULT_MIN_SECTION_SECONDS = 8
DEFAULT_SENSITIVITY = 0.55
DEFAULT_FAMILY_SIMILARITY = 0.78
MIN_POINT_COVERAGE = 0.2
MAX_SECTION_MAPS = 12

SCALAR_GROUPS = {
    "energy": ("rms_db", "lufs_s"),
    "spectrum": (
        "centroid_log2",
        "sub_20_120_db",
        "low_mid_120_500_db",
        "mid_500_2000_db",
        "presence_2000_5000_db",
        "high_5000_20000_db",
    ),
    "stereo": ("stereo_correlation", "stereo_width"),
    "dynamics": ("crest_db",),
    "temporal": ("flux_log",),
}

NOVELTY_WEIGHTS = {
    "activity": 0.25,
    "energy": 0.20,
    "spectrum": 0.20,
    "chroma": 0.15,
    "stereo": 0.08,
    "dynamics": 0.06,
    "temporal": 0.06,
}

SIMILARITY_WEIGHTS = {
    "activity": 0.30,
    "spectrum": 0.22,
    "energy": 0.18,
    "chroma": 0.15,
    "stereo": 0.07,
    "dynamics": 0.05,
    "duration": 0.03,
}

_section_lock = threading.RLock()
_section_maps: OrderedDict[str, dict[str, Any]] = OrderedDict()


def _safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _mean(values: list[float]) -> float | None:
    return None if not values else sum(values) / len(values)


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = _clamp(q, 0.0, 1.0) * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _alpha_label(index: int) -> str:
    index = max(0, int(index))
    label = ""
    while True:
        label = chr(ord("A") + index % 26) + label
        index = index // 26 - 1
        if index < 0:
            return label


def _resolve_reference(reference_track: str | None) -> str:
    if reference_track is not None and str(reference_track).strip():
        return core._resolve_track(str(reference_track))
    with core._lock:
        runtime_ids = list(core._tracks)
    if not runtime_ids:
        raise ValueError("No live Analyzer instances are available.")
    runtime_ids = sorted(runtime_ids, key=song._runtime_sort_key)
    return next((runtime_id for runtime_id in runtime_ids if song._is_master(runtime_id)), runtime_ids[0])


def _rows_overlap(rows: list[dict[str, Any]], start: float, end: float) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if float(row["end_seconds"]) > start and float(row["start_seconds"]) < end
    ]


def _select_epoch_for_range(
    runtime_id: str,
    start: float,
    end: float,
    preferred_epoch: int | None = None,
) -> tuple[int | None, list[dict[str, Any]], float]:
    epochs = song._available_epochs(runtime_id)
    if preferred_epoch is not None and int(preferred_epoch) in epochs:
        rows = _rows_overlap(song._bins_for(runtime_id, int(preferred_epoch)), start, end)
        covered = sum(song._covered_seconds(row) for row in rows)
        if rows:
            return int(preferred_epoch), rows, covered

    best_epoch: int | None = None
    best_rows: list[dict[str, Any]] = []
    best_covered = -1.0
    for epoch in epochs:
        rows = _rows_overlap(song._bins_for(runtime_id, epoch), start, end)
        covered = sum(song._covered_seconds(row) for row in rows)
        if covered > best_covered or (covered == best_covered and best_epoch is not None and epoch > best_epoch):
            best_epoch = epoch
            best_rows = rows
            best_covered = covered
    return best_epoch, best_rows, max(0.0, best_covered)


def _row_activity(row: dict[str, Any]) -> float | None:
    frames = int(row.get("frame_count", 0) or 0)
    if frames <= 0 or song._covered_seconds(row) < MIN_POINT_COVERAGE:
        return None
    return _clamp(int(row.get("active_count", 0) or 0) / frames, 0.0, 1.0)


def _row_point(row: dict[str, Any]) -> dict[str, Any]:
    summary = song._finalize_rows(
        [row],
        start_seconds=float(row["start_seconds"]),
        end_seconds=float(row["end_seconds"]),
        expected_seconds=song.TIMELINE_BIN_SECONDS,
    )
    quality = summary["data_quality"]
    coverage = float(quality.get("coverage_ratio") or 0.0)
    regions = summary.get("spectral_regions") or {}
    centroid = _safe_float(summary.get("centroid_hz"))
    flux = _safe_float(summary.get("spectral_flux_mean"))
    values = {
        "rms_db": _safe_float(summary.get("rms_db")),
        "lufs_s": _safe_float(summary.get("lufs_s")),
        "centroid_log2": None if centroid is None or centroid <= 0.0 else math.log2(centroid),
        "stereo_correlation": _safe_float(summary.get("stereo_correlation")),
        "stereo_width": _safe_float(summary.get("stereo_width")),
        "crest_db": _safe_float(summary.get("crest_db")),
        "flux_log": None if flux is None else math.log1p(max(0.0, flux) * 1000.0),
    }
    for name, _lo, _hi in song.SPECTRAL_REGIONS:
        values[name] = _safe_float(regions.get(name))
    if coverage < MIN_POINT_COVERAGE:
        values = {key: None for key in values}
    return {
        "bin_index": int(row["bin_index"]),
        "start_seconds": float(row["start_seconds"]),
        "end_seconds": float(row["end_seconds"]),
        "coverage": coverage,
        "values": values,
        "chroma": summary.get("chroma") if coverage >= MIN_POINT_COVERAGE else None,
    }


def _robust_normalize(points: list[dict[str, Any]]) -> None:
    fields = sorted({field for group in SCALAR_GROUPS.values() for field in group})
    for field in fields:
        values = [
            float(point["values"][field])
            for point in points
            if point["values"].get(field) is not None
        ]
        if not values:
            for point in points:
                point.setdefault("z", {})[field] = None
            continue
        median = statistics.median(values)
        deviations = [abs(value - median) for value in values]
        mad = statistics.median(deviations) if deviations else 0.0
        floor = 0.15 if field in ("centroid_log2", "flux_log") else 0.08 if field == "stereo_correlation" else 0.05 if field == "stereo_width" else 0.75 if field == "crest_db" else 1.0
        scale = max(floor, 1.4826 * mad)
        for point in points:
            value = point["values"].get(field)
            point.setdefault("z", {})[field] = None if value is None else _clamp((float(value) - median) / scale, -5.0, 5.0)


def _mean_vector(points: list[dict[str, Any]], fields: tuple[str, ...]) -> list[float | None]:
    result: list[float | None] = []
    for field in fields:
        values = [float(point["z"][field]) for point in points if point.get("z", {}).get(field) is not None]
        result.append(_mean(values))
    return result


def _scalar_change(left: list[dict[str, Any]], right: list[dict[str, Any]], fields: tuple[str, ...]) -> float | None:
    left_mean = _mean_vector(left, fields)
    right_mean = _mean_vector(right, fields)
    differences = [
        abs(float(a) - float(b))
        for a, b in zip(left_mean, right_mean)
        if a is not None and b is not None
    ]
    if not differences:
        return None
    distance = sum(differences) / len(differences)
    return 1.0 - math.exp(-distance / 1.5)


def _mean_chroma(points: list[dict[str, Any]]) -> list[float] | None:
    rows = [point["chroma"] for point in points if isinstance(point.get("chroma"), list) and len(point["chroma"]) == 12]
    if not rows:
        return None
    vector = [sum(float(row[index]) for row in rows) / len(rows) for index in range(12)]
    total = sum(vector)
    return None if total <= 1.0e-12 else [value / total for value in vector]


def _cosine_similarity(a: list[float] | None, b: list[float] | None) -> float | None:
    if a is None or b is None or len(a) != len(b) or not a:
        return None
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 1.0e-12 or nb <= 1.0e-12:
        return None
    return _clamp(dot / (na * nb), 0.0, 1.0)


def _activity_window(
    bin_indices: list[int],
    track_rows: dict[str, dict[int, dict[str, Any]]],
) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for runtime_id, row_map in track_rows.items():
        values = [
            value
            for index in bin_indices
            if (row := row_map.get(index)) is not None and (value := _row_activity(row)) is not None
        ]
        result[runtime_id] = _mean(values)
    return result


def _activity_change(left: dict[str, float | None], right: dict[str, float | None]) -> float | None:
    diffs = [
        abs(float(left[key]) - float(right[key]))
        for key in left.keys() & right.keys()
        if left[key] is not None and right[key] is not None
    ]
    return None if not diffs else _clamp(sum(diffs) / len(diffs), 0.0, 1.0)


def _weighted_score(components: dict[str, float | None], weights: dict[str, float]) -> float | None:
    pairs = [(float(value), weights[name]) for name, value in components.items() if value is not None and name in weights]
    if not pairs:
        return None
    total_weight = sum(weight for _value, weight in pairs)
    return sum(value * weight for value, weight in pairs) / total_weight


def _candidate_novelty(
    boundary_bin: int,
    point_by_bin: dict[int, dict[str, Any]],
    track_rows: dict[str, dict[int, dict[str, Any]]],
    scales: tuple[int, ...] = DEFAULT_SCALES_SECONDS,
) -> dict[str, Any] | None:
    scale_results: list[dict[str, Any]] = []
    for scale in scales:
        left_bins = list(range(boundary_bin - scale, boundary_bin))
        right_bins = list(range(boundary_bin, boundary_bin + scale))
        left = [point_by_bin[index] for index in left_bins if index in point_by_bin]
        right = [point_by_bin[index] for index in right_bins if index in point_by_bin]
        minimum = max(1, int(math.ceil(scale * 0.5)))
        if len(left) < minimum or len(right) < minimum:
            continue
        left_coverage = _mean([float(point["coverage"]) for point in left]) or 0.0
        right_coverage = _mean([float(point["coverage"]) for point in right]) or 0.0
        coverage = min(left_coverage, right_coverage)
        if coverage < 0.35:
            continue

        components = {
            name: _scalar_change(left, right, fields)
            for name, fields in SCALAR_GROUPS.items()
        }
        chroma_similarity = _cosine_similarity(_mean_chroma(left), _mean_chroma(right))
        components["chroma"] = None if chroma_similarity is None else 1.0 - chroma_similarity
        components["activity"] = _activity_change(
            _activity_window(left_bins, track_rows),
            _activity_window(right_bins, track_rows),
        )
        raw = _weighted_score(components, NOVELTY_WEIGHTS)
        if raw is None:
            continue
        score = _clamp(raw * math.sqrt(coverage), 0.0, 1.0)
        scale_results.append({"scale_seconds": scale, "score": score, "coverage": coverage, "components": components})

    if not scale_results:
        return None
    score = sum(item["score"] for item in scale_results) / len(scale_results)
    components: dict[str, float | None] = {}
    for name in NOVELTY_WEIGHTS:
        values = [float(item["components"][name]) for item in scale_results if item["components"].get(name) is not None]
        components[name] = _mean(values)
    return {
        "bin_index": boundary_bin,
        "time_seconds": float(boundary_bin),
        "score": _clamp(score, 0.0, 1.0),
        "coverage": min(float(item["coverage"]) for item in scale_results),
        "components": components,
        "scales_used": [int(item["scale_seconds"]) for item in scale_results],
    }


def _detect_boundaries(
    points: list[dict[str, Any]],
    track_rows: dict[str, dict[int, dict[str, Any]]],
    min_section_seconds: int,
    sensitivity: float,
    max_sections: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    point_by_bin = {int(point["bin_index"]): point for point in points}
    bins = sorted(point_by_bin)
    if len(bins) < max(12, min_section_seconds * 2):
        return [], {"threshold": None, "candidate_count": 0, "reason": "insufficient_timeline"}

    raw: dict[int, dict[str, Any]] = {}
    for boundary in range(bins[0] + 1, bins[-1] + 1):
        candidate = _candidate_novelty(boundary, point_by_bin, track_rows)
        if candidate is not None:
            raw[boundary] = candidate
    if not raw:
        return [], {"threshold": None, "candidate_count": 0, "reason": "no_valid_context_windows"}

    smoothed: dict[int, float] = {}
    for boundary, candidate in raw.items():
        neighbors = [
            (raw[index]["score"], weight)
            for index, weight in ((boundary - 1, 0.25), (boundary, 0.5), (boundary + 1, 0.25))
            if index in raw
        ]
        total = sum(weight for _value, weight in neighbors)
        smoothed[boundary] = sum(value * weight for value, weight in neighbors) / max(total, 1.0e-9)
        candidate["smoothed_score"] = smoothed[boundary]

    scores = list(smoothed.values())
    median = statistics.median(scores)
    p90 = _percentile(scores, 0.90)
    threshold = max(0.12, median + _clamp(sensitivity, 0.1, 0.95) * max(0.0, p90 - median))

    peaks: list[dict[str, Any]] = []
    for boundary, candidate in raw.items():
        score = smoothed[boundary]
        if score < threshold:
            continue
        if score < smoothed.get(boundary - 1, -1.0) or score < smoothed.get(boundary + 1, -1.0):
            continue
        candidate = dict(candidate)
        candidate["smoothed_score"] = score
        peaks.append(candidate)

    start = float(points[0]["start_seconds"])
    end = float(points[-1]["end_seconds"])
    selected: list[dict[str, Any]] = []
    for candidate in sorted(peaks, key=lambda item: float(item["smoothed_score"]), reverse=True):
        position = float(candidate["time_seconds"])
        if position - start < min_section_seconds or end - position < min_section_seconds:
            continue
        if any(abs(position - float(item["time_seconds"])) < min_section_seconds for item in selected):
            continue
        selected.append(candidate)
        if len(selected) >= max(0, max_sections - 1):
            break
    selected.sort(key=lambda item: float(item["time_seconds"]))

    return selected, {
        "threshold": round(threshold, 5),
        "novelty_median": round(median, 5),
        "novelty_p90": round(p90, 5),
        "candidate_count": len(raw),
        "peak_count_before_spacing": len(peaks),
        "selected_boundary_count": len(selected),
        "scales_seconds": list(DEFAULT_SCALES_SECONDS),
    }


def _range_summary(rows: list[dict[str, Any]], start: float, end: float) -> dict[str, Any] | None:
    overlap = _rows_overlap(rows, start, end)
    if not overlap:
        return None
    return song._finalize_rows(overlap, start_seconds=start, end_seconds=end, expected_seconds=max(1.0e-6, end - start))


def _track_activity_signature(
    track_epochs: dict[str, dict[str, Any]],
    start: float,
    end: float,
) -> tuple[dict[str, float | None], list[dict[str, Any]]]:
    vector: dict[str, float | None] = {}
    public: list[dict[str, Any]] = []
    duration = max(1.0e-6, end - start)
    for runtime_id, selection in track_epochs.items():
        rows = _rows_overlap(selection["rows"], start, end)
        frames = sum(int(row.get("frame_count", 0) or 0) for row in rows)
        active = sum(int(row.get("active_count", 0) or 0) for row in rows)
        covered = sum(song._covered_seconds(row) for row in rows)
        coverage = min(1.0, covered / duration)
        activity = None if frames <= 0 or coverage < MIN_POINT_COVERAGE else _clamp(active / frames, 0.0, 1.0)
        vector[runtime_id] = activity
        if activity is not None:
            public.append({
                "runtime_id": runtime_id,
                "selector": song._binding_selector(runtime_id),
                "display_name": song._display_name(runtime_id),
                "active_ratio": round(activity, 4),
                "coverage_ratio": round(coverage, 4),
                "selected_transport_epoch": selection["epoch"],
            })
    public.sort(key=lambda item: (-float(item["active_ratio"]), str(item["display_name"]).casefold()))
    return vector, public


def _distance_similarity(a: float | None, b: float | None, scale: float) -> float | None:
    if a is None or b is None:
        return None
    return math.exp(-abs(float(a) - float(b)) / max(scale, 1.0e-9))


def _mean_available(values: list[float | None]) -> float | None:
    available = [float(value) for value in values if value is not None]
    return _mean(available)


def _section_similarity(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    sa = a["summary"]
    sb = b["summary"]
    ra = sa.get("spectral_regions") or {}
    rb = sb.get("spectral_regions") or {}

    energy = _mean_available([
        _distance_similarity(_safe_float(sa.get("rms_db")), _safe_float(sb.get("rms_db")), 6.0),
        _distance_similarity(_safe_float(sa.get("lufs_s")), _safe_float(sb.get("lufs_s")), 6.0),
    ])
    centroid_a = _safe_float(sa.get("centroid_hz"))
    centroid_b = _safe_float(sb.get("centroid_hz"))
    centroid_similarity = None
    if centroid_a is not None and centroid_b is not None and centroid_a > 0.0 and centroid_b > 0.0:
        centroid_similarity = math.exp(-abs(math.log2(centroid_a / centroid_b)) / 1.0)
    spectrum = _mean_available([
        centroid_similarity,
        *[
            _distance_similarity(_safe_float(ra.get(name)), _safe_float(rb.get(name)), 6.0)
            for name, _lo, _hi in song.SPECTRAL_REGIONS
        ],
    ])
    stereo = _mean_available([
        _distance_similarity(_safe_float(sa.get("stereo_correlation")), _safe_float(sb.get("stereo_correlation")), 0.5),
        _distance_similarity(_safe_float(sa.get("stereo_width")), _safe_float(sb.get("stereo_width")), 0.75),
    ])
    dynamics = _mean_available([
        _distance_similarity(_safe_float(sa.get("crest_db")), _safe_float(sb.get("crest_db")), 6.0),
        _distance_similarity(
            None if _safe_float(sa.get("spectral_flux_mean")) is None else math.log1p(max(0.0, float(sa["spectral_flux_mean"])) * 1000.0),
            None if _safe_float(sb.get("spectral_flux_mean")) is None else math.log1p(max(0.0, float(sb["spectral_flux_mean"])) * 1000.0),
            1.0,
        ),
    ])
    chroma = _cosine_similarity(sa.get("chroma"), sb.get("chroma"))
    activity_values = [
        1.0 - abs(float(a["activity_vector"][key]) - float(b["activity_vector"][key]))
        for key in a["activity_vector"].keys() & b["activity_vector"].keys()
        if a["activity_vector"][key] is not None and b["activity_vector"][key] is not None
    ]
    activity = _mean(activity_values)
    duration_a = max(1.0e-6, float(a["end_seconds"]) - float(a["start_seconds"]))
    duration_b = max(1.0e-6, float(b["end_seconds"]) - float(b["start_seconds"]))
    duration = math.exp(-abs(math.log(duration_a / duration_b)) / 0.7)

    components = {
        "activity": activity,
        "spectrum": spectrum,
        "energy": energy,
        "chroma": chroma,
        "stereo": stereo,
        "dynamics": dynamics,
        "duration": duration,
    }
    score = _weighted_score(components, SIMILARITY_WEIGHTS)
    return {
        "score": None if score is None else round(_clamp(score, 0.0, 1.0), 5),
        "components": {key: None if value is None else round(_clamp(float(value), 0.0, 1.0), 5) for key, value in components.items()},
    }


def _assign_families(sections: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    families: list[list[int]] = []
    pair_cache: dict[tuple[int, int], dict[str, Any]] = {}

    def similarity(i: int, j: int) -> dict[str, Any]:
        key = (min(i, j), max(i, j))
        if key not in pair_cache:
            pair_cache[key] = _section_similarity(sections[i], sections[j])
        return pair_cache[key]

    for index, section in enumerate(sections):
        best_family: int | None = None
        best_score = -1.0
        for family_index, members in enumerate(families):
            scores = [similarity(index, member)["score"] for member in members]
            valid = [float(score) for score in scores if score is not None]
            family_score = -1.0 if not valid else sum(valid) / len(valid)
            if family_score > best_score:
                best_score = family_score
                best_family = family_index
        if best_family is None or best_score < threshold:
            families.append([index])
            best_family = len(families) - 1
        else:
            families[best_family].append(index)
        section["family_id"] = _alpha_label(best_family)
        section["family_occurrence"] = len(families[best_family])

    pairs: list[dict[str, Any]] = []
    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):
            result = similarity(i, j)
            if result["score"] is None:
                continue
            pairs.append({
                "section_a": sections[i]["section_id"],
                "section_b": sections[j]["section_id"],
                "family_a": sections[i]["family_id"],
                "family_b": sections[j]["family_id"],
                "similarity": result["score"],
                "components": result["components"],
            })
    pairs.sort(key=lambda item: float(item["similarity"]), reverse=True)
    return pairs


def _build_map(
    reference_runtime_id: str,
    transport_epoch: int | None,
    min_section_seconds: int,
    sensitivity: float,
    family_similarity: float,
    max_sections: int,
    max_tracks: int,
) -> dict[str, Any]:
    epochs = song._available_epochs(reference_runtime_id)
    if not epochs:
        return {"available": False, "reason": "Reference track has no transport-aligned Song Memory."}
    reference_epoch = epochs[-1] if transport_epoch is None else int(transport_epoch)
    reference_rows = song._bins_for(reference_runtime_id, reference_epoch)
    if not reference_rows:
        return {
            "available": False,
            "reason": "Requested reference transport epoch is not retained.",
            "available_epochs": epochs[-12:],
        }

    start = min(float(row["start_seconds"]) for row in reference_rows)
    end = max(float(row["end_seconds"]) for row in reference_rows)
    span = max(song.TIMELINE_BIN_SECONDS, end - start)
    covered = sum(song._covered_seconds(row) for row in reference_rows)
    reference_coverage = min(1.0, covered / span)

    with core._lock:
        runtime_ids = sorted(list(core._tracks), key=song._runtime_sort_key)
    runtime_ids = runtime_ids[:max_tracks]
    if reference_runtime_id not in runtime_ids:
        runtime_ids = [reference_runtime_id] + runtime_ids[:-1]

    track_epochs: dict[str, dict[str, Any]] = {}
    for runtime_id in runtime_ids:
        preferred = reference_epoch if runtime_id == reference_runtime_id else None
        epoch, rows, track_covered = _select_epoch_for_range(runtime_id, start, end, preferred)
        if epoch is None or not rows:
            continue
        track_epochs[runtime_id] = {"epoch": epoch, "rows": rows, "covered_seconds": track_covered}

    reference_points = [_row_point(row) for row in reference_rows]
    _robust_normalize(reference_points)
    track_rows_by_bin = {
        runtime_id: {int(row["bin_index"]): row for row in selection["rows"]}
        for runtime_id, selection in track_epochs.items()
    }
    boundaries, detector = _detect_boundaries(
        reference_points,
        track_rows_by_bin,
        min_section_seconds,
        sensitivity,
        max_sections,
    )

    cut_points = [start] + [float(item["time_seconds"]) for item in boundaries] + [end]
    sections: list[dict[str, Any]] = []
    for index, (section_start, section_end) in enumerate(zip(cut_points, cut_points[1:]), start=1):
        summary = _range_summary(reference_rows, section_start, section_end)
        if summary is None:
            continue
        activity_vector, activity_public = _track_activity_signature(track_epochs, section_start, section_end)
        sections.append({
            "section_id": f"S{index:02d}",
            "start_seconds": round(section_start, 3),
            "end_seconds": round(section_end, 3),
            "duration_seconds": round(max(0.0, section_end - section_start), 3),
            "summary": summary,
            "activity_vector": activity_vector,
            "track_activity": activity_public,
        })

    similarity_pairs = _assign_families(sections, _clamp(family_similarity, 0.5, 0.95)) if sections else []
    family_counts: dict[str, int] = {}
    for section in sections:
        family_counts[section["family_id"]] = family_counts.get(section["family_id"], 0) + 1

    coverage_gaps = []
    row_bins = sorted(int(row["bin_index"]) for row in reference_rows)
    for previous, current in zip(row_bins, row_bins[1:]):
        if current - previous > 1:
            coverage_gaps.append({"start_seconds": float(previous + 1), "end_seconds": float(current), "missing_seconds": float(current - previous - 1)})

    boundary_public = []
    for item in boundaries:
        ranked = sorted(
            ((name, value) for name, value in item["components"].items() if value is not None),
            key=lambda pair: float(pair[1]),
            reverse=True,
        )
        boundary_public.append({
            "time_seconds": round(float(item["time_seconds"]), 3),
            "strength": round(float(item["smoothed_score"]), 5),
            "context_coverage": round(float(item["coverage"]), 4),
            "scales_used_seconds": item["scales_used"],
            "evidence": {name: round(float(value), 5) for name, value in ranked},
            "dominant_evidence": [name for name, _value in ranked[:3]],
        })

    public_sections = []
    for section in sections:
        summary = section["summary"]
        active_tracks = [item for item in section["track_activity"] if float(item["active_ratio"]) >= 0.25]
        public_sections.append({
            "section_id": section["section_id"],
            "family_id": section["family_id"],
            "family_occurrence": section["family_occurrence"],
            "start_seconds": section["start_seconds"],
            "end_seconds": section["end_seconds"],
            "duration_seconds": section["duration_seconds"],
            "reference_summary": {
                "rms_db": summary.get("rms_db"),
                "lufs_s": summary.get("lufs_s"),
                "crest_db": summary.get("crest_db"),
                "centroid_hz": summary.get("centroid_hz"),
                "stereo_width": summary.get("stereo_width"),
                "spectral_flux_mean": summary.get("spectral_flux_mean"),
                "spectral_regions": summary.get("spectral_regions"),
                "chroma": summary.get("chroma"),
                "coverage_ratio": summary.get("data_quality", {}).get("coverage_ratio"),
            },
            "active_tracks": active_tracks[:16],
        })

    map_seed = f"{reference_runtime_id}|{reference_epoch}|{min_section_seconds}|{sensitivity:.4f}|{family_similarity:.4f}|" + ",".join(f"{value:.3f}" for value in cut_points)
    map_id = "section-map-" + hashlib.sha1(map_seed.encode("utf-8")).hexdigest()[:12]
    warnings: list[str] = []
    if reference_coverage < 0.75:
        warnings.append("Reference Song Memory covers less than 75% of its DAW-time span; inferred boundaries may be incomplete.")
    if coverage_gaps:
        warnings.append("Reference Song Memory contains time gaps. Missing evidence is not interpreted as a musical boundary.")
    if len(track_epochs) < len(runtime_ids):
        warnings.append("Some live Analyzer instances have no overlapping retained pass for the reference DAW-time range and were excluded from track-activity evidence.")
    if not boundaries:
        warnings.append("No structural novelty peaks passed the current adaptive threshold/minimum-section constraints.")

    public = {
        "available": True,
        "map_id": map_id,
        "reference": {
            "runtime_id": reference_runtime_id,
            "selector": song._binding_selector(reference_runtime_id),
            "display_name": song._display_name(reference_runtime_id),
            "transport_epoch": reference_epoch,
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
            "span_seconds": round(span, 3),
            "coverage_ratio": round(reference_coverage, 4),
        },
        "detector": {
            **detector,
            "minimum_section_seconds": min_section_seconds,
            "sensitivity": round(sensitivity, 4),
            "method": "multi-scale novelty from energy/spectrum/chroma/stereo/dynamics/temporal + cross-track activity",
        },
        "boundaries": boundary_public,
        "section_count": len(public_sections),
        "family_count": len(family_counts),
        "family_counts": family_counts,
        "sections": public_sections,
        "recurring_similarity_pairs": [item for item in similarity_pairs if float(item["similarity"]) >= family_similarity][:24],
        "coverage_gaps": coverage_gaps[:24],
        "track_activity_source_count": len(track_epochs),
        "warnings": warnings,
        "semantics": {
            "family_id": "Neutral recurring-structure family label (A/B/C/...). It is not a Verse/Chorus/Drop label.",
            "boundary_strength": "Explainable novelty evidence, not calibrated probability that a human would mark a formal section boundary.",
            "epoch_alignment": "Non-reference Analyzer passes are selected by overlapping DAW-time coverage, not by assuming equal instance-local epoch numbers.",
        },
        "note": "Use exact DAW markers/Playlist metadata for exact section names when available. The Analyzer exposes structural evidence and neutral recurrence families; an LLM may interpret names later with explicit uncertainty.",
    }
    return {
        "public": public,
        "sections": sections,
        "similarity_pairs": similarity_pairs,
        "track_epochs": track_epochs,
        "reference_runtime_id": reference_runtime_id,
        "reference_epoch": reference_epoch,
        "start_seconds": start,
        "end_seconds": end,
    }


def _cache_map(result: dict[str, Any]) -> dict[str, Any]:
    public = result.get("public")
    if not isinstance(public, dict) or not public.get("available"):
        return result
    map_id = str(public["map_id"])
    with _section_lock:
        _section_maps[map_id] = result
        _section_maps.move_to_end(map_id)
        while len(_section_maps) > MAX_SECTION_MAPS:
            _section_maps.popitem(last=False)
    return public


@core.mcp.tool()
def audio_section_map(
    reference_track: str | None = None,
    transport_epoch: int | None = None,
    min_section_seconds: int = DEFAULT_MIN_SECTION_SECONDS,
    sensitivity: float = DEFAULT_SENSITIVITY,
    family_similarity: float = DEFAULT_FAMILY_SIMILARITY,
    max_sections: int = 48,
    max_tracks: int = 32,
) -> dict[str, Any]:
    """Detect structural boundaries and neutral recurring A/B/C section families from Song Memory."""
    reference_runtime_id = _resolve_reference(reference_track)
    result = _build_map(
        reference_runtime_id,
        transport_epoch,
        max(4, min(int(min_section_seconds), 60)),
        _clamp(float(sensitivity), 0.1, 0.95),
        _clamp(float(family_similarity), 0.5, 0.95),
        max(2, min(int(max_sections), 96)),
        max(1, min(int(max_tracks), 64)),
    )
    if result.get("available") is False:
        result.update({
            "reference_runtime_id": reference_runtime_id,
            "reference_display_name": song._display_name(reference_runtime_id),
        })
        return result
    return _cache_map(result)


def _latest_cached_map() -> tuple[str | None, dict[str, Any] | None]:
    with _section_lock:
        if not _section_maps:
            return None, None
        map_id = next(reversed(_section_maps))
        return map_id, _section_maps[map_id]


@core.mcp.tool()
def audio_section_profile(
    section_id: str,
    map_id: str | None = None,
    max_tracks: int = 32,
    max_related: int = 8,
) -> dict[str, Any]:
    """Return detailed per-track evidence for one section from a previously generated section map."""
    section_id = str(section_id).strip().upper()
    with _section_lock:
        if map_id is None:
            resolved_map_id, cached = _latest_cached_map()
        else:
            resolved_map_id = str(map_id)
            cached = _section_maps.get(resolved_map_id)
    if cached is None or resolved_map_id is None:
        return {
            "available": False,
            "reason": "No matching cached section map. Call audio_section_map() first and keep its map_id for deterministic follow-up.",
        }

    sections = cached["sections"]
    section = next((item for item in sections if item["section_id"] == section_id), None)
    if section is None:
        return {
            "available": False,
            "map_id": resolved_map_id,
            "requested_section_id": section_id,
            "available_section_ids": [item["section_id"] for item in sections],
            "reason": "Requested section_id is not present in the cached map.",
        }

    start = float(section["start_seconds"])
    end = float(section["end_seconds"])
    track_profiles: list[dict[str, Any]] = []
    for runtime_id, selection in list(cached["track_epochs"].items())[:max(1, min(int(max_tracks), 64))]:
        summary = _range_summary(selection["rows"], start, end)
        if summary is None:
            continue
        track_profiles.append({
            "runtime_id": runtime_id,
            "selector": song._binding_selector(runtime_id),
            "display_name": song._display_name(runtime_id),
            "is_master": song._is_master(runtime_id),
            "selected_transport_epoch": selection["epoch"],
            "active_ratio": summary.get("active_ratio"),
            "rms_db": summary.get("rms_db"),
            "lufs_s": summary.get("lufs_s"),
            "crest_db": summary.get("crest_db"),
            "centroid_hz": summary.get("centroid_hz"),
            "stereo_correlation": summary.get("stereo_correlation"),
            "stereo_width": summary.get("stereo_width"),
            "spectral_flux_mean": summary.get("spectral_flux_mean"),
            "spectral_regions": summary.get("spectral_regions"),
            "chroma": summary.get("chroma"),
            "data_quality": summary.get("data_quality"),
        })
    track_profiles.sort(key=lambda item: (not bool(item["is_master"]), -(float(item["active_ratio"]) if item["active_ratio"] is not None else -1.0), str(item["display_name"]).casefold()))

    related = [
        item for item in cached["similarity_pairs"]
        if item["section_a"] == section_id or item["section_b"] == section_id
    ]
    related.sort(key=lambda item: float(item["similarity"]), reverse=True)
    related_public = []
    for item in related[:max(1, min(int(max_related), 24))]:
        other_id = item["section_b"] if item["section_a"] == section_id else item["section_a"]
        other = next(candidate for candidate in sections if candidate["section_id"] == other_id)
        related_public.append({
            "section_id": other_id,
            "family_id": other["family_id"],
            "start_seconds": other["start_seconds"],
            "end_seconds": other["end_seconds"],
            "similarity": item["similarity"],
            "components": item["components"],
        })

    same_family = [
        item for item in sections
        if item["family_id"] == section["family_id"] and item["section_id"] != section_id
    ]
    return {
        "available": True,
        "map_id": resolved_map_id,
        "section_id": section_id,
        "family_id": section["family_id"],
        "family_occurrence": section["family_occurrence"],
        "start_seconds": section["start_seconds"],
        "end_seconds": section["end_seconds"],
        "duration_seconds": section["duration_seconds"],
        "reference_summary": section["summary"],
        "same_family_sections": [item["section_id"] for item in same_family],
        "related_sections": related_public,
        "track_profiles": track_profiles,
        "note": "Section/profile evidence is descriptive. Family recurrence does not prove a Verse/Chorus/Drop identity, and no processing action is implied.",
    }


def _self_test() -> dict[str, Any]:
    """Pure synthetic regression for boundaries and recurring-family behavior."""
    points: list[dict[str, Any]] = []
    track_rows: dict[str, dict[int, dict[str, Any]]] = {"kick": {}, "vocal": {}}
    for index in range(72):
        family_a = index < 24 or index >= 48
        values = {
            "rms_db": -24.0 if family_a else -15.0,
            "lufs_s": -20.0 if family_a else -12.0,
            "centroid_log2": math.log2(900.0 if family_a else 2600.0),
            "sub_20_120_db": -31.0 if family_a else -24.0,
            "low_mid_120_500_db": -28.0 if family_a else -21.0,
            "mid_500_2000_db": -32.0 if family_a else -23.0,
            "presence_2000_5000_db": -38.0 if family_a else -25.0,
            "high_5000_20000_db": -45.0 if family_a else -30.0,
            "stereo_correlation": 0.88 if family_a else 0.58,
            "stereo_width": 0.28 if family_a else 0.82,
            "crest_db": 11.0 if family_a else 7.0,
            "flux_log": math.log1p(40.0 if family_a else 180.0),
        }
        chroma = [0.05] * 12
        chroma[0 if family_a else 7] = 0.45
        total = sum(chroma)
        points.append({
            "bin_index": index,
            "start_seconds": float(index),
            "end_seconds": float(index + 1),
            "coverage": 1.0,
            "values": values,
            "chroma": [value / total for value in chroma],
        })
        for runtime_id, active in (("kick", 0.15 if family_a else 0.95), ("vocal", 0.85 if family_a else 0.35)):
            track_rows[runtime_id][index] = {
                "frame_count": 10,
                "active_count": int(round(active * 10)),
                "coverage_mask": (1 << song.COVERAGE_SLOTS_PER_BIN) - 1,
            }
    _robust_normalize(points)
    boundaries, _meta = _detect_boundaries(points, track_rows, 8, 0.45, 12)
    times = [int(round(float(item["time_seconds"]))) for item in boundaries]
    if not any(abs(value - 24) <= 2 for value in times) or not any(abs(value - 48) <= 2 for value in times):
        raise RuntimeError(f"Section-boundary synthetic regression failed: {times}")

    def fake_section(section_id: str, family_a: bool, start: float, end: float) -> dict[str, Any]:
        return {
            "section_id": section_id,
            "start_seconds": start,
            "end_seconds": end,
            "summary": {
                "rms_db": -24.0 if family_a else -15.0,
                "lufs_s": -20.0 if family_a else -12.0,
                "centroid_hz": 900.0 if family_a else 2600.0,
                "stereo_correlation": 0.88 if family_a else 0.58,
                "stereo_width": 0.28 if family_a else 0.82,
                "crest_db": 11.0 if family_a else 7.0,
                "spectral_flux_mean": 0.04 if family_a else 0.18,
                "spectral_regions": {name: (-30.0 if family_a else -22.0) for name, _lo, _hi in song.SPECTRAL_REGIONS},
                "chroma": [1.0 if i == (0 if family_a else 7) else 0.0 for i in range(12)],
            },
            "activity_vector": {"kick": 0.15 if family_a else 0.95, "vocal": 0.85 if family_a else 0.35},
        }

    sections = [fake_section("S01", True, 0.0, 24.0), fake_section("S02", False, 24.0, 48.0), fake_section("S03", True, 48.0, 72.0)]
    pairs = _assign_families(sections, 0.78)
    if sections[0]["family_id"] != sections[2]["family_id"] or sections[0]["family_id"] == sections[1]["family_id"]:
        raise RuntimeError(f"Section-family synthetic regression failed: {[item['family_id'] for item in sections]}")
    recurrence = next(item for item in pairs if {item["section_a"], item["section_b"]} == {"S01", "S03"})
    if float(recurrence["similarity"]) < 0.9:
        raise RuntimeError(f"Section-similarity synthetic regression failed: {recurrence}")
    return {"boundary_times": times, "families": [item["family_id"] for item in sections]}
