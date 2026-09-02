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
MIN_HZ = 20.0
MAX_HZ = 20000.0
HISTORY_LENGTH = 3600

BAND_EDGES = [
    MIN_HZ * (MAX_HZ / MIN_HZ) ** (i / NUM_BANDS)
    for i in range(NUM_BANDS + 1)
]
BAND_CENTERS = [math.sqrt(BAND_EDGES[i] * BAND_EDGES[i + 1]) for i in range(NUM_BANDS)]

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


def _on_frame(_address: str, *args: Any) -> None:
    # Schema:
    # instance, sample_rate, plugin_timestamp, peak, rms, crest,
    # centroid, rolloff, flatness, correlation, width, 32 band dB values
    if len(args) < 11 + NUM_BANDS:
        print(
            f"AI Analyzer: ignored malformed OSC frame with {len(args)} args",
            file=sys.stderr,
        )
        return

    instance = str(args[0]).strip() or "Track"
    bands = [float(v) for v in args[11 : 11 + NUM_BANDS]]
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
        "band_centers_hz": BAND_CENTERS,
        "bands_db": bands,
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
                "rms_db": frame["rms_db"],
            }
            for name, frame in sorted(_tracks.items())
        ]
    return {"tracks": tracks, "count": len(tracks)}


@mcp.tool()
def audio_snapshot(track: str) -> dict[str, Any]:
    """Get the most recent spectrum, dynamics, and stereo frame for one track."""
    return _snapshot(track)


@mcp.tool()
def audio_average(track: str, seconds: float = 5.0) -> dict[str, Any]:
    """Average recent analysis for a track over a time window (default 5 s)."""
    seconds = max(0.1, min(float(seconds), 60.0))
    name = _resolve_track(track)
    cutoff = time.time() - seconds

    with _lock:
        frames = [f for f in _history.get(name, ()) if f["_received_at"] >= cutoff]

    if not frames:
        return _snapshot(name)

    scalar_keys = [
        "peak_db",
        "rms_db",
        "crest_db",
        "centroid_hz",
        "rolloff_hz",
        "flatness",
        "stereo_correlation",
        "stereo_width",
    ]

    result: dict[str, Any] = {
        "track": name,
        "window_seconds": seconds,
        "frames": len(frames),
        "band_centers_hz": BAND_CENTERS,
    }

    # Peak dB is most useful as the maximum; the others use arithmetic means.
    result["peak_db"] = max(f["peak_db"] for f in frames)
    for key in scalar_keys[1:]:
        result[key] = sum(float(f[key]) for f in frames) / len(frames)

    # Average spectral bands in linear power, then convert back to dB.
    bands_db: list[float] = []
    for band in range(NUM_BANDS):
        mean_power = sum(10.0 ** (float(f["bands_db"][band]) / 10.0) for f in frames) / len(frames)
        bands_db.append(10.0 * math.log10(max(mean_power, 1e-12)))
    result["bands_db"] = bands_db
    return result


def _band_range(index: int) -> str:
    lo = BAND_EDGES[index]
    hi = BAND_EDGES[index + 1]
    if hi < 1000:
        return f"{lo:.0f}-{hi:.0f} Hz"
    return f"{lo / 1000:.2f}-{hi / 1000:.2f} kHz"


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
    """Summarize a master/bus analyzer frame for quick mix/master checks."""
    frame = _snapshot(track)
    warnings: list[str] = []
    if frame["peak_db"] > -0.1:
        warnings.append("Peak is at/near digital full scale; inspect clipping/headroom.")
    if frame["stereo_correlation"] < 0.0:
        warnings.append("Negative stereo correlation may indicate mono-compatibility problems.")
    if frame["crest_db"] < 4.0:
        warnings.append("Very low crest factor: dynamics may be heavily constrained, depending on genre.")

    return {
        "track": frame["track"],
        "peak_db": frame["peak_db"],
        "rms_db": frame["rms_db"],
        "crest_db": frame["crest_db"],
        "centroid_hz": frame["centroid_hz"],
        "rolloff_hz": frame["rolloff_hz"],
        "stereo_correlation": frame["stereo_correlation"],
        "stereo_width": frame["stereo_width"],
        "warnings": warnings,
        "note": "V0.1 does not yet implement LUFS or true-peak; do not infer them from RMS/sample peak.",
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
