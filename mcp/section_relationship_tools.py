#!/usr/bin/env python3
"""Bounded section-aware track-relationship shortlisting.

This MCP reasoning layer reuses Song Memory, Section Structure and Track Story
summaries. It identifies track pairs whose measured relationship is worth a
closer look in particular sections/families without calling the pair a mix
problem or prescribing processing.
"""

from __future__ import annotations

import math
from collections import defaultdict
from itertools import combinations
from typing import Any

import server as core
import section_tools as structure
import song_tools as song
import track_story_tools as story

DEFAULT_MAX_PAIRS = 12
DEFAULT_MAX_TRACKS = 32
MAX_SECTION_TRACK_CANDIDATES = 24
MIN_RELATION_COVERAGE = story.MIN_STORY_COVERAGE
DEFAULT_MIN_ACTIVITY_OVERLAP = 0.15
DEFAULT_MIN_SHORTLIST_PRIORITY = 0.18


def _safe_float(value: Any) -> float | None:
    return story._safe_float(value)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def _spectral_shape(entry: dict[str, Any]) -> list[float] | None:
    regions = entry.get("spectral_regions") or {}
    powers: list[float] = []
    for name, _lo, _hi in song.SPECTRAL_REGIONS:
        db = _safe_float(regions.get(name))
        if db is None:
            return None
        powers.append(math.pow(10.0, db / 10.0))
    total = sum(powers)
    if total <= 1.0e-20:
        return None
    return [value / total for value in powers]


def _spectral_overlap(a: dict[str, Any], b: dict[str, Any]) -> float | None:
    left = _spectral_shape(a)
    right = _spectral_shape(b)
    if left is None or right is None:
        return None
    return _clamp(sum(min(x, y) for x, y in zip(left, right)))


def _proximity(delta: float | None, full_scale: float) -> float | None:
    if delta is None:
        return None
    return 1.0 - _clamp(abs(float(delta)) / max(1.0e-9, float(full_scale)))


def _weighted_mean(parts: list[tuple[float | None, float]]) -> float | None:
    available = [(float(value), float(weight)) for value, weight in parts if value is not None]
    weight_sum = sum(weight for _value, weight in available)
    if weight_sum <= 0.0:
        return None
    return sum(value * weight for value, weight in available) / weight_sum


def _pair_id(runtime_a: str, runtime_b: str) -> str:
    left, right = sorted((str(runtime_a), str(runtime_b)))
    return f"{left}::{right}"


def _track_public(runtime_id: str) -> dict[str, Any]:
    return {
        "runtime_id": runtime_id,
        "selector": song._binding_selector(runtime_id),
        "display_name": song._display_name(runtime_id),
        "is_master": song._is_master(runtime_id),
    }


def _directional_region_deltas(a: dict[str, Any], b: dict[str, Any]) -> tuple[dict[str, float | None], list[dict[str, Any]]]:
    left = a.get("spectral_regions") or {}
    right = b.get("spectral_regions") or {}
    deltas: dict[str, float | None] = {}
    ranked: list[tuple[float, str, float]] = []
    for name, _lo, _hi in song.SPECTRAL_REGIONS:
        va = _safe_float(left.get(name))
        vb = _safe_float(right.get(name))
        delta = None if va is None or vb is None else vb - va
        deltas[name] = None if delta is None else round(delta, 5)
        if delta is not None:
            ranked.append((abs(delta), name, delta))
    ranked.sort(reverse=True)
    strongest = [
        {
            "region": name,
            "b_minus_a_db": round(delta, 5),
            "stronger_runtime_id": b["runtime_id"] if delta > 0.0 else a["runtime_id"] if delta < 0.0 else None,
        }
        for _magnitude, name, delta in ranked[:3]
    ]
    return deltas, strongest


