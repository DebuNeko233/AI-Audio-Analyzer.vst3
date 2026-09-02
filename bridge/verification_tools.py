#!/usr/bin/env python3
"""Closed-loop verification sessions for AI Audio Analyzer MCP 1.0.

This layer does not control a DAW. It records a measurement baseline, preserves
Analyzer topology/binding context, accepts an external control-MCP change/readback
summary, then captures a comparable After window and returns auditable A/B
measurement evidence.
"""

from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
import uuid
from typing import Any

import server as core
import project_tools as project

VERIFICATION_LIMIT = 12
DEFAULT_VERIFICATION_SECONDS = 5.0
ACTIVE_RATIO_TOLERANCE = 0.15

_verification_lock = threading.RLock()
_verifications: dict[str, dict[str, Any]] = {}


def _clean_text(value: str, *, field: str, max_length: int, required: bool = False) -> str:
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{field} must not be empty.")
    if len(text) > max_length:
        raise ValueError(f"{field} must be {max_length} characters or fewer.")
    return text


def _normalize_targets(target_selectors: list[str] | None) -> list[str]:
    if target_selectors is None:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for raw in target_selectors:
        selector = str(raw).strip()
        if not selector or selector in seen:
            continue
        seen.add(selector)
        result.append(selector)
    if len(result) > 32:
        raise ValueError("target_selectors supports at most 32 selectors.")
    return result


