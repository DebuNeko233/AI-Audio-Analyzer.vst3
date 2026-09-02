#!/usr/bin/env python3
"""Single MCP entrypoint for AI Audio Analyzer.

`server.py` is the only supported source/PyInstaller entrypoint. Product and
protocol versions are metadata, not filenames. Feature modules register tools on
the shared MCP server defined by `analyzer_core.py`.

Current layers:
- core: signal validity, runtime identity, FL Mixer binding, base measurements
- project_tools: project overview and Snapshot A/B
- temporal_tools: V0.6 temporal frame tail and temporal comparisons
- masking_tools: V0.7 masking-evidence tools
- stereo_tools: V0.8 Mid/Side, Side-spectrum, and stereo evidence
- semantic_tools: V0.9 chroma, tonal-center, and harmonic-alignment evidence

Set AI_ANALYZER_SELF_TEST=1 to validate source or packaged runtime without
opening the OSC listener or MCP stdio transport.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

import analyzer_core as core

# When executed as `python bridge/server.py`, feature modules still import
# `server`. Alias this __main__ module before loading them so Python does not
# execute the entrypoint a second time under another module name.
sys.modules.setdefault("server", sys.modules[__name__])

# Public shared MCP object must exist before feature modules import `server`.
mcp = core.mcp


def __getattr__(name: str) -> Any:
    """Forward legacy/core attribute reads to the internal core module."""
    return getattr(core, name)


# Import order matters. Each protocol layer wraps the previous append-only
# frame parser. V0.9 therefore preserves the stable core + V0.6 + V0.8 fields
# before attaching its own music-semantic tail.
import project_tools as project  # noqa: E402,F401
import temporal_tools as temporal  # noqa: E402

core._on_frame = temporal.on_frame_v06

import masking_tools as masking  # noqa: E402,F401
import stereo_tools as stereo  # noqa: E402

core._on_frame = stereo.on_frame_v08

import semantic_tools as semantic  # noqa: E402

core._on_frame = semantic.on_frame_v09

MCP_VERSION = "0.9"
OSC_PROTOCOL_VERSION = "0.9"

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
}


def self_test() -> None:
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    missing = sorted(EXPECTED_TOOLS - names)
    unexpected = sorted(names - EXPECTED_TOOLS)
    if missing or unexpected:
        raise RuntimeError(
            f"MCP tool registry mismatch: missing={missing}, unexpected={unexpected}"
        )

    print(
        json.dumps(
            {
                "ok": True,
                "server": "AI Audio Analyzer MCP",
                "entrypoint": "server.py",
                "mcp_version": MCP_VERSION,
                "osc_protocol_version": OSC_PROTOCOL_VERSION,
                "tool_count": len(names),
                "expected_tools": len(EXPECTED_TOOLS),
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
