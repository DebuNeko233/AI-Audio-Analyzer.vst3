#!/usr/bin/env python3
"""OSC receiver + MCP server core for AI Audio Analyzer.vst3.

VST3 instances send compact analysis frames over UDP/OSC. This module owns the
shared runtime state, stable OSC parser, identity/binding logic, base MCP tools,
and stdio/OSC runtime. User-facing startup belongs to `server.py`.

V0.3 adds signal validity and runtime UUIDs.
V0.4 adds deterministic instance identification and session-scoped bindings
between analyzer runtime UUIDs and DAW mixer track/slot locations.
"""

from __future__ import annotations

import math
import os
import re
import sys
import threading
import time
from collections import Counter, deque
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from mcp.server import MCPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

import self_description

NUM_BANDS = 32
NUM_STEREO_CORR_BANDS = 8
MIN_HZ = 20.0
MAX_HZ = 20000.0
HISTORY_LENGTH = 3600
IDENTIFY_HISTORY_LENGTH = 64
DEFAULT_OSC_HOST = "127.0.0.1"
DEFAULT_OSC_PORT = 9855
SIGNAL_CLOSE_DB = -50.0
SIGNAL_OPEN_DB = -48.0
SHORT_TERM_INVALID_SILENCE_SECONDS = 3.0
STALE_SECONDS = 3.0
DEFAULT_IDENTIFY_MAX_AGE_SECONDS = 5.0

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
_bindings: dict[str, dict[str, Any]] = {}
_identify_events: deque[dict[str, Any]] = deque(maxlen=IDENTIFY_HISTORY_LENGTH)
_identify_sequence = 0

_bridge_started_at = time.time()
_osc_host = DEFAULT_OSC_HOST
_osc_port = DEFAULT_OSC_PORT
_osc_listening = False
_osc_error: str | None = None
_last_frame_at: float | None = None
_last_identify_at: float | None = None

mcp = MCPServer(
    "AI Audio Analyzer MCP",
    title="AI Audio Analyzer MCP",
    description=self_description.SERVER_DESCRIPTION,
    instructions=self_description.SERVER_INSTRUCTIONS,
    version=self_description.MCP_PUBLIC_VERSION,
)


def _mcp_version() -> str:
    try:
        return version("mcp")
    except PackageNotFoundError:
        return "unknown"


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


def _band_range(index: int) -> str:
    lo = BAND_EDGES[index]
    hi = BAND_EDGES[index + 1]
    if hi < 1000:
        return f"{lo:.0f}-{hi:.0f} Hz"
    return f"{lo / 1000:.2f}-{hi / 1000:.2f} kHz"


def _mean_db_like(values: list[float]) -> float | None:
    finite = [value for value in values if math.isfinite(value) and value > -120.0]
    if not finite:
        return None
    mean_power = sum(10.0 ** (value / 10.0) for value in finite) / len(finite)
    return 10.0 * math.log10(max(mean_power, 1e-12))


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


def _binding_public(binding: dict[str, Any] | None) -> dict[str, Any] | None:
    if binding is None:
        return None
    return {
        "runtime_id": binding["runtime_id"],
        "fl_track_index": binding["fl_track_index"],
        "fl_track_name": binding["fl_track_name"],
        "slot": binding["slot"],
        "analyzer_name": binding["analyzer_name"],
        "identify_sequence": binding["identify_sequence"],
        "bound_at": binding["bound_at"],
    }


def _public_frame(frame: dict[str, Any]) -> dict[str, Any]:
    result = {key: value for key, value in frame.items() if not key.startswith("_")}
    signal_present = bool(result.get("signal_present", True))
    spectrum_valid = bool(result.get("spectrum_valid", signal_present))
    stereo_valid = bool(result.get("stereo_valid", signal_present))
    silence_seconds = float(result.get("silence_seconds", 0.0))
    if not spectrum_valid:
        result["centroid_hz"] = None
        result["rolloff_hz"] = None
        result["flatness"] = None
        result["bands_db"] = None
    if not stereo_valid:
        result["stereo_correlation"] = None
        result["stereo_width"] = None
        result["band_stereo_correlation"] = None
    if silence_seconds >= SHORT_TERM_INVALID_SILENCE_SECONDS:
        result["lufs_s"] = None
    runtime_id = str(result.get("id") or result.get("runtime_id") or "")
    with _lock:
        binding = _bindings.get(runtime_id)
    result["bound"] = binding is not None
    result["binding"] = _binding_public(binding)
    return result