def _pair_section_evidence(
    section: dict[str, Any],
    a: dict[str, Any] | None,
    b: dict[str, Any] | None,
    min_activity_overlap: float,
    min_shortlist_priority: float,
) -> dict[str, Any]:
    base = {
        "section_id": section["section_id"],
        "family_id": section["family_id"],
        "start_seconds": section["start_seconds"],
        "end_seconds": section["end_seconds"],
    }
    if a is None or b is None:
        return {
            **base,
            "evidence_available": False,
            "shortlisted": False,
            "status": "missing_track_evidence",
            "coverage_ratio_min": None,
        }

    coverage_a = _safe_float(a.get("coverage_ratio")) or 0.0
    coverage_b = _safe_float(b.get("coverage_ratio")) or 0.0
    coverage_min = min(coverage_a, coverage_b)
    if not a.get("evidence_available") or not b.get("evidence_available") or coverage_min < MIN_RELATION_COVERAGE:
        return {
            **base,
            "evidence_available": False,
            "shortlisted": False,
            "status": "insufficient_coverage",
            "coverage_ratio_min": round(coverage_min, 4),
        }

    active_a = _safe_float(a.get("active_ratio"))
    active_b = _safe_float(b.get("active_ratio"))
    if active_a is None or active_b is None:
        return {
            **base,
            "evidence_available": False,
            "shortlisted": False,
            "status": "missing_activity_evidence",
            "coverage_ratio_min": round(coverage_min, 4),
        }

    active_overlap = _clamp(min(active_a, active_b))
    rms_a = _safe_float(a.get("rms_db"))
    rms_b = _safe_float(b.get("rms_db"))
    rms_delta = None if rms_a is None or rms_b is None else rms_b - rms_a
    width_a = _safe_float(a.get("stereo_width"))
    width_b = _safe_float(b.get("stereo_width"))
    width_delta = None if width_a is None or width_b is None else width_b - width_a
    spectral = _spectral_overlap(a, b)
    level_proximity = _proximity(rms_delta, 24.0)
    stereo_proximity = _proximity(width_delta, 1.5)
    shape_proximity = _weighted_mean(
        [
            (spectral, 0.50),
            (level_proximity, 0.30),
            (stereo_proximity, 0.20),
        ]
    )
    priority = None if shape_proximity is None else active_overlap * shape_proximity
    shortlisted = bool(
        active_overlap >= min_activity_overlap
        and priority is not None
        and priority >= min_shortlist_priority
    )

    region_deltas, strongest_regions = _directional_region_deltas(a, b)
    louder_runtime_id = None
    if rms_delta is not None and abs(rms_delta) >= 0.25:
        louder_runtime_id = b["runtime_id"] if rms_delta > 0.0 else a["runtime_id"]

    status = "shortlisted" if shortlisted else "below_shortlist_threshold"
    if active_overlap < min_activity_overlap:
        status = "insufficient_activity_overlap"

    return {
        **base,
        "evidence_available": True,
        "shortlisted": shortlisted,
        "status": status,
        "coverage_ratio_min": round(coverage_min, 4),
        "activity_overlap": round(active_overlap, 5),
        "coarse_spectral_shape_overlap": None if spectral is None else round(spectral, 5),
        "level_proximity": None if level_proximity is None else round(level_proximity, 5),
        "stereo_width_proximity": None if stereo_proximity is None else round(stereo_proximity, 5),
        "shortlist_priority": None if priority is None else round(priority, 5),
        "rms_db_b_minus_a": None if rms_delta is None else round(rms_delta, 5),
        "louder_runtime_id": louder_runtime_id,
        "stereo_width_b_minus_a": None if width_delta is None else round(width_delta, 5),
        "spectral_region_b_minus_a_db": region_deltas,
        "strongest_directional_regions": strongest_regions,
    }


