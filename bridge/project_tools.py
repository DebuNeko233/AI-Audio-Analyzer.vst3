#!/usr/bin/env python3
"""Project-level MCP tools for AI Audio Analyzer Bridge 0.5.

This module layers project intelligence and A/B snapshots on top of the stable
0.4 bridge without changing the OSC protocol or VST3 DSP.
"""

from __future__ import annotations

import copy
import math
import threading
import time
from collections import Counter
from typing import Any

import server as core

PROJECT_SNAPSHOT_LIMIT = 16
DEFAULT_OVERVIEW_SECONDS = 10.0

_snapshot_lock = threading.RLock()
_project_snapshots: dict[str, dict[str, Any]] = {}


def _clamp_seconds(seconds: float) -> float:
    return max(0.5, min(float(seconds), 60.0))


def _binding_selector(binding: dict[str, Any] | None, runtime_id: str) -> str:
    if binding is None:
        return runtime_id
    return f"mixer:{int(binding['fl_track_index'])}/slot:{int(binding['slot'])}"


def _display_name(avg: dict[str, Any]) -> str:
    binding = avg.get("binding")
    if binding:
        return str(binding.get("fl_track_name") or avg.get("track") or avg.get("id"))
    return str(avg.get("track") or avg.get("id"))


def _is_master(avg: dict[str, Any]) -> bool:
    binding = avg.get("binding")
    if binding is not None:
        if int(binding.get("fl_track_index", -1)) == 0:
            return True
        if str(binding.get("fl_track_name", "")).casefold() == "master":
            return True
    return str(avg.get("track", "")).casefold() == "master"


def _safe_delta(before: Any, after: Any, digits: int = 4) -> float | None:
    if before is None or after is None:
        return None
    try:
        a = float(before)
        b = float(after)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(a) and math.isfinite(b)):
        return None
    return round(b - a, digits)


def _range_db(bands_db: list[float] | None, lo_hz: float, hi_hz: float) -> float | None:
    if not bands_db:
        return None
    powers = [
        10.0 ** (float(db) / 10.0)
        for center, db in zip(core.BAND_CENTERS, bands_db)
        if lo_hz <= center < hi_hz and math.isfinite(float(db))
    ]
    if not powers:
        return None
    return 10.0 * math.log10(max(sum(powers) / len(powers), 1e-12))


def _spectral_regions(bands_db: list[float] | None) -> dict[str, float | None]:
    return {
        "sub_20_120_db": _range_db(bands_db, 20.0, 120.0),
        "low_mid_120_500_db": _range_db(bands_db, 120.0, 500.0),
        "mid_500_2000_db": _range_db(bands_db, 500.0, 2000.0),
        "presence_2000_5000_db": _range_db(bands_db, 2000.0, 5000.0),
        "high_5000_20000_db": _range_db(bands_db, 5000.0, 20000.0),
    }


def _overlap_score(a_bands: list[float] | None, b_bands: list[float] | None) -> float | None:
    if not a_bands or not b_bands:
        return None
    if len(a_bands) != len(b_bands):
        return None

    max_a = max(float(value) for value in a_bands)
    max_b = max(float(value) for value in b_bands)
    scores: list[float] = []
    for db_a, db_b in zip(a_bands, b_bands):
        rel_a = 10.0 ** ((float(db_a) - max_a) / 10.0)
        rel_b = 10.0 ** ((float(db_b) - max_b) / 10.0)
        scores.append(min(rel_a, rel_b))
    strongest = sorted(scores, reverse=True)[:5]
    if not strongest:
        return None
    return round(sum(strongest) / len(strongest), 4)


def _average_for_runtime(runtime_id: str, seconds: float) -> dict[str, Any]:
    avg = core.audio_average(runtime_id, seconds)
    binding = avg.get("binding")
    avg["selector"] = _binding_selector(binding, runtime_id)
    avg["display_name"] = _display_name(avg)
    avg["spectral_regions"] = _spectral_regions(avg.get("bands_db"))
    return avg


def _live_runtime_ids() -> list[str]:
    with core._lock:
        frames = {runtime_id: dict(frame) for runtime_id, frame in core._tracks.items()}
        bindings = {runtime_id: dict(binding) for runtime_id, binding in core._bindings.items()}

    def sort_key(runtime_id: str) -> tuple[int, int, str, str]:
        frame = frames[runtime_id]
        binding = bindings.get(runtime_id)
        if binding is None:
            return (1, 9999, str(frame.get("track", "")).casefold(), runtime_id)
        return (
            0,
            int(binding.get("fl_track_index", 9999)),
            str(binding.get("fl_track_name", frame.get("track", ""))).casefold(),
            runtime_id,
        )

    return sorted(frames, key=sort_key)