def _resolve_track(track: str) -> str:
    query = str(track).strip()
    if not query:
        raise ValueError("Track selector is empty.")
    wanted = query.casefold()
    with _lock:
        if query in _tracks:
            return query
        selector = re.fullmatch(r"(?:mixer|fl):(\d+)(?:/slot:(\d+))?", wanted)
        if selector is not None:
            track_index = int(selector.group(1))
            slot = int(selector.group(2)) if selector.group(2) is not None else None
            matches = [
                runtime_id for runtime_id, binding in _bindings.items()
                if runtime_id in _tracks
                and int(binding["fl_track_index"]) == track_index
                and (slot is None or int(binding["slot"]) == slot)
            ]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise ValueError(
                    f"Ambiguous DAW selector {query!r}; multiple analyzer slots match: "
                    f"{[_binding_public(_bindings[runtime_id]) for runtime_id in matches]}"
                )
            raise ValueError(f"No live analyzer is bound to DAW selector {query!r}.")
        fl_name_matches = [
            runtime_id for runtime_id, binding in _bindings.items()
            if runtime_id in _tracks and str(binding["fl_track_name"]).casefold() == wanted
        ]
        if len(fl_name_matches) == 1:
            return fl_name_matches[0]
        if len(fl_name_matches) > 1:
            raise ValueError(
                f"Ambiguous FL mixer track name {query!r}; use mixer:<index>/slot:<slot> "
                f"or a runtime id instead: "
                f"{[_binding_public(_bindings[runtime_id]) for runtime_id in fl_name_matches]}"
            )
        name_matches = [
            runtime_id for runtime_id, frame in _tracks.items()
            if str(frame["track"]).casefold() == wanted
        ]
        if len(name_matches) == 1:
            return name_matches[0]
        if len(name_matches) > 1:
            matches = [
                {
                    "id": runtime_id,
                    "track": _tracks[runtime_id]["track"],
                    "binding": _binding_public(_bindings.get(runtime_id)),
                    "age_seconds": round(max(0.0, time.time() - float(_tracks[runtime_id]["_received_at"])), 3),
                }
                for runtime_id in name_matches
            ]
            raise ValueError(
                f"Ambiguous analyzer instance name {query!r}; multiple live instances match. "
                f"Use an FL binding selector or runtime id instead: {matches}"
            )
        id_matches = [runtime_id for runtime_id in _tracks if runtime_id.casefold().startswith(wanted)]
        if len(id_matches) == 1:
            return id_matches[0]
        if len(id_matches) > 1:
            raise ValueError(f"Ambiguous runtime-id prefix {query!r}; matches: {sorted(id_matches)}")
        available = [
            {"track": frame["track"], "id": runtime_id, "binding": _binding_public(_bindings.get(runtime_id))}
            for runtime_id, frame in sorted(_tracks.items())
        ]
    raise ValueError(f"Unknown analyzer instance: {query!r}. Available: {available}")


def _snapshot(track: str) -> dict[str, Any]:
    runtime_id = _resolve_track(track)
    with _lock:
        return _public_frame(dict(_tracks[runtime_id]))


