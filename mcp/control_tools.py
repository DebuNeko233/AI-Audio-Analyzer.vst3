#!/usr/bin/env python3
"""Analyzer-owned local control for Analysis Profile.

This module is deliberately narrow. It can only request the Analyzer's own
measurement-performance profile (Eco/Balanced/Mix/Full). It does not expose DAW
mixing, synth, routing, gain, pan, EQ, compressor, or other artistic parameters.

The control path is loopback-only and session-scoped:

MCP tool -> deterministic local UDP candidate ports -> target VST3 runtime UUID
-> JUCE message thread -> host-visible analysis_profile parameter -> UDP ACK.

No OSC analysis-frame fields are changed; frame protocol 1.2 remains append-only.
"""

from __future__ import annotations

import socket
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from pythonosc import osc_packet
from pythonosc.osc_message_builder import OscMessageBuilder

import server as core

CONTROL_PORT_BASE = 20000
CONTROL_PORT_SPAN = 40000
CONTROL_CANDIDATE_COUNT = 16
CONTROL_STEP_MODULO = 997
CONTROL_PROFILE_ADDRESS = "/aianalyzer/control/profile"
CONTROL_ACK_ADDRESS = "/aianalyzer/control/ack"
CONTROL_REVISION = "1"

PROFILE_NAMES = ("eco", "balanced", "mix", "full")
PROFILE_DISPLAY_NAMES = ("Eco", "Balanced", "Mix", "Full")


def _fnv1a(text: str) -> int:
    value = 2166136261
    for byte in text.encode("utf-8"):
        value ^= byte
        value = (value * 16777619) & 0xFFFFFFFF
    return value


def _candidate_ports(runtime_id: str) -> list[int]:
    digest = _fnv1a(runtime_id)
    start = digest % CONTROL_PORT_SPAN
    step = 1 + ((digest ^ 0x9E3779B9) % CONTROL_STEP_MODULO)
    while step % 2 == 0 or step % 5 == 0:
        step += 1
    return [
        CONTROL_PORT_BASE + ((start + i * step) % CONTROL_PORT_SPAN)
        for i in range(CONTROL_CANDIDATE_COUNT)
    ]


def _parse_profile(profile: str | int) -> int:
    if isinstance(profile, bool):
        raise ValueError("profile must be Eco, Balanced, Mix, Full, or index 0..3")
    if isinstance(profile, int):
        if 0 <= profile <= 3:
            return profile
        raise ValueError("profile index must be 0..3")

    clean = str(profile).strip().casefold()
    aliases = {
        "0": 0,
        "eco": 0,
        "1": 1,
        "balanced": 1,
        "balance": 1,
        "2": 2,
        "mix": 2,
        "3": 3,
        "full": 3,
    }
    if clean not in aliases:
        raise ValueError("profile must be Eco, Balanced, Mix, Full, or index 0..3")
    return aliases[clean]


def _build_profile_command(runtime_id: str,
                           profile_index: int,
                           request_id: str,
                           reply_port: int) -> bytes:
    builder = OscMessageBuilder(address=CONTROL_PROFILE_ADDRESS)
    builder.add_arg(runtime_id)
    builder.add_arg(int(profile_index))
    builder.add_arg(request_id)
    builder.add_arg(int(reply_port))
    return builder.build().dgram


def _decode_ack(data: bytes,
                runtime_id: str,
                request_id: str,
                profile_index: int) -> tuple[bool, bool | None]:
    """Validate an ACK and return (acknowledged, host_state_changed).

    Revision 1 originally defined four required ACK arguments. Current VST3
    builds append a fifth integer carrying whether the real host-visible profile
    differed immediately before this request. Keeping the first four arguments
    unchanged preserves compatibility with older revision-1 ACK readers.
    """
    try:
        packet = osc_packet.OscPacket(data)
    except osc_packet.ParseError:
        return False, None

    for timed_message in packet.messages:
        message = timed_message.message
        if message.address != CONTROL_ACK_ADDRESS:
            continue
        args = list(message)
        if len(args) < 4:
            continue
        try:
            ack_profile = int(args[2])
        except (TypeError, ValueError):
            continue
        if (str(args[0]) != runtime_id
                or str(args[1]) != request_id
                or ack_profile != profile_index
                or str(args[3]) != CONTROL_REVISION):
            continue

        changed: bool | None = None
        if len(args) >= 5:
            try:
                changed = bool(int(args[4]))
            except (TypeError, ValueError):
                changed = None
        return True, changed
    return False, None


