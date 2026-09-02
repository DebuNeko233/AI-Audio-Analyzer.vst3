#!/usr/bin/env python3
"""OSC receiver + MCP server for AI Analyzer.vst3.

The VST3 sends compact analysis frames to UDP localhost. This process caches the
latest/history per plugin instance and exposes LLM-friendly MCP tools over stdio.
"""

from __future__ import annotations

import math
import os
import sys
import threading
import time
from collections import deque
from typing import Any

from mcp.server.fastmcp import FastMCP
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

NUM_BANDS = 32
NUM_STEREO_CORR_BANDS = 8
MIN_HZ = 20.0
MAX_HZ = 20000.0
HISTORY_LENGTH = 3600

BAND_EDGES = [
    MIN_HZ * (MAX_HZ / MIN_HZ) ** (i / NUM_BANDS)
    for i in range(NUM_BANDS + 1)
]
BAND_CENTERS = [math.sqrt(BAND_EDGES[i] * BAND_EDGES[i + 1]) for i in range(NUM_BANDS)]
STEREO_CORR_EDGES = [20.0, 60.0, 120.0, 250.0, 500.0, 1000.0, 2000.0, 5000.0, 20000.0]

_lock = threading.RLock()
_tracks: dict[str, dict[str, Any]] = {}
_history: dict[str, deque[dict[str, Any]]] = {}

mcp = FastMCP("AI Analyzer Audio MCP")


def _clean_frame(frame: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in frame.items() if not k.startswith("_")}


def _resolve_track(track: str) -> str:
    with _lock:
        if track in _tracks:
            return track
        wanted = track.casefold()
        for name in _tracks:
            if name.casefold() == wanted:
                return name
    raise ValueError(f"Unknown analyzer instance: {track!r}. Available: {sorted(_tracks)}")


def _stereo_corr_ranges() -> list[str]:
    result: list[str] = []
    for lo, hi in zip(STEREO_CORR_EDGES[:-1], STEREO_CORR_EDGES[1:]):
        if hi <= 1000:
            result.append(f"{lo:.0f}-{hi:.0f} Hz")
        elif lo >= 1000:
            result.append(f"{lo / 1000:.1f}-{hi / 1000:.1f} kHz")
        else:
            result.append(f"{lo:.0f} Hz-{hi / 1000:.1f} kHz")
    return result


def _on_frame(_address: str, *args: Any) -> None:
    # Backward-compatible V0.2 schema:
    # V0.1 prefix:
    # instance, sample_rate, plugin_timestamp, peak, rms, crest,
    # centroid, rolloff, flatness, correlation, width, 32 spectrum dB values
    # V0.2 appended extras:
    # LUFS-S, LUFS-I, current true peak dBTP, session max true peak dBTP,
    # 8 band-limited stereo-correlation values.
    base_count = 11 + NUM_BANDS
    if len(args) < base_count:
        print(
            f"AI Analyzer: ignored malformed OSC frame with {len(args)} args",
            file=sys.stderr,
        )
        return

    instance = str(args[0]).strip() or "Track"
    bands = [float(v) for v in args[11 : 11 + NUM_BANDS]]
    extra = 11 + NUM_BANDS

    lufs_s: float | None = None
    lufs_i: float | None = None
    true_peak_dbtp: float | None = None
    max_true_peak_dbtp: float | None = None
    band_stereo_correlation: list[float] | None = None

    if len(args) >= extra + 4:
        lufs_s = float(args[extra])
        lufs_i = float(args[extra + 1])
        true_peak_dbtp = float(args[extra + 2])
        max_true_peak_dbtp = float(args[extra + 3])

    corr_start = extra + 4
    if len(args) >= corr_start + NUM_STEREO_CORR_BANDS:
        band_stereo_correlation = [
            float(v) for v in args[corr_start : corr_start + NUM_STEREO_CORR_BANDS]
        ]

    now = time.time()
    frame = {
        "track": instance,
        "sample_rate": float(args[1]),
        "plugin_timestamp": float(args[2]),
        "peak_db": float(args[3]),
        "rms_db": float(args[4]),
        "crest_db": float(args[5]),
        "centroid_hz": float(args[6]),
        "rolloff_hz": float(args[7]),
        "flatness": float(args[8]),
        "stereo_correlation": float(args[9]),
        "stereo_width": float(args[10]),
        "lufs_s": lufs_s,
        "lufs_i": lufs_i,
        "true_peak_dbtp": true_peak_dbtp,
        "max_true_peak_dbtp": max_true_peak_dbtp,
        "band_centers_hz": BAND_CENTERS,
        "bands_db": bands,
        "stereo_correlation_band_ranges": _stereo_corr_ranges(),
        "band_stereo_correlation": band_stereo_correlation,
        "_received_at": now,
    }

    with _lock:
        _tracks[instance] = frame
        history = _history.setdefault(instance, deque(maxlen=HISTORY_LENGTH))
        history.append(frame)


