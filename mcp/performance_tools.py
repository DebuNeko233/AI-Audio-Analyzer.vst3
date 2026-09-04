#!/usr/bin/env python3
"""Adaptive-analysis and worker-performance layer for AI Audio Analyzer.

Analysis Profile is a host-visible VST3 parameter that changes Analyzer
measurement cost only. Newer Analyzer builds can change that parameter through
the Analyzer-owned loopback control tools; DAW-control MCP remains responsible
for all artistic/technical project parameters outside the Analyzer itself.

This module parses the append-only runtime telemetry tail and lets the LLM verify
which feature groups are really enabled and whether the background analysis
worker is keeping up.
"""

from __future__ import annotations

import time
from collections import Counter
from typing import Any

import server as core
import semantic_tools as semantic
import temporal_tools as temporal

PROFILE_NAMES = ["eco", "balanced", "mix", "full"]
PROFILE_DISPLAY_NAMES = ["Eco", "Balanced", "Mix", "Full"]

FEATURE_CORE = 1 << 0
FEATURE_LOUDNESS = 1 << 1
FEATURE_SPECTRUM = 1 << 2
FEATURE_STEREO = 1 << 3
FEATURE_TEMPORAL = 1 << 4
FEATURE_SEMANTIC = 1 << 5

V11_START = semantic.V09_START + semantic.V09_FIELD_COUNT
V11_FIELD_COUNT = 7

_ORIGINAL_ON_FRAME = core._on_frame


def _features(mask: int) -> dict[str, bool]:
    return {
        "core": bool(mask & FEATURE_CORE),
        "loudness": bool(mask & FEATURE_LOUDNESS),
        "spectrum": bool(mask & FEATURE_SPECTRUM),
        "stereo": bool(mask & FEATURE_STEREO),
        "temporal": bool(mask & FEATURE_TEMPORAL),
        "semantic": bool(mask & FEATURE_SEMANTIC),
    }


def on_frame_v11(address: str, *args: Any) -> None:
    """Parse all older fields first, then attach adaptive runtime telemetry."""
    _ORIGINAL_ON_FRAME(address, *args)

    if len(args) < V11_START + V11_FIELD_COUNT:
        return

    runtime_id = str(args[temporal.V03_START + 3]).strip()
    if not runtime_id:
        return

    try:
        profile_index = max(0, min(3, int(args[V11_START])))
        feature_mask = max(0, int(args[V11_START + 1]))
        worker_load_ratio = max(0.0, min(1.0, float(args[V11_START + 2])))
        fifo_fill_ratio = max(0.0, min(1.0, float(args[V11_START + 3])))
        fft_runs_per_second = max(0.0, float(args[V11_START + 4]))
        semantic_runs_per_second = max(0.0, float(args[V11_START + 5]))
        schema_version = str(args[V11_START + 6]).strip() or "1.1"
    except (TypeError, ValueError):
        return

    features = _features(feature_mask)

    with core._lock:
        frame = core._tracks.get(runtime_id)
        if frame is None:
            return

        frame["schema_version"] = schema_version
        frame["adaptive_analysis_supported"] = True
        frame["analysis_profile_index"] = profile_index
        frame["analysis_profile"] = PROFILE_NAMES[profile_index]
        frame["analysis_profile_display"] = PROFILE_DISPLAY_NAMES[profile_index]
        frame["analysis_feature_mask"] = feature_mask
        frame["analysis_features"] = features
        frame["worker_load_ratio"] = worker_load_ratio
        frame["fifo_fill_ratio"] = fifo_fill_ratio
        frame["fft_runs_per_second"] = fft_runs_per_second
        frame["semantic_runs_per_second"] = semantic_runs_per_second

        # Older append-only tails remain physically present in every new OSC
        # frame. The feature mask is authoritative: clear disabled families in
        # the shared history object itself so older tools that inspect history
        # directly cannot mistake compatibility placeholders for measurements.
        if not features["loudness"]:
            frame["lufs_s"] = None
            frame["lufs_i"] = None
            frame["true_peak_dbtp"] = None
            frame["max_true_peak_dbtp"] = None

        if not features["spectrum"]:
            frame["spectrum_valid"] = False
            frame["centroid_hz"] = None
            frame["rolloff_hz"] = None
            frame["flatness"] = None
            frame["bands_db"] = None

        if not features["stereo"]:
            frame["stereo_valid"] = False
            frame["stereo_v08_valid"] = False
            frame["stereo_correlation"] = None
            frame["stereo_width"] = None
            frame["band_stereo_correlation"] = None
            for key in (
                "mid_rms_db",
                "side_rms_db",
                "side_to_mid_db",
                "negative_cross_energy_ratio",
                "low_band_20_120_correlation",
                "low_band_20_120_side_to_mid_db",
                "side_bands_db",
                "band_side_to_mid_db",
            ):
                if key in frame:
                    frame[key] = None

        if not features["temporal"]:
            frame["temporal_valid"] = False
            frame["temporal_window_seconds"] = 0.0
            frame["spectral_flux_mean"] = None
            frame["spectral_flux_peak"] = None
            frame["rms_rise_peak_db"] = None
            frame["low_band_energy_db"] = None

        if not features["semantic"]:
            frame["semantic_v09_valid"] = False
            frame["chroma"] = None
            frame["chroma_energy_ratio"] = None
            frame["single_f0_harmonic_energy_ratio"] = None
            frame["harmonic_f0_candidate_hz"] = None


