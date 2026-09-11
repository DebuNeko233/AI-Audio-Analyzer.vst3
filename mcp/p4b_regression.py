#!/usr/bin/env python3
"""Synthetic regression for P4b bounded historical retained detail."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyzer_core as core  # noqa: E402
import server as entry  # noqa: E402,F401
import historical_detail_tools as historical  # noqa: E402
import performance_tools as performance  # noqa: E402
import section_tools as structure  # noqa: E402
import song_tools as song  # noqa: E402


def synthetic_frame(
    name: str,
    runtime_id: str,
    plugin_timestamp: float,
    transport_time_seconds: float,
    transport_epoch: int,
    bands: list[float],
    *,
    rms: float = -24.0,
    side_offset_db: float = -12.0,
    negative_cross: float = 0.08,
    low_corr: float = 0.92,
    feature_mask: int = 63,
    flux: float = 0.08,
    rise: float = 1.0,
) -> list[object]:
    peak = rms + 10.0
    prefix: list[object] = [
        name, 48000.0, plugin_timestamp, peak, rms, peak - rms,
        700.0, 6000.0, 0.15, 0.75, 0.25,
    ] + list(bands)
    v02: list[object] = [-18.0, -14.0, -1.0, -0.5] + [0.82] * core.NUM_STEREO_CORR_BANDS
    v03: list[object] = [1, peak, 0.0, runtime_id]
    v06: list[object] = [0.1, flux * 0.5, flux, rise, -28.0, "0.6"]
    side_bands = [float(value) + side_offset_db for value in bands]
    side_mid = [-18.0, -16.0, -14.0, -12.0, -10.0, -8.0, -6.0, -4.0]
    v08: list[object] = [
        rms - 1.0, rms - 10.0, -9.0, negative_cross, low_corr, -15.0,
    ] + side_bands + side_mid + ["0.8"]
    chroma = [1.0 / 12.0] * 12
    v09: list[object] = chroma + [0.7, 0.5, 130.81, "0.9"]
    v11: list[object] = [3, feature_mask, 0.2, 0.01, 46.0, 5.0, "1.1"]
    bpm = 120.0
    v12: list[object] = [
        1,
        transport_time_seconds,
        transport_time_seconds * bpm / 60.0,
        bpm,
        4,
        4,
        1,
        0,
        0,
        0.0,
        0.0,
        transport_epoch,
        40.0,
        0,
        "1.2",
    ]
    return prefix + v02 + v03 + v06 + v08 + v09 + v11 + v12


def reset() -> None:
    with core._lock:
        core._tracks.clear()
        core._history.clear()
        core._bindings.clear()
        core._identify_events.clear()
        core._identify_sequence = 0
    with song._song_lock:
        song._timeline.clear()
    with structure._section_lock:
        structure._section_maps.clear()


def emit_track(runtime_id: str, name: str, epoch: int, gain: float, side_offset: float) -> None:
    base = [-56.0 + min(i, 14) * 1.55 for i in range(core.NUM_BANDS)]
    frame_index = 0
    for second in range(4):
        for slot in range(song.COVERAGE_SLOTS_PER_BIN):
            t = second + slot * song.COVERAGE_SLOT_SECONDS + 0.05
            bands = [value + gain + second * 0.4 for value in base]
            flux = 0.24 if slot == 4 else 0.05
            rise = 5.0 if slot == 4 else 0.7
            core._on_frame(
                "/aianalyzer/frame",
                *synthetic_frame(
                    name,
                    runtime_id,
                    100.0 + frame_index * 0.1,
                    t,
                    epoch,
                    bands,
                    rms=-24.0 + gain + second * 0.2,
                    side_offset_db=side_offset,
                    negative_cross=0.06 if runtime_id == "a" else 0.18,
                    low_corr=0.93 if runtime_id == "a" else 0.68,
                    flux=flux,
                    rise=rise,
                ),
            )
            frame_index += 1


def main() -> None:
    reset()
    emit_track("a", "Track A", 1, 0.0, -13.0)
    emit_track("b", "Track B", 7, 3.0, -7.0)

    report = historical.audio_historical_detail(
        "a",
        start_seconds=0.0,
        end_seconds=4.0,
        compare_track="b",
        minimum_coverage=0.8,
        max_masking_regions=6,
    )
    assert report["available"] is True
    a = report["track"]
    b = report["compare_track"]
    assert a["selected_transport_epoch"] == 1
    assert b["selected_transport_epoch"] == 7
    assert a["coverage_ratio"] >= 0.99
    assert b["coverage_ratio"] >= 0.99
    assert a["detail_available"] is True
    assert len(a["spectrum"]["mid_spectrum_db"]) == core.NUM_BANDS
    assert len(a["spectrum"]["side_spectrum_db"]) == core.NUM_BANDS
    assert len(a["stereo"]["frequency_dependent_stereo"]) == core.NUM_STEREO_CORR_BANDS
    assert a["mono_compatibility"]["available"] is True
    assert a["mono_compatibility"]["peak_fold_down"]["available"] is False
    assert a["temporal"]["available"] is True
    assert report["pair_evidence"]["available"] is True
    assert report["pair_evidence"]["comparability"]["controlled_comparison"] is True
    assert report["pair_evidence"]["comparability"]["common_one_second_bins"] == 4
    assert len(report["pair_evidence"]["masking"]["strongest_regions"]) == 6
    assert report["pair_evidence"]["masking"]["temporal_component_resolution_seconds"] == 1.0
    assert report["pair_evidence"]["temporal"]["resolution_seconds"] == 1.0
    assert report["scope"]["subsecond_historical_alignment_supported"] is False
    assert report["scope"]["raw_audio_retained"] is False
    assert report["interpretation_boundary"]["quality_score"] is None
    assert report["interpretation_boundary"]["processing_recommendation"] is None

    per_bin = int(a["retention"]["estimated_container_plus_array_bytes_per_bin"])
    assert 0 < per_bin < 4096, per_bin
    assert a["retention"]["estimated_max_detail_bytes_per_track"] == per_bin * song.MAX_TIMELINE_BINS_PER_INSTANCE

    with structure._section_lock:
        structure._section_maps["p4b-test-map"] = {
            "sections": [
                {
                    "section_id": "S01",
                    "family_id": "A",
                    "family_occurrence": 1,
                    "start_seconds": 1.0,
                    "end_seconds": 3.0,
                }
            ]
        }
    section = historical.audio_historical_detail("a", map_id="p4b-test-map", section_id="S01")
    assert section["scope"]["section"]["section_id"] == "S01"
    assert section["track"]["effective_range"] == {"start_seconds": 1.0, "end_seconds": 3.0}

    base = [-50.0] * core.NUM_BANDS
    for slot in range(song.COVERAGE_SLOTS_PER_BIN):
        t = slot * song.COVERAGE_SLOT_SECONDS + 0.05
        song.on_frame_v12(
            "/aianalyzer/frame",
            *synthetic_frame("Legacy", "legacy", 200.0 + t, t, 3, base),
        )
    legacy = historical.audio_historical_detail("legacy", start_seconds=0.0, end_seconds=1.0)
    assert legacy["available"] is True
    assert legacy["track"]["detail_available"] is False
    assert "unavailable" in legacy["track"]["reason"].lower()
    assert legacy["interpretation_boundary"]["missing_is_silence"] is False

    core_only = performance.FEATURE_CORE
    for slot in range(song.COVERAGE_SLOTS_PER_BIN):
        t = 10.0 + slot * song.COVERAGE_SLOT_SECONDS + 0.05
        core._on_frame(
            "/aianalyzer/frame",
            *synthetic_frame(
                "Eco", "eco", 300.0 + t, t, 5, base, feature_mask=core_only,
            ),
        )
    eco = historical.audio_historical_detail("eco", start_seconds=10.0, end_seconds=11.0)
    assert eco["track"]["detail_available"] is True
    assert all(value is None for value in eco["track"]["spectrum"]["mid_spectrum_db"])
    assert eco["track"]["mono_compatibility"]["available"] is False
    assert eco["track"]["temporal"]["available"] is False

    print(
        {
            "ok": True,
            "detail_bytes_per_bin_estimate": per_bin,
            "selected_epochs": [a["selected_transport_epoch"], b["selected_transport_epoch"]],
            "masking_regions": len(report["pair_evidence"]["masking"]["strongest_regions"]),
        }
    )


if __name__ == "__main__":
    main()
