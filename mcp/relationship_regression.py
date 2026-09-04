#!/usr/bin/env python3
"""End-to-end synthetic regression for section-aware mix relationships.

Repository test code only; never ship this file in beginner Releases.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyzer_core as core  # noqa: E402
import ci_regression as ci  # noqa: E402
import section_relationship_tools as relationships  # noqa: E402
import section_tools as structure  # noqa: E402


def main() -> None:
    ci.reset_state()

    chroma = [1.0] + [0.0] * 11
    base_shape = [-48.0 + min(index, 14) * 1.2 for index in range(32)]

    # Track A is active through both families. Track B is active only in A,
    # while Track C is active only in B. All instances intentionally use
    # different local epoch numbers for the same DAW-time range.
    for second in range(48):
        family_a = second < 24
        for offset in (0.05, 0.15, 0.25, 0.35):
            t = second + offset
            core._on_frame(
                "/aianalyzer/frame",
                *ci.synthetic_frame(
                    "Track A",
                    "uuid-rel-a",
                    100.0 + t,
                    base_shape,
                    rms=-18.0 if family_a else -19.0,
                    chroma=chroma,
                    signal_present=True,
                    transport_epoch=2,
                    transport_time_seconds=t,
                ),
            )
            core._on_frame(
                "/aianalyzer/frame",
                *ci.synthetic_frame(
                    "Track B",
                    "uuid-rel-b",
                    200.0 + t,
                    [value - 1.0 for value in base_shape],
                    rms=-19.0 if family_a else -35.0,
                    chroma=chroma,
                    signal_present=family_a,
                    transport_epoch=7,
                    transport_time_seconds=t,
                ),
            )
            core._on_frame(
                "/aianalyzer/frame",
                *ci.synthetic_frame(
                    "Track C",
                    "uuid-rel-c",
                    300.0 + t,
                    [value + 0.5 for value in base_shape],
                    rms=-34.0 if family_a else -20.0,
                    chroma=chroma,
                    signal_present=not family_a,
                    transport_epoch=11,
                    transport_time_seconds=t,
                ),
            )

    ci.bind("uuid-rel-a", "Track A", 1)
    ci.bind("uuid-rel-b", "Track B", 2)
    ci.bind("uuid-rel-c", "Track C", 3)

    map_id = "relationship-regression-map"
    cached = {
        "public": {"available": True, "map_id": map_id},
        "sections": [
            {
                "section_id": "S01",
                "family_id": "A",
                "family_occurrence": 1,
                "start_seconds": 0.0,
                "end_seconds": 24.0,
                "duration_seconds": 24.0,
            },
            {
                "section_id": "S02",
                "family_id": "B",
                "family_occurrence": 1,
                "start_seconds": 24.0,
                "end_seconds": 48.0,
                "duration_seconds": 24.0,
            },
        ],
        "track_epochs": {},
        "start_seconds": 0.0,
        "end_seconds": 48.0,
    }
    with structure._section_lock:
        structure._section_maps[map_id] = cached

    result = relationships.audio_section_relationships(
        map_id,
        max_pairs=8,
        max_tracks=8,
        include_master=False,
        min_activity_overlap=0.15,
        min_shortlist_priority=0.18,
    )
    assert result["available"] is True, result
    assert result["returned_pair_count"] >= 2, result

    pair_ab = next(
        item
        for item in result["relationships"]
        if {item["track_a"]["runtime_id"], item["track_b"]["runtime_id"]}
        == {"uuid-rel-a", "uuid-rel-b"}
    )
    pair_ac = next(
        item
        for item in result["relationships"]
        if {item["track_a"]["runtime_id"], item["track_b"]["runtime_id"]}
        == {"uuid-rel-a", "uuid-rel-c"}
    )

    assert pair_ab["shortlisted_section_ids"] == ["S01"], pair_ab
    assert pair_ab["present_family_ids"] == ["A"], pair_ab
    assert "B" in pair_ab["observed_but_not_shortlisted_family_ids"], pair_ab
    assert any(change["change"] == "left_shortlist" for change in pair_ab["adjacent_changes"]), pair_ab

    assert pair_ac["shortlisted_section_ids"] == ["S02"], pair_ac
    assert pair_ac["present_family_ids"] == ["B"], pair_ac
    assert "A" in pair_ac["observed_but_not_shortlisted_family_ids"], pair_ac
    assert any(change["change"] == "entered_shortlist" for change in pair_ac["adjacent_changes"]), pair_ac

    # The selected passes must come from overlapping DAW time rather than equal
    # instance-local epoch numbers. The public relationship output does not need
    # to expose one shared epoch because no such project-global epoch exists.
    selection_a = relationships.story._selection_for_track("uuid-rel-a", cached)
    selection_b = relationships.story._selection_for_track("uuid-rel-b", cached)
    selection_c = relationships.story._selection_for_track("uuid-rel-c", cached)
    assert selection_a is not None and selection_a["epoch"] == 2
    assert selection_b is not None and selection_b["epoch"] == 7
    assert selection_c is not None and selection_c["epoch"] == 11

    print(
        "AI Audio Analyzer section relationships: bounded project shortlist, "
        "family appearance/disappearance, cross-instance epoch alignment and coverage guards OK"
    )


if __name__ == "__main__":
    main()
