#!/usr/bin/env python3
"""OSC receiver + MCP server for AI Analyzer.vst3.

AI Analyzer VST3 instances send compact analysis frames over UDP/OSC. This
process caches the latest/history per instance and exposes LLM-friendly tools
through MCP stdio.

The bridge deliberately keeps MCP alive even when OSC cannot bind. This makes
startup problems observable through ``audio_bridge_status`` instead of causing
an opaque "MCP error -32000: Connection closed" in desktop MCP clients.
"""

from __future__ import annotations

import math
import os
import sys
import threading
import time
from collections import deque
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from mcp.server import MCPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

NUM_BANDS = 32
NUM_STEREO_CORR_BANDS = 8
MIN_HZ = 20.0
MAX_HZ = 20000.0
HISTORY_LENGTH = 3600
DEFAULT_OSC_HOST = "127.0.0.1"
DEFAULT_OSC_PORT = 9855

BAND_EDGES = [
    MIN_HZ * (MAX_HZ / MIN_HZ) ** (i / NUM_BANDS)
    for i in range(NUM_BANDS + 1)
]
BAND_CENTERS = [
    math.sqrt(BAND_EDGES[i] * BAND_EDGES[i + 1]) for i in range(NUM_BANDS)
]
STEREO_CORR_EDGES = [
    20.0,
    60.0,
    120.0,
    250.0,
    500.0,
    1000.0,
    2000.0,
    5000.0,
    20000.0,
]

_lock = threading.RLock()
_tracks: dict[str, dict[str, Any]] = {}
_history: dict[str, deque[dict[str, Any]]] = {}
_bridge_started_at = time.time()
_osc_host = DEFAULT_OSC_HOST
_osc_port = DEFAULT_OSC_PORT
_osc_listening = False
_osc_error: str | None = None
_last_frame_at: float | None = None

mcp = MCPServer("AI Analyzer Audio MCP")


def _mcp_version() -> str:
    try:
        return version("mcp")
    except PackageNotFoundError:
        return "unknown"


def _clean_frame(frame: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in frame.items() if not key.startswith("_")}


def _resolve_track(track: str) -> str:
    with _lock:
        if track in _tracks:
            return track
        wanted = track.casefold()
        for name in _tracks:
            if name.casefold() == wanted:
                return name
        available = sorted(_tracks)
    raise ValueError(f"Unknown analyzer instance: {track!r}. Available: {available}")


def _snapshot(track: str) -> dict[str, Any]:
    name = _resolve_track(track)
    with _lock:
        return _clean_frame(dict(_tracks[name]))


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


def _mean_db_like(values: list[float]) -> float | None:
    finite = [value for value in values if math.isfinite(value) and value > -120.0]
    if not finite:
        return None
    mean_power = sum(10.0 ** (value / 10.0) for value in finite) / len(finite)
    return 10.0 * math.log10(max(mean_power, 1e-12))


def _band_range(index: int) -> str:
    lo = BAND_EDGES[index]
    hi = BAND_EDGES[index + 1]
    if hi < 1000:
        return f"{lo:.0f}-{hi:.0f} Hz"
    return f"{lo / 1000:.2f}-{hi / 1000:.2f} kHz"


def _read_osc_config() -> tuple[str, int, str | None]:
    host = os.getenv("AI_ANALYZER_OSC_HOST", DEFAULT_OSC_HOST).strip() or DEFAULT_OSC_HOST
    raw_port = os.getenv("AI_ANALYZER_OSC_PORT", str(DEFAULT_OSC_PORT)).strip()
    try:
        port = int(raw_port)
    except ValueError:
        return host, DEFAULT_OSC_PORT, f"Invalid AI_ANALYZER_OSC_PORT={raw_port!r}; expected an integer."
    if not 1 <= port <= 65535:
        return host, DEFAULT_OSC_PORT, f"Invalid AI_ANALYZER_OSC_PORT={port}; expected 1..65535."
    return host, port, None