def _on_frame(_address: str, *args: Any) -> None:
    global _last_frame_at
    base_count = 11 + NUM_BANDS
    if len(args) < base_count:
        print(f"AI Audio Analyzer: ignored malformed OSC frame with {len(args)} args", file=sys.stderr, flush=True)
        return
    instance_name = str(args[0]).strip() or "Track"
    bands = [float(value) for value in args[11 : 11 + NUM_BANDS]]
    extra = 11 + NUM_BANDS
    lufs_s = lufs_i = true_peak_dbtp = max_true_peak_dbtp = None
    band_stereo_correlation: list[float] | None = None
    if len(args) >= extra + 4:
        lufs_s = float(args[extra]); lufs_i = float(args[extra + 1])
        true_peak_dbtp = float(args[extra + 2]); max_true_peak_dbtp = float(args[extra + 3])
    corr_start = extra + 4
    if len(args) >= corr_start + NUM_STEREO_CORR_BANDS:
        band_stereo_correlation = [float(value) for value in args[corr_start : corr_start + NUM_STEREO_CORR_BANDS]]
    v03_start = corr_start + NUM_STEREO_CORR_BANDS
    has_v03 = len(args) >= v03_start + 4
    peak_db = float(args[3])
    if has_v03:
        signal_present = bool(int(args[v03_start]))
        detector_peak_db = float(args[v03_start + 1])
        silence_seconds = max(0.0, float(args[v03_start + 2]))
        runtime_id = str(args[v03_start + 3]).strip() or f"legacy:{instance_name.casefold()}"
        schema_version = "0.3+"
    else:
        signal_present = peak_db >= SIGNAL_CLOSE_DB
        detector_peak_db = peak_db
        silence_seconds = 0.0 if signal_present else float("inf")
        runtime_id = f"legacy:{instance_name.casefold()}"
        schema_version = "0.2-or-earlier"
    now = time.time()
    frame = {
        "id": runtime_id, "runtime_id": runtime_id, "track": instance_name,
        "schema_version": schema_version, "sample_rate": float(args[1]),
        "plugin_timestamp": float(args[2]), "signal_present": signal_present,
        "detector_peak_db": detector_peak_db, "silence_seconds": silence_seconds,
        "spectrum_valid": signal_present, "stereo_valid": signal_present,
        "peak_db": peak_db, "rms_db": float(args[4]), "crest_db": float(args[5]),
        "centroid_hz": float(args[6]), "rolloff_hz": float(args[7]), "flatness": float(args[8]),
        "stereo_correlation": float(args[9]), "stereo_width": float(args[10]),
        "lufs_s": lufs_s, "lufs_i": lufs_i, "true_peak_dbtp": true_peak_dbtp,
        "max_true_peak_dbtp": max_true_peak_dbtp, "band_centers_hz": BAND_CENTERS,
        "bands_db": bands, "stereo_correlation_band_ranges": _stereo_corr_ranges(),
        "band_stereo_correlation": band_stereo_correlation, "_received_at": now,
    }
    with _lock:
        _tracks[runtime_id] = frame
        _history.setdefault(runtime_id, deque(maxlen=HISTORY_LENGTH)).append(frame)
        _last_frame_at = now


def _on_identify(_address: str, *args: Any) -> None:
    global _identify_sequence, _last_identify_at
    if len(args) < 2:
        print(f"AI Audio Analyzer: ignored malformed identify event with {len(args)} args", file=sys.stderr, flush=True)
        return
    runtime_id = str(args[0]).strip(); instance_name = str(args[1]).strip() or "Track"
    if not runtime_id:
        return
    plugin_timestamp = float(args[2]) if len(args) >= 3 else None
    schema_version = str(args[3]) if len(args) >= 4 else "0.4"
    now = time.time()
    with _lock:
        _identify_sequence += 1
        _identify_events.append({
            "sequence": _identify_sequence, "runtime_id": runtime_id, "analyzer_name": instance_name,
            "plugin_timestamp": plugin_timestamp, "schema_version": schema_version,
            "received_at": now, "_consumed": False,
        })
        _last_identify_at = now