def _status_from_frame(frame: dict[str, Any]) -> dict[str, Any]:
    profile_index = int(frame.get("analysis_profile_index", 3))
    profile_index = max(0, min(3, profile_index))
    feature_mask = int(frame.get("analysis_feature_mask", 63))
    return {
        "id": frame.get("id"),
        "track": frame.get("track"),
        "adaptive_analysis_supported": bool(frame.get("adaptive_analysis_supported")),
        "profile": frame.get("analysis_profile", PROFILE_NAMES[profile_index]),
        "profile_display": frame.get("analysis_profile_display", PROFILE_DISPLAY_NAMES[profile_index]),
        "profile_index": profile_index,
        "feature_mask": feature_mask,
        "features": dict(frame.get("analysis_features") or _features(feature_mask)),
        "worker_load_ratio": frame.get("worker_load_ratio"),
        "fifo_fill_ratio": frame.get("fifo_fill_ratio"),
        "fft_runs_per_second": frame.get("fft_runs_per_second"),
        "semantic_runs_per_second": frame.get("semantic_runs_per_second"),
        "age_seconds": round(max(0.0, time.time() - float(frame.get("_received_at", time.time()))), 3),
        "control_parameter": {
            "parameter_id": "analysis_profile",
            "display_name": "Analysis Profile",
            "choices": [
                {"index": 0, "name": "Eco", "features": _features(1)},
                {"index": 1, "name": "Balanced", "features": _features(15)},
                {"index": 2, "name": "Mix", "features": _features(31)},
                {"index": 3, "name": "Full", "features": _features(63)},
            ],
            "writer": (
                "Prefer audio_set_analysis_profile() or audio_set_project_analysis_profile() on control-capable Analyzer builds. "
                "The control path is limited to this Analyzer measurement-performance parameter."
            ),
        },
        "telemetry_semantics": {
            "worker_load_ratio": "Background Analyzer worker busy-time ratio, not DAW audio-thread CPU usage.",
            "fifo_fill_ratio": "Fraction of the Analyzer SPSC FIFO currently queued; sustained growth indicates analysis lag risk.",
            "fft_runs_per_second": "Observed internal FFT executions per second.",
            "semantic_runs_per_second": "Observed Chroma/Single-F0 semantic analysis executions per second.",
        },
    }


@core.mcp.tool()
def audio_analysis_status(track: str) -> dict[str, Any]:
    """Return one Analyzer instance's active profile, feature groups and worker telemetry."""
    runtime_id = core._resolve_track(track)
    with core._lock:
        frame = dict(core._tracks[runtime_id])
        binding = core._binding_public(core._bindings.get(runtime_id))
    result = _status_from_frame(frame)
    result["binding"] = binding
    if not result["adaptive_analysis_supported"]:
        result["note"] = (
            "This instance does not expose adaptive-analysis telemetry. Treat it as legacy Full behavior and do not assume profile control is available."
        )
    return result


@core.mcp.tool()
def audio_project_performance() -> dict[str, Any]:
    """Summarize adaptive-analysis profiles and worker backlog/load across live instances."""
    with core._lock:
        frames = [dict(frame) for frame in core._tracks.values()]

    rows = [_status_from_frame(frame) for frame in frames]
    profile_counts = Counter(row["profile"] for row in rows)
    loads = [float(row["worker_load_ratio"]) for row in rows if row["worker_load_ratio"] is not None]
    fifo = [float(row["fifo_fill_ratio"]) for row in rows if row["fifo_fill_ratio"] is not None]

    warnings: list[str] = []
    if fifo and max(fifo) >= 0.5:
        warnings.append("At least one Analyzer FIFO is half full or more; sustained growth can make measurements stale relative to the DAW.")
    if loads and max(loads) >= 0.8:
        warnings.append("At least one Analyzer background worker is busy most of the observed time. Consider a lower Analysis Profile when those evidence families are not needed.")

    return {
        "instance_count": len(rows),
        "adaptive_instance_count": sum(bool(row["adaptive_analysis_supported"]) for row in rows),
        "profile_counts": dict(sorted(profile_counts.items())),
        "max_worker_load_ratio": None if not loads else round(max(loads), 4),
        "mean_worker_load_ratio": None if not loads else round(sum(loads) / len(loads), 4),
        "max_fifo_fill_ratio": None if not fifo else round(max(fifo), 4),
        "instances": sorted(rows, key=lambda row: (str(row.get("track") or "").casefold(), str(row.get("id") or ""))),
        "warnings": warnings,
        "note": (
            "Profiles are Analyzer performance controls, not artistic modes. Use the Analyzer-owned profile-control tools when available, then verify fresh telemetry if the transport is running."
        ),
    }