def _on_frame(_address: str, *args: Any) -> None:
    """Receive one backward-compatible V0.2 analyzer frame."""
    global _last_frame_at

    # V0.1 prefix:
    # instance, sample_rate, plugin_timestamp, peak, rms, crest,
    # centroid, rolloff, flatness, correlation, width, 32 spectrum dB values
    # V0.2 extras:
    # LUFS-S, LUFS-I, current true peak dBTP, session max true peak dBTP,
    # 8 band-limited stereo-correlation values.
    base_count = 11 + NUM_BANDS
    if len(args) < base_count:
        print(
            f"AI Analyzer: ignored malformed OSC frame with {len(args)} args",
            file=sys.stderr,
            flush=True,
        )
        return

    instance = str(args[0]).strip() or "Track"
    bands = [float(value) for value in args[11 : 11 + NUM_BANDS]]
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
            float(value)
            for value in args[corr_start : corr_start + NUM_STEREO_CORR_BANDS]
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
        _history.setdefault(instance, deque(maxlen=HISTORY_LENGTH)).append(frame)
        _last_frame_at = now


def _compare_tracks(track_a: str, track_b: str) -> dict[str, Any]:
    a = _snapshot(track_a)
    b = _snapshot(track_b)
    max_a = max(a["bands_db"])
    max_b = max(b["bands_db"])
    overlaps: list[dict[str, Any]] = []

    for index, (db_a, db_b) in enumerate(zip(a["bands_db"], b["bands_db"])):
        rel_a = 10.0 ** ((float(db_a) - max_a) / 10.0)
        rel_b = 10.0 ** ((float(db_b) - max_b) / 10.0)
        score = min(rel_a, rel_b)
        overlaps.append(
            {
                "band": index,
                "range": _band_range(index),
                "center_hz": BAND_CENTERS[index],
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
def audio_bridge_status() -> dict[str, Any]:
    """Report MCP/OSC bridge health, startup errors, and analyzer stream state."""
    now = time.time()
    with _lock:
        track_names = sorted(_tracks)
        last_frame_at = _last_frame_at
        listening = _osc_listening
        error = _osc_error
        host = _osc_host
        port = _osc_port

    last_age = None if last_frame_at is None else round(max(0.0, now - last_frame_at), 3)

    if error:
        hint = (
            "MCP is running, but OSC is unavailable. If the error says address already in use, "
            "stop any manually started server.py/older bridge using the same UDP port, then restart this MCP server."
        )
    elif not listening:
        hint = "MCP is running, but OSC listener has not started."
    elif not track_names:
        hint = (
            "OSC is listening but no analyzer frames have arrived yet. Load AI Analyzer.vst3, "
            "use the same OSC port, click Apply if needed, and start FL Studio playback."
        )
    elif last_age is not None and last_age > 3.0:
        hint = "Analyzer data is stale; check FL Studio playback and the VST3 OSC connection."
    else:
        hint = "Bridge is healthy and receiving analyzer frames."

    return {
        "ok": bool(listening and error is None),
        "pid": os.getpid(),
        "mcp_sdk_version": _mcp_version(),
        "uptime_seconds": round(max(0.0, now - _bridge_started_at), 3),
        "osc": {
            "host": host,
            "port": port,
            "listening": listening,
            "error": error,
        },
        "track_count": len(track_names),
        "tracks": track_names,
        "last_frame_age_seconds": last_age,
        "hint": hint,
    }


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
        frames = [frame for frame in _history.get(name, ()) if frame["_received_at"] >= cutoff]

    if not frames:
        return _snapshot(name)

    result: dict[str, Any] = {
        "track": name,
        "window_seconds": seconds,
        "frames": len(frames),
        "band_centers_hz": BAND_CENTERS,
        "stereo_correlation_band_ranges": _stereo_corr_ranges(),
        "peak_db": max(float(frame["peak_db"]) for frame in frames),
        "rms_db": _mean_db_like([float(frame["rms_db"]) for frame in frames]),
        "crest_db": sum(float(frame["crest_db"]) for frame in frames) / len(frames),
        "centroid_hz": sum(float(frame["centroid_hz"]) for frame in frames) / len(frames),
        "rolloff_hz": sum(float(frame["rolloff_hz"]) for frame in frames) / len(frames),
        "flatness": sum(float(frame["flatness"]) for frame in frames) / len(frames),
        "stereo_correlation": sum(float(frame["stereo_correlation"]) for frame in frames) / len(frames),
        "stereo_width": sum(float(frame["stereo_width"]) for frame in frames) / len(frames),
    }

    short_term = [float(frame["lufs_s"]) for frame in frames if frame.get("lufs_s") is not None]
    result["lufs_s"] = _mean_db_like(short_term)
    result["lufs_i"] = next(
        (float(frame["lufs_i"]) for frame in reversed(frames) if frame.get("lufs_i") is not None),
        None,
    )

    true_peaks = [
        float(frame["true_peak_dbtp"])
        for frame in frames
        if frame.get("true_peak_dbtp") is not None
    ]
    result["true_peak_dbtp"] = max(true_peaks) if true_peaks else None
    result["max_true_peak_dbtp"] = next(
        (
            float(frame["max_true_peak_dbtp"])
            for frame in reversed(frames)
            if frame.get("max_true_peak_dbtp") is not None
        ),
        None,
    )

    averaged_bands: list[float] = []
    for band in range(NUM_BANDS):
        mean_power = sum(
            10.0 ** (float(frame["bands_db"][band]) / 10.0) for frame in frames
        ) / len(frames)
        averaged_bands.append(10.0 * math.log10(max(mean_power, 1e-12)))
    result["bands_db"] = averaged_bands

    corr_frames = [frame for frame in frames if frame.get("band_stereo_correlation") is not None]
    result["band_stereo_correlation"] = (
        [
            sum(float(frame["band_stereo_correlation"][i]) for frame in corr_frames)
            / len(corr_frames)
            for i in range(NUM_STEREO_CORR_BANDS)
        ]
        if corr_frames
        else None
    )
    return result


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
        numeric = float(value)
        if numeric < -0.25:
            flag = "high mono-compatibility risk"
        elif numeric < 0.0:
            flag = "negative correlation"
        elif numeric < 0.25:
            flag = "very wide / weakly correlated"
        else:
            flag = "normal/positive correlation"
        bands.append({"range": label, "correlation": numeric, "flag": flag})

    return {
        "track": frame["track"],
        "available": True,
        "bands": bands,
        "note": "Near-silent bands can yield unstable or low-information correlation values; interpret them together with spectrum level.",
    }


@mcp.tool()
def audio_compare_tracks(track_a: str, track_b: str) -> dict[str, Any]:
    """Compare two tracks and return a heuristic spectral-overlap report."""
    return _compare_tracks(track_a, track_b)


@mcp.tool()
def audio_detect_masking(track_a: str, track_b: str) -> dict[str, Any]:
    """Find likely masking regions between two analyzer instances."""
    report = _compare_tracks(track_a, track_b)
    candidates = [
        band for band in report["strongest_overlap_bands"] if band["score"] >= 0.15
    ]
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
        numeric_peak = float(true_peak)
        if numeric_peak > 0.0:
            warnings.append("True peak exceeds 0 dBTP; inter-sample clipping is likely.")
        elif numeric_peak > -1.0:
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
    global _osc_error, _osc_host, _osc_listening, _osc_port

    host, port, config_error = _read_osc_config()
    with _lock:
        _osc_host = host
        _osc_port = port
        _osc_error = config_error
        _osc_listening = False

    osc_server: ThreadingOSCUDPServer | None = None

    if config_error is None:
        dispatcher = Dispatcher()
        dispatcher.map("/aianalyzer/frame", _on_frame)
        try:
            osc_server = ThreadingOSCUDPServer((host, port), dispatcher)
        except OSError as exc:
            with _lock:
                _osc_error = f"{type(exc).__name__}: {exc}"
            print(
                f"AI Analyzer OSC unavailable on udp://{host}:{port}: {exc}. MCP will stay online; use audio_bridge_status for details.",
                file=sys.stderr,
                flush=True,
            )
        else:
            thread = threading.Thread(
                target=osc_server.serve_forever,
                name="AIAnalyzerOSC",
                daemon=True,
            )
            thread.start()
            with _lock:
                _osc_listening = True
                _osc_error = None
            print(
                f"AI Analyzer OSC listening on udp://{host}:{port}",
                file=sys.stderr,
                flush=True,
            )
    else:
        print(
            f"AI Analyzer OSC configuration error: {config_error}. MCP will stay online; use audio_bridge_status for details.",
            file=sys.stderr,
            flush=True,
        )

    try:
        mcp.run(transport="stdio")
    finally:
        if osc_server is not None:
            osc_server.shutdown()
            osc_server.server_close()
        with _lock:
            _osc_listening = False


if __name__ == "__main__":
    main()
