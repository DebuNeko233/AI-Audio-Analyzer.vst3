#!/usr/bin/env python3
"""P4b high-level historical detail MCP tool."""

from __future__ import annotations

from typing import Any

import masking_tools as masking
import range_tools as ranges
import server as core
import song_tools as song
import historical_detail_store as store
import historical_detail_profile as profile
import historical_detail_pair as pair

DEFAULT_MINIMUM_COVERAGE = ranges.DEFAULT_MINIMUM_COVERAGE
DEFAULT_TEMPORAL_LOW_HZ = store.DEFAULT_TEMPORAL_LOW_HZ
DEFAULT_TEMPORAL_HIGH_HZ = store.DEFAULT_TEMPORAL_HIGH_HZ
DEFAULT_MAX_MASKING_REGIONS = store.DEFAULT_MAX_MASKING_REGIONS
_resolve_requested_range = profile._resolve_requested_range
_profile = profile._profile
_pair_evidence = pair._pair_evidence
on_frame_p4b = store.on_frame_p4b


@core.mcp.tool()
def audio_historical_detail(
    track: str,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    map_id: str | None = None,
    section_id: str | None = None,
    compare_track: str | None = None,
    minimum_coverage: float = DEFAULT_MINIMUM_COVERAGE,
    max_masking_regions: int = DEFAULT_MAX_MASKING_REGIONS,
    temporal_low_hz: float = DEFAULT_TEMPORAL_LOW_HZ,
    temporal_high_hz: float = DEFAULT_TEMPORAL_HIGH_HZ,
) -> dict[str, Any]:
    """Query one-second retained deep evidence for a DAW range/Section, optionally comparing a second track without replay."""
    start, end, section = _resolve_requested_range(start_seconds, end_seconds, map_id, section_id)
    minimum = ranges._minimum_coverage(minimum_coverage)
    max_regions = max(1, min(int(max_masking_regions), masking.ERB_BAND_COUNT))
    low_hz = max(core.MIN_HZ, float(temporal_low_hz))
    high_hz = min(core.MAX_HZ, float(temporal_high_hz))
    if high_hz <= low_hz:
        raise ValueError("temporal_high_hz must be greater than temporal_low_hz within 20 Hz-20 kHz.")

    profile_a, rows_a = _profile(track, start, end, minimum)
    result = {
        "available": bool(profile_a.get("available")),
        "scope": {
            "kind": "historical_daw_range",
            "section": section,
            "requested_range": profile_a.get("requested_range"),
            "effective_range": profile_a.get("effective_range"),
            "resolution_seconds": song.TIMELINE_BIN_SECONDS,
            "raw_audio_retained": False,
            "subsecond_historical_alignment_supported": False,
        },
        "track": profile_a,
        "compare_track": None,
        "pair_evidence": None,
        "interpretation_boundary": {
            "missing_is_silence": False,
            "quality_score": None,
            "processing_recommendation": None,
            "note": "P4b lets the LLM inspect past passages without forced replay; it does not judge artistic quality.",
        },
    }
    if compare_track is None or not str(compare_track).strip():
        return result
    profile_b, rows_b = _profile(str(compare_track), start, end, minimum)
    result["available"] = bool(profile_a.get("available") and profile_b.get("available"))
    result["compare_track"] = profile_b
    result["pair_evidence"] = _pair_evidence(
        profile_a, profile_b, rows_a, rows_b, max_regions, low_hz, high_hz
    )
    return result
