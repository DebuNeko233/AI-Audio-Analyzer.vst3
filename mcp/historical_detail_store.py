#!/usr/bin/env python3
"""P4b bounded historical-detail retention and DAW-range evidence."""

from __future__ import annotations

import math
import sys
from array import array
from typing import Any

import masking_tools as masking
import mono_compatibility_tools as mono
import range_tools as ranges
import server as core
import song_tools as song
import temporal_tools as temporal

DETAIL_SCHEMA_VERSION = 1
DETAIL_KEY = "_p4b_detail_v1"
DEFAULT_MINIMUM_COVERAGE = ranges.DEFAULT_MINIMUM_COVERAGE
DEFAULT_TEMPORAL_LOW_HZ = 40.0
DEFAULT_TEMPORAL_HIGH_HZ = 160.0
DEFAULT_MAX_MASKING_REGIONS = 8

SUM_MID_RMS_POWER = 0
SUM_SIDE_RMS_POWER = 1
SUM_NEGATIVE_CROSS = 2
SUM_LOW_CORRELATION = 3
SUM_LOW_SIDE_MID_RATIO_POWER = 4
SUM_TEMPORAL_FLUX_WEIGHTED = 5
SUM_TEMPORAL_SECONDS = 6
SUM_LOW_BAND_POWER = 7
SUM_COUNT = 8

COUNT_MID_RMS = 0
COUNT_SIDE_RMS = 1
COUNT_NEGATIVE_CROSS = 2
COUNT_LOW_CORRELATION = 3
COUNT_LOW_SIDE_MID_RATIO = 4
COUNT_LOW_BAND = 5
COUNT_STEREO_VALID = 6
COUNT_TEMPORAL_VALID = 7
COUNT_ONSET_CANDIDATE = 8
COUNT_COUNT = 9

EXT_NEGATIVE_CROSS_MAX = 0
EXT_LOW_CORRELATION_MIN = 1
EXT_TEMPORAL_FLUX_PEAK_MAX = 2
EXT_RMS_RISE_PEAK_MAX = 3
EXT_COUNT = 4

_ORIGINAL_ON_FRAME = core._on_frame