def _compare_tracks(track_a: str, track_b: str) -> dict[str, Any]:
    a = _snapshot(track_a); b = _snapshot(track_b)
    if not a.get("spectrum_valid") or a.get("bands_db") is None:
        return {"available": False, "track_a": a["track"], "track_a_id": a["id"], "track_b": b["track"], "track_b_id": b["id"], "reason": f"{a['track']} has no active input above the analyzer signal threshold."}
    if not b.get("spectrum_valid") or b.get("bands_db") is None:
        return {"available": False, "track_a": a["track"], "track_a_id": a["id"], "track_b": b["track"], "track_b_id": b["id"], "reason": f"{b['track']} has no active input above the analyzer signal threshold."}
    max_a = max(a["bands_db"]); max_b = max(b["bands_db"]); overlaps = []
    for index, (db_a, db_b) in enumerate(zip(a["bands_db"], b["bands_db"])):
        rel_a = 10.0 ** ((float(db_a) - max_a) / 10.0); rel_b = 10.0 ** ((float(db_b) - max_b) / 10.0)
        overlaps.append({"band": index, "range": _band_range(index), "center_hz": BAND_CENTERS[index], "score": round(min(rel_a, rel_b), 4), "a_db": float(db_a), "b_db": float(db_b)})
    strongest = sorted(overlaps, key=lambda item: item["score"], reverse=True)[:8]
    overall = sum(item["score"] for item in strongest[:5]) / max(1, min(5, len(strongest)))
    return {"available": True, "track_a": a["track"], "track_a_id": a["id"], "track_b": b["track"], "track_b_id": b["id"], "spectral_overlap_score": round(overall, 4), "strongest_overlap_bands": strongest, "note": "Heuristic relative spectral overlap, not a psychoacoustic masking model. Use musical context before EQ/sidechain decisions."}


@mcp.tool()
def audio_bridge_status() -> dict[str, Any]:
    """Check MCP/OSC bridge health, frame freshness, bindings and live Analyzer connectivity."""
    now = time.time()
    with _lock:
        frames = list(_tracks.values()); last_frame_at = _last_frame_at; last_identify_at = _last_identify_at
        listening = _osc_listening; error = _osc_error; host = _osc_host; port = _osc_port; bound_ids = set(_bindings)
    duplicate_counts = Counter(str(frame["track"]).casefold() for frame in frames)
    tracks = [{"track": frame["track"], "id": frame["id"], "signal_present": bool(frame.get("signal_present")), "duplicate_name": duplicate_counts[str(frame["track"]).casefold()] > 1, "bound": frame["id"] in bound_ids, "age_seconds": round(max(0.0, now - float(frame["_received_at"])), 3)} for frame in sorted(frames, key=lambda item: (str(item["track"]).casefold(), str(item["id"])))]
    last_age = None if last_frame_at is None else round(max(0.0, now - last_frame_at), 3)
    identify_age = None if last_identify_at is None else round(max(0.0, now - last_identify_at), 3)
    if error:
        hint = "MCP is running, but OSC is unavailable. If the error says address already in use, stop any manually started bridge using the same UDP port, then restart this MCP server."
    elif not listening: hint = "MCP is running, but OSC listener has not started."
    elif not tracks: hint = "OSC is listening but no analyzer frames have arrived yet. Load AI Audio Analyzer.vst3, use the same OSC port, click Apply if needed, and start DAW playback."
    elif last_age is not None and last_age > STALE_SECONDS: hint = "Analyzer data is stale; check DAW playback and the VST3 OSC connection."
    else: hint = "Bridge is healthy and receiving analyzer frames."
    return {"ok": bool(listening and error is None), "pid": os.getpid(), "mcp_sdk_version": _mcp_version(), "uptime_seconds": round(max(0.0, now - _bridge_started_at), 3), "signal_gate": {"close_dbfs": SIGNAL_CLOSE_DB, "reopen_dbfs": SIGNAL_OPEN_DB, "plugin_hold_seconds": 0.4}, "osc": {"host": host, "port": port, "listening": listening, "error": error}, "track_count": len(tracks), "bound_track_count": sum(1 for item in tracks if item["bound"]), "unbound_track_count": sum(1 for item in tracks if not item["bound"]), "tracks": tracks, "last_frame_age_seconds": last_age, "last_identify_age_seconds": identify_age, "hint": hint}


