#!/usr/bin/env python3
"""Transport-anchored same-range verification for AI Audio Analyzer MCP.

This is deliberately separate from the legacy recent-window verification API.
It freezes a retained Before range, requires a clean post-baseline replay of the
same effective DAW-time range, and returns auditable After-minus-Before evidence.
"""

from __future__ import annotations

import copy
import threading
import time
import uuid
from typing import Any

import server as core
import project_tools as project
import range_tools as ranges
import verification_tools as legacy

RANGE_VERIFICATION_LIMIT = 12

_range_verification_lock = threading.RLock()
_range_verifications: dict[str, dict[str, Any]] = {}


def _live_feature_masks() -> dict[str, int]:
    masks: dict[str, int] = {}
    for runtime_id in project._live_runtime_ids():
        with core._lock:
            frame = dict(core._tracks.get(runtime_id, {}))
            binding = copy.deepcopy(core._bindings.get(runtime_id))
        selector = project._binding_selector(binding, runtime_id)
        try:
            masks[selector] = max(0, int(frame.get("analysis_feature_mask", 63)))
        except (TypeError, ValueError):
            masks[selector] = 63
    return masks


def _state_summary(state: dict[str, Any]) -> dict[str, Any]:
    tracks = state.get("tracks") or {}
    return {
        "captured_at": state.get("captured_at"),
        "capture_mode": "transport_range",
        "requested_range": copy.deepcopy(state.get("requested_range")),
        "effective_range": copy.deepcopy(state.get("effective_range")),
        "resolution_seconds": state.get("resolution_seconds"),
        "minimum_coverage": state.get("minimum_coverage"),
        "track_count": len(tracks),
        "valid_track_count": sum(bool(track.get("analysis_valid")) for track in tracks.values()),
        "topology_fingerprint": legacy._topology_fingerprint(state),
        "tracks": [
            {
                "identity": identity,
                "runtime_id": track.get("runtime_id"),
                "display_name": track.get("display_name"),
                "analysis_valid": bool(track.get("analysis_valid")),
                "active_ratio": track.get("active_ratio"),
                "feature_availability": copy.deepcopy(track.get("feature_availability") or {}),
                "selected_transport_epoch": track.get("selected_transport_epoch"),
                "coverage_ratio": track.get("range_coverage_ratio"),
                "first_received_at": (track.get("range_provenance") or {}).get("first_received_at"),
                "last_received_at": (track.get("range_provenance") or {}).get("last_received_at"),
            }
            for identity, track in sorted(tracks.items())
        ],
    }


def _target_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_regions = before.get("spectral_regions") or {}
    after_regions = after.get("spectral_regions") or {}
    return {
        "peak_db": project._safe_delta(before.get("peak_db"), after.get("peak_db")),
        "rms_db": project._safe_delta(before.get("rms_db"), after.get("rms_db")),
        "crest_db": project._safe_delta(before.get("crest_db"), after.get("crest_db")),
        "lufs_s": project._safe_delta(before.get("lufs_s"), after.get("lufs_s")),
        "true_peak_dbtp": project._safe_delta(
            before.get("true_peak_dbtp"), after.get("true_peak_dbtp")
        ),
        "centroid_hz": project._safe_delta(
            before.get("centroid_hz"), after.get("centroid_hz"), 2
        ),
        "stereo_correlation": project._safe_delta(
            before.get("stereo_correlation"), after.get("stereo_correlation")
        ),
        "stereo_width": project._safe_delta(
            before.get("stereo_width"), after.get("stereo_width")
        ),
        "spectral_flux_mean": project._safe_delta(
            before.get("spectral_flux_mean"), after.get("spectral_flux_mean"), 6
        ),
        "spectral_regions_db": {
            key: project._safe_delta(before_regions.get(key), after_regions.get(key))
            for key in sorted(set(before_regions) | set(after_regions))
        },
    }


