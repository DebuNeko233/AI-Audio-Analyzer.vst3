#!/usr/bin/env python3
"""AI Audio Analyzer MCP 0.6 entrypoint.

Loads the stable 0.4 core bridge, the 0.5 project-intelligence layer, and the
0.6 temporal-analysis layer. The V0.6 frame protocol extends the existing OSC
frame only by appending fields.

Set AI_ANALYZER_SELF_TEST=1 to validate a source or PyInstaller-packaged runtime
without opening the OSC listener or MCP stdio transport.
"""

from __future__ import annotations

import asyncio
import json
import os

import server as core
import server_v05 as v05  # noqa: F401  # registers 0.5 project tools
import temporal_tools as temporal  # registers 0.6 tools and provides frame wrapper

# Replace only the runtime frame callback. temporal.on_frame_v06 first delegates
# to the stable parser, then appends V0.6 fields to the same history frame.
core._on_frame = temporal.on_frame_v06

mcp = core.mcp

EXPECTED_TOOLS = set(v05.EXPECTED_TOOLS) | {
    "audio_temporal_profile",
    "audio_temporal_compare",
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
                "entrypoint": "0.6",
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
