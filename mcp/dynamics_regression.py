#!/usr/bin/env python3
"""Synthetic regression for P6a coverage-aware retained dynamics distributions."""

from __future__ import annotations

import copy
import time
from collections import OrderedDict

import server as core
import dynamics_tools as dynamics
import section_tools as structure
import song_tools as song


def _frame(runtime_id: str, track: str) -> dict:
    return {
        "id": runtime_id,
        "track": track,
        "signal_present": True,
        "analysis_feature_mask": 63,
        "_received_at": time.time(),
    }


def _seed_bin(
    runtime_id: str,
    epoch: int,
    bin_index: int,
    *,
    slots: int,
    rms_db: float,
    lufs_s: float | None,
    crest_db: float,
    peak_db: float,
    true_peak_dbtp: float,
    first_received_at: float,
) -> None:
    acc = song._new_accumulator({"_received_at": first_received_at}, epoch, bin_index)
    for slot in range(slots):
        position = bin_index + min(0.95, 0.05 + slot * 0.1)
        frame = {
            "_received_at": first_received_at + slot * 0.002,
            "transport_time_seconds": position,
            "signal_present": True,
            "rms_db": rms_db,
            "peak_db": peak_db,
            "true_peak_dbtp": true_peak_dbtp,
            "max_true_peak_dbtp": true_peak_dbtp,
            "crest_db": crest_db,
            "estimated_analysis_lag_ms": 5.0,
            "dropped_blocks": 0,
        }
        if lufs_s is not None:
            frame["lufs_s"] = lufs_s
        song._accumulate(acc, frame)
    with song._song_lock:
        instance = song._timeline.setdefault(runtime_id, OrderedDict())
        instance[(epoch, bin_index)] = acc
        instance.move_to_end((epoch, bin_index))


def _install_section_map() -> str:
    map_id = "section-map-p6a-synthetic"
    cached = {
        "sections": [
            {
                "section_id": "S01",
                "family_id": "A",
                "start_seconds": 0.0,
                "end_seconds": 2.0,
            },
            {
                "section_id": "S02",
                "family_id": "B",
                "start_seconds": 2.0,
                "end_seconds": 4.0,
            },
        ],
        "track_epochs": {},
    }
    with structure._section_lock:
        structure._section_maps[map_id] = cached
        structure._section_maps.move_to_end(map_id)
    return map_id