@mcp.tool()
def audio_list_tracks() -> dict[str, Any]:
    """List known Analyzer instances with signal, freshness and deterministic binding context."""
    now = time.time()
    with _lock:
        frames = [dict(frame) for frame in _tracks.values()]; bindings = {runtime_id: dict(binding) for runtime_id, binding in _bindings.items()}
    duplicate_counts = Counter(str(frame["track"]).casefold() for frame in frames); tracks = []
    for frame in sorted(frames, key=lambda item: (str(item["track"]).casefold(), str(item["id"]))):
        binding = bindings.get(frame["id"])
        tracks.append({"id": frame["id"], "track": frame["track"], "duplicate_name": duplicate_counts[str(frame["track"]).casefold()] > 1, "bound": binding is not None, "binding": _binding_public(binding), "age_seconds": round(max(0.0, now - float(frame["_received_at"])), 3), "signal_present": bool(frame.get("signal_present")), "detector_peak_db": frame.get("detector_peak_db"), "silence_seconds": frame.get("silence_seconds"), "peak_db": frame["peak_db"], "true_peak_dbtp": frame.get("true_peak_dbtp"), "lufs_s": None if float(frame.get("silence_seconds", 0.0)) >= SHORT_TERM_INVALID_SILENCE_SECONDS else frame.get("lufs_s"), "lufs_i": frame.get("lufs_i")})
    return {"tracks": tracks, "count": len(tracks), "duplicate_name_count": sum(1 for count in duplicate_counts.values() if count > 1), "bound_count": sum(1 for item in tracks if item["bound"]), "note": "After V0.4 discovery, prefer FL mixer names or mixer:<index>/slot:<slot> selectors. Before discovery, duplicate analyzer names must be addressed by runtime id."}


@mcp.tool()
def audio_last_identify(max_age_seconds: float = 10.0) -> dict[str, Any]:
    """Read the latest host-triggered Identify event before binding one Analyzer to a DAW mixer slot."""
    max_age_seconds = max(0.1, min(float(max_age_seconds), 60.0)); now = time.time()
    with _lock: event = dict(_identify_events[-1]) if _identify_events else None
    if event is None: return {"available": False, "reason": "No Identify event has been received in this bridge session."}
    age = max(0.0, now - float(event["received_at"]))
    return {"available": True, "fresh": age <= max_age_seconds, "age_seconds": round(age, 3), "sequence": event["sequence"], "runtime_id": event["runtime_id"], "analyzer_name": event["analyzer_name"], "schema_version": event["schema_version"], "consumed": bool(event.get("_consumed"))}


@mcp.tool()
def audio_bind_last_identified(fl_track_index: int, fl_track_name: str, slot: int, max_age_seconds: float = DEFAULT_IDENTIFY_MAX_AGE_SECONDS) -> dict[str, Any]:
    """Bind the fresh unconsumed Identify event to one DAW mixer track/slot for this MCP session."""
    fl_track_index = int(fl_track_index); slot = int(slot)
    if fl_track_index < 0: raise ValueError("fl_track_index must be >= 0")
    if slot < 0: raise ValueError("slot must be >= 0")
    clean_name = str(fl_track_name).strip() or f"Mixer {fl_track_index}"; max_age_seconds = max(0.1, min(float(max_age_seconds), 30.0)); now = time.time()
    with _lock:
        if not _identify_events: raise ValueError("No Identify event is available. Toggle the target AI Audio Analyzer's host parameter named 'Identify', then call this tool immediately.")
        event = _identify_events[-1]; age = max(0.0, now - float(event["received_at"]))
        if age > max_age_seconds: raise ValueError(f"Latest Identify event is stale ({age:.3f}s old). Toggle the target Analyzer's Identify parameter again before binding.")
        if bool(event.get("_consumed")): raise ValueError("Latest Identify event was already consumed by a binding. Toggle the next target Analyzer's Identify parameter before binding another mixer slot.")
        runtime_id = str(event["runtime_id"])
        for existing_id, existing in list(_bindings.items()):
            if existing_id != runtime_id and int(existing["fl_track_index"]) == fl_track_index and int(existing["slot"]) == slot: del _bindings[existing_id]
        binding = {"runtime_id": runtime_id, "fl_track_index": fl_track_index, "fl_track_name": clean_name, "slot": slot, "analyzer_name": str(event["analyzer_name"]), "identify_sequence": int(event["sequence"]), "bound_at": now}
        _bindings[runtime_id] = binding; event["_consumed"] = True
    return {"ok": True, "binding": _binding_public(binding), "selector": f"mixer:{fl_track_index}/slot:{slot}", "note": "Binding is session-scoped. If the plugin/runtime UUID changes after reopening the project, run Identify discovery again."}