def _comparison(
    before_state: dict[str, Any],
    after_state: dict[str, Any],
    targets: list[str],
    *,
    baseline_ready: bool,
    baseline_feature_masks: dict[str, int],
    after_feature_masks: dict[str, int],
    receive_fence: float,
) -> dict[str, Any]:
    before_tracks = before_state.get("tracks") or {}
    after_tracks = after_state.get("tracks") or {}
    before_ids = set(before_tracks)
    after_ids = set(after_tracks)
    shared = sorted(before_ids & after_ids)
    target_ids = targets or shared

    before_range = before_state.get("effective_range") or {}
    after_range = after_state.get("effective_range") or {}
    same_effective_range = before_range == after_range and bool(before_range)

    added = sorted(after_ids - before_ids)
    removed = sorted(before_ids - after_ids)
    topology_before = legacy._topology_fingerprint(before_state)
    topology_after = legacy._topology_fingerprint(after_state)
    topology_unchanged = topology_before == topology_after and not added and not removed

    missing_targets: list[str] = []
    invalid_targets: list[str] = []
    retained_feature_mismatch_targets: list[str] = []
    live_feature_mask_mismatch_targets: list[str] = []
    dropped_block_regression_targets: list[str] = []
    stale_after_targets: list[str] = []
    target_rows: list[dict[str, Any]] = []

    for identity in target_ids:
        before = before_tracks.get(identity)
        after = after_tracks.get(identity)
        if before is None or after is None:
            missing_targets.append(identity)
            continue

        before_valid = bool(before.get("analysis_valid"))
        after_valid = bool(after.get("analysis_valid"))
        if not before_valid or not after_valid:
            invalid_targets.append(identity)

        before_features = copy.deepcopy(before.get("feature_availability") or {})
        after_features = copy.deepcopy(after.get("feature_availability") or {})
        retained_features_compatible = before_features == after_features and bool(before_features)
        if not retained_features_compatible:
            retained_feature_mismatch_targets.append(identity)

        before_mask = baseline_feature_masks.get(identity)
        after_mask = after_feature_masks.get(identity)
        live_feature_mask_compatible = before_mask is not None and before_mask == after_mask
        if not live_feature_mask_compatible:
            live_feature_mask_mismatch_targets.append(identity)

        before_quality = (before.get("range_provenance") or {}).get("data_quality") or {}
        after_quality = (after.get("range_provenance") or {}).get("data_quality") or {}
        before_drops = int(before_quality.get("dropped_blocks_cumulative", 0) or 0)
        after_drops = int(after_quality.get("dropped_blocks_cumulative", 0) or 0)
        dropped_regression = after_drops > before_drops
        if dropped_regression:
            dropped_block_regression_targets.append(identity)

        after_first_received = (after.get("range_provenance") or {}).get("first_received_at")
        after_is_new = (
            after_first_received is not None
            and float(after_first_received) > float(receive_fence)
        )
        if not after_is_new:
            stale_after_targets.append(identity)

        before_active = before.get("active_ratio")
        after_active = after.get("active_ratio")
        active_delta = project._safe_delta(before_active, after_active)
        active_abs_delta = None if active_delta is None else round(abs(active_delta), 4)

        target_rows.append(
            {
                "identity": identity,
                "display_name_before": before.get("display_name"),
                "display_name_after": after.get("display_name"),
                "before": {
                    "runtime_id": before.get("runtime_id"),
                    "selected_transport_epoch": before.get("selected_transport_epoch"),
                    "coverage_ratio": before.get("range_coverage_ratio"),
                    "first_received_at": (before.get("range_provenance") or {}).get("first_received_at"),
                    "last_received_at": (before.get("range_provenance") or {}).get("last_received_at"),
                    "feature_availability": before_features,
                    "live_feature_mask_at_freeze": before_mask,
                    "dropped_blocks_cumulative": before_drops,
                },
                "after": {
                    "runtime_id": after.get("runtime_id"),
                    "selected_transport_epoch": after.get("selected_transport_epoch"),
                    "coverage_ratio": after.get("range_coverage_ratio"),
                    "first_received_at": after_first_received,
                    "last_received_at": (after.get("range_provenance") or {}).get("last_received_at"),
                    "feature_availability": after_features,
                    "live_feature_mask_at_freeze": after_mask,
                    "dropped_blocks_cumulative": after_drops,
                    "post_baseline_receive_fence": after_is_new,
                },
                "analysis_valid_before": before_valid,
                "analysis_valid_after": after_valid,
                "retained_feature_availability_compatible": retained_features_compatible,
                "live_feature_mask_compatible": live_feature_mask_compatible,
                "dropped_block_regression": dropped_regression,
                "active_ratio_before": before_active,
                "active_ratio_after": after_active,
                "active_ratio_abs_delta": active_abs_delta,
                "delta": _target_delta(before, after),
            }
        )

    controlled = bool(
        baseline_ready
        and target_rows
        and same_effective_range
        and topology_unchanged
        and not missing_targets
        and not invalid_targets
        and not retained_feature_mismatch_targets
        and not dropped_block_regression_targets
        and not stale_after_targets
    )

    warnings: list[str] = []
    if not baseline_ready:
        warnings.append("The frozen Before range was not ready for an external change.")
    if not same_effective_range:
        warnings.append("Before and After do not refer to the same normalized DAW-time range.")
    if not topology_unchanged:
        warnings.append("Analyzer topology/bindings changed between Before and After.")
    if missing_targets:
        warnings.append("Some requested targets are missing from Before or After.")
    if invalid_targets:
        warnings.append("Some targets do not have adequate retained coverage in both passes.")
    if retained_feature_mismatch_targets:
        warnings.append("Some targets retained different measurement families in Before and After, so their range evidence is not feature-compatible.")
    if live_feature_mask_mismatch_targets:
        warnings.append("Some live Analyzer feature masks differ at the Before/After freeze moments. This is audit context only; historical comparability is judged from retained range evidence.")
    if dropped_block_regression_targets:
        warnings.append("Some targets report a higher cumulative dropped-block count after the change.")
    if stale_after_targets:
        warnings.append("Some After targets are not from a clean pass first observed after the frozen receive-time fence.")

    return {
        "controlled_comparison": controlled,
        "comparability": {
            "baseline_ready": bool(baseline_ready),
            "same_effective_range": same_effective_range,
            "topology_unchanged": topology_unchanged,
            "missing_targets": missing_targets,
            "invalid_targets": invalid_targets,
            "retained_feature_mismatch_targets": retained_feature_mismatch_targets,
            "live_feature_mask_mismatch_targets": live_feature_mask_mismatch_targets,
            "dropped_block_regression_targets": dropped_block_regression_targets,
            "stale_after_targets": stale_after_targets,
            "warnings": warnings,
        },
        "range": {
            "requested_range": copy.deepcopy(before_state.get("requested_range")),
            "effective_range": copy.deepcopy(before_state.get("effective_range")),
            "resolution_seconds": before_state.get("resolution_seconds"),
            "receive_fence": receive_fence,
        },
        "topology": {
            "before_fingerprint": topology_before,
            "after_fingerprint": topology_after,
            "added_tracks": added,
            "removed_tracks": removed,
        },
        "target_count": len(target_ids),
        "compared_target_count": len(target_rows),
        "targets": target_rows,
        "interpretation": {
            "delta_convention": "After - Before",
            "active_ratio": "Descriptive evidence only in same-range mode; it is not used as a proxy for passage identity.",
            "controlled_comparison": "Technical same-range comparability only. It does not mean the artistic change is better.",
            "retained_feature_availability": "Derived from measurement families actually present in each retained range summary. It is the historical feature-compatibility gate for P4a.",
            "live_feature_mask": "Captured from the live Analyzer frame at each freeze moment for audit context only. Song Memory does not yet retain an exact per-bin feature-mask bitfield.",
        },
    }


