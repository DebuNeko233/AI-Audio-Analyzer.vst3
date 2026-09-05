#!/usr/bin/env python3
"""Project/runtime identity disclosure for AI Audio Analyzer MCP.

This module intentionally does not invent a stable DAW project identity.
It exposes the current limitation in machine-readable form so callers do not
mistake runtime UUIDs, mixer-slot bindings, or retained MCP state for persistent
project/track identity across project switches or project reopen events.
"""

from __future__ import annotations

from typing import Any

import server as core


def identity_status() -> dict[str, Any]:
    """Return current identity guarantees and explicit non-guarantees."""
    return {
        "stable_project_id": None,
        "project_identity_confidence": "UNRESOLVED",
        "project_switch_detection": "not_available",
        "runtime_id": {
            "scope": "live_plugin_instance",
            "persistent": False,
            "serialized_with_project": False,
            "stable_when_same_project_is_reopened": False,
            "changes_when_plugin_instance_is_recreated": True,
        },
        "binding": {
            "scope": "mcp_session",
            "persistent": False,
            "selector_example": "mixer:<index>/slot:<slot>",
            "stable_track_identity": False,
        },
        "retained_state": {
            "scope": "mcp_session",
            "automatically_partitioned_by_stable_project_id": False,
            "cross_project_isolation_guaranteed": False,
            "may_outlive_a_project_switch_while_mcp_keeps_running": True,
        },
        "caller_requirements": [
            "Do not use runtime_id as a persistent project or track identifier.",
            "Do not assume that a new runtime UUID means a different project; reopening the same project also recreates runtime UUIDs.",
            "Do not assume retained Song Memory, Section Maps, snapshots, relationships, or verification sessions belong to the current project after a project switch/reopen while MCP remains running.",
            "Until exact external project identity is integrated, restart the Analyzer MCP when changing/reopening projects if strict state isolation is required.",
        ],
        "future_authority": (
            "A future exact DAW project identity from the external DAW-control layer (P3/P5) must become authoritative for persistent project memory and automatic cross-session reconciliation."
        ),
    }


@core.mcp.tool()
def audio_project_identity_status() -> dict[str, Any]:
    """Describe project/runtime identity scope and cross-project state limitations."""
    return identity_status()


def _self_test() -> dict[str, Any]:
    status = identity_status()
    assert status["stable_project_id"] is None
    assert status["project_identity_confidence"] == "UNRESOLVED"
    assert status["runtime_id"]["scope"] == "live_plugin_instance"
    assert status["runtime_id"]["persistent"] is False
    assert status["runtime_id"]["stable_when_same_project_is_reopened"] is False
    assert status["binding"]["scope"] == "mcp_session"
    assert status["retained_state"]["cross_project_isolation_guaranteed"] is False
    assert status["retained_state"]["may_outlive_a_project_switch_while_mcp_keeps_running"] is True
    return {
        "stable_project_id": None,
        "project_identity_confidence": "UNRESOLVED",
        "runtime_id_scope": "live_plugin_instance",
        "cross_project_isolation_guaranteed": False,
    }