@mcp.tool()
def audio_instance_map() -> dict[str, Any]:
    """Inspect current Analyzer runtime instances and their session-scoped deterministic DAW bindings."""
    now = time.time()
    with _lock:
        frames = {runtime_id: dict(frame) for runtime_id, frame in _tracks.items()}; bindings = {runtime_id: dict(binding) for runtime_id, binding in _bindings.items()}
    instances = []
    for runtime_id, frame in sorted(frames.items(), key=lambda item: (str(item[1]["track"]).casefold(), item[0])):
        binding = bindings.get(runtime_id)
        instances.append({"runtime_id": runtime_id, "analyzer_name": frame["track"], "live": True, "age_seconds": round(max(0.0, now - float(frame["_received_at"])), 3), "signal_present": bool(frame.get("signal_present")), "bound": binding is not None, "binding": _binding_public(binding), "selector": f"mixer:{binding['fl_track_index']}/slot:{binding['slot']}" if binding is not None else runtime_id})
    stale_bindings = [_binding_public(binding) for runtime_id, binding in bindings.items() if runtime_id not in frames]
    return {"instances": instances, "live_count": len(instances), "bound_count": sum(1 for item in instances if item["bound"]), "unbound_count": sum(1 for item in instances if not item["bound"]), "stale_bindings": stale_bindings, "discovery_complete": bool(instances) and all(item["bound"] for item in instances), "note": "The map is deterministic because each binding is created from a host-triggered Identify event carrying that plugin instance's runtime UUID."}


@mcp.tool()
def audio_snapshot(track: str) -> dict[str, Any]:
    """Return the latest measurement frame for one Analyzer selector; use for current-state inspection."""
    return _snapshot(track)


@mcp.tool()
def audio_average(track: str, seconds: float = 5.0) -> dict[str, Any]:
    """Average recent measurements for one track over 0.1-60 seconds, using active frames for spectral/stereo evidence."""
    seconds = max(0.1, min(float(seconds), 60.0)); runtime_id = _resolve_track(track); cutoff = time.time() - seconds
    with _lock:
        frames = [frame for frame in _history.get(runtime_id, ()) if frame["_received_at"] >= cutoff]; binding = _binding_public(_bindings.get(runtime_id))
    if not frames: return _snapshot(runtime_id)
    latest = frames[-1]; active_frames = [frame for frame in frames if bool(frame.get("signal_present", True))]; active_ratio = len(active_frames) / len(frames)
    result: dict[str, Any] = {"id": runtime_id, "track": latest["track"], "bound": binding is not None, "binding": binding, "window_seconds": seconds, "frames": len(frames), "active_frames": len(active_frames), "active_ratio": round(active_ratio, 4), "analysis_valid": bool(active_frames), "signal_present": bool(latest.get("signal_present")), "detector_peak_db": latest.get("detector_peak_db"), "silence_seconds": latest.get("silence_seconds"), "band_centers_hz": BAND_CENTERS, "stereo_correlation_band_ranges": _stereo_corr_ranges(), "peak_db": max(float(frame["peak_db"]) for frame in frames), "rms_db": _mean_db_like([float(frame["rms_db"]) for frame in frames])}
    result["lufs_i"] = next((float(frame["lufs_i"]) for frame in reversed(frames) if frame.get("lufs_i") is not None), None)
    result["max_true_peak_dbtp"] = next((float(frame["max_true_peak_dbtp"]) for frame in reversed(frames) if frame.get("max_true_peak_dbtp") is not None), None)
    true_peaks = [float(frame["true_peak_dbtp"]) for frame in frames if frame.get("true_peak_dbtp") is not None]; result["true_peak_dbtp"] = max(true_peaks) if true_peaks else None
    if not active_frames:
        result.update({"crest_db": None, "centroid_hz": None, "rolloff_hz": None, "flatness": None, "stereo_correlation": None, "stereo_width": None, "lufs_s": None, "bands_db": None, "band_stereo_correlation": None, "note": "No active frames above the analyzer signal threshold occurred in this window. Spectral/stereo statistics are intentionally omitted."}); return result
    result["crest_db"] = sum(float(frame["crest_db"]) for frame in active_frames) / len(active_frames)
    result["centroid_hz"] = sum(float(frame["centroid_hz"]) for frame in active_frames) / len(active_frames)
    result["rolloff_hz"] = sum(float(frame["rolloff_hz"]) for frame in active_frames) / len(active_frames)
    result["flatness"] = sum(float(frame["flatness"]) for frame in active_frames) / len(active_frames)
    result["stereo_correlation"] = sum(float(frame["stereo_correlation"]) for frame in active_frames) / len(active_frames)
    result["stereo_width"] = sum(float(frame["stereo_width"]) for frame in active_frames) / len(active_frames)
    short_term = [float(frame["lufs_s"]) for frame in active_frames if frame.get("lufs_s") is not None]; result["lufs_s"] = _mean_db_like(short_term)
    averaged_bands = []
    for band in range(NUM_BANDS):
        mean_power = sum(10.0 ** (float(frame["bands_db"][band]) / 10.0) for frame in active_frames) / len(active_frames); averaged_bands.append(10.0 * math.log10(max(mean_power, 1e-12)))
    result["bands_db"] = averaged_bands
    corr_frames = [frame for frame in active_frames if frame.get("band_stereo_correlation") is not None]
    result["band_stereo_correlation"] = [sum(float(frame["band_stereo_correlation"][i]) for frame in corr_frames) / len(corr_frames) for i in range(NUM_STEREO_CORR_BANDS)] if corr_frames else None
    result["note"] = "Spectrum/stereo statistics use active frames only; active_ratio reports how much of the requested window contained valid input."
    return result


