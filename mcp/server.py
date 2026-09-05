#!/usr/bin/env python3
"""Single MCP entrypoint for AI Audio Analyzer.

`server.py` is the only supported source/PyInstaller entrypoint. Product and
protocol versions are metadata, not filenames. Feature modules register tools on
the shared MCP server defined by `analyzer_core.py`.

Current layers:
- core: signal validity, runtime identity, FL Mixer binding, base measurements
- project_tools: project overview and Snapshot A/B
- project_identity_tools: explicit project/runtime identity scope disclosure
- temporal_tools: temporal frame tail and temporal comparisons
- masking_tools: masking-evidence tools
- stereo_tools: Mid/Side, Side-spectrum, and stereo evidence
- semantic_tools: chroma, tonal-center, and harmonic-alignment evidence
- performance_tools: Analysis Profile, feature-mask and worker telemetry parsing
- control_tools: Analyzer-owned loopback Analysis Profile control
- song_tools: DAW transport, continuous-pass song memory and latency-aware summaries
- section_tools: explainable boundaries, neutral recurring families and section profiles
- track_story_tools: per-track behavior across sections/families
- section_relationship_tools: bounded cross-track relationships across sections/families
- verification_tools: recent-window controlled Before/After verification sessions
- range_verification_tools: transport-anchored same-range Before/After verification
- dynamics_tools: coverage-aware retained dynamics/mastering distributions
- self_description: server instructions and Skill-backed MCP guide resources

Set AI_ANALYZER_SELF_TEST=1 to validate source or packaged runtime without
opening the OSC listener or MCP stdio transport. Package assembly tests may also
set AI_ANALYZER_REQUIRE_GUIDES=1 to require the sibling Skill/reference files.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

import analyzer_core as core
import self_description

# When executed as `python mcp/server.py`, feature modules still import
# `server`. Alias this __main__ module before loading them so Python does not
# execute the entrypoint a second time under another module name.
sys.modules.setdefault("server", sys.modules[__name__])

mcp = core.mcp


def __getattr__(name: str) -> Any:
    return getattr(core, name)


# Import order matters because every protocol layer wraps the previous parser.
import project_tools as project  # noqa: E402,F401
import project_identity_tools as project_identity  # noqa: E402
import temporal_tools as temporal  # noqa: E402

core._on_frame = temporal.on_frame_v06

import masking_tools as masking  # noqa: E402,F401
import stereo_tools as stereo  # noqa: E402

core._on_frame = stereo.on_frame_v08

import semantic_tools as semantic  # noqa: E402

core._on_frame = semantic.on_frame_v09

import performance_tools as performance  # noqa: E402

core._on_frame = performance.on_frame_v11

import song_tools as song  # noqa: E402

core._on_frame = song.on_frame_v12

import control_tools as control  # noqa: E402
import section_tools as structure  # noqa: E402
import track_story_tools as story  # noqa: E402
import section_relationship_tools as relationships  # noqa: E402
import verification_tools as verification  # noqa: E402,F401
import range_verification_tools as range_verification  # noqa: E402,F401
import dynamics_tools as dynamics  # noqa: E402,F401

self_description.register_resources(mcp)

MCP_VERSION = self_description.MCP_PUBLIC_VERSION
OSC_PROTOCOL_VERSION = "1.2"
CONTROL_PROTOCOL_VERSION = control.CONTROL_REVISION

EXPECTED_TOOLS = {
    "audio_bridge_status",
    "audio_list_tracks",
    "audio_last_identify",
    "audio_bind_last_identified",
    "audio_instance_map",
    "audio_snapshot",
    "audio_average",
    "audio_stereo_bands",
    "audio_compare_tracks",
    "audio_detect_masking",
    "audio_master_status",
    "audio_project_status",
    "audio_project_identity_status",
    "audio_mix_overview",
    "audio_capture_snapshot",
    "audio_list_snapshots",
    "audio_compare_snapshots",
    "audio_temporal_profile",
    "audio_temporal_compare",
    "audio_masking_evidence",
    "audio_project_masking_scan",
    "audio_stereo_profile",
    "audio_stereo_compare",
    "audio_tonal_profile",
    "audio_tonal_compare",
    "audio_analysis_status",
    "audio_project_performance",
    "audio_set_analysis_profile",
    "audio_set_project_analysis_profile",
    "audio_song_status",
    "audio_song_timeline",
    "audio_song_overview",
    "audio_section_map",
    "audio_section_profile",
    "audio_track_story",
    "audio_section_relationships",
    "audio_begin_verification",
    "audio_complete_verification",
    "audio_verification_status",
    "audio_begin_range_verification",
    "audio_complete_range_verification",
    "audio_range_verification_status",
    "audio_dynamics_distribution",
}


def _self_test_song_coverage() -> None:
    """Guard against sparse one-second bins becoming 100% covered after merging."""
    first = song._new_accumulator({"_received_at": 1.0}, 1, 0)
    last = song._new_accumulator({"_received_at": 2.0}, 1, 4)
    for acc, positions in ((first, (0.05, 0.15)), (last, (4.05, 4.15))):
        for position in positions:
            song._accumulate(
                acc,
                {
                    "_received_at": 1.0 + position,
                    "transport_time_seconds": position,
                    "signal_present": True,
                    "rms_db": -24.0,
                    "estimated_analysis_lag_ms": 10.0,
                    "dropped_blocks": 0,
                },
            )
    summary = song._finalize_rows(
        [first, last],
        start_seconds=0.0,
        end_seconds=5.0,
        expected_seconds=5.0,
    )
    quality = summary["data_quality"]
    if quality["covered_seconds"] != 0.4 or quality["coverage_ratio"] != 0.08:
        raise RuntimeError(f"Song-memory sparse coverage regression: {quality}")


def self_test() -> None:
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    missing = sorted(EXPECTED_TOOLS - names)
    unexpected = sorted(names - EXPECTED_TOOLS)
    if missing or unexpected:
        raise RuntimeError(
            f"MCP tool registry mismatch: missing={missing}, unexpected={unexpected}"
        )

    missing_descriptions = sorted(
        tool.name for tool in tools if not str(tool.description or "").strip()
    )
    if missing_descriptions:
        raise RuntimeError(
            "MCP self-describing API requires every tool to have a description; "
            f"missing={missing_descriptions}"
        )

    if not str(mcp.instructions or "").strip():
        raise RuntimeError("MCP server instructions are missing.")
    for required_phrase in (
        "audio_project_identity_status",
        "runtime_id",
        "missing retained coverage is not silence",
        "same-range verification",
        "Analysis Profile",
    ):
        if required_phrase.casefold() not in mcp.instructions.casefold():
            raise RuntimeError(
                f"MCP server instructions lost required guidance: {required_phrase!r}"
            )

    resources = asyncio.run(mcp.list_resources())
    resource_uris = {str(resource.uri) for resource in resources}
    missing_resources = sorted(self_description.EXPECTED_GUIDE_URIS - resource_uris)
    unexpected_resources = sorted(resource_uris - self_description.EXPECTED_GUIDE_URIS)
    if missing_resources or unexpected_resources:
        raise RuntimeError(
            "MCP guide resource registry mismatch: "
            f"missing={missing_resources}, unexpected={unexpected_resources}"
        )
    missing_resource_descriptions = sorted(
        str(resource.uri)
        for resource in resources
        if not str(resource.description or "").strip()
    )
    if missing_resource_descriptions:
        raise RuntimeError(
            "MCP guide resources require descriptions; "
            f"missing={missing_resource_descriptions}"
        )

    _self_test_song_coverage()
    identity_result = project_identity._self_test()
    control_result = control._self_test()
    structure_result = structure._self_test()
    story_result = story._self_test()
    relationship_result = relationships._self_test()
    resource_result = self_description.resource_status()
    require_guides = os.getenv("AI_ANALYZER_REQUIRE_GUIDES", "").strip() == "1"
    if require_guides and not resource_result["guide_files_available"]:
        raise RuntimeError(
            "Packaged MCP self-description requires the canonical Skill/reference files, "
            f"but they are unavailable: {resource_result}"
        )

    print(
        json.dumps(
            {
                "ok": True,
                "server": "AI Audio Analyzer MCP",
                "entrypoint": "server.py",
                "mcp_version": MCP_VERSION,
                "osc_protocol_version": OSC_PROTOCOL_VERSION,
                "control_protocol_version": CONTROL_PROTOCOL_VERSION,
                "tool_count": len(names),
                "expected_tools": len(EXPECTED_TOOLS),
                "tool_descriptions": "complete",
                "server_instructions": "available",
                "guide_resources": resource_result,
                "guide_files_required": require_guides,
                "song_memory_sparse_coverage": "ok",
                "project_identity_scope": identity_result,
                "analyzer_profile_control": control_result,
                "song_structure_synthetic": structure_result,
                "track_story_synthetic": story_result,
                "section_relationships_synthetic": relationship_result,
            },
            ensure_ascii=False,
        )
    )


def main() -> None:
    if os.getenv("AI_ANALYZER_SELF_TEST", "").strip() == "1":
        self_test()
        return
    core.main()


if __name__ == "__main__":
    main()