def _family_presence(section_evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in section_evidence:
        grouped[str(item["family_id"])].append(item)

    result: list[dict[str, Any]] = []
    for family_id, items in grouped.items():
        observed = [item for item in items if item.get("evidence_available")]
        shortlisted = [item for item in observed if item.get("shortlisted")]
        unavailable = [item for item in items if not item.get("evidence_available")]
        priorities = [
            float(value)
            for item in shortlisted
            if (value := _safe_float(item.get("shortlist_priority"))) is not None
        ]
        result.append({
            "family_id": family_id,
            "section_ids": [item["section_id"] for item in items],
            "observed_section_count": len(observed),
            "shortlisted_section_ids": [item["section_id"] for item in shortlisted],
            "unavailable_section_ids": [item["section_id"] for item in unavailable],
            "shortlisted_ratio": None if not observed else round(len(shortlisted) / len(observed), 5),
            "max_shortlist_priority": None if not priorities else round(max(priorities), 5),
        })
    return result


def _adjacent_changes(section_evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for previous, current in zip(section_evidence, section_evidence[1:]):
        if not previous.get("evidence_available") or not current.get("evidence_available"):
            if previous.get("evidence_available") != current.get("evidence_available"):
                changes.append({
                    "from_section_id": previous["section_id"],
                    "to_section_id": current["section_id"],
                    "change": "evidence_availability_changed",
                })
            continue

        before_shortlisted = bool(previous.get("shortlisted"))
        after_shortlisted = bool(current.get("shortlisted"))
        if before_shortlisted != after_shortlisted:
            changes.append({
                "from_section_id": previous["section_id"],
                "to_section_id": current["section_id"],
                "change": "entered_shortlist" if after_shortlisted else "left_shortlist",
                "from_family_id": previous["family_id"],
                "to_family_id": current["family_id"],
            })
            continue

        if before_shortlisted and after_shortlisted:
            changes.append({
                "from_section_id": previous["section_id"],
                "to_section_id": current["section_id"],
                "change": "relationship_evidence_changed",
                "shortlist_priority_delta": round(
                    float(current["shortlist_priority"]) - float(previous["shortlist_priority"]), 5
                ),
                "activity_overlap_delta": round(
                    float(current["activity_overlap"]) - float(previous["activity_overlap"]), 5
                ),
                "coarse_spectral_shape_overlap_delta": None
                if previous.get("coarse_spectral_shape_overlap") is None or current.get("coarse_spectral_shape_overlap") is None
                else round(
                    float(current["coarse_spectral_shape_overlap"])
                    - float(previous["coarse_spectral_shape_overlap"]),
                    5,
                ),
            })
    return changes


def _resolve_map(map_id: str | None) -> tuple[str | None, dict[str, Any] | None, bool]:
    resolved_map_id, cached = story._cached_map(map_id)
    generated = False
    if cached is None and map_id is None:
        resolved_map_id, cached = story._build_default_map()
        generated = story._map_is_usable(cached)
    return resolved_map_id, cached, generated


@core.mcp.tool()
def audio_section_relationships(
    map_id: str | None = None,
    max_pairs: int = DEFAULT_MAX_PAIRS,
    max_tracks: int = DEFAULT_MAX_TRACKS,
    include_master: bool = False,
    min_activity_overlap: float = DEFAULT_MIN_ACTIVITY_OVERLAP,
    min_shortlist_priority: float = DEFAULT_MIN_SHORTLIST_PRIORITY,
) -> dict[str, Any]:
    """Return a bounded shortlist of track relationships that vary across song sections."""
    resolved_map_id, cached, generated = _resolve_map(map_id)
    if not story._map_is_usable(cached) or resolved_map_id is None:
        reason = "No usable cached section map. Call audio_section_map() after collecting transport-aligned Song Memory."
        if isinstance(cached, dict) and cached.get("reason"):
            reason = str(cached["reason"])
        return {"available": False, "map_id": resolved_map_id, "reason": reason}

    max_pairs = max(1, min(int(max_pairs), 32))
    max_tracks = max(2, min(int(max_tracks), 64))
    min_activity_overlap = _clamp(float(min_activity_overlap), 0.0, 1.0)
    min_shortlist_priority = _clamp(float(min_shortlist_priority), 0.0, 1.0)

    with core._lock:
        runtime_ids = sorted(list(core._tracks), key=song._runtime_sort_key)
    if not include_master:
        runtime_ids = [runtime_id for runtime_id in runtime_ids if not song._is_master(runtime_id)]
    project_track_count = len(runtime_ids)
    runtime_ids = runtime_ids[:max_tracks]

    selections: dict[str, dict[str, Any]] = {}
    for runtime_id in runtime_ids:
        selection = story._selection_for_track(runtime_id, cached)
        if selection is not None:
            selections[runtime_id] = selection

    section_entries: dict[str, dict[str, dict[str, Any]]] = {}
    candidate_keys: set[str] = set()
    candidate_scores: dict[str, list[float]] = defaultdict(list)
    candidate_tracks: dict[str, tuple[str, str]] = {}
    section_track_truncation = False

    for section in cached["sections"]:
        entries: dict[str, dict[str, Any]] = {}
        for runtime_id, selection in selections.items():
            entry = story._build_section_entry(section, selection)
            entry["runtime_id"] = runtime_id
            entries[runtime_id] = entry

        section_entries[str(section["section_id"])] = entries
        observed = [
            entry for entry in entries.values()
            if entry.get("evidence_available") and (_safe_float(entry.get("active_ratio")) or 0.0) > 0.0
        ]
        observed.sort(
            key=lambda entry: _safe_float(entry.get("active_ratio")) or 0.0,
            reverse=True,
        )
        if len(observed) > MAX_SECTION_TRACK_CANDIDATES:
            section_track_truncation = True
        observed = observed[:MAX_SECTION_TRACK_CANDIDATES]

        for a, b in combinations(observed, 2):
            evidence = _pair_section_evidence(
                section,
                a,
                b,
                min_activity_overlap,
                min_shortlist_priority,
            )
            if not evidence.get("shortlisted"):
                continue
            key = _pair_id(a["runtime_id"], b["runtime_id"])
            candidate_keys.add(key)
            candidate_tracks[key] = tuple(sorted((str(a["runtime_id"]), str(b["runtime_id"]))))
            priority = _safe_float(evidence.get("shortlist_priority"))
            if priority is not None:
                candidate_scores[key].append(priority)

    ranked_keys = sorted(
        candidate_keys,
        key=lambda key: (
            max(candidate_scores.get(key, [0.0])),
            sum(candidate_scores.get(key, [0.0])) / max(1, len(candidate_scores.get(key, []))),
            key,
        ),
        reverse=True,
    )
    selected_keys = ranked_keys[:max_pairs]

    relationships: list[dict[str, Any]] = []
    for key in selected_keys:
        runtime_a, runtime_b = candidate_tracks[key]
        section_evidence: list[dict[str, Any]] = []
        for section in cached["sections"]:
            entries = section_entries[str(section["section_id"])]
            section_evidence.append(
                _pair_section_evidence(
                    section,
                    entries.get(runtime_a),
                    entries.get(runtime_b),
                    min_activity_overlap,
                    min_shortlist_priority,
                )
            )

        families = _family_presence(section_evidence)
        present_families = [
            item["family_id"] for item in families if item["shortlisted_section_ids"]
        ]
        absent_families = [
            item["family_id"]
            for item in families
            if item["observed_section_count"] > 0 and not item["shortlisted_section_ids"]
        ]
        priorities = [
            float(value)
            for item in section_evidence
            if item.get("shortlisted") and (value := _safe_float(item.get("shortlist_priority"))) is not None
        ]
        relationships.append({
            "pair_id": key,
            "track_a": _track_public(runtime_a),
            "track_b": _track_public(runtime_b),
            "shortlisted_section_ids": [
                item["section_id"] for item in section_evidence if item.get("shortlisted")
            ],
            "present_family_ids": present_families,
            "observed_but_not_shortlisted_family_ids": absent_families,
            "max_shortlist_priority": None if not priorities else round(max(priorities), 5),
            "mean_shortlist_priority": None if not priorities else round(sum(priorities) / len(priorities), 5),
            "family_presence": families,
            "adjacent_changes": _adjacent_changes(section_evidence),
            "section_evidence": section_evidence,
        })

    warnings: list[str] = []
    if project_track_count > max_tracks:
        warnings.append(
            f"Project has {project_track_count} eligible Analyzer tracks; only the first {max_tracks} deterministic selectors were considered."
        )
    if section_track_truncation:
        warnings.append(
            f"At least one section had more than {MAX_SECTION_TRACK_CANDIDATES} active/covered tracks; pair evaluation was capped by activity to keep work bounded."
        )
    if len(ranked_keys) > max_pairs:
        warnings.append(
            f"{len(ranked_keys)} candidate pairs passed the shortlist threshold; only the top {max_pairs} are returned."
        )
    if not relationships:
        warnings.append(
            "No pair passed the current bounded shortlist thresholds. This does not prove the mix has no interaction or masking issues."
        )

    return {
        "available": True,
        "map_id": resolved_map_id,
        "generated_section_map": generated,
        "include_master": bool(include_master),
        "eligible_project_track_count": project_track_count,
        "evaluated_track_count": len(selections),
        "section_track_candidate_cap": MAX_SECTION_TRACK_CANDIDATES,
        "candidate_pair_count_before_limit": len(ranked_keys),
        "returned_pair_count": len(relationships),
        "thresholds": {
            "minimum_coverage_ratio": MIN_RELATION_COVERAGE,
            "minimum_activity_overlap": round(min_activity_overlap, 5),
            "minimum_shortlist_priority": round(min_shortlist_priority, 5),
        },
        "relationships": relationships,
        "warnings": warnings,
        "semantics": {
            "shortlist_priority": "A bounded ranking heuristic for deciding which measured pair/section deserves deeper inspection. It is not a masking probability, audibility probability, quality score, or proof of a mix problem.",
            "activity": "Both tracks need observed overlapping activity. Low activity or missing coverage is not interpreted as muting or absence from the arrangement.",
            "direction": "B-minus-A level/spectral/stereo fields preserve pair direction only; they do not imply which track should be processed.",
            "family": "A/B/C family IDs are neutral recurring-structure labels, not semantic Verse/Chorus/Drop names.",
            "follow_up": "For deeper recent-window masking/stereo/temporal evidence, replay or select the relevant section before calling pair-specific tools so the measured window matches the reported song context.",
        },
        "note": "This project-level tool deliberately shortlists a bounded number of pair/section relationships. It does not emit all possible pairs and does not prescribe EQ, sidechain, compression, panning, widening, or other processing.",
    }


def _self_test() -> dict[str, Any]:
    section_a = {"section_id": "S01", "family_id": "A", "start_seconds": 0.0, "end_seconds": 16.0}
    section_b = {"section_id": "S02", "family_id": "B", "start_seconds": 16.0, "end_seconds": 32.0}
    section_c = {"section_id": "S03", "family_id": "A", "start_seconds": 32.0, "end_seconds": 48.0}

    def entry(runtime_id: str, active: float, rms: float, width: float, coverage: float) -> dict[str, Any]:
        return {
            "runtime_id": runtime_id,
            "evidence_available": coverage >= MIN_RELATION_COVERAGE,
            "coverage_ratio": coverage,
            "active_ratio": active,
            "rms_db": rms,
            "stereo_width": width,
            "spectral_regions": {
                name: rms - index * 1.5 for index, (name, _lo, _hi) in enumerate(song.SPECTRAL_REGIONS)
            },
        }

    left_a = entry("a", 0.90, -18.0, 0.50, 1.0)
    right_a = entry("b", 0.85, -19.0, 0.55, 1.0)
    left_b = entry("a", 0.90, -18.0, 0.50, 1.0)
    right_b = entry("b", 0.03, -28.0, 0.80, 1.0)
    left_c = entry("a", 0.90, -18.0, 0.50, 1.0)
    right_c = entry("b", 0.85, -19.0, 0.55, 0.10)

    first = _pair_section_evidence(section_a, left_a, right_a, 0.15, 0.18)
    second = _pair_section_evidence(section_b, left_b, right_b, 0.15, 0.18)
    third = _pair_section_evidence(section_c, left_c, right_c, 0.15, 0.18)
    if not first["shortlisted"]:
        raise RuntimeError(f"Section relationship shortlist regression failed: {first}")
    if second["shortlisted"] or second["status"] != "insufficient_activity_overlap":
        raise RuntimeError(f"Section relationship disappearance regression failed: {second}")
    if third["evidence_available"] or third["status"] != "insufficient_coverage":
        raise RuntimeError(f"Section relationship coverage guard failed: {third}")

    families = _family_presence([first, second, third])
    family_a = next(item for item in families if item["family_id"] == "A")
    family_b = next(item for item in families if item["family_id"] == "B")
    if family_a["shortlisted_section_ids"] != ["S01"] or family_a["unavailable_section_ids"] != ["S03"]:
        raise RuntimeError(f"Section relationship family A regression failed: {family_a}")
    if family_b["shortlisted_section_ids"]:
        raise RuntimeError(f"Section relationship family B should not be shortlisted: {family_b}")

    changes = _adjacent_changes([first, second, third])
    if not any(item["change"] == "left_shortlist" for item in changes):
        raise RuntimeError(f"Section relationship transition regression failed: {changes}")

    return {
        "shortlist_priority": first["shortlist_priority"],
        "family_a_present": "S01",
        "family_b_absent": "ok",
        "low_coverage_guard": "ok",
    }