def _topology_payload(state: dict[str, Any]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for identity, track in sorted((state.get("tracks") or {}).items()):
        binding = track.get("binding") or {}
        payload.append(
            {
                "identity": identity,
                "runtime_id": track.get("runtime_id"),
                "analyzer_name": track.get("analyzer_name"),
                "fl_track_index": binding.get("fl_track_index"),
                "fl_track_name": binding.get("fl_track_name"),
                "slot": binding.get("slot"),
            }
        )
    return payload


def _topology_fingerprint(state: dict[str, Any]) -> str:
    encoded = json.dumps(
        _topology_payload(state),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _state_summary(state: dict[str, Any]) -> dict[str, Any]:
    tracks = state.get("tracks") or {}
    return {
        "captured_at": state.get("captured_at"),
        "window_seconds": state.get("window_seconds"),
        "track_count": len(tracks),
        "valid_track_count": sum(1 for track in tracks.values() if track.get("analysis_valid")),
        "topology_fingerprint": _topology_fingerprint(state),
        "tracks": [
            {
                "identity": identity,
                "display_name": track.get("display_name"),
                "analysis_valid": bool(track.get("analysis_valid")),
                "active_ratio": track.get("active_ratio"),
            }
            for identity, track in sorted(tracks.items())
        ],
    }


def _comparison_for_states(
    before_state: dict[str, Any],
    after_state: dict[str, Any],
    target_selectors: list[str],
) -> dict[str, Any]:
    before_tracks = before_state.get("tracks") or {}
    after_tracks = after_state.get("tracks") or {}
    before_ids = set(before_tracks)
    after_ids = set(after_tracks)
    shared = sorted(before_ids & after_ids)
    added = sorted(after_ids - before_ids)
    removed = sorted(before_ids - after_ids)

    targets = target_selectors or shared
    target_rows: list[dict[str, Any]] = []
    missing_targets: list[str] = []
    invalid_targets: list[str] = []
    coverage_mismatch_targets: list[str] = []

    for identity in targets:
        a = before_tracks.get(identity)
        b = after_tracks.get(identity)
        if a is None or b is None:
            missing_targets.append(identity)
            continue

        before_active = a.get("active_ratio")
        after_active = b.get("active_ratio")
        active_delta = project._safe_delta(before_active, after_active)
        active_abs_delta = abs(active_delta) if active_delta is not None else None
        both_valid = bool(a.get("analysis_valid")) and bool(b.get("analysis_valid"))
        coverage_ok = active_abs_delta is not None and active_abs_delta <= ACTIVE_RATIO_TOLERANCE

        if not both_valid:
            invalid_targets.append(identity)
        if not coverage_ok:
            coverage_mismatch_targets.append(identity)

        before_regions = a.get("spectral_regions") or {}
        after_regions = b.get("spectral_regions") or {}
        target_rows.append(
            {
                "identity": identity,
                "display_name_before": a.get("display_name"),
                "display_name_after": b.get("display_name"),
                "analysis_valid_before": bool(a.get("analysis_valid")),
                "analysis_valid_after": bool(b.get("analysis_valid")),
                "active_ratio_before": before_active,
                "active_ratio_after": after_active,
                "active_ratio_abs_delta": round(active_abs_delta, 4) if active_abs_delta is not None else None,
                "coverage_within_tolerance": coverage_ok,
                "delta": {
                    "peak_db": project._safe_delta(a.get("peak_db"), b.get("peak_db")),
                    "rms_db": project._safe_delta(a.get("rms_db"), b.get("rms_db")),
                    "crest_db": project._safe_delta(a.get("crest_db"), b.get("crest_db")),
                    "lufs_s": project._safe_delta(a.get("lufs_s"), b.get("lufs_s")),
                    "lufs_i": project._safe_delta(a.get("lufs_i"), b.get("lufs_i")),
                    "true_peak_dbtp": project._safe_delta(
                        a.get("true_peak_dbtp"), b.get("true_peak_dbtp")
                    ),
                    "centroid_hz": project._safe_delta(
                        a.get("centroid_hz"), b.get("centroid_hz"), 2
                    ),
                    "rolloff_hz": project._safe_delta(
                        a.get("rolloff_hz"), b.get("rolloff_hz"), 2
                    ),
                    "flatness": project._safe_delta(a.get("flatness"), b.get("flatness")),
                    "stereo_correlation": project._safe_delta(
                        a.get("stereo_correlation"), b.get("stereo_correlation")
                    ),
                    "stereo_width": project._safe_delta(
                        a.get("stereo_width"), b.get("stereo_width")
                    ),
                    "spectral_regions_db": {
                        key: project._safe_delta(before_regions.get(key), after_regions.get(key))
                        for key in sorted(set(before_regions) | set(after_regions))
                    },
                },
            }
        )

    topology_before = _topology_fingerprint(before_state)
    topology_after = _topology_fingerprint(after_state)
    topology_unchanged = topology_before == topology_after and not added and not removed
    same_window = abs(
        float(before_state.get("window_seconds") or 0.0)
        - float(after_state.get("window_seconds") or 0.0)
    ) < 1.0e-6
    controlled_comparison = bool(
        target_rows
        and not missing_targets
        and not invalid_targets
        and not coverage_mismatch_targets
        and same_window
        and topology_unchanged
    )

    warnings: list[str] = []
    if added or removed or not topology_unchanged:
        warnings.append(
            "Analyzer topology changed between Before and After; confirm that any routing/plugin-instance change was intentional."
        )
    if missing_targets:
        warnings.append("Some requested verification targets are missing from Before or After.")
    if invalid_targets:
        warnings.append("Some verification targets do not contain valid active analysis in both windows.")
    if coverage_mismatch_targets:
        warnings.append(
            "Some targets exceed the active-ratio comparability tolerance; use the same musical passage before interpreting deltas strongly."
        )
    if not same_window:
        warnings.append("Before and After measurement windows differ in duration.")

    return {
        "controlled_comparison": controlled_comparison,
        "comparability": {
            "same_window_seconds": same_window,
            "topology_unchanged": topology_unchanged,
            "active_ratio_tolerance": ACTIVE_RATIO_TOLERANCE,
            "missing_targets": missing_targets,
            "invalid_targets": invalid_targets,
            "coverage_mismatch_targets": coverage_mismatch_targets,
            "warnings": warnings,
        },
        "topology": {
            "before_fingerprint": topology_before,
            "after_fingerprint": topology_after,
            "added_tracks": added,
            "removed_tracks": removed,
        },
        "target_count": len(targets),
        "compared_target_count": len(target_rows),
        "targets": target_rows,
        "interpretation": {
            "delta_convention": "After - Before",
            "active_ratio_tolerance": (
                "A transparent passage-comparability guardrail, not a mix-quality threshold."
            ),
            "controlled_comparison": (
                "True only when topology/window/target validity/active coverage satisfy the stated guardrails. "
                "It does not mean the change is artistically better."
            ),
        },
    }


def _session_public(session: dict[str, Any], include_result: bool = False) -> dict[str, Any]:
    item = {
        "verification_id": session["verification_id"],
        "label": session["label"],
        "status": session["status"],
        "created_at": session["created_at"],
        "completed_at": session.get("completed_at"),
        "target_selectors": list(session.get("target_selectors") or []),
        "baseline": _state_summary(session["before_state"]),
        "ready_for_external_change": bool(session.get("ready_for_external_change")),
        "baseline_blockers": list(session.get("baseline_blockers") or []),
        "change_summary": session.get("change_summary", ""),
        "host_readback": session.get("host_readback", ""),
    }
    if include_result and session.get("result") is not None:
        item["result"] = copy.deepcopy(session["result"])
    return item


@core.mcp.tool()
def audio_begin_verification(
    label: str,
    seconds: float = DEFAULT_VERIFICATION_SECONDS,
    target_selectors: list[str] | None = None,
) -> dict[str, Any]:
    """Capture a controlled Before baseline before an external DAW change."""
    clean_label = _clean_text(label, field="label", max_length=96, required=True)
    seconds = project._clamp_seconds(seconds)
    targets = _normalize_targets(target_selectors)
    project_status = project.audio_project_status()
    before_state = project._capture_state(seconds)
    tracks = before_state.get("tracks") or {}

    blockers: list[str] = []
    if not tracks:
        blockers.append("No Analyzer measurement tracks were captured.")
    if not project_status.get("project_ready"):
        blockers.append(
            "Project Analyzer mapping/readiness is incomplete; establish deterministic bindings and clear stale streams first."
        )
    missing = [selector for selector in targets if selector not in tracks]
    if missing:
        blockers.append(f"Requested target selectors are not present in the baseline: {missing}")
    invalid = [
        selector
        for selector in (targets or sorted(tracks))
        if selector in tracks and not tracks[selector].get("analysis_valid")
    ]
    if invalid:
        blockers.append(
            f"Baseline contains targets without valid active analysis: {invalid}. Play the intended comparison passage and retry."
        )

    verification_id = f"verify-{uuid.uuid4().hex[:12]}"
    session = {
        "verification_id": verification_id,
        "label": clean_label,
        "status": "awaiting_external_change",
        "created_at": time.time(),
        "completed_at": None,
        "target_selectors": targets,
        "before_state": before_state,
        "baseline_project_status": copy.deepcopy(project_status),
        "ready_for_external_change": not blockers,
        "baseline_blockers": blockers,
        "change_summary": "",
        "host_readback": "",
        "result": None,
    }

    with _verification_lock:
        _verifications[verification_id] = session
        while len(_verifications) > VERIFICATION_LIMIT:
            oldest = next(iter(_verifications))
            del _verifications[oldest]

    response = _session_public(session)
    response["ok"] = True
    response["recommended_next_step"] = (
        "Use the external DAW-control MCP to make the intended change, read back the actual host state, then call audio_complete_verification()."
        if session["ready_for_external_change"]
        else "Resolve baseline_blockers and begin a new verification before making the DAW change."
    )
    response["note"] = (
        "The Analyzer does not perform the DAW change. This session records measurement/topology evidence only."
    )
    return response


@core.mcp.tool()
def audio_complete_verification(
    verification_id: str,
    seconds: float = 0.0,
    change_summary: str = "",
    host_readback: str = "",
) -> dict[str, Any]:
    """Capture the After window and return auditable closed-loop A/B evidence."""
    clean_id = _clean_text(
        verification_id, field="verification_id", max_length=64, required=True
    )
    clean_change = _clean_text(
        change_summary, field="change_summary", max_length=512, required=False
    )
    clean_readback = _clean_text(
        host_readback, field="host_readback", max_length=4096, required=False
    )

    with _verification_lock:
        session = _verifications.get(clean_id)
        if session is None:
            raise ValueError(
                f"Unknown verification {clean_id!r}. Use audio_verification_status() first."
            )
        if session.get("status") == "completed" and session.get("result") is not None:
            response = _session_public(session, include_result=True)
            response["ok"] = True
            response["already_completed"] = True
            return response
        before_state = copy.deepcopy(session["before_state"])
        targets = list(session.get("target_selectors") or [])

    baseline_seconds = float(before_state.get("window_seconds") or DEFAULT_VERIFICATION_SECONDS)
    after_seconds = baseline_seconds if float(seconds) <= 0.0 else project._clamp_seconds(seconds)
    after_project_status = project.audio_project_status()
    after_state = project._capture_state(after_seconds)
    comparison = _comparison_for_states(before_state, after_state, targets)

    result = {
        "before": _state_summary(before_state),
        "after": _state_summary(after_state),
        "comparison": comparison,
        "external_change": {
            "change_summary": clean_change,
            "host_readback": clean_readback,
            "readback_supplied": bool(clean_readback),
        },
        "project_status_after": {
            "project_ready": bool(after_project_status.get("project_ready")),
            "audio_ready": bool(after_project_status.get("audio_ready")),
            "live_count": after_project_status.get("live_count"),
            "bound_count": after_project_status.get("bound_count"),
            "stale_count": after_project_status.get("stale_count"),
            "warnings": list(after_project_status.get("warnings") or []),
        },
        "audit": {
            "verification_id": clean_id,
            "captured_at_before": before_state.get("captured_at"),
            "captured_at_after": after_state.get("captured_at"),
            "baseline_window_seconds": baseline_seconds,
            "after_window_seconds": after_seconds,
            "measurement_only": True,
            "control_mcp_required_for_change": True,
        },
    }

    with _verification_lock:
        live_session = _verifications.get(clean_id)
        if live_session is None:
            raise ValueError(f"Verification {clean_id!r} expired before completion.")
        live_session["status"] = "completed"
        live_session["completed_at"] = time.time()
        live_session["change_summary"] = clean_change
        live_session["host_readback"] = clean_readback
        live_session["after_state"] = after_state
        live_session["result"] = result
        response = _session_public(live_session, include_result=True)

    response["ok"] = True
    response["already_completed"] = False
    response["recommended_next_step"] = (
        "Use specialized Analyzer tools (temporal/masking/stereo/tonal) only where the measured deltas require deeper evidence."
    )
    return response


@core.mcp.tool()
def audio_verification_status(verification_id: str = "") -> dict[str, Any]:
    """Inspect one verification session or list recent session-scoped verifications."""
    clean_id = str(verification_id or "").strip()
    now = time.time()
    with _verification_lock:
        if clean_id:
            session = _verifications.get(clean_id)
            if session is None:
                raise ValueError(f"Unknown verification {clean_id!r}.")
            response = _session_public(copy.deepcopy(session), include_result=True)
            response["ok"] = True
            response["age_seconds"] = round(max(0.0, now - float(session["created_at"])), 3)
            response["note"] = "Verification state is Bridge-session memory only."
            return response

        sessions = [copy.deepcopy(value) for value in _verifications.values()]

    return {
        "ok": True,
        "count": len(sessions),
        "verifications": [
            {
                "verification_id": session["verification_id"],
                "label": session["label"],
                "status": session["status"],
                "age_seconds": round(max(0.0, now - float(session["created_at"])), 3),
                "ready_for_external_change": bool(session.get("ready_for_external_change")),
                "target_selectors": list(session.get("target_selectors") or []),
                "controlled_comparison": (
                    ((session.get("result") or {}).get("comparison") or {}).get(
                        "controlled_comparison"
                    )
                    if session.get("status") == "completed"
                    else None
                ),
            }
            for session in sessions
        ],
        "note": "Verification sessions are in-memory and disappear when the Analyzer MCP Bridge exits.",
    }
