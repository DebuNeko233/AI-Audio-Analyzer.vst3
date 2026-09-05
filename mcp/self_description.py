#!/usr/bin/env python3
"""Self-describing MCP metadata and Skill-backed guide resources.

The complete long-form guidance stays in the repository/release Skill folder.
MCP Resources read that same content on demand instead of copying the Markdown
into Python constants. Server instructions stay intentionally short and contain
only cross-cutting rules that every caller should know.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

MCP_PUBLIC_VERSION = "1.2"
SELF_DESCRIPTION_SCHEMA_VERSION = 1
GUIDE_URI_PREFIX = "aianalyzer://guide/"

SERVER_DESCRIPTION = (
    "Realtime and retained audio measurement, Song Memory, structure, relationship, "
    "comparison and verification evidence for AI-assisted mixing. Analyzer-owned "
    "writes are limited to its own Analysis Profile; sound/project changes belong "
    "to an external DAW-control MCP."
)

SERVER_INSTRUCTIONS = """\
AI Audio Analyzer MCP is a measurement, memory, analysis, comparison and verification server.

Recommended start:
1. Call audio_project_identity_status(). Current stable project identity may be unresolved.
2. Call audio_project_status(). Establish deterministic Identify bindings when needed.
3. For whole-song work, call audio_song_status() and prefer Section Map / Track Story / Section Relationships before raw timeline queries.
4. Drill into temporal, masking, stereo or tonal evidence only when the task needs it. Do not call every tool mechanically.
5. For a known musical passage around an external DAW/plugin change, prefer transport-anchored same-range verification.

Hard rules:
- runtime_id identifies one live plugin instance; it is not persistent project or track identity and changes when the same project is reopened.
- Until authoritative project identity exists, a suspected project switch/reopen requires strict isolation before reusing retained project-level state; audio_project_identity_status() gives the current required action.
- transport_epoch is instance-local. Equal epoch numbers across tracks are not required and do not identify a project.
- null means unavailable, not zero. Missing retained coverage is not silence. Low activity does not prove mute state.
- A/B/C section families are neutral recurrence labels, not automatic Intro/Verse/Chorus/Drop labels.
- Relationship shortlist_priority is inspection priority only, not masking probability, problem probability, quality score or a processing command.
- controlled_comparison means technical comparability only; closed_loop_complete additionally requires caller-supplied actual host readback. Neither means the result sounds better.
- AI Audio Analyzer may modify only its own Analysis Profile. EQ, compression, gain, pan, routing, synth, automation and project/plugin writes belong to the external DAW-control layer.