def _snapshot(track: str) -> dict[str, Any]:
    name = _resolve_track(track)
    with _lock:
        return _clean_frame(dict(_tracks[name]))


def _mean_db_like(values: list[float]) -> float | None:
    finite = [v for v in values if math.isfinite(v) and v > -120.0]
    if not finite:
        return None
    mean_power = sum(10.0 ** (v / 10.0) for v in finite) / len(finite)
    return 10.0 * math.log10(max(mean_power, 1e-12))


@mcp.tool()
def audio_list_tracks() -> dict[str, Any]:
    """List currently visible AI Analyzer plugin instances and frame age."""
    now = time.time()
    with _lock:
        tracks = [
            {
                "track": name,
                "age_seconds": round(max(0.0, now - frame["_received_at"]), 3),
                "peak_db": frame["peak_db"],
                "true_peak_dbtp": frame.get("true_peak_dbtp"),
                "lufs_s": frame.get("lufs_s"),
                "lufs_i": frame.get("lufs_i"),
            }
            for name, frame in sorted(_tracks.items())
        ]
    return {"tracks": tracks, "count": len(tracks)}


@mcp.tool()
def audio_snapshot(track: str) -> dict[str, Any]:
    """Get the latest spectrum, loudness, true-peak, and stereo frame for one track."""
    return _snapshot(track)


