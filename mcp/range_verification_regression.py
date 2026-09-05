#!/usr/bin/env python3
"""Synthetic regression for transport-anchored same-range verification."""

from __future__ import annotations

import copy
import time
from collections import OrderedDict

import server as core
import range_tools as ranges
import range_verification_tools as verification
import song_tools as song


def _frame(runtime_id: str, track: str) -> dict:
    return {
        "id": runtime_id,
        "track": track,
        "signal_present": True,
        "analysis_feature_mask": 63,
        "_received_at": time.time(),
    }


def _bind(runtime_id: str, track: str, track_index: int) -> None:
    core._on_identify(
        "/aianalyzer/identify",
        runtime_id,
        track,
        1.0 + track_index * 0.01,
        "0.4",
    )
    result = core.audio_bind_last_identified(track_index, track, 1)
    assert result["selector"] == f"mixer:{track_index}/slot:1"


def _seed_pass(
    runtime_id: str,
    epoch: int,
    start_bin: int,
    end_bin: int,
    *,
    first_received_at: float,
    slots_per_bin: int = 10,
    rms_db: float = -18.0,
    dropped_blocks: int = 0,
) -> None:
    with song._song_lock:
        instance = song._timeline.setdefault(runtime_id, OrderedDict())
        for bin_index in range(start_bin, end_bin):
            base_received = first_received_at + (bin_index - start_bin) * 0.1
            acc = song._new_accumulator({"_received_at": base_received}, epoch, bin_index)
            for slot in range(slots_per_bin):
                position = bin_index + min(0.95, 0.05 + slot * 0.1)
                bands = [-24.0 + (index % 5) for index in range(len(core.BAND_CENTERS))]
                chroma = [1.0 if index == 0 else 0.1 for index in range(12)]
                song._accumulate(
                    acc,
                    {
                        "_received_at": base_received + slot * 0.005,
                        "transport_time_seconds": position,
                        "signal_present": True,
                        "rms_db": rms_db,
                        "lufs_s": rms_db - 1.0,
                        "lufs_i": rms_db - 2.0,
                        "peak_db": rms_db + 6.0,
                        "true_peak_dbtp": rms_db + 6.5,
                        "max_true_peak_dbtp": rms_db + 7.0,
                        "crest_db": 6.0,
                        "centroid_hz": 1200.0,
                        "stereo_correlation": 0.8,
                        "stereo_width": 0.45,
                        "spectral_flux_mean": 0.1,
                        "bands_db": bands,
                        "chroma": chroma,
                        "chroma_energy_ratio": 0.8,
                        "estimated_analysis_lag_ms": 10.0,
                        "dropped_blocks": dropped_blocks,
                        "transport_bpm": 120.0,
                        "transport_time_signature_numerator": 4,
                        "transport_time_signature_denominator": 4,
                    },
                )
            instance[(epoch, bin_index)] = acc
        while len(instance) > song.MAX_TIMELINE_BINS_PER_INSTANCE:
            instance.popitem(last=False)