def _observed_profile(runtime_id: str) -> tuple[int | None, float | None]:
    with core._lock:
        frame = core._tracks.get(runtime_id)
        if frame is None:
            return None, None
        raw_index = frame.get("analysis_profile_index")
        received_at = frame.get("_received_at")
    try:
        index = None if raw_index is None else max(0, min(3, int(raw_index)))
    except (TypeError, ValueError):
        index = None
    try:
        received = None if received_at is None else float(received_at)
    except (TypeError, ValueError):
        received = None
    return index, received


def _send_profile_request(runtime_id: str,
                          profile_index: int,
                          timeout_seconds: float) -> dict[str, Any]:
    # Retained telemetry is observation evidence, not authority for current host
    # state while transport is stopped. Always require a live VST3 control ACK,
    # even when the newest retained frame already shows the requested profile.
    before_index, before_received = _observed_profile(runtime_id)
    request_id = uuid.uuid4().hex
    ports = _candidate_ports(runtime_id)
    timeout_seconds = max(0.25, min(float(timeout_seconds), 3.0))

    attempts = 0
    acknowledged = False
    ack_changed: bool | None = None
    socket_error: str | None = None

    reply_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        try:
            reply_socket.bind(("127.0.0.1", 0))
            reply_port = int(reply_socket.getsockname()[1])
            command = _build_profile_command(runtime_id, profile_index, request_id, reply_port)
            deadline = time.monotonic() + timeout_seconds
            next_send = 0.0

            while time.monotonic() < deadline:
                now = time.monotonic()
                if now >= next_send:
                    attempts += 1
                    try:
                        for port in ports:
                            reply_socket.sendto(command, ("127.0.0.1", port))
                    except OSError as exc:
                        socket_error = f"{type(exc).__name__}: {exc}"
                        break
                    next_send = now + 0.20

                remaining = deadline - time.monotonic()
                if remaining <= 0.0:
                    break
                reply_socket.settimeout(min(0.08, remaining))
                try:
                    data, _sender = reply_socket.recvfrom(4096)
                except socket.timeout:
                    continue
                except BlockingIOError:
                    # Defensive guard for platforms that can expose a
                    # nonblocking edge at an extremely small timeout.
                    continue
                except OSError as exc:
                    socket_error = f"{type(exc).__name__}: {exc}"
                    break

                acknowledged, ack_changed = _decode_ack(
                    data, runtime_id, request_id, profile_index
                )
                if acknowledged:
                    break
        except OSError as exc:
            socket_error = f"{type(exc).__name__}: {exc}"
    finally:
        reply_socket.close()

    after_index, after_received = _observed_profile(runtime_id)
    telemetry_confirmed = (
        after_index == profile_index
        and after_received is not None
        and (before_received is None or after_received > before_received)
    )

    common = {
        "runtime_id": runtime_id,
        "profile": PROFILE_NAMES[profile_index],
        "profile_display": PROFILE_DISPLAY_NAMES[profile_index],
        "profile_index": profile_index,
        "observed_profile_before": (
            None if before_index is None else PROFILE_NAMES[before_index]
        ),
        "attempts": attempts,
        "candidate_port_count": len(ports),
    }

    if not acknowledged:
        reason = (
            "No loopback control ACK was received. The live VST3 may predate Analyzer-owned "
            "profile control, its local control receiver may be unavailable, or the host may be shutting down. "
            "Do not assume the profile changed."
        )
        if socket_error is not None:
            reason = f"Local control socket failed ({socket_error}). Do not assume the profile changed."
        return {
            **common,
            "ok": False,
            "changed": None,
            "control_acknowledged": False,
            "telemetry_confirmed": telemetry_confirmed,
            "reason": reason,
        }

    return {
        **common,
        "ok": True,
        "changed": ack_changed,
        "control_acknowledged": True,
        "telemetry_confirmed": telemetry_confirmed,
        "note": (
            "The live VST3 acknowledged the host-visible Analysis Profile request. "
            "When available, changed is reported by the VST3 from the actual host parameter state immediately "
            "before applying this request. telemetry_confirmed is true only if a newer Analyzer frame also reports "
            "the target profile; playback is not required for the control ACK itself."
        ),
    }


@core.mcp.tool()
def audio_set_analysis_profile(track: str,
                               profile: str,
                               timeout_seconds: float = 1.0) -> dict[str, Any]:
    """Set one Analyzer's own measurement profile without changing the audio signal."""
    runtime_id = core._resolve_track(track)
    profile_index = _parse_profile(profile)
    result = _send_profile_request(runtime_id, profile_index, timeout_seconds)
    with core._lock:
        frame = core._tracks.get(runtime_id)
        binding = core._binding_public(core._bindings.get(runtime_id))
        analyzer_name = None if frame is None else frame.get("track")
    result["track"] = analyzer_name
    result["binding"] = binding
    result["scope"] = "Analyzer measurement-performance control only; no DAW/artistic audio parameter is modified."
    return result


