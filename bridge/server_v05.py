#!/usr/bin/env python3
"""AI Audio Analyzer MCP 0.5 entrypoint.

Loads the stable 0.4 bridge and registers project-level intelligence tools
without changing the VST3 OSC protocol.
"""

from __future__ import annotations

import server as core
import project_tools  # noqa: F401  # registers 0.5 MCP tools on import

mcp = core.mcp


def main() -> None:
    core.main()


if __name__ == "__main__":
    main()