def _public(session: dict[str, Any], *, include_result: bool = False) -> dict[str, Any]:
    item = {
        "verification_id": session["verification_id"],
        "label": session["label"],
        "status": session["status"],
        "created_at": session["created_at"],
        "completed_at": session.get("completed_at"),
        "target_selectors": list(session.get("target_selectors") or []),
        "requested_range": copy.deepcopy(session.get("requested_range")),
        "effective_range": copy.deepcopy(session.get("effective_range")),
        "resolution_seconds": session.get("resolution_seconds"),
        "minimum_coverage": session.get("minimum_coverage"),
        "receive_fence": session.get("receive_fence"),
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
def audio_begin_range_verification(
    label: str,
    start_seconds: float,
    end_seconds: float,
    target_selectors: list[str] | None = None,
    minimum_coverage: float = ranges.DEFAULT_MINIMUM_COVERAGE,
) -> dict[str, Any]:
    """Freeze a retained Before baseline for one explicit DAW-time range."""
    clean_label = legacy._clean_text(label, field="label", max_length=96, required=True)
    targets = legacy._normalize_targets(target_selectors)
    project_status = project.audio_project_status()
    before_state = ranges.capture_range_state(
        start_seconds,
        end_seconds,
        target_selectors=targets,
        minimum_coverage=minimum_coverage,
    )
    canonical_targets = list(before_state.get("canonical_target_selectors") or [])
    effective_targets = canonical_targets or sorted((before_state.get("tracks") or {}).keys())
    tracks = before_state.get("tracks") or {}

    blockers: list[str] = []
    if not tracks:
        blockers.append("No live Analyzer instances are available.")
    if not project_status.get("project_ready"):
        blockers.append("Project Analyzer mapping/readiness is incomplete; establish deterministic bindings and clear stale streams first.")
    invalid = [identity for identity in effective_targets if not (tracks.get(identity) or {}).get("analysis_valid")]
    if invalid:
        blockers.append(
            f"Before range does not have adequate retained coverage for targets: {invalid}. Play/capture the intended range and retry."
        )

    receive_fence = time.time()
    verification_id = f"verify-range-{uuid.uuid4().hex[:12]}"
    session = {
        "verification_id": verification_id,
        "label": clean_label,
        "status": "awaiting_external_change",
        "created_at": receive_fence,
        "completed_at": None,
        "target_selectors": effective_targets,
        "requested_range": copy.deepcopy(before_state.get("requested_range")),
        "effective_range": copy.deepcopy(before_state.get("effective_range")),
        "resolution_seconds": before_state.get("resolution_seconds"),
        "minimum_coverage": before_state.get("minimum_coverage"),
        "receive_fence": receive_fence,
        "before_state": before_state,
        "baseline_feature_masks": _live_feature_masks(),
        "baseline_project_status": copy.deepcopy(project_status),
        "ready_for_external_change": not blockers,
        "baseline_blockers": blockers,
        "change_summary": "",
        "host_readback": "",
        "result": None,
    }

    with _range_verification_lock:
        _range_verifications[verification_id] = session
        while len(_range_verifications) > RANGE_VERIFICATION_LIMIT:
            oldest = next(iter(_range_verifications))
            del _range_verifications[oldest]

    response = _public(session)
    response["ok"] = True
    response["recommended_next_step"] = (
        "Use the external DAW-control MCP for one intended change and actual host readback, then replay the same effective DAW range and call audio_complete_range_verification()."
        if session["ready_for_external_change"]
        else "Resolve baseline_blockers, capture the intended range with adequate coverage, and begin a new range verification before changing the DAW."
    )
    response["note"] = (
        "Fractional boundaries are normalized to one-second retained Song Memory bins. "
        "This API does not perform any sound-changing DAW operation."
    )
    return response


@core.mcp.tool()
def audio_complete_range_verification(
    verification_id: str,
    change_summary: str = "",
    host_readback: str = "",
) -> dict[str, Any]:
    """Resolve a clean post-change replay of the same range and compare it."""
    clean_id = legacy._clean_text(
        verification_id, field="verification_id", max_length=64, required=True
    )
    clean_change = legacy._clean_text(
        change_summary, field="change_summary", max_length=512, required=False
    )
    clean_readback = legacy._clean_text(
        host_readback, field="host_readback", max_length=4096, required=False
    )

    with _range_verification_lock:
        session = _range_verifications.get(clean_id)
        if session is None:
            raise ValueError(
                f"Unknown range verification {clean_id!r}. Use audio_range_verification_status() first."
            )
        if session.get("status") == "completed" and session.get("result") is not None:
            response = _public(session, include_result=True)
            response["ok"] = True
            response["already_completed"] = True
            return response
        before_state = copy.deepcopy(session["before_state"])
        targets = list(session.get("target_selectors") or [])
        baseline_ready = bool(session.get("ready_for_external_change"))
        receive_fence = float(session["receive_fence"])
        minimum_coverage = float(session["minimum_coverage"])
        requested = copy.deepcopy(session["requested_range"])
        baseline_feature_masks = copy.deepcopy(session.get("baseline_feature_masks") or {})

    after_project_status = project.audio_project_status()
    after_state = ranges.capture_range_state(
        float(requested["start_seconds"]),
        float(requested["end_seconds"]),
        target_selectors=targets,
        after_received_at=receive_fence,
        minimum_coverage=minimum_coverage,
    )
    after_feature_masks = _live_feature_masks()
    comparison = _comparison(
        before_state,
        after_state,
        targets,
        baseline_ready=baseline_ready,
        baseline_feature_masks=baseline_feature_masks,
        after_feature_masks=after_feature_masks,
        receive_fence=receive_fence,
    )
    readback_supplied = bool(clean_readback)
    closed_loop_complete = bool(comparison["controlled_comparison"] and readback_supplied)

    result = {
        "closed_loop_complete": closed_loop_complete,
        "before": _state_summary(before_state),
        "after": _state_summary(after_state),
        "comparison": comparison,
        "external_change": {
            "change_summary": clean_change,
            "host_readback": clean_readback,
            "readback_supplied": readback_supplied,
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
            "capture_mode": "transport_range",
            "requested_range": copy.deepcopy(before_state.get("requested_range")),
            "effective_range": copy.deepcopy(before_state.get("effective_range")),
            "resolution_seconds": before_state.get("resolution_seconds"),
            "minimum_coverage": minimum_coverage,
            "receive_fence": receive_fence,
            "baseline_ready": baseline_ready,
            "measurement_only": True,
            "control_mcp_required_for_change": True,
            "closed_loop_complete_requires_readback": True,
        },
        "interpretation": {
            "controlled_comparison": "Technical same-range measurement comparability only; not artistic success.",
            "closed_loop_complete": "True only when the same-range comparison is controlled and caller-supplied actual host readback is present. It still does not mean the change is artistically better.",
        },
    }

    with _range_verification_lock:
        live_session = _range_verifications.get(clean_id)
        if live_session is None:
            raise ValueError(f"Range verification {clean_id!r} expired before completion.")
        live_session["status"] = "completed"
        live_session["completed_at"] = time.time()
        live_session["change_summary"] = clean_change
        live_session["host_readback"] = clean_readback
        live_session["after_state"] = after_state
        live_session["result"] = result
        response = _public(live_session, include_result=True)

    response["ok"] = True
    response["already_completed"] = False
    response["recommended_next_step"] = (
        "Use the measured same-range deltas plus specialized evidence to decide whether to keep, refine, or roll back the external DAW change."
        if closed_loop_complete
        else "Resolve the reported coverage/new-pass/retained-feature/topology/readback gap before treating this as a complete verification."
    )
    return response


@core.mcp.tool()
def audio_range_verification_status(verification_id: str = "") -> dict[str, Any]:
    """Inspect one same-range verification or list recent range verifications."""
    clean_id = str(verification_id or "").strip()
    now = time.time()
    with _range_verification_lock:
        if clean_id:
            session = _range_verifications.get(clean_id)
            if session is None:
                raise ValueError(f"Unknown range verification {clean_id!r}.")
            response = _public(copy.deepcopy(session), include_result=True)
            response["ok"] = True
            response["age_seconds"] = round(max(0.0, now - float(session["created_at"])), 3)
            response["note"] = "Range verification state is MCP-session memory only."
            return response
        sessions = [copy.deepcopy(value) for value in _range_verifications.values()]

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
                "effective_range": copy.deepcopy(session.get("effective_range")),
                "controlled_comparison": (
                    ((session.get("result") or {}).get("comparison") or {}).get("controlled_comparison")
                    if session.get("status") == "completed"
                    else None
                ),
                "closed_loop_complete": (
                    (session.get("result") or {}).get("closed_loop_complete")
                    if session.get("status") == "completed"
                    else None
                ),
            }
            for session in sessions
        ],
        "note": "Range verification sessions are in-memory and disappear when the Analyzer MCP exits.",
    }