def main() -> None:
    with core._lock:
        saved_tracks = copy.deepcopy(core._tracks)
        saved_bindings = copy.deepcopy(core._bindings)
    with song._song_lock:
        saved_timeline = copy.deepcopy(song._timeline)
    with structure._section_lock:
        saved_maps = copy.deepcopy(structure._section_maps)

    try:
        now = time.time()
        with core._lock:
            core._tracks.clear()
            core._bindings.clear()
            core._tracks.update(
                {
                    "runtime-dyn": _frame("runtime-dyn", "Dynamics Track"),
                    "runtime-no-loudness": _frame("runtime-no-loudness", "No Loudness"),
                }
            )
        with song._song_lock:
            song._timeline.clear()
        with structure._section_lock:
            structure._section_maps.clear()

        # Epoch 3 is the best overlapping pass for 0..5 s: 2.7 covered seconds.
        # Bin 3 is deliberately only 20% covered and must be rejected by the
        # 50% per-bin floor; bin 4 is completely missing and must stay missing.
        values = [
            (0, 10, -30.0, -31.0, 4.0, -24.0, -23.5),
            (1, 10, -20.0, -21.0, 6.0, -14.0, -13.5),
            (2, 5, -10.0, -11.0, 8.0, -4.0, -3.5),
            (3, 2, 0.0, -1.0, 10.0, 6.0, 6.5),
        ]
        for bin_index, slots, rms, lufs, crest, peak, true_peak in values:
            _seed_bin(
                "runtime-dyn",
                3,
                bin_index,
                slots=slots,
                rms_db=rms,
                lufs_s=lufs,
                crest_db=crest,
                peak_db=peak,
                true_peak_dbtp=true_peak,
                first_received_at=now - 20.0 + bin_index * 0.1,
            )

        # Newer but sparser pass: coverage-first range selection must still use epoch 3.
        for bin_index in range(5):
            _seed_bin(
                "runtime-dyn",
                4,
                bin_index,
                slots=1,
                rms_db=-5.0,
                lufs_s=-6.0,
                crest_db=12.0,
                peak_db=1.0,
                true_peak_dbtp=1.5,
                first_received_at=now - 10.0 + bin_index * 0.1,
            )

        # Separate track proves unavailable loudness remains unavailable rather than zero.
        for bin_index in range(2):
            _seed_bin(
                "runtime-no-loudness",
                7,
                bin_index,
                slots=10,
                rms_db=-18.0 + bin_index,
                lufs_s=None,
                crest_db=7.0,
                peak_db=-8.0,
                true_peak_dbtp=-7.5,
                first_received_at=now - 5.0 + bin_index * 0.1,
            )

        result = dynamics.audio_dynamics_distribution(
            "runtime-dyn",
            start_seconds=0.0,
            end_seconds=5.0,
            minimum_range_coverage=0.5,
            minimum_bin_coverage=0.5,
        )
        assert result["available"] is True, result
        assert result["scope"]["selected_transport_epoch"] == 3
        assert result["coverage"]["accepted_bin_count"] == 3
        assert result["coverage"]["rejected_low_coverage_bin_count"] == 1
        assert result["coverage"]["missing_bin_count"] == 1
        assert result["coverage"]["covered_seconds"] == 2.7
        assert result["coverage"]["accepted_covered_seconds"] == 2.5

        rms = result["energy_distribution"]["rms_db"]
        assert rms["available"] is True
        assert rms["min"] == -30.0
        assert rms["max"] == -10.0  # The 20%-covered 0 dB bin cannot dominate.
        assert rms["p50"] == -22.5
        assert rms["p90"] == -10.0
        assert rms["covered_seconds_power_mean_db"] != rms["p50"]

        lufs = result["loudness_short_term_distribution"]
        assert lufs["lufs_s"]["available"] is True
        assert lufs["lufs_s_interpercentile_range_lu"] is not None
        assert result["standardized_metrics"]["ebu_lra_lu"]["value"] is None
        assert result["standardized_metrics"]["plr_db"]["value"] is None
        assert "lra" not in {key.casefold() for key in lufs.keys()}

        no_loudness = dynamics.audio_dynamics_distribution(
            "runtime-no-loudness",
            transport_epoch=7,
            minimum_range_coverage=0.8,
            minimum_bin_coverage=0.5,
        )
        assert no_loudness["available"] is True
        assert no_loudness["loudness_short_term_distribution"]["lufs_s"]["available"] is False
        assert no_loudness["loudness_short_term_distribution"]["lufs_s_interpercentile_range_lu"] is None

        map_id = _install_section_map()
        sections = dynamics.audio_dynamics_distribution(
            "runtime-dyn",
            map_id=map_id,
            section_id="S01",
            compare_section_id="S02",
            minimum_range_coverage=0.5,
            minimum_bin_coverage=0.5,
        )
        assert sections["scope"]["kind"] == "section_range"
        assert sections["scope"]["effective_range"] == {"start_seconds": 0.0, "end_seconds": 2.0}
        assert sections["comparison_scope"]["scope"]["effective_range"] == {"start_seconds": 2.0, "end_seconds": 4.0}
        assert sections["section_comparison"]["direction"] == "comparison_minus_primary"
        assert sections["section_comparison"]["deltas"]["median_rms_db"] is not None
        assert "quality" not in sections["section_comparison"]

        print(
            "P6a dynamics regression: ok "
            "(coverage weighting, low-coverage rejection, missing!=silence, deterministic percentiles, "
            "dB/power mean separation, loudness unavailable state, section range isolation, no fake LRA/PLR)"
        )
    finally:
        with core._lock:
            core._tracks.clear()
            core._tracks.update(saved_tracks)
            core._bindings.clear()
            core._bindings.update(saved_bindings)
        with song._song_lock:
            song._timeline.clear()
            song._timeline.update(saved_timeline)
        with structure._section_lock:
            structure._section_maps.clear()
            structure._section_maps.update(saved_maps)


if __name__ == "__main__":
    main()