@mcp.tool()
def audio_stereo_bands(track: str) -> dict[str, Any]:
    """Return current frequency-dependent stereo correlation bands; low correlation is evidence, not an automatic quality judgment."""
    frame = _snapshot(track); values = frame.get("band_stereo_correlation")
    if not frame.get("stereo_valid") or values is None: return {"id": frame["id"], "track": frame["track"], "binding": frame.get("binding"), "available": False, "signal_present": frame.get("signal_present"), "reason": "No active input; stereo correlation is intentionally invalid while the signal gate is closed."}
    bands = []
    for label, value in zip(_stereo_corr_ranges(), values):
        numeric = float(value); flag = "high mono-compatibility risk" if numeric < -0.25 else "negative correlation" if numeric < 0.0 else "very wide / weakly correlated" if numeric < 0.25 else "normal/positive correlation"; bands.append({"range": label, "correlation": numeric, "flag": flag})
    return {"id": frame["id"], "track": frame["track"], "binding": frame.get("binding"), "available": True, "bands": bands, "note": "Correlation still needs musical context. Very low-energy sub-bands can carry less useful phase information than strongly occupied bands."}


@mcp.tool()
def audio_compare_tracks(track_a: str, track_b: str) -> dict[str, Any]:
    """Compare two current track spectra with a relative overlap heuristic; this does not prove audible masking."""
    return _compare_tracks(track_a, track_b)


@mcp.tool()
def audio_detect_masking(track_a: str, track_b: str) -> dict[str, Any]:
    """Return legacy current spectral-overlap masking candidates; prefer deeper masking evidence when timing/alignment matters."""
    report = _compare_tracks(track_a, track_b)
    if not report.get("available"): return {**report, "severity": None, "candidate_regions": [], "guidance": "Start playback or choose analyzer instances with active input before masking analysis."}
    candidates = [band for band in report["strongest_overlap_bands"] if band["score"] >= 0.15]
    return {"available": True, "track_a": report["track_a"], "track_a_id": report["track_a_id"], "track_b": report["track_b"], "track_b_id": report["track_b_id"], "severity": report["spectral_overlap_score"], "candidate_regions": candidates, "guidance": "Treat these regions as candidates only; also inspect timing, level, arrangement, stereo position, and transient overlap."}


