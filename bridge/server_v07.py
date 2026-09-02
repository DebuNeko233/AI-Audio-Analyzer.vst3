#!/usr/bin/env python3
"""AI Audio Analyzer MCP 0.7 entrypoint.

Loads the stable 0.4 core bridge, the 0.5 project-intelligence layer, the 0.6
temporal-analysis layer, and the 0.7 masking-evidence layer.

V0.7 is Bridge/MCP-only: it reuses the existing 0.6 VST3 measurements and does
not change the OSC frame schema or plugin DSP.

Set AI_ANALYZER_SELF_TEST=1 to validate a source or PyInstaller-packaged runtime
without opening the OSC listener or MCP stdio transport.
"""

from __future__ import annotations

import asyncio
import json
import os

import masking_tools as masking  # noqa: F401  # registers 0.7 tools
import server as core
import server_v06 as v06

mcp = core.mcp

EXPECTED_TOOLS = set(v06.EXPECTED_TOOLS) | {
    "audio_masking_evidence",
    "audio_project_masking_scan",
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
                "entrypoint": "0.7",
                "vst3_protocol": "0.6-compatible",
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