def _capture_state(seconds: float) -> dict[str, Any]:
    runtime_ids = _live_runtime_ids()
    tracks: dict[str, dict[str, Any]] = {}

    for runtime_id in runtime_ids:
        avg = _average_for_runtime(runtime_id, seconds)
        binding = avg.get("binding")
        identity = _binding_selector(binding, runtime_id)
        tracks[identity] = {
            "identity": identity,
            "runtime_id": runtime_id,
            "display_name": avg["display_name"],
            "analyzer_name": avg.get("track"),
            "binding": copy.deepcopy(binding),
            "signal_present": avg.get("signal_present"),
            "analysis_valid": bool(avg.get("analysis_valid", avg.get("signal_present"))),
            "active_ratio": avg.get(
                "active_ratio",
                1.0 if avg.get("signal_present") else 0.0,
            ),
            "peak_db": avg.get("peak_db"),
            "rms_db": avg.get("rms_db"),
            "crest_db": avg.get("crest_db"),
            "lufs_s": avg.get("lufs_s"),
            "lufs_i": avg.get("lufs_i"),
            "true_peak_dbtp": avg.get("true_peak_dbtp"),
            "max_true_peak_dbtp": avg.get("max_true_peak_dbtp"),
            "centroid_hz": avg.get("centroid_hz"),
            "rolloff_hz": avg.get("rolloff_hz"),
            "flatness": avg.get("flatness"),
            "stereo_correlation": avg.get("stereo_correlation"),
            "stereo_width": avg.get("stereo_width"),
            "bands_db": copy.deepcopy(avg.get("bands_db")),
            "spectral_regions": copy.deepcopy(avg.get("spectral_regions")),
        }

    return {
        "captured_at": time.time(),
        "window_seconds": seconds,
        "tracks": tracks,
    }


@core.mcp.tool()
def audio_project_status() -> dict[str, Any]:
    """Summarize project-level Analyzer readiness, mapping completeness, and signal state."""
    now = time.time()
    with core._lock:
        frames = {runtime_id: dict(frame) for runtime_id, frame in core._tracks.items()}
        bindings = {runtime_id: dict(binding) for runtime_id, binding in core._bindings.items()}
        osc_listening = bool(core._osc_listening)
        osc_error = core._osc_error

    duplicate_counts = Counter(str(frame.get("track", "")).casefold() for frame in frames.values())
    instances: list[dict[str, Any]] = []
    master_candidates: list[dict[str, Any]] = []

    for runtime_id in _live_runtime_ids():
        frame = frames[runtime_id]
        binding = bindings.get(runtime_id)
        age = max(0.0, now - float(frame.get("_received_at", now)))
        item = {
            "runtime_id": runtime_id,
            "analyzer_name": frame.get("track"),
            "selector": _binding_selector(binding, runtime_id),
            "bound": binding is not None,
            "binding": core._binding_public(binding),
            "signal_present": bool(frame.get("signal_present")),
            "duplicate_name": duplicate_counts[str(frame.get("track", "")).casefold()] > 1,
            "stale": age > core.STALE_SECONDS,
            "age_seconds": round(age, 3),
        }
        instances.append(item)
        if (
            (binding is not None and int(binding.get("fl_track_index", -1)) == 0)
            or str(frame.get("track", "")).casefold() == "master"
            or (binding is not None and str(binding.get("fl_track_name", "")).casefold() == "master")
        ):
            master_candidates.append(item)

    live_count = len(instances)
    bound_count = sum(1 for item in instances if item["bound"])
    active_count = sum(1 for item in instances if item["signal_present"] and not item["stale"])
    stale_count = sum(1 for item in instances if item["stale"])
    duplicate_groups = sum(1 for count in duplicate_counts.values() if count > 1)

    warnings: list[str] = []
    if not osc_listening or osc_error:
        warnings.append("Analyzer OSC listener is not healthy.")
    if live_count == 0:
        warnings.append("No live AI Audio Analyzer instances are currently visible.")
    if live_count and bound_count < live_count:
        warnings.append("Some Analyzer instances are not yet bound to FL Mixer Track/Slot.")
    if duplicate_groups:
        warnings.append("Duplicate Analyzer display names exist; use deterministic bindings or runtime IDs.")
    if stale_count:
        warnings.append("Some Analyzer streams are stale.")
    if not master_candidates:
        warnings.append("No Master Analyzer could be identified from current names/bindings.")

    return {
        "ok": bool(osc_listening and osc_error is None),
        "project_ready": bool(live_count and bound_count == live_count and stale_count == 0),
        "audio_ready": active_count > 0,
        "live_count": live_count,
        "bound_count": bound_count,
        "unbound_count": live_count - bound_count,
        "active_count": active_count,
        "silent_count": sum(1 for item in instances if not item["signal_present"]),
        "stale_count": stale_count,
        "duplicate_name_groups": duplicate_groups,
        "master_candidates": master_candidates,
        "instances": instances,
        "warnings": warnings,
        "recommended_next_step": (
            "Run Identify mapping for unbound instances before project-wide analysis."
            if live_count and bound_count < live_count
            else "Start playback and use audio_mix_overview() for project-level analysis."
            if live_count and active_count == 0
            else "Project-level Analyzer state is ready for analysis."
        ),
    }