@mcp.tool()
def audio_master_status(track: str = "Master") -> dict[str, Any]:
    """Summarize current master technical measurements and transparent warnings; there is no universal loudness or crest target."""
    frame = _snapshot(track); warnings = []; signal_present = bool(frame.get("signal_present"))
    if not signal_present: warnings.append("No active input above -50 dBFS; current spectrum/stereo metrics are invalid.")
    true_peak = frame.get("max_true_peak_dbtp") if frame.get("max_true_peak_dbtp") is not None else frame.get("true_peak_dbtp")
    if true_peak is not None:
        numeric_peak = float(true_peak)
        if numeric_peak > 0.0: warnings.append("True peak exceeds 0 dBTP; inter-sample clipping is likely.")
        elif numeric_peak > -1.0: warnings.append("True peak is above -1 dBTP; codec/transcoding headroom is limited.")
    elif frame["peak_db"] > -0.1: warnings.append("Sample peak is at/near digital full scale; true-peak data is unavailable.")
    if signal_present:
        correlation = frame.get("stereo_correlation"); crest = frame.get("crest_db")
        if correlation is not None and float(correlation) < 0.0: warnings.append("Negative full-band stereo correlation may indicate mono-compatibility problems.")
        if crest is not None and float(crest) < 4.0: warnings.append("Very low crest factor: dynamics may be heavily constrained, depending on genre.")
    return {"id": frame["id"], "track": frame["track"], "bound": frame.get("bound"), "binding": frame.get("binding"), "signal_present": signal_present, "detector_peak_db": frame.get("detector_peak_db"), "silence_seconds": frame.get("silence_seconds"), "peak_db": frame["peak_db"], "true_peak_dbtp": frame.get("true_peak_dbtp"), "max_true_peak_dbtp": frame.get("max_true_peak_dbtp"), "rms_db": frame["rms_db"], "crest_db": frame.get("crest_db") if signal_present else None, "lufs_s": frame.get("lufs_s"), "lufs_i": frame.get("lufs_i"), "centroid_hz": frame.get("centroid_hz"), "rolloff_hz": frame.get("rolloff_hz"), "stereo_correlation": frame.get("stereo_correlation"), "stereo_width": frame.get("stereo_width"), "band_stereo_correlation": frame.get("band_stereo_correlation"), "stereo_correlation_band_ranges": frame.get("stereo_correlation_band_ranges"), "warnings": warnings, "note": "LUFS-I is integrated since the analyzer loudness state was last reset/prepared. There is no universal LUFS target; compare against genre/reference and delivery requirements."}


def main() -> None:
    global _osc_error, _osc_host, _osc_listening, _osc_port
    host, port, config_error = _read_osc_config()
    with _lock:
        _osc_host = host; _osc_port = port; _osc_error = config_error; _osc_listening = False
    osc_server: ThreadingOSCUDPServer | None = None
    if config_error is None:
        dispatcher = Dispatcher(); dispatcher.map("/aianalyzer/frame", _on_frame); dispatcher.map("/aianalyzer/identify", _on_identify)
        try: osc_server = ThreadingOSCUDPServer((host, port), dispatcher)
        except OSError as exc:
            with _lock: _osc_error = f"{type(exc).__name__}: {exc}"
            print(f"AI Audio Analyzer OSC unavailable on udp://{host}:{port}: {exc}. MCP will stay online; use audio_bridge_status for details.", file=sys.stderr, flush=True)
        else:
            thread = threading.Thread(target=osc_server.serve_forever, name="AIAudioAnalyzerOSC", daemon=True); thread.start()
            with _lock: _osc_listening = True; _osc_error = None
            print(f"AI Audio Analyzer OSC listening on udp://{host}:{port}", file=sys.stderr, flush=True)
    else:
        print(f"AI Audio Analyzer OSC configuration error: {config_error}. MCP will stay online; use audio_bridge_status for details.", file=sys.stderr, flush=True)
    try: mcp.run(transport="stdio")
    finally:
        if osc_server is not None: osc_server.shutdown(); osc_server.server_close()
        with _lock: _osc_listening = False
