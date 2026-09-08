#!/usr/bin/env python3
"""Synthetic regressions for P8a session reference comparison semantics."""

from __future__ import annotations

import copy
import math

import reference_tools as reference


def _profile(*, rms: float, bands: list[float], crest: float = 10.0, corr: float = 0.8, width: float = 0.4) -> dict:
    centers = [100.0 * (2.0 ** index) for index in range(len(bands))]
    return {
        "coverage": {"analysis_valid": True},
        "energy": {
            "rms_dbfs": rms,
            "crest_db": crest,
            "lufs_s": rms - 1.0,
            "peak_dbfs": rms + crest,
            "true_peak_dbtp": rms + crest + 0.2,
        },
        "spectrum": {
            "centroid_hz": 1500.0,
            "bands": [
                {"center_hz": center, "db": value}
                for center, value in zip(centers, bands)
            ],
            "regions": {
                "low": bands[0],
                "mid": bands[min(1, len(bands) - 1)],
                "high": bands[-1],
            },
        },
        "stereo": {"correlation": corr, "width": width},
        "mono_compatibility": {
            "available": True,
            "full_band": {"mono_fold_rms_delta_db": -0.5, "floor_censored": False},
            "grouped_ranges": [
                {"range": "20-120 Hz", "mono_fold_delta_db": -0.2, "floor_censored": False},
                {"range": "120-500 Hz", "mono_fold_delta_db": -0.8, "floor_censored": False},
            ],
        },
    }


def _assert_close(value: float | None, expected: float, tol: float = 1.0e-6) -> None:
    assert value is not None
    assert math.isclose(float(value), expected, abs_tol=tol), (value, expected)


def main() -> None:
    base = _profile(rms=-20.0, bands=[-30.0, -24.0, -28.0])

    identical = reference._compare_profiles(base, copy.deepcopy(base))
    _assert_close(identical["energy"]["rms_db"], 0.0)
    for band in identical["spectrum"]["absolute"]["bands"]:
        _assert_close(band["target_minus_reference_db"], 0.0)
    for band in identical["spectrum"]["level_normalized"]["bands"]:
        _assert_close(band["level_normalized_target_minus_reference_db"], 0.0)

    # Pure +6 dB target gain remains visible absolutely but disappears from the
    # explicit RMS-level-normalized spectral-shape view.
    gain = _profile(rms=-14.0, bands=[-24.0, -18.0, -22.0])
    gain_cmp = reference._compare_profiles(base, gain)
    _assert_close(gain_cmp["energy"]["rms_db"], 6.0)
    for band in gain_cmp["spectrum"]["absolute"]["bands"]:
        _assert_close(band["target_minus_reference_db"], 6.0)
    _assert_close(gain_cmp["spectrum"]["level_normalized"]["target_gain_to_reference_db"], -6.0)
    for band in gain_cmp["spectrum"]["level_normalized"]["bands"]:
        _assert_close(band["level_normalized_target_minus_reference_db"], 0.0)

    # Spectral shape survives level normalization.
    shape = _profile(rms=-14.0, bands=[-24.0, -16.0, -24.0])
    shape_cmp = reference._compare_profiles(base, shape)
    normalized = {
        item["center_hz"]: item["level_normalized_target_minus_reference_db"]
        for item in shape_cmp["spectrum"]["level_normalized"]["bands"]
    }
    values = list(normalized.values())
    assert values == [0.0, 2.0, -2.0], values

    # Missing feature families stay unavailable/null rather than becoming zero.
    unavailable = copy.deepcopy(base)
    unavailable["energy"]["rms_dbfs"] = None
    unavailable["mono_compatibility"] = {"available": False, "reason": "disabled"}
    unavailable_cmp = reference._compare_profiles(base, unavailable)
    assert unavailable_cmp["energy"]["rms_db"] is None
    assert unavailable_cmp["spectrum"]["level_normalized"]["available"] is False
    assert unavailable_cmp["mono_compatibility"]["available"] is False

    # P8a must remain descriptive and must not emit a quality score or recipe.
    boundary = shape_cmp["interpretation_boundary"]
    assert boundary["quality_score"] is None
    assert boundary["processing_recommendation"] is None
    assert boundary["automatic_eq_match"] is False
    assert boundary["automatic_master_match"] is False
    assert shape_cmp["comparability"]["same_section_or_song_assumed"] is False

    print("P8a reference regression OK")


if __name__ == "__main__":
    main()