@core.mcp.tool()
def audio_mix_overview(seconds: float = DEFAULT_OVERVIEW_SECONDS, max_tracks: int = 32) -> dict[str, Any]:
    """Return one project-wide recent mix summary plus candidate spectral conflicts."""
    seconds = _clamp_seconds(seconds)
    max_tracks = max(1, min(int(max_tracks), 64))
    runtime_ids = _live_runtime_ids()[:max_tracks]

    tracks: list[dict[str, Any]] = []
    for runtime_id in runtime_ids:
        avg = _average_for_runtime(runtime_id, seconds)
        tracks.append(
            {
                "runtime_id": runtime_id,
                "selector": avg["selector"],
                "display_name": avg["display_name"],
                "analyzer_name": avg.get("track"),
                "binding": avg.get("binding"),
                "signal_present": avg.get("signal_present"),
                "analysis_valid": bool(avg.get("analysis_valid", avg.get("signal_present"))),
                "active_ratio": avg.get("active_ratio"),
                "peak_db": avg.get("peak_db"),
                "rms_db": avg.get("rms_db"),
                "crest_db": avg.get("crest_db"),
                "lufs_s": avg.get("lufs_s"),
                "lufs_i": avg.get("lufs_i"),
                "true_peak_dbtp": avg.get("true_peak_dbtp"),
                "max_true_peak_dbtp": avg.get("max_true_peak_dbtp"),
                "centroid_hz": avg.get("centroid_hz"),
                "stereo_correlation": avg.get("stereo_correlation"),
                "stereo_width": avg.get("stereo_width"),
                "spectral_regions": avg.get("spectral_regions"),
                "_bands_db": avg.get("bands_db"),
            }
        )

    potential_conflicts: list[dict[str, Any]] = []
    usable = [item for item in tracks if item["analysis_valid"] and item.get("_bands_db") and not _is_master(item)]
    for index, a in enumerate(usable):
        for b in usable[index + 1 :]:
            binding_a = a.get("binding")
            binding_b = b.get("binding")
            if (
                binding_a is not None
                and binding_b is not None
                and int(binding_a.get("fl_track_index", -1)) == int(binding_b.get("fl_track_index", -2))
            ):
                continue
            score = _overlap_score(a.get("_bands_db"), b.get("_bands_db"))
            if score is None or score < 0.15:
                continue
            potential_conflicts.append(
                {
                    "track_a": a["display_name"],
                    "selector_a": a["selector"],
                    "track_b": b["display_name"],
                    "selector_b": b["selector"],
                    "spectral_overlap_score": score,
                }
            )

    potential_conflicts.sort(key=lambda item: item["spectral_overlap_score"], reverse=True)
    potential_conflicts = potential_conflicts[:8]

    for item in tracks:
        item.pop("_bands_db", None)

    masters = [item for item in tracks if _is_master(item)]
    active_count = sum(1 for item in tracks if item["analysis_valid"])

    return {
        "window_seconds": seconds,
        "track_count": len(tracks),
        "active_track_count": active_count,
        "master": masters[0] if len(masters) == 1 else None,
        "master_candidates": masters if len(masters) != 1 else [],
        "tracks": tracks,
        "potential_spectral_conflicts": potential_conflicts,
        "note": (
            "Project overview uses recent active-frame averages. Potential conflicts are heuristic relative spectral overlap, "
            "not proof of audible masking. Routed buses can naturally resemble their source tracks."
        ),
    }


@core.mcp.tool()
def audio_capture_snapshot(name: str, seconds: float = 5.0) -> dict[str, Any]:
    """Capture a named project-level recent-analysis snapshot for later A/B comparison."""
    clean_name = str(name).strip()
    if not clean_name:
        raise ValueError("Snapshot name must not be empty.")
    if len(clean_name) > 64:
        raise ValueError("Snapshot name must be 64 characters or fewer.")

    seconds = _clamp_seconds(seconds)
    state = _capture_state(seconds)
    state["name"] = clean_name

    with _snapshot_lock:
        if clean_name in _project_snapshots:
            del _project_snapshots[clean_name]
        _project_snapshots[clean_name] = state
        while len(_project_snapshots) > PROJECT_SNAPSHOT_LIMIT:
            oldest = next(iter(_project_snapshots))
            del _project_snapshots[oldest]

    return {
        "ok": True,
        "name": clean_name,
        "captured_at": state["captured_at"],
        "window_seconds": seconds,
        "track_count": len(state["tracks"]),
        "tracks": [
            {
                "identity": identity,
                "display_name": track["display_name"],
                "analysis_valid": track["analysis_valid"],
                "active_ratio": track["active_ratio"],
            }
            for identity, track in state["tracks"].items()
        ],
        "note": (
            "Snapshots are bridge-session memory only. For meaningful A/B, play the same musical section for comparable durations."
        ),
    }