def _finite(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _db_to_power(value: Any) -> float | None:
    numeric = _finite(value)
    if numeric is None:
        return None
    if numeric <= mono.FLOOR_DB:
        return 0.0
    return 10.0 ** (numeric / 10.0)


def _power_to_db(power: float | None, count: int = 1) -> float | None:
    if power is None or count <= 0:
        return None
    mean_power = max(0.0, float(power)) / count
    if mean_power <= mono._POWER_FLOOR:
        return mono.FLOOR_DB
    return 10.0 * math.log10(mean_power)


def _new_detail() -> dict[str, Any]:
    return {
        "schema_version": DETAIL_SCHEMA_VERSION,
        "mid_power_sum": array("f", [0.0] * core.NUM_BANDS),
        "mid_count": array("H", [0] * core.NUM_BANDS),
        "side_power_sum": array("f", [0.0] * core.NUM_BANDS),
        "side_count": array("H", [0] * core.NUM_BANDS),
        "band_corr_sum": array("f", [0.0] * core.NUM_STEREO_CORR_BANDS),
        "band_corr_count": array("H", [0] * core.NUM_STEREO_CORR_BANDS),
        "band_side_mid_ratio_power_sum": array("f", [0.0] * core.NUM_STEREO_CORR_BANDS),
        "band_side_mid_ratio_count": array("H", [0] * core.NUM_STEREO_CORR_BANDS),
        "scalar_sum": array("f", [0.0] * SUM_COUNT),
        "scalar_count": array("H", [0] * COUNT_COUNT),
        "extrema": array("f", [math.nan] * EXT_COUNT),
    }


def _estimate_detail_bytes() -> int:
    detail = _new_detail()
    return int(sys.getsizeof(detail) + sum(sys.getsizeof(v) for v in detail.values()))


def _inc(values: array, index: int) -> None:
    values[index] = min(65535, int(values[index]) + 1)


def _accumulate_db_bands(sums: array, counts: array, values: Any, expected: int) -> None:
    if not isinstance(values, list) or len(values) != expected:
        return
    for index, raw in enumerate(values):
        power = _db_to_power(raw)
        if power is None:
            continue
        sums[index] = float(sums[index]) + float(power)
        _inc(counts, index)


def _accumulate_linear_bands(sums: array, counts: array, values: Any, expected: int) -> None:
    if not isinstance(values, list) or len(values) != expected:
        return
    for index, raw in enumerate(values):
        value = _finite(raw)
        if value is None:
            continue
        sums[index] = float(sums[index]) + value
        _inc(counts, index)


def _accumulate_ratio_bands(sums: array, counts: array, values: Any, expected: int) -> None:
    if not isinstance(values, list) or len(values) != expected:
        return
    for index, raw in enumerate(values):
        value = _finite(raw)
        if value is None:
            continue
        sums[index] = float(sums[index]) + 10.0 ** (value / 10.0)
        _inc(counts, index)


def _set_max(extrema: array, index: int, value: Any) -> None:
    numeric = _finite(value)
    if numeric is None:
        return
    current = float(extrema[index])
    extrema[index] = numeric if math.isnan(current) else max(current, numeric)


def _set_min(extrema: array, index: int, value: Any) -> None:
    numeric = _finite(value)
    if numeric is None:
        return
    current = float(extrema[index])
    extrema[index] = numeric if math.isnan(current) else min(current, numeric)


def _accumulate_detail(detail: dict[str, Any], frame: dict[str, Any]) -> None:
    features = frame.get("analysis_features")
    spectrum_enabled = not isinstance(features, dict) or bool(features.get("spectrum"))
    stereo_enabled = not isinstance(features, dict) or bool(features.get("stereo"))
    temporal_enabled = not isinstance(features, dict) or bool(features.get("temporal"))

    if spectrum_enabled and bool(frame.get("spectrum_valid", frame.get("signal_present", True))):
        _accumulate_db_bands(detail["mid_power_sum"], detail["mid_count"], frame.get("bands_db"), core.NUM_BANDS)

    if stereo_enabled and bool(frame.get("stereo_valid", frame.get("signal_present", True))):
        _accumulate_linear_bands(
            detail["band_corr_sum"],
            detail["band_corr_count"],
            frame.get("band_stereo_correlation"),
            core.NUM_STEREO_CORR_BANDS,
        )

    sums = detail["scalar_sum"]
    counts = detail["scalar_count"]
    extrema = detail["extrema"]

    if stereo_enabled and bool(frame.get("stereo_v08_valid")):
        _inc(counts, COUNT_STEREO_VALID)
        _accumulate_db_bands(detail["side_power_sum"], detail["side_count"], frame.get("side_bands_db"), core.NUM_BANDS)
        _accumulate_ratio_bands(
            detail["band_side_mid_ratio_power_sum"],
            detail["band_side_mid_ratio_count"],
            frame.get("band_side_to_mid_db"),
            core.NUM_STEREO_CORR_BANDS,
        )
        mid_power = _db_to_power(frame.get("mid_rms_db"))
        if mid_power is not None:
            sums[SUM_MID_RMS_POWER] = float(sums[SUM_MID_RMS_POWER]) + mid_power
            _inc(counts, COUNT_MID_RMS)
        side_power = _db_to_power(frame.get("side_rms_db"))
        if side_power is not None:
            sums[SUM_SIDE_RMS_POWER] = float(sums[SUM_SIDE_RMS_POWER]) + side_power
            _inc(counts, COUNT_SIDE_RMS)
        negative = _finite(frame.get("negative_cross_energy_ratio"))
        if negative is not None:
            sums[SUM_NEGATIVE_CROSS] = float(sums[SUM_NEGATIVE_CROSS]) + negative
            _inc(counts, COUNT_NEGATIVE_CROSS)
            _set_max(extrema, EXT_NEGATIVE_CROSS_MAX, negative)
        low_corr = _finite(frame.get("low_band_20_120_correlation"))
        if low_corr is not None:
            sums[SUM_LOW_CORRELATION] = float(sums[SUM_LOW_CORRELATION]) + low_corr
            _inc(counts, COUNT_LOW_CORRELATION)
            _set_min(extrema, EXT_LOW_CORRELATION_MIN, low_corr)
        low_ratio_db = _finite(frame.get("low_band_20_120_side_to_mid_db"))
        if low_ratio_db is not None:
            sums[SUM_LOW_SIDE_MID_RATIO_POWER] = float(sums[SUM_LOW_SIDE_MID_RATIO_POWER]) + 10.0 ** (low_ratio_db / 10.0)
            _inc(counts, COUNT_LOW_SIDE_MID_RATIO)

    if temporal_enabled and bool(frame.get("temporal_valid")):
        _inc(counts, COUNT_TEMPORAL_VALID)
        window = _finite(frame.get("temporal_window_seconds"))
        weight = 0.0 if window is None else max(0.0, window)
        if weight > 0.0:
            flux = _finite(frame.get("spectral_flux_mean"))
            if flux is not None:
                sums[SUM_TEMPORAL_FLUX_WEIGHTED] = float(sums[SUM_TEMPORAL_FLUX_WEIGHTED]) + flux * weight
            sums[SUM_TEMPORAL_SECONDS] = float(sums[SUM_TEMPORAL_SECONDS]) + weight
        _set_max(extrema, EXT_TEMPORAL_FLUX_PEAK_MAX, frame.get("spectral_flux_peak"))
        _set_max(extrema, EXT_RMS_RISE_PEAK_MAX, frame.get("rms_rise_peak_db"))
        low_power = _db_to_power(frame.get("low_band_energy_db"))
        if low_power is not None:
            sums[SUM_LOW_BAND_POWER] = float(sums[SUM_LOW_BAND_POWER]) + low_power
            _inc(counts, COUNT_LOW_BAND)
        if temporal._candidate(frame):
            _inc(counts, COUNT_ONSET_CANDIDATE)


def on_frame_p4b(address: str, *args: Any) -> None:
    _ORIGINAL_ON_FRAME(address, *args)
    if len(args) < song.V12_START + song.V12_FIELD_COUNT:
        return
    try:
        runtime_id = str(args[temporal.V03_START + 3]).strip()
    except (IndexError, TypeError, ValueError):
        return
    if not runtime_id:
        return
    with core._lock:
        frame = core._tracks.get(runtime_id)
        if frame is None:
            return
        frame_copy = dict(frame)
    if not bool(frame_copy.get("transport_v12_supported")) or not bool(frame_copy.get("transport_is_playing")):
        return
    position = _finite(frame_copy.get("transport_time_seconds"))
    epoch = frame_copy.get("transport_epoch")
    if position is None or epoch is None:
        return
    key = (int(epoch), int(math.floor(position / song.TIMELINE_BIN_SECONDS)))
    with song._song_lock:
        instance = song._timeline.get(runtime_id)
        if not instance:
            return
        acc = instance.get(key)
        if acc is None:
            return
        detail = acc.get(DETAIL_KEY)
        if not isinstance(detail, dict):
            detail = _new_detail()
            acc[DETAIL_KEY] = detail
        _accumulate_detail(detail, frame_copy)


def _mean_db_array(rows: list[dict[str, Any]], sum_key: str, count_key: str, size: int) -> list[float | None]:
    out = []
    for i in range(size):
        power_sum = 0.0
        count = 0
        for row in rows:
            detail = row.get(DETAIL_KEY)
            if not isinstance(detail, dict):
                continue
            sums = detail.get(sum_key)
            counts = detail.get(count_key)
            if isinstance(sums, array) and isinstance(counts, array):
                power_sum += float(sums[i])
                count += int(counts[i])
        value = _power_to_db(power_sum, count)
        out.append(None if value is None else round(value, 4))
    return out


def _mean_linear_array(rows: list[dict[str, Any]], sum_key: str, count_key: str, size: int) -> list[float | None]:
    out = []
    for i in range(size):
        total = 0.0
        count = 0
        for row in rows:
            detail = row.get(DETAIL_KEY)
            if not isinstance(detail, dict):
                continue
            sums = detail.get(sum_key)
            counts = detail.get(count_key)
            if isinstance(sums, array) and isinstance(counts, array):
                total += float(sums[i])
                count += int(counts[i])
        out.append(None if count <= 0 else round(total / count, 6))
    return out


def _mean_ratio_array(rows: list[dict[str, Any]], sum_key: str, count_key: str, size: int) -> list[float | None]:
    out = []
    for i in range(size):
        total = 0.0
        count = 0
        for row in rows:
            detail = row.get(DETAIL_KEY)
            if not isinstance(detail, dict):
                continue
            sums = detail.get(sum_key)
            counts = detail.get(count_key)
            if isinstance(sums, array) and isinstance(counts, array):
                total += float(sums[i])
                count += int(counts[i])
        out.append(None if count <= 0 or total <= 0.0 else round(10.0 * math.log10(total / count), 4))
    return out


def _scalar_total(rows: list[dict[str, Any]], index: int) -> float:
    total = 0.0
    for row in rows:
        detail = row.get(DETAIL_KEY)
        if isinstance(detail, dict) and isinstance(detail.get("scalar_sum"), array):
            total += float(detail["scalar_sum"][index])
    return total


def _scalar_count(rows: list[dict[str, Any]], index: int) -> int:
    total = 0
    for row in rows:
        detail = row.get(DETAIL_KEY)
        if isinstance(detail, dict) and isinstance(detail.get("scalar_count"), array):
            total += int(detail["scalar_count"][index])
    return total


def _extreme(rows: list[dict[str, Any]], index: int, mode: str) -> float | None:
    values = []
    for row in rows:
        detail = row.get(DETAIL_KEY)
        if isinstance(detail, dict) and isinstance(detail.get("extrema"), array):
            value = float(detail["extrema"][index])
            if math.isfinite(value):
                values.append(value)
    if not values:
        return None
    return round(max(values) if mode == "max" else min(values), 6)