@core.mcp.tool()
def audio_set_project_analysis_profile(profile: str,
                                       tracks: list[str] | None = None,
                                       timeout_seconds: float = 1.0) -> dict[str, Any]:
    """Set the Analyzer measurement profile across selected or all live instances."""
    profile_index = _parse_profile(profile)

    if tracks is None:
        with core._lock:
            runtime_ids = list(core._tracks.keys())
    else:
        runtime_ids = []
        for selector in tracks:
            runtime_id = core._resolve_track(selector)
            if runtime_id not in runtime_ids:
                runtime_ids.append(runtime_id)

    if not runtime_ids:
        return {
            "ok": False,
            "profile": PROFILE_NAMES[profile_index],
            "profile_display": PROFILE_DISPLAY_NAMES[profile_index],
            "requested_count": 0,
            "confirmed_count": 0,
            "failed_count": 0,
            "results": [],
            "reason": "No live Analyzer instances matched the request.",
        }

    workers = min(16, len(runtime_ids))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="AnalyzerProfileControl") as executor:
        futures = [
            executor.submit(_send_profile_request, runtime_id, profile_index, timeout_seconds)
            for runtime_id in runtime_ids
        ]
        results = [future.result() for future in futures]

    with core._lock:
        names = {
            runtime_id: core._tracks.get(runtime_id, {}).get("track")
            for runtime_id in runtime_ids
        }
        bindings = {
            runtime_id: core._binding_public(core._bindings.get(runtime_id))
            for runtime_id in runtime_ids
        }
    for row in results:
        runtime_id = str(row["runtime_id"])
        row["track"] = names.get(runtime_id)
        row["binding"] = bindings.get(runtime_id)

    confirmed = sum(bool(row.get("ok")) for row in results)
    return {
        "ok": confirmed == len(results),
        "profile": PROFILE_NAMES[profile_index],
        "profile_display": PROFILE_DISPLAY_NAMES[profile_index],
        "profile_index": profile_index,
        "requested_count": len(results),
        "confirmed_count": confirmed,
        "failed_count": len(results) - confirmed,
        "results": results,
        "scope": "Analyzer measurement-performance control only; no DAW/artistic audio parameter is modified.",
    }


def _self_test() -> dict[str, Any]:
    runtime_id = "00000000-0000-0000-0000-000000000001"
    expected = [
        43038, 43415, 43792, 44169,
        44546, 44923, 45300, 45677,
        46054, 46431, 46808, 47185,
        47562, 47939, 48316, 48693,
    ]
    actual = _candidate_ports(runtime_id)
    if actual != expected:
        raise RuntimeError(f"Analyzer control port protocol regression: {actual}")
    if len(set(actual)) != CONTROL_CANDIDATE_COUNT:
        raise RuntimeError("Analyzer control candidate ports must be unique")
    if [_parse_profile(name) for name in PROFILE_NAMES] != [0, 1, 2, 3]:
        raise RuntimeError("Analyzer profile parser regression")

    request_id = "self-test-request"
    ack_builder = OscMessageBuilder(address=CONTROL_ACK_ADDRESS)
    ack_builder.add_arg(runtime_id)
    ack_builder.add_arg(request_id)
    ack_builder.add_arg(2)
    ack_builder.add_arg(CONTROL_REVISION)
    ack_builder.add_arg(1)
    acknowledged, changed = _decode_ack(
        ack_builder.build().dgram, runtime_id, request_id, 2
    )
    if not acknowledged or changed is not True:
        raise RuntimeError("Analyzer control ACK parser regression")

    legacy_ack_builder = OscMessageBuilder(address=CONTROL_ACK_ADDRESS)
    legacy_ack_builder.add_arg(runtime_id)
    legacy_ack_builder.add_arg(request_id)
    legacy_ack_builder.add_arg(2)
    legacy_ack_builder.add_arg(CONTROL_REVISION)
    acknowledged, changed = _decode_ack(
        legacy_ack_builder.build().dgram, runtime_id, request_id, 2
    )
    if not acknowledged or changed is not None:
        raise RuntimeError("Analyzer legacy revision-1 ACK compatibility regression")

    return {
        "revision": CONTROL_REVISION,
        "candidate_port_protocol": "ok",
        "profile_parser": "ok",
        "ack_parser": "ok",
    }