@mcp.tool()
def audio_average(track: str, seconds: float = 5.0) -> dict[str, Any]:
    """Summarize recent analysis for a track over a time window (default 5 s)."""
    seconds = max(0.1, min(float(seconds), 60.0))
    name = _resolve_track(track)
    cutoff = time.time() - seconds

    with _lock:
        frames = [f for f in _history.get(name, ()) if f["_received_at"] >= cutoff]

    if not frames:
        return _snapshot(name)

    result: dict[str, Any] = {
        "track": name,
        "window_seconds": seconds,
        "frames": len(frames),
        "band_centers_hz": BAND_CENTERS,
        "stereo_correlation_band_ranges": _stereo_corr_ranges(),
    }

    result["peak_db"] = max(float(f["peak_db"]) for f in frames)
    result["rms_db"] = _mean_db_like([float(f["rms_db"]) for f in frames])
    result["crest_db"] = sum(float(f["crest_db"]) for f in frames) / len(frames)
    result["centroid_hz"] = sum(float(f["centroid_hz"]) for f in frames) / len(frames)
    result["rolloff_hz"] = sum(float(f["rolloff_hz"]) for f in frames) / len(frames)
    result["flatness"] = sum(float(f["flatness"]) for f in frames) / len(frames)
    result["stereo_correlation"] = sum(float(f["stereo_correlation"]) for f in frames) / len(frames)
    result["stereo_width"] = sum(float(f["stereo_width"]) for f in frames) / len(frames)

    short_term_values = [float(f["lufs_s"]) for f in frames if f.get("lufs_s") is not None]
    result["lufs_s"] = _mean_db_like(short_term_values)

    # LUFS-I is already integrated by the plugin since its loudness state was reset;
    # averaging those cumulative values would be misleading, so return the newest one.
    result["lufs_i"] = next(
        (float(f["lufs_i"]) for f in reversed(frames) if f.get("lufs_i") is not None),
        None,
    )

    true_peaks = [float(f["true_peak_dbtp"]) for f in frames if f.get("true_peak_dbtp") is not None]
    result["true_peak_dbtp"] = max(true_peaks) if true_peaks else None
    result["max_true_peak_dbtp"] = next(
        (
            float(f["max_true_peak_dbtp"])
            for f in reversed(frames)
            if f.get("max_true_peak_dbtp") is not None
        ),
        None,
    )

    bands_db: list[float] = []
    for band in range(NUM_BANDS):
        mean_power = sum(10.0 ** (float(f["bands_db"][band]) / 10.0) for f in frames) / len(frames)
        bands_db.append(10.0 * math.log10(max(mean_power, 1e-12)))
    result["bands_db"] = bands_db

    corr_frames = [f for f in frames if f.get("band_stereo_correlation") is not None]
    if corr_frames:
        result["band_stereo_correlation"] = [
            sum(float(f["band_stereo_correlation"][i]) for f in corr_frames) / len(corr_frames)
            for i in range(NUM_STEREO_CORR_BANDS)
        ]
    else:
        result["band_stereo_correlation"] = None

    return result


def _band_range(index: int) -> str:
    lo = BAND_EDGES[index]
    hi = BAND_EDGES[index + 1]
    if hi < 1000:
        return f"{lo:.0f}-{hi:.0f} Hz"
    return f"{lo / 1000:.2f}-{hi / 1000:.2f} kHz"


@mcp.tool()
def audio_stereo_bands(track: str) -> dict[str, Any]:
    """Return eight band-limited L/R stereo-correlation values for a track."""
    frame = _snapshot(track)
    values = frame.get("band_stereo_correlation")
    if values is None:
        return {
            "track": frame["track"],
            "available": False,
            "reason": "Analyzer frame does not include V0.2 band-limited correlation data.",
        }

    bands = []
    for label, value in zip(_stereo_corr_ranges(), values):
        value = float(value)
        if value < -0.25:
            flag = "high mono-compatibility risk"
        elif value < 0.0:
            flag = "negative correlation"
        elif value < 0.25:
            flag = "very wide / weakly correlated"
        else:
            flag = "normal/positive correlation"
        bands.append({"range": label, "correlation": value, "flag": flag})

    return {
        "track": frame["track"],
        "available": True,
        "bands": bands,
        "note": "Near-silent bands can yield unstable or low-information correlation values; interpret them together with spectrum level.",
    }


@mcp.tool()
def audio_compare_tracks(track_a: str, track_b: str) -> dict[str, Any]:
    """Compare two tracks and return a heuristic spectral-overlap report."""
    a = _snapshot(track_a)
    b = _snapshot(track_b)

    max_a = max(a["bands_db"])
    max_b = max(b["bands_db"])
    overlaps = []

    for i, (db_a, db_b) in enumerate(zip(a["bands_db"], b["bands_db"])):
        rel_a = 10.0 ** ((float(db_a) - max_a) / 10.0)
        rel_b = 10.0 ** ((float(db_b) - max_b) / 10.0)
        score = min(rel_a, rel_b)
        overlaps.append(
            {
                "band": i,
                "range": _band_range(i),
                "center_hz": BAND_CENTERS[i],
                "score": round(score, 4),
                "a_db": float(db_a),
                "b_db": float(db_b),
            }
        )

    strongest = sorted(overlaps, key=lambda item: item["score"], reverse=True)[:8]
    overall = sum(item["score"] for item in strongest[:5]) / max(1, min(5, len(strongest)))

    return {
        "track_a": a["track"],
        "track_b": b["track"],
        "spectral_overlap_score": round(overall, 4),
        "strongest_overlap_bands": strongest,
        "note": "Heuristic relative spectral overlap, not a psychoacoustic masking model. Use musical context before EQ/sidechain decisions.",
    }


