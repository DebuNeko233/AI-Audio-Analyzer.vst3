#!/usr/bin/env python3
"""Synthetic regression for P7a direct mono-fold compatibility evidence."""

from __future__ import annotations

import copy
import math
import time
from collections import deque

import server as core
import mono_compatibility_tools as mono


def _frame(
    runtime_id: str,
    track: str,
    *,
    rms_db: float,
    mid_rms_db: float,
    side_rms_db: float,
    mid_bands: list[float],
    side_bands: list[float],
    correlation: float,
    negative_cross: float = 0.0,
) -> dict:
    return {
        "id": runtime_id,
        "runtime_id": runtime_id,
        "track": track,
        "signal_present": True,
        "stereo_v08_supported": True,
        "stereo_v08_valid": True,
        "stereo_valid": True,
        "rms_db": rms_db,
        "mid_rms_db": mid_rms_db,
        "side_rms_db": side_rms_db,
        "side_to_mid_db": side_rms_db - mid_rms_db,
        "stereo_correlation": correlation,
        "negative_cross_energy_ratio": negative_cross,
        "low_band_20_120_correlation": correlation,
        "low_band_20_120_side_to_mid_db": side_rms_db - mid_rms_db,
        "bands_db": list(mid_bands),
        "side_bands_db": list(side_bands),
        "band_stereo_correlation": [correlation] * core.NUM_STEREO_CORR_BANDS,
        "band_side_to_mid_db": [side_rms_db - mid_rms_db] * core.NUM_STEREO_CORR_BANDS,
        "_received_at": time.time(),
    }


def _install(runtime_id: str, frame: dict) -> None:
    with core._lock:
        core._tracks[runtime_id] = frame
        core._history[runtime_id] = deque([frame], maxlen=core.HISTORY_LENGTH)


def _assert_close(actual: float | None, expected: float, tolerance: float = 0.02) -> None:
    assert actual is not None, (actual, expected)
    assert abs(float(actual) - expected) <= tolerance, (actual, expected)