def main() -> None:
    with core._lock:
        saved_tracks = copy.deepcopy(core._tracks)
        saved_bindings = copy.deepcopy(core._bindings)
        saved_identify_events = copy.deepcopy(core._identify_events)
        saved_identify_sequence = core._identify_sequence
        saved_last_identify_at = core._last_identify_at
    with song._song_lock:
        saved_timeline = copy.deepcopy(song._timeline)
    with verification._range_verification_lock:
        saved_verifications = copy.deepcopy(verification._range_verifications)

    try:
        now = time.time()
        with core._lock:
            core._tracks.clear()
            core._bindings.clear()
            core._identify_events.clear()
            core._identify_sequence = 0
            core._last_identify_at = None
            core._tracks.update(
                {
                    "runtime-a": _frame("runtime-a", "Track A"),
                    "runtime-b": _frame("runtime-b", "Track B"),
                }
            )
        _bind("runtime-a", "Track A", 1)
        _bind("runtime-b", "Track B", 2)
        with song._song_lock:
            song._timeline.clear()
        with verification._range_verification_lock:
            verification._range_verifications.clear()

        # A has an older complete pass and newer sparse pass. Coverage must win
        # before recency. B deliberately uses a different local epoch number.
        _seed_pass("runtime-a", 3, 2, 5, first_received_at=now - 20.0, slots_per_bin=10, rms_db=-18.0)
        _seed_pass("runtime-a", 4, 2, 5, first_received_at=now - 10.0, slots_per_bin=2, rms_db=-17.0)
        _seed_pass("runtime-b", 9, 2, 5, first_received_at=now - 19.0, slots_per_bin=10, rms_db=-20.0)

        normalized = ranges.normalize_range(2.25, 4.2)
        assert normalized["effective_range"] == {"start_seconds": 2.0, "end_seconds": 5.0}
        assert normalized["normalized"] is True

        selected_a = ranges.resolve_track_range("runtime-a", 2.25, 4.2)
        assert selected_a["adequate_coverage"] is True
        assert selected_a["selected_transport_epoch"] == 3
        assert selected_a["coverage_ratio"] == 1.0

        begin = verification.audio_begin_range_verification(
            "synthetic same-range",
            2.25,
            4.2,
            ["mixer:1/slot:1", "mixer:2/slot:1"],
        )
        assert begin["ready_for_external_change"] is True, begin
        assert begin["effective_range"] == {"start_seconds": 2.0, "end_seconds": 5.0}
        verification_id = begin["verification_id"]
        receive_fence = float(begin["receive_fence"])

        # Pre-change Song Memory cannot silently be selected as After.
        stale_after = ranges.resolve_track_range(
            "runtime-a",
            2.25,
            4.2,
            after_received_at=receive_fence,
        )
        assert stale_after["available"] is False

        _seed_pass("runtime-a", 11, 2, 5, first_received_at=receive_fence + 1.0, slots_per_bin=10, rms_db=-16.0)
        _seed_pass("runtime-b", 17, 2, 5, first_received_at=receive_fence + 1.2, slots_per_bin=10, rms_db=-19.0)
        with core._lock:
            core._tracks["runtime-a"]["_received_at"] = time.time()
            core._tracks["runtime-b"]["_received_at"] = time.time()

        completed = verification.audio_complete_range_verification(
            verification_id,
            change_summary="Synthetic external gain change",
            host_readback="Synthetic host readback confirmed",
        )
        result = completed["result"]
        comparison = result["comparison"]
        assert comparison["controlled_comparison"] is True, comparison
        assert result["closed_loop_complete"] is True
        assert comparison["comparability"]["stale_after_targets"] == []
        assert comparison["comparability"]["retained_feature_mismatch_targets"] == []
        assert comparison["comparability"]["no_common_feature_targets"] == []
        assert comparison["comparability"]["dropped_block_regression_targets"] == []

        targets = {item["identity"]: item for item in comparison["targets"]}
        assert targets["mixer:1/slot:1"]["before"]["selected_transport_epoch"] == 3
        assert targets["mixer:1/slot:1"]["after"]["selected_transport_epoch"] == 11
        assert targets["mixer:2/slot:1"]["before"]["selected_transport_epoch"] == 9
        assert targets["mixer:2/slot:1"]["after"]["selected_transport_epoch"] == 17
        assert targets["mixer:1/slot:1"]["delta"]["rms_db"] == 2.0
        assert "core" in targets["mixer:1/slot:1"]["comparable_feature_families"]

        # Content-dependent evidence availability must not be mistaken for proof
        # that the historical Analysis Profile changed. It is a per-dimension
        # audit warning; common retained families remain comparable.
        session = verification._range_verifications[verification_id]
        before_state = copy.deepcopy(session["before_state"])
        after_state = copy.deepcopy(session["after_state"])
        after_state["tracks"]["mixer:1/slot:1"]["feature_availability"]["semantic"] = False
        availability_change = verification._comparison(
            before_state,
            after_state,
            ["mixer:1/slot:1", "mixer:2/slot:1"],
            baseline_ready=True,
            receive_fence=receive_fence,
        )
        assert availability_change["controlled_comparison"] is True
        assert "mixer:1/slot:1" in availability_change["comparability"]["retained_feature_mismatch_targets"]
        changed_target = next(
            item for item in availability_change["targets"]
            if item["identity"] == "mixer:1/slot:1"
        )
        assert "semantic" not in changed_target["comparable_feature_families"]
        assert "core" in changed_target["comparable_feature_families"]

        # A new dropped-block regression remains a hard data-integrity blocker.
        dropped_state = copy.deepcopy(after_state)
        dropped_state["tracks"]["mixer:1/slot:1"]["range_provenance"]["data_quality"]["dropped_blocks_cumulative"] = 5
        dropped_change = verification._comparison(
            before_state,
            dropped_state,
            ["mixer:1/slot:1"],
            baseline_ready=True,
            receive_fence=receive_fence,
        )
        assert dropped_change["controlled_comparison"] is False
        assert "mixer:1/slot:1" in dropped_change["comparability"]["dropped_block_regression_targets"]

        print(
            "transport-range verification regression: ok "
            "(fractional normalization, coverage-first pass selection, cross-instance epochs, "
            "post-fence replay, field-level retained-feature comparability, drop guard, readback gate)"
        )
    finally:
        with core._lock:
            core._tracks.clear()
            core._tracks.update(saved_tracks)
            core._bindings.clear()
            core._bindings.update(saved_bindings)
            core._identify_events.clear()
            core._identify_events.extend(saved_identify_events)
            core._identify_sequence = saved_identify_sequence
            core._last_identify_at = saved_last_identify_at
        with song._song_lock:
            song._timeline.clear()
            song._timeline.update(saved_timeline)
        with verification._range_verification_lock:
            verification._range_verifications.clear()
            verification._range_verifications.update(saved_verifications)


if __name__ == "__main__":
    main()