@mcp.tool()
def audio_detect_masking(track_a: str, track_b: str) -> dict[str, Any]:
    """Find likely masking regions between two analyzer instances."""
    report = audio_compare_tracks(track_a, track_b)
    candidates = [b for b in report["strongest_overlap_bands"] if b["score"] >= 0.15]
    return {
        "track_a": report["track_a"],
        "track_b": report["track_b"],
        "severity": report["spectral_overlap_score"],
        "candidate_regions": candidates,
        "guidance": "Treat these regions as candidates only; also inspect timing, level, arrangement, stereo position, and transient overlap.",
    }


@mcp.tool()
def audio_master_status(track: str = "Master") -> dict[str, Any]:
    """Summarize master/bus loudness, true peak, dynamics, and stereo status."""
    frame = _snapshot(track)
    warnings: list[str] = []

    true_peak = frame.get("max_true_peak_dbtp")
    if true_peak is None:
        true_peak = frame.get("true_peak_dbtp")

    if true_peak is not None:
        true_peak = float(true_peak)
        if true_peak > 0.0:
            warnings.append("True peak exceeds 0 dBTP; inter-sample clipping is likely.")
        elif true_peak > -1.0:
            warnings.append("True peak is above -1 dBTP; codec/transcoding headroom is limited.")
    elif frame["peak_db"] > -0.1:
        warnings.append("Sample peak is at/near digital full scale; true-peak data is unavailable.")

    if frame["stereo_correlation"] < 0.0:
        warnings.append("Negative full-band stereo correlation may indicate mono-compatibility problems.")
    if frame["crest_db"] < 4.0:
        warnings.append("Very low crest factor: dynamics may be heavily constrained, depending on genre.")

    return {
        "track": frame["track"],
        "peak_db": frame["peak_db"],
        "true_peak_dbtp": frame.get("true_peak_dbtp"),
        "max_true_peak_dbtp": frame.get("max_true_peak_dbtp"),
        "rms_db": frame["rms_db"],
        "crest_db": frame["crest_db"],
        "lufs_s": frame.get("lufs_s"),
        "lufs_i": frame.get("lufs_i"),
        "centroid_hz": frame["centroid_hz"],
        "rolloff_hz": frame["rolloff_hz"],
        "stereo_correlation": frame["stereo_correlation"],
        "stereo_width": frame["stereo_width"],
        "band_stereo_correlation": frame.get("band_stereo_correlation"),
        "stereo_correlation_band_ranges": frame.get("stereo_correlation_band_ranges"),
        "warnings": warnings,
        "note": "LUFS-I is integrated since the analyzer loudness state was last reset/prepared. There is no universal LUFS target; compare against genre/reference and delivery requirements.",
    }


def main() -> None:
    host = os.getenv("AI_ANALYZER_OSC_HOST", "127.0.0.1")
    port = int(os.getenv("AI_ANALYZER_OSC_PORT", "9855"))

    dispatcher = Dispatcher()
    dispatcher.map("/aianalyzer/frame", _on_frame)
    osc_server = ThreadingOSCUDPServer((host, port), dispatcher)
    osc_thread = threading.Thread(target=osc_server.serve_forever, name="AIAnalyzerOSC", daemon=True)
    osc_thread.start()

    print(f"AI Analyzer OSC listening on udp://{host}:{port}", file=sys.stderr)

    try:
        mcp.run(transport="stdio")
    finally:
        osc_server.shutdown()
        osc_server.server_close()


if __name__ == "__main__":
    main()
