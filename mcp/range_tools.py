#!/usr/bin/env python3
"""Shared DAW-time range resolution for retained Analyzer Song Memory.

This module is intentionally MCP-side. It selects one instance-local transport
pass per Analyzer by coverage of an exact retained DAW-time range. Epoch numbers
are never assumed to match across Analyzer instances.
"""

from __future__ import annotations

import copy
import math
import time
from typing import Any

import server as core
import project_tools as project
import song_tools as song

DEFAULT_MINIMUM_COVERAGE = 0.8
MAX_RANGE_SECONDS = 1200.0


def normalize_range(start_seconds: float, end_seconds: float) -> dict[str, Any]:
    """Normalize a requested range to the one-second Song Memory resolution."""
    try:
        requested_start = float(start_seconds)
        requested_end = float(end_seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError("start_seconds and end_seconds must be finite numbers.") from exc
    if not (math.isfinite(requested_start) and math.isfinite(requested_end)):
        raise ValueError("start_seconds and end_seconds must be finite numbers.")
    if requested_start < 0.0:
        raise ValueError("start_seconds must be >= 0.")
    if requested_end <= requested_start:
        raise ValueError("end_seconds must be greater than start_seconds.")
    if requested_end - requested_start > MAX_RANGE_SECONDS:
        raise ValueError(f"Transport-range verification supports at most {MAX_RANGE_SECONDS:.0f} seconds per range.")

    resolution = float(song.TIMELINE_BIN_SECONDS)
    effective_start = math.floor(requested_start / resolution) * resolution
    effective_end = math.ceil(requested_end / resolution) * resolution
    if effective_end <= effective_start:
        effective_end = effective_start + resolution

    return {
        "requested_range": {
            "start_seconds": round(requested_start, 6),
            "end_seconds": round(requested_end, 6),
        },
        "effective_range": {
            "start_seconds": round(effective_start, 3),
            "end_seconds": round(effective_end, 3),
        },
        "resolution_seconds": resolution,
        "normalized": (
            abs(effective_start - requested_start) > 1.0e-9
            or abs(effective_end - requested_end) > 1.0e-9
        ),
    }


def _minimum_coverage(value: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("minimum_coverage must be a number.") from exc
    if not math.isfinite(numeric):
        raise ValueError("minimum_coverage must be finite.")
    return max(0.1, min(numeric, 1.0))


def _identity(runtime_id: str) -> tuple[str, str, dict[str, Any] | None, str]:
    with core._lock:
        frame = dict(core._tracks.get(runtime_id, {}))
        binding = copy.deepcopy(core._bindings.get(runtime_id))
    selector = project._binding_selector(binding, runtime_id)
    display_name = str(
        (binding or {}).get("fl_track_name")
        or frame.get("track")
        or runtime_id
    )
    analyzer_name = str(frame.get("track") or runtime_id)
    return selector, display_name, binding, analyzer_name


def canonical_target_selectors(target_selectors: list[str] | None) -> list[str]:
    if not target_selectors:
        return []
    canonical: list[str] = []
    seen: set[str] = set()
    for raw in target_selectors:
        runtime_id = core._resolve_track(str(raw).strip())
        selector, _display, _binding, _analyzer = _identity(runtime_id)
        if selector not in seen:
            seen.add(selector)
            canonical.append(selector)
    return canonical


def _feature_availability(summary: dict[str, Any]) -> dict[str, bool]:
    regions = summary.get("spectral_regions") or {}
    return {
        "core": int(summary.get("frame_count", 0) or 0) > 0,
        "loudness": summary.get("lufs_s") is not None or summary.get("true_peak_dbtp") is not None,
        "spectrum": summary.get("centroid_hz") is not None or any(value is not None for value in regions.values()),
        "stereo": summary.get("stereo_correlation") is not None or summary.get("stereo_width") is not None,
        "temporal": summary.get("spectral_flux_mean") is not None,
        "semantic": summary.get("chroma") is not None,
    }


def resolve_track_range(
    runtime_id: str,
    start_seconds: float,
    end_seconds: float,
    *,
    after_received_at: float | None = None,
    minimum_coverage: float = DEFAULT_MINIMUM_COVERAGE,
) -> dict[str, Any]:
    """Select the best retained instance-local pass for one normalized DAW range."""
    runtime_id = str(runtime_id)
    normalized = normalize_range(start_seconds, end_seconds)
    effective = normalized["effective_range"]
    start = float(effective["start_seconds"])
    end = float(effective["end_seconds"])
    expected = end - start
    minimum = _minimum_coverage(minimum_coverage)

    candidates: list[dict[str, Any]] = []
    for epoch in song._available_epochs(runtime_id):
        rows = [
            row
            for row in song._bins_for(runtime_id, epoch)
            if float(row["end_seconds"]) > start and float(row["start_seconds"]) < end
        ]
        if not rows:
            continue

        first_received = min(float(row["first_received_at"]) for row in rows)
        last_received = max(float(row["last_received_at"]) for row in rows)
        if after_received_at is not None and first_received <= float(after_received_at):
            # A post-change candidate must be a clean retained pass for the range,
            # not a pre-change accumulator that merely received more frames later.
            continue

        summary = song._finalize_rows(
            rows,
            start_seconds=start,
            end_seconds=end,
            expected_seconds=expected,
        )
        coverage = float((summary.get("data_quality") or {}).get("coverage_ratio") or 0.0)
        candidates.append(
            {
                "transport_epoch": int(epoch),
                "summary": summary,
                "coverage_ratio": coverage,
                "first_received_at": first_received,
                "last_received_at": last_received,
            }
        )

    selector, display_name, _binding, _analyzer_name = _identity(runtime_id)
    if not candidates:
        return {
            "available": False,
            "runtime_id": runtime_id,
            "selector": selector,
            "display_name": display_name,
            **normalized,
            "minimum_coverage": minimum,
            "after_received_at": after_received_at,
            "reason": (
                "No retained transport pass cleanly covers the requested effective range after the required receive-time fence."
                if after_received_at is not None
                else "No retained transport pass overlaps the requested effective range."
            ),
        }

    selected = max(
        candidates,
        key=lambda item: (
            float(item["coverage_ratio"]),
            float(item["last_received_at"]),
            int(item["transport_epoch"]),
        ),
    )
    summary = copy.deepcopy(selected["summary"])
    coverage = float(selected["coverage_ratio"])
    warnings: list[str] = []
    if coverage < minimum:
        warnings.append(
            f"Best retained pass covers only {coverage:.3f} of the effective range; minimum required coverage is {minimum:.3f}."
        )

    return {
        "available": True,
        "adequate_coverage": coverage >= minimum,
        "runtime_id": runtime_id,
        "selector": selector,
        "display_name": display_name,
        **normalized,
        "minimum_coverage": minimum,
        "selected_transport_epoch": int(selected["transport_epoch"]),
        "coverage_ratio": round(coverage, 4),
        "first_received_at": float(selected["first_received_at"]),
        "last_received_at": float(selected["last_received_at"]),
        "summary": summary,
        "feature_availability": _feature_availability(summary),
        "warnings": warnings,
        "selection_semantics": (
            "Maximize retained coverage first, then prefer the newest pass. "
            "Epoch IDs are instance-local and are never compared across tracks."
        ),
    }


def capture_range_state(
    start_seconds: float,
    end_seconds: float,
    *,
    target_selectors: list[str] | None = None,
    after_received_at: float | None = None,
    minimum_coverage: float = DEFAULT_MINIMUM_COVERAGE,
) -> dict[str, Any]:
    """Capture one auditable project state from retained Song Memory."""
    normalized = normalize_range(start_seconds, end_seconds)
    minimum = _minimum_coverage(minimum_coverage)
    canonical_targets = canonical_target_selectors(target_selectors)
    runtime_ids = project._live_runtime_ids()
    tracks: dict[str, dict[str, Any]] = {}

    for runtime_id in runtime_ids:
        selector, display_name, binding, analyzer_name = _identity(runtime_id)
        resolved = resolve_track_range(
            runtime_id,
            start_seconds,
            end_seconds,
            after_received_at=after_received_at,
            minimum_coverage=minimum,
        )
        summary = copy.deepcopy(resolved.get("summary") or {})
        quality = copy.deepcopy(summary.get("data_quality") or {})
        coverage = resolved.get("coverage_ratio")
        adequate = bool(resolved.get("available") and resolved.get("adequate_coverage"))
        active_ratio = summary.get("active_ratio")
        features = copy.deepcopy(resolved.get("feature_availability") or {})

        tracks[selector] = {
            "identity": selector,
            "runtime_id": runtime_id,
            "display_name": display_name,
            "analyzer_name": analyzer_name,
            "binding": binding,
            "signal_present": None if active_ratio is None else float(active_ratio) > 0.0,
            "analysis_valid": adequate,
            "active_ratio": active_ratio,
            "peak_db": summary.get("peak_db"),
            "rms_db": summary.get("rms_db"),
            "crest_db": summary.get("crest_db"),
            "lufs_s": summary.get("lufs_s"),
            # LUFS-I is pass-cumulative, not range-integrated. Do not expose it
            # as a range delta until a scope-compatible integrated value exists.
            "lufs_i": None,
            "true_peak_dbtp": summary.get("true_peak_dbtp"),
            "max_true_peak_dbtp": summary.get("max_true_peak_dbtp"),
            "centroid_hz": summary.get("centroid_hz"),
            "rolloff_hz": None,
            "flatness": None,
            "stereo_correlation": summary.get("stereo_correlation"),
            "stereo_width": summary.get("stereo_width"),
            "spectral_flux_mean": summary.get("spectral_flux_mean"),
            "spectral_regions": copy.deepcopy(summary.get("spectral_regions") or {}),
            "feature_availability": features,
            "range_available": bool(resolved.get("available")),
            "range_coverage_ratio": coverage,
            "selected_transport_epoch": resolved.get("selected_transport_epoch"),
            "range_provenance": {
                "first_received_at": resolved.get("first_received_at"),
                "last_received_at": resolved.get("last_received_at"),
                "coverage_ratio": coverage,
                "data_quality": quality,
                "warnings": list(resolved.get("warnings") or []),
            },
        }

    effective = normalized["effective_range"]
    return {
        "captured_at": time.time(),
        "capture_mode": "transport_range",
        "window_seconds": round(
            float(effective["end_seconds"]) - float(effective["start_seconds"]), 3
        ),
        **normalized,
        "minimum_coverage": minimum,
        "after_received_at": after_received_at,
        "canonical_target_selectors": canonical_targets,
        "tracks": tracks,
        "semantics": {
            "coverage": "Observed 100 ms coverage slots inside one-second retained Song Memory bins.",
            "range_resolution": "Metrics are retained at one-second bin resolution; requested fractional boundaries are normalized explicitly.",
            "after_received_at": "When present, every selected range pass must have been first observed after this fence, preventing reuse of frozen pre-change bins.",
        },
    }