def main() -> None:
    with core._lock:
        saved_tracks = copy.deepcopy(core._tracks)
        saved_history = copy.deepcopy(core._history)
        saved_bindings = copy.deepcopy(core._bindings)

    try:
        with core._lock:
            core._tracks.clear()
            core._history.clear()
            core._bindings.clear()

        flat_mid = [-18.0] * core.NUM_BANDS
        no_side = [mono.FLOOR_DB] * core.NUM_BANDS

        # Identical L/R: M=L=R, S=0, so fold-down RMS/energy delta is 0 dB.
        identical = _frame(
            "mono-identical",
            "Identical",
            rms_db=-12.0,
            mid_rms_db=-12.0,
            side_rms_db=mono.FLOOR_DB,
            mid_bands=flat_mid,
            side_bands=no_side,
            correlation=1.0,
        )
        _install("mono-identical", identical)
        result = mono.audio_mono_compatibility("mono-identical", 5.0)
        assert result["available"] is True, result
        _assert_close(result["full_band"]["mono_fold_rms_delta_db"], 0.0)
        assert result["full_band"]["floor_censored"] is False
        assert all(
            band["mono_fold_delta_db"] is None
            or abs(float(band["mono_fold_delta_db"])) <= 0.02
            for band in result["frequency"]["bands"]
            if band["available"]
        )

        # Left-only: stereo-equivalent RMS is A/sqrt(2), mono fold is A/2,
        # therefore fold-down loses 3.0103 dB RMS energy.
        left_only = _frame(
            "mono-left",
            "Left Only",
            rms_db=-3.0103,
            mid_rms_db=-6.0206,
            side_rms_db=-6.0206,
            mid_bands=[-12.0] * core.NUM_BANDS,
            side_bands=[-12.0] * core.NUM_BANDS,
            correlation=0.0,
        )
        _install("mono-left", left_only)
        left_result = mono.audio_mono_compatibility("mono-left", 5.0)
        _assert_close(left_result["full_band"]["mono_fold_rms_delta_db"], -3.0103)
        for band in left_result["frequency"]["bands"]:
            if band["available"]:
                _assert_close(band["mono_fold_delta_db"], -3.0103)

        # Hard anti-phase: Mid reaches the Analyzer floor while Side remains
        # strong. The tool must report strong floor-censored loss, not a fake
        # zero/positive result or an infinitely precise cancellation depth.
        anti_frame = _frame(
            "mono-antiphase",
            "Anti Phase",
            rms_db=-9.0,
            mid_rms_db=mono.FLOOR_DB,
            side_rms_db=-9.0,
            mid_bands=[mono.FLOOR_DB] * core.NUM_BANDS,
            side_bands=[-9.0] * core.NUM_BANDS,
            correlation=-1.0,
            negative_cross=1.0,
        )
        _install("mono-antiphase", anti_frame)
        anti_result = mono.audio_mono_compatibility("mono-antiphase", 5.0)
        assert anti_result["available"] is True
        assert anti_result["full_band"]["floor_censored"] is True
        _assert_close(anti_result["full_band"]["mono_fold_rms_delta_db"], -111.0)
        anti_band = anti_result["frequency"]["bands"][0]
        assert anti_band["floor_censored"] is True
        _assert_close(anti_band["mono_fold_delta_db"], -111.0)
        assert anti_band["energy_loss_fraction"] == 1.0

        # Unequal correlated stereo has finite Side energy and a finite loss.
        unequal = mono._band_evidence(-10.0, -20.0, 500.0)
        assert unequal["available"] is True
        assert unequal["floor_censored"] is False
        assert -1.0 < float(unequal["mono_fold_delta_db"]) < 0.0

        # Energy weighting: a near-silent band with total cancellation cannot
        # outrank a strong energetic band merely because its raw delta is huge.
        strong = mono._band_evidence(-12.0, -12.0, 100.0)
        silent_loss = mono._band_evidence(mono.FLOOR_DB, -80.0, 10000.0)
        bands = [strong, silent_loss]
        mono._finalize_relative_energy(bands)
        assert float(strong["inspection_priority"]) > float(silent_loss["inspection_priority"])

        # Completely unmeasurable Mid+Side energy remains unavailable rather
        # than becoming an artificial compatibility problem.
        silent = mono._band_evidence(mono.FLOOR_DB, mono.FLOOR_DB, 16000.0)
        assert silent["available"] is False
        assert silent["mono_fold_delta_db"] is None
        assert silent["inspection_priority"] is None

        # Grouped low-band evidence must be derived from the same raw band
        # powers and no universal quality/fail score may appear anywhere.
        assert result["frequency"]["grouped_ranges"][0]["range"] == "20-120 Hz"
        serialized_keys = str(result).casefold()
        assert "quality_score" not in serialized_keys
        assert "pass_fail" not in serialized_keys
        assert result["peak_fold_down"]["available"] is False
        assert result["scope"]["historical_daw_range_supported"] is False
        assert result["scope"]["section_range_supported"] is False

        # Basic power identity helper check: M^2 + S^2 is the stereo-equivalent
        # reference used by every band result.
        mid_power = 10.0 ** (-12.0 / 10.0)
        side_power = 10.0 ** (-18.0 / 10.0)
        identity = mono._band_evidence(-12.0, -18.0, 2000.0)
        expected = 10.0 * math.log10(mid_power / (mid_power + side_power))
        _assert_close(identity["mono_fold_delta_db"], expected)

        print(
            "P7a mono compatibility regression: ok "
            "(identical, left-only, anti-phase floor censoring, unequal stereo, M/S power identity, "
            "silent unavailable, energy-aware shortlist, no quality score, peak/historical boundaries)"
        )
    finally:
        with core._lock:
            core._tracks.clear()
            core._tracks.update(saved_tracks)
            core._history.clear()
            core._history.update(saved_history)
            core._bindings.clear()
            core._bindings.update(saved_bindings)


if __name__ == "__main__":
    main()