@core.mcp.tool()
def audio_list_snapshots() -> dict[str, Any]:
    """List named project snapshots stored in the current bridge session."""
    now = time.time()
    with _snapshot_lock:
        snapshots = [copy.deepcopy(value) for value in _project_snapshots.values()]

    return {
        "count": len(snapshots),
        "snapshots": [
            {
                "name": snapshot["name"],
                "age_seconds": round(max(0.0, now - float(snapshot["captured_at"])), 3),
                "window_seconds": snapshot["window_seconds"],
                "track_count": len(snapshot["tracks"]),
            }
            for snapshot in snapshots
        ],
    }


@core.mcp.tool()
def audio_compare_snapshots(before: str, after: str) -> dict[str, Any]:
    """Compare two named project snapshots and return measurement deltas for A/B verification."""
    before_name = str(before).strip()
    after_name = str(after).strip()

    with _snapshot_lock:
        before_state = copy.deepcopy(_project_snapshots.get(before_name))
        after_state = copy.deepcopy(_project_snapshots.get(after_name))

    if before_state is None:
        raise ValueError(f"Unknown snapshot {before_name!r}. Use audio_list_snapshots() first.")
    if after_state is None:
        raise ValueError(f"Unknown snapshot {after_name!r}. Use audio_list_snapshots() first.")

    before_tracks = before_state["tracks"]
    after_tracks = after_state["tracks"]
    shared = sorted(set(before_tracks) & set(after_tracks))
    added = sorted(set(after_tracks) - set(before_tracks))
    removed = sorted(set(before_tracks) - set(after_tracks))

    comparisons: list[dict[str, Any]] = []
    for identity in shared:
        a = before_tracks[identity]
        b = after_tracks[identity]
        before_regions = a.get("spectral_regions") or {}
        after_regions = b.get("spectral_regions") or {}

        comparisons.append(
            {
                "identity": identity,
                "display_name_before": a.get("display_name"),
                "display_name_after": b.get("display_name"),
                "analysis_valid_before": a.get("analysis_valid"),
                "analysis_valid_after": b.get("analysis_valid"),
                "delta": {
                    "active_ratio": _safe_delta(a.get("active_ratio"), b.get("active_ratio")),
                    "peak_db": _safe_delta(a.get("peak_db"), b.get("peak_db")),
                    "rms_db": _safe_delta(a.get("rms_db"), b.get("rms_db")),
                    "crest_db": _safe_delta(a.get("crest_db"), b.get("crest_db")),
                    "lufs_s": _safe_delta(a.get("lufs_s"), b.get("lufs_s")),
                    "lufs_i": _safe_delta(a.get("lufs_i"), b.get("lufs_i")),
                    "true_peak_dbtp": _safe_delta(a.get("true_peak_dbtp"), b.get("true_peak_dbtp")),
                    "centroid_hz": _safe_delta(a.get("centroid_hz"), b.get("centroid_hz"), 2),
                    "stereo_correlation": _safe_delta(
                        a.get("stereo_correlation"), b.get("stereo_correlation")
                    ),
                    "stereo_width": _safe_delta(a.get("stereo_width"), b.get("stereo_width")),
                    "spectral_regions_db": {
                        key: _safe_delta(before_regions.get(key), after_regions.get(key))
                        for key in sorted(set(before_regions) | set(after_regions))
                    },
                },
            }
        )

    return {
        "before": {
            "name": before_name,
            "captured_at": before_state["captured_at"],
            "window_seconds": before_state["window_seconds"],
        },
        "after": {
            "name": after_name,
            "captured_at": after_state["captured_at"],
            "window_seconds": after_state["window_seconds"],
        },
        "shared_track_count": len(shared),
        "added_tracks": added,
        "removed_tracks": removed,
        "tracks": comparisons,
        "interpretation": {
            "db_delta": "positive means the After snapshot is higher/louder in that measurement or spectral region",
            "correlation_delta": "positive means more positively correlated; negative means less correlated/wider or more phase-opposed",
        },
        "note": (
            "Use the same musical section and similar active_ratio for controlled A/B. LUFS-I is session-integrated and continues accumulating, "
            "so LUFS-S, RMS, True Peak, spectrum and stereo changes are usually more useful for short A/B checks."
        ),
    }
