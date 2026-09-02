#!/usr/bin/env python3
"""AI Audio Analyzer MCP 0.5 entrypoint.

Loads the stable 0.4 bridge and registers project-level intelligence tools
without changing the VST3 OSC protocol.

Set AI_ANALYZER_SELF_TEST=1 to validate a source or PyInstaller-packaged runtime
without opening the OSC listener or MCP stdio transport.
"""

from __future__ import annotations

import asyncio
import json
import os

import server as core
import project_tools  # noqa: F401  # registers 0.5 MCP tools on import

mcp = core.mcp

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
}


def self_test() -> None:
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    missing = sorted(EXPECTED_TOOLS - names)
    if missing:
        raise RuntimeError(f"Missing MCP tools: {missing}")

    print(
        json.dumps(
            {
                "ok": True,
                "server": "AI Audio Analyzer MCP",
                "tool_count": len(names),
                "expected_tools": len(EXPECTED_TOOLS),
                "entrypoint": "0.5",
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