For detailed semantics, list/read the aianalyzer://guide/* MCP Resources on demand. Do not load every guide unless the current task needs it.
"""

# key -> (URI, relative Skill path, description)
GUIDE_MANIFEST: dict[str, tuple[str, str, str]] = {
    "core": (
        "aianalyzer://guide/core",
        "SKILL.md",
        "Core Analyzer MCP workflow, boundaries, evidence semantics and output discipline.",
    ),
    "analyzer-mcp": (
        "aianalyzer://guide/analyzer-mcp",
        "references/analyzer-mcp.md",
        "Detailed MCP tool hierarchy, selectors, identity, Song Memory and verification reference.",
    ),
    "parameters": (
        "aianalyzer://guide/parameters",
        "references/parameters.md",
        "Analyzer measurement fields, units, validity and interpretation limits.",
    ),
    "performance-evidence": (
        "aianalyzer://guide/performance-evidence",
        "references/performance-evidence.md",
        "Analysis Profile, feature availability and worker/FIFO performance evidence.",
    ),
    "song-memory": (
        "aianalyzer://guide/song-memory",
        "references/song-memory.md",
        "Transport-aware retained Song Memory, coverage and instance-local epoch semantics.",
    ),
    "section-structure": (
        "aianalyzer://guide/section-structure",
        "references/section-structure.md",
        "Explainable section boundary and neutral recurrence-family semantics.",
    ),
    "track-story": (
        "aianalyzer://guide/track-story",
        "references/track-story.md",
        "Track Story evidence across sections and recurring families.",
    ),
    "section-relationships": (
        "aianalyzer://guide/section-relationships",
        "references/section-relationships.md",
        "Bounded section-aware relationship shortlist semantics and limitations.",
    ),
    "masking-evidence": (
        "aianalyzer://guide/masking-evidence",
        "references/masking-evidence.md",
        "Masking/overlap evidence semantics, heuristics and interpretation limits.",
    ),
    "stereo-evidence": (
        "aianalyzer://guide/stereo-evidence",
        "references/stereo-evidence.md",
        "Stereo, Mid/Side, correlation and negative-cross evidence semantics.",
    ),
    "tonal-evidence": (
        "aianalyzer://guide/tonal-evidence",
        "references/tonal-evidence.md",
        "Chroma, tonal-center and harmonic evidence semantics and limitations.",
    ),
    "verification-evidence": (
        "aianalyzer://guide/verification-evidence",
        "references/verification-evidence.md",
        "Recent-window and transport-anchored same-range verification semantics.",
    ),
}

GUIDE_INDEX_URI = "aianalyzer://guide/index"
EXPECTED_GUIDE_URIS = {GUIDE_INDEX_URI, *(item[0] for item in GUIDE_MANIFEST.values())}


def _candidate_skill_roots() -> list[Path]:
    roots: list[Path] = []
    override = os.getenv("AI_ANALYZER_SKILL_DIR", "").strip()
    if override:
        roots.append(Path(override).expanduser())

    module_dir = Path(__file__).resolve().parent
    roots.extend(
        [
            # Source repository layout: mcp/ beside skills/ai-analyzer-flstudio/.
            module_dir.parent / "skills" / "ai-analyzer-flstudio",
            # Development component layout: dist/mcp/ beside dist/skill/.
            module_dir.parent / "skill",
            # Beginner Release install: <app>/mcp/executable beside <app>/skill/.
            Path(sys.executable).resolve().parent.parent / "skill",
            Path.cwd() / "skill",
            Path.cwd() / "skills" / "ai-analyzer-flstudio",
        ]
    )

    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def resolve_skill_root() -> Path | None:
    for root in _candidate_skill_roots():
        if (root / "SKILL.md").is_file():
            return root
    return None


def _read_skill_file(relative_path: str) -> str:
    root = resolve_skill_root()
    if root is None:
        return (
            "# AI Audio Analyzer guide unavailable\n\n"
            "The MCP runtime could not locate the packaged `skill` directory. "
            "Server instructions and tool descriptions remain available. For long-form MCP Resources, "
            "install the complete AI Audio Analyzer package or set `AI_ANALYZER_SKILL_DIR` to the "
            "`ai-analyzer-flstudio` Skill directory."
        )
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        raise RuntimeError("Guide path escaped the configured Skill root.")
    if not path.is_file():
        return (
            "# AI Audio Analyzer guide unavailable\n\n"
            f"The expected Skill file `{relative_path}` is missing from the current installation."
        )
    return path.read_text(encoding="utf-8")


def _guide_index() -> str:
    root = resolve_skill_root()
    lines = [
        "# AI Audio Analyzer MCP Guide Resources",
        "",
        f"Self-description schema: {SELF_DESCRIPTION_SCHEMA_VERSION}.",
        "",
        "These resources expose the same Markdown used by the packaged/repository Skill. Read only the guide needed for the current task.",
        "",
        f"Guide files available from current runtime: {'yes' if root is not None else 'no'}.",
        "",
    ]
    for key, (uri, _relative, description) in GUIDE_MANIFEST.items():
        lines.append(f"- `{uri}` — {description}")
    lines.extend(
        [
            "",
            "The external Skill remains the canonical long-form content source. MCP Resources are an on-demand transport for the same files, not a second copy.",
        ]
    )
    return "\n".join(lines)


def register_resources(mcp: Any) -> None:
    """Register static, discoverable, Skill-backed guide resources."""

    @mcp.resource(
        GUIDE_INDEX_URI,
        name="ai_analyzer_guide_index",
        description="Index of AI Audio Analyzer self-description and evidence guides.",
        mime_type="text/markdown",
    )
    def ai_analyzer_guide_index() -> str:
        return _guide_index()

    for key, (uri, relative_path, description) in GUIDE_MANIFEST.items():
        def make_reader(path: str):
            def read_guide() -> str:
                return _read_skill_file(path)

            return read_guide

        reader = make_reader(relative_path)
        reader.__name__ = f"ai_analyzer_guide_{key.replace('-', '_')}"
        mcp.resource(
            uri,
            name=reader.__name__,
            description=description,
            mime_type="text/markdown",
        )(reader)


def resource_status() -> dict[str, Any]:
    root = resolve_skill_root()
    missing_files: list[str] = []
    if root is not None:
        for _key, (_uri, relative_path, _description) in GUIDE_MANIFEST.items():
            if not (root / relative_path).is_file():
                missing_files.append(relative_path)
    return {
        "schema_version": SELF_DESCRIPTION_SCHEMA_VERSION,
        "guide_uri_prefix": GUIDE_URI_PREFIX,
        "server_instructions_available": bool(SERVER_INSTRUCTIONS.strip()),
        "guide_resource_count": len(EXPECTED_GUIDE_URIS),
        "guide_files_available": root is not None and not missing_files,
        "missing_guide_files": missing_files,
        "content_source": "packaged/repository Skill Markdown",
        "fallback_when_guides_missing": "server instructions + tool descriptions",
    }
