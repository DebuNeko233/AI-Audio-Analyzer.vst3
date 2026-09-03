#!/usr/bin/env python3
"""Transport-aware song-memory layer for AI Audio Analyzer MCP.

The LLM is deliberately outside the realtime path. Analyzer instances continue
measuring while the model thinks or controls the DAW; this module retains a
bounded DAW-time memory that can be queried later at coarser resolutions.

A transport epoch is one continuous playback pass for one Analyzer instance.
The VST3 increments it on playback start or a detected seek/loop discontinuity
and resets pass-dependent analysis state. Epoch IDs are instance-local.
"""

from __future__ import annotations

import math
import threading
import time
from collections import OrderedDict
from typing import Any

import server as core
import performance_tools as performance
import temporal_tools as temporal

V12_START = performance.V11_START + performance.V11_FIELD_COUNT
V12_FIELD_COUNT = 15
TIMELINE_BIN_SECONDS = 1.0
COVERAGE_SLOT_SECONDS = 0.1
COVERAGE_SLOTS_PER_BIN = int(round(TIMELINE_BIN_SECONDS / COVERAGE_SLOT_SECONDS))
MAX_TIMELINE_BINS_PER_INSTANCE = 1200  # 20 minutes at 1 s resolution.
RESOLUTIONS_SECONDS = (1, 2, 5, 10, 15, 30)

SPECTRAL_REGIONS = (
    ("sub_20_120_db", 20.0, 120.0),
    ("low_mid_120_500_db", 120.0, 500.0),
    ("mid_500_2000_db", 500.0, 2000.0),
    ("presence_2000_5000_db", 2000.0, 5000.0),
    ("high_5000_20000_db", 5000.0, 20000.0),
)

_ORIGINAL_ON_FRAME = core._on_frame
_song_lock = threading.RLock()
_timeline: dict[str, OrderedDict[tuple[int, int], dict[str, Any]]] = {}


def _safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _db_power(value: Any) -> float | None:
    numeric = _safe_float(value)
    if numeric is None or numeric <= -120.0:
        return None
    return 10.0 ** (numeric / 10.0)


def _db_from_power(power_sum: float, count: int) -> float | None:
    if count <= 0 or power_sum <= 0.0:
        return None
    return round(10.0 * math.log10(max(power_sum / count, 1.0e-12)), 4)


def _region_powers(bands_db: Any) -> list[float | None]:
    if not isinstance(bands_db, list) or len(bands_db) != len(core.BAND_CENTERS):
        return [None] * len(SPECTRAL_REGIONS)
    result: list[float | None] = []
    for _name, lo, hi in SPECTRAL_REGIONS:
        values = [
            power
            for center, value in zip(core.BAND_CENTERS, bands_db)
            if lo <= center < hi and (power := _db_power(value)) is not None
        ]
        result.append(None if not values else sum(values) / len(values))
    return result


def _new_accumulator(frame: dict[str, Any], epoch: int, bin_index: int) -> dict[str, Any]:
    start = bin_index * TIMELINE_BIN_SECONDS
    received = float(frame.get("_received_at", time.time()))
    return {
        "transport_epoch": epoch,
        "bin_index": bin_index,
        "start_seconds": start,
        "end_seconds": start + TIMELINE_BIN_SECONDS,
        "frame_count": 0,
        "active_count": 0,
        "coverage_mask": 0,
        "first_received_at": received,
        "last_received_at": received,
        "rms_power_sum": 0.0,
        "rms_count": 0,
        "lufs_s_power_sum": 0.0,
        "lufs_s_count": 0,
        "lufs_i_latest": None,
        "peak_db_max": None,
        "true_peak_db_max": None,
        "max_true_peak_dbtp": None,
        "crest_sum": 0.0,
        "crest_count": 0,
        "centroid_sum": 0.0,
        "centroid_count": 0,
        "stereo_corr_sum": 0.0,
        "stereo_corr_count": 0,
        "stereo_width_sum": 0.0,
        "stereo_width_count": 0,
        "flux_sum": 0.0,
        "flux_count": 0,
        "spectral_region_power_sum": [0.0] * len(SPECTRAL_REGIONS),
        "spectral_region_count": [0] * len(SPECTRAL_REGIONS),
        "chroma_sum": [0.0] * 12,
        "chroma_weight_sum": 0.0,
        "lag_sum_ms": 0.0,
        "lag_count": 0,
        "lag_max_ms": 0.0,
        "dropped_blocks_max": 0,
        "bpm_latest": frame.get("transport_bpm"),
        "time_signature_numerator": frame.get("transport_time_signature_numerator"),
        "time_signature_denominator": frame.get("transport_time_signature_denominator"),
    }


def _mark_coverage(acc: dict[str, Any], frame: dict[str, Any]) -> None:
    position = _safe_float(frame.get("transport_time_seconds"))
    if position is None:
        return
    local = max(0.0, min(TIMELINE_BIN_SECONDS - 1.0e-9, position - float(acc["start_seconds"])))
    slot = max(0, min(COVERAGE_SLOTS_PER_BIN - 1, int(local / COVERAGE_SLOT_SECONDS)))
    acc["coverage_mask"] = int(acc["coverage_mask"]) | (1 << slot)


def _covered_seconds(acc: dict[str, Any]) -> float:
    mask = max(0, int(acc.get("coverage_mask", 0)))
    return min(TIMELINE_BIN_SECONDS, mask.bit_count() * COVERAGE_SLOT_SECONDS)


def _accumulate(acc: dict[str, Any], frame: dict[str, Any]) -> None:
    acc["frame_count"] += 1
    if bool(frame.get("signal_present")):
        acc["active_count"] += 1
    acc["last_received_at"] = max(
        float(acc["last_received_at"]), float(frame.get("_received_at", time.time()))
    )
    _mark_coverage(acc, frame)

    for field, sum_key, count_key in (
        ("rms_db", "rms_power_sum", "rms_count"),
        ("lufs_s", "lufs_s_power_sum", "lufs_s_count"),
    ):
        power = _db_power(frame.get(field))
        if power is not None:
            acc[sum_key] += power
            acc[count_key] += 1

    for field, key in (
        ("peak_db", "peak_db_max"),
        ("true_peak_dbtp", "true_peak_db_max"),
        ("max_true_peak_dbtp", "max_true_peak_dbtp"),
    ):
        value = _safe_float(frame.get(field))
        if value is not None:
            old = acc[key]
            acc[key] = value if old is None else max(float(old), value)

    lufs_i = _safe_float(frame.get("lufs_i"))
    if lufs_i is not None:
        acc["lufs_i_latest"] = lufs_i

    for field, sum_key, count_key in (
        ("crest_db", "crest_sum", "crest_count"),
        ("centroid_hz", "centroid_sum", "centroid_count"),
        ("stereo_correlation", "stereo_corr_sum", "stereo_corr_count"),
        ("stereo_width", "stereo_width_sum", "stereo_width_count"),
        ("spectral_flux_mean", "flux_sum", "flux_count"),
    ):
        value = _safe_float(frame.get(field))
        if value is not None:
            acc[sum_key] += value
            acc[count_key] += 1

    for index, power in enumerate(_region_powers(frame.get("bands_db"))):
        if power is not None:
            acc["spectral_region_power_sum"][index] += power
            acc["spectral_region_count"][index] += 1

    chroma = frame.get("chroma")
    chroma_coverage = _safe_float(frame.get("chroma_energy_ratio"))
    if isinstance(chroma, list) and len(chroma) == 12 and chroma_coverage is not None and chroma_coverage > 0.0:
        values = [_safe_float(value) for value in chroma]
        if all(value is not None and value >= 0.0 for value in values):
            total = sum(float(value) for value in values)
            if total > 1.0e-12:
                weight = max(1.0e-6, chroma_coverage)
                for index, value in enumerate(values):
                    acc["chroma_sum"][index] += (float(value) / total) * weight
                acc["chroma_weight_sum"] += weight

    lag = _safe_float(frame.get("estimated_analysis_lag_ms"))
    if lag is not None:
        lag = max(0.0, lag)
        acc["lag_sum_ms"] += lag
        acc["lag_count"] += 1
        acc["lag_max_ms"] = max(float(acc["lag_max_ms"]), lag)

    try:
        dropped = max(0, int(frame.get("dropped_blocks", 0)))
    except (TypeError, ValueError):
        dropped = 0
    acc["dropped_blocks_max"] = max(int(acc["dropped_blocks_max"]), dropped)

    if frame.get("transport_bpm") is not None:
        acc["bpm_latest"] = frame.get("transport_bpm")
    if frame.get("transport_time_signature_numerator") is not None:
        acc["time_signature_numerator"] = frame.get("transport_time_signature_numerator")
    if frame.get("transport_time_signature_denominator") is not None:
        acc["time_signature_denominator"] = frame.get("transport_time_signature_denominator")


def _sum(rows: list[dict[str, Any]], key: str) -> float:
    return sum(float(row[key]) for row in rows)


def _count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(int(row[key]) for row in rows)


def _latest_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return max(rows, key=lambda row: float(row["last_received_at"]))


def _finalize_rows(
    rows: list[dict[str, Any]],
    *,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    expected_seconds: float | None = None,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("Cannot summarize an empty timeline range.")

    start = min(float(row["start_seconds"]) for row in rows) if start_seconds is None else float(start_seconds)
    end = max(float(row["end_seconds"]) for row in rows) if end_seconds is None else float(end_seconds)
    frames = max(1, _count(rows, "frame_count"))
    active = _count(rows, "active_count")
    latest = _latest_row(rows)

    rms_power = _sum(rows, "rms_power_sum")
    rms_count = _count(rows, "rms_count")
    lufs_s_power = _sum(rows, "lufs_s_power_sum")
    lufs_s_count = _count(rows, "lufs_s_count")

    def max_optional(key: str) -> float | None:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        return None if not values else max(values)

    def mean(sum_key: str, count_key: str, digits: int) -> float | None:
        count = _count(rows, count_key)
        return None if count <= 0 else round(_sum(rows, sum_key) / count, digits)

    spectral_regions: dict[str, float | None] = {}
    for index, (name, _lo, _hi) in enumerate(SPECTRAL_REGIONS):
        power_sum = sum(float(row["spectral_region_power_sum"][index]) for row in rows)
        count = sum(int(row["spectral_region_count"][index]) for row in rows)
        spectral_regions[name] = _db_from_power(power_sum, count)

    chroma_weight = sum(float(row["chroma_weight_sum"]) for row in rows)
    chroma = None
    if chroma_weight > 0.0:
        raw = [
            sum(float(row["chroma_sum"][index]) for row in rows) / chroma_weight
            for index in range(12)
        ]
        total = sum(raw)
        if total > 1.0e-12:
            chroma = [round(value / total, 5) for value in raw]

    covered_seconds = sum(_covered_seconds(row) for row in rows)
    expected = expected_seconds
    if expected is None:
        expected = max(TIMELINE_BIN_SECONDS, end - start)
    coverage_ratio = min(1.0, covered_seconds / expected) if expected > 0.0 else None

    lag_count = _count(rows, "lag_count")
    lag_sum = _sum(rows, "lag_sum_ms")
    lag_max = max(float(row["lag_max_ms"]) for row in rows)
    dropped_max = max(int(row["dropped_blocks_max"]) for row in rows)
    last_received = max(float(row["last_received_at"]) for row in rows)

    latest_lufs_i = latest.get("lufs_i_latest")
    bpm = latest.get("bpm_latest")
    num = latest.get("time_signature_numerator")
    den = latest.get("time_signature_denominator")

    return {
        "transport_epoch": int(rows[0]["transport_epoch"]),
        "start_seconds": round(start, 3),
        "end_seconds": round(end, 3),
        "frame_count": _count(rows, "frame_count"),
        "active_ratio": round(active / frames, 4),
        "rms_db": _db_from_power(rms_power, rms_count),
        "lufs_s": _db_from_power(lufs_s_power, lufs_s_count),
        "lufs_i_latest": None if latest_lufs_i is None else round(float(latest_lufs_i), 4),
        "peak_db": None if (value := max_optional("peak_db_max")) is None else round(value, 4),
        "true_peak_dbtp": None if (value := max_optional("true_peak_db_max")) is None else round(value, 4),
        "max_true_peak_dbtp": None if (value := max_optional("max_true_peak_dbtp")) is None else round(value, 4),
        "crest_db": mean("crest_sum", "crest_count", 4),
        "centroid_hz": mean("centroid_sum", "centroid_count", 2),
        "stereo_correlation": mean("stereo_corr_sum", "stereo_corr_count", 5),
        "stereo_width": mean("stereo_width_sum", "stereo_width_count", 5),
        "spectral_flux_mean": mean("flux_sum", "flux_count", 6),
        "spectral_regions": spectral_regions,
        "chroma": chroma,
        "bpm": bpm,
        "time_signature": None if num is None or den is None else [int(num), int(den)],
        "data_quality": {
            "covered_seconds": round(covered_seconds, 3),
            "mean_estimated_analysis_lag_ms": None if lag_count <= 0 else round(lag_sum / lag_count, 3),
            "max_estimated_analysis_lag_ms": round(lag_max, 3),
            "dropped_blocks_cumulative": dropped_max,
            "data_age_seconds": round(max(0.0, time.time() - last_received), 3),
            "coverage_ratio": None if coverage_ratio is None else round(coverage_ratio, 4),
        },
    }


def _binding_selector(runtime_id: str) -> str:
    with core._lock:
        binding = core._bindings.get(runtime_id)
        if binding is None:
            return runtime_id
        return f"mixer:{int(binding['fl_track_index'])}/slot:{int(binding['slot'])}"


def _display_name(runtime_id: str) -> str:
    with core._lock:
        frame = core._tracks.get(runtime_id, {})
        binding = core._bindings.get(runtime_id)
        if binding is not None:
            return str(binding.get("fl_track_name") or frame.get("track") or runtime_id)
        return str(frame.get("track") or runtime_id)


def _runtime_sort_key(runtime_id: str) -> tuple[int, int, str]:
    with core._lock:
        binding = core._bindings.get(runtime_id)
        frame = core._tracks.get(runtime_id, {})
        if binding is None:
            return (1, 9999, str(frame.get("track", runtime_id)).casefold())
        return (0, int(binding.get("fl_track_index", 9999)), str(binding.get("fl_track_name", "")).casefold())


def _is_master(runtime_id: str) -> bool:
    with core._lock:
        binding = core._bindings.get(runtime_id)
        frame = core._tracks.get(runtime_id, {})
        if binding is not None and int(binding.get("fl_track_index", -1)) == 0:
            return True
        return str((binding or {}).get("fl_track_name") or frame.get("track") or "").casefold() == "master"


def on_frame_v12(address: str, *args: Any) -> None:
    """Parse older fields, attach transport/data quality, then remember DAW time."""
    _ORIGINAL_ON_FRAME(address, *args)
    if len(args) < V12_START + V12_FIELD_COUNT:
        return

    runtime_id = str(args[temporal.V03_START + 3]).strip()
    if not runtime_id:
        return

    try:
        transport_supported = bool(int(args[V12_START]))
        transport_time_seconds = max(0.0, float(args[V12_START + 1]))
        transport_ppq_position = float(args[V12_START + 2])
        transport_bpm = max(0.0, float(args[V12_START + 3]))
        time_sig_num = max(1, int(args[V12_START + 4]))
        time_sig_den = max(1, int(args[V12_START + 5]))
        transport_is_playing = bool(int(args[V12_START + 6]))
        transport_is_recording = bool(int(args[V12_START + 7]))
        transport_is_looping = bool(int(args[V12_START + 8]))
        loop_start_ppq = float(args[V12_START + 9])
        loop_end_ppq = float(args[V12_START + 10])
        transport_epoch = max(0, int(args[V12_START + 11]))
        estimated_analysis_lag_ms = max(0.0, float(args[V12_START + 12]))
        dropped_blocks = max(0, int(args[V12_START + 13]))
        schema_version = str(args[V12_START + 14]).strip() or "1.2"
    except (TypeError, ValueError):
        return

    with core._lock:
        frame = core._tracks.get(runtime_id)
        if frame is None:
            return
        frame["schema_version"] = schema_version
        frame["transport_v12_supported"] = transport_supported
        frame["transport_time_seconds"] = transport_time_seconds if transport_supported else None
        frame["transport_ppq_position"] = transport_ppq_position if transport_supported else None
        frame["transport_bpm"] = transport_bpm if transport_supported and transport_bpm > 0.0 else None
        frame["transport_time_signature_numerator"] = time_sig_num if transport_supported else None
        frame["transport_time_signature_denominator"] = time_sig_den if transport_supported else None
        frame["transport_is_playing"] = transport_is_playing if transport_supported else None
        frame["transport_is_recording"] = transport_is_recording if transport_supported else None
        frame["transport_is_looping"] = transport_is_looping if transport_supported else None
        frame["transport_loop_start_ppq"] = loop_start_ppq if transport_supported and transport_is_looping else None
        frame["transport_loop_end_ppq"] = loop_end_ppq if transport_supported and transport_is_looping else None
        frame["transport_epoch"] = transport_epoch if transport_supported else None
        frame["estimated_analysis_lag_ms"] = estimated_analysis_lag_ms
        frame["dropped_blocks"] = dropped_blocks
        frame_for_memory = dict(frame)

    if not transport_supported or not transport_is_playing:
        return

    bin_index = int(math.floor(transport_time_seconds / TIMELINE_BIN_SECONDS))
    key = (transport_epoch, bin_index)
    with _song_lock:
        instance = _timeline.setdefault(runtime_id, OrderedDict())
        acc = instance.get(key)
        if acc is None:
            acc = _new_accumulator(frame_for_memory, transport_epoch, bin_index)
            instance[key] = acc
        _accumulate(acc, frame_for_memory)
        instance.move_to_end(key)
        while len(instance) > MAX_TIMELINE_BINS_PER_INSTANCE:
            instance.popitem(last=False)


def _available_epochs(runtime_id: str) -> list[int]:
    with _song_lock:
        instance = _timeline.get(runtime_id, OrderedDict())
        return sorted({int(epoch) for epoch, _bin in instance})


def _bins_for(runtime_id: str, epoch: int) -> list[dict[str, Any]]:
    with _song_lock:
        instance = _timeline.get(runtime_id, OrderedDict())
        rows = [dict(acc) for (item_epoch, _bin), acc in instance.items() if item_epoch == epoch]
    rows.sort(key=lambda item: int(item["bin_index"]))
    return rows


def _pass_summaries(runtime_id: str) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for epoch in _available_epochs(runtime_id):
        rows = _bins_for(runtime_id, epoch)
        if not rows:
            continue
        start = min(float(row["start_seconds"]) for row in rows)
        end = max(float(row["end_seconds"]) for row in rows)
        span = max(TIMELINE_BIN_SECONDS, end - start)
        covered = sum(_covered_seconds(row) for row in rows)
        summaries.append({
            "transport_epoch": epoch,
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
            "span_seconds": round(span, 3),
            "observed_bins": len(rows),
            "covered_seconds": round(covered, 3),
            "coverage_ratio": round(min(1.0, covered / span), 4),
            "last_data_age_seconds": round(max(0.0, time.time() - max(float(row["last_received_at"]) for row in rows)), 3),
        })
    return summaries[-12:]


@core.mcp.tool()
def audio_song_status() -> dict[str, Any]:
    """Return transport readiness, continuous-pass memory and latency quality."""
    now = time.time()
    with core._lock:
        frames = {runtime_id: dict(frame) for runtime_id, frame in core._tracks.items()}

    instances: list[dict[str, Any]] = []
    for runtime_id in sorted(frames, key=_runtime_sort_key):
        frame = frames[runtime_id]
        epochs = _available_epochs(runtime_id)
        remembered = sum(len(_bins_for(runtime_id, epoch)) for epoch in epochs)
        instances.append({
            "runtime_id": runtime_id,
            "selector": _binding_selector(runtime_id),
            "display_name": _display_name(runtime_id),
            "transport_supported": bool(frame.get("transport_v12_supported")),
            "transport_epoch": frame.get("transport_epoch"),
            "transport_time_seconds": frame.get("transport_time_seconds"),
            "is_playing": frame.get("transport_is_playing"),
            "is_looping": frame.get("transport_is_looping"),
            "bpm": frame.get("transport_bpm"),
            "data_age_seconds": round(max(0.0, now - float(frame.get("_received_at", now))), 3),
            "estimated_analysis_lag_ms": frame.get("estimated_analysis_lag_ms"),
            "dropped_blocks": int(frame.get("dropped_blocks", 0) or 0),
            "remembered_epochs": epochs[-12:],
            "remembered_bin_count": remembered,
        })

    supported = [item for item in instances if item["transport_supported"]]
    epochs_now = {int(item["transport_epoch"]) for item in supported if item["transport_epoch"] is not None}
    lag_values = [float(item["estimated_analysis_lag_ms"]) for item in supported if item["estimated_analysis_lag_ms"] is not None]
    dropped = [int(item["dropped_blocks"]) for item in supported]
    warnings: list[str] = []
    if instances and len(supported) < len(instances):
        warnings.append("Some live Analyzer instances do not expose the transport-aware 1.2 tail; their audio cannot be placed on the song timeline.")
    if len(epochs_now) > 1:
        warnings.append("Live Analyzer epoch counters differ. Epoch IDs are instance-local; compare DAW-time ranges rather than assuming equal numbers identify the same pass.")
    if lag_values and max(lag_values) >= 250.0:
        warnings.append("At least one Analyzer reports >=250 ms estimated analysis backlog. Prefer retained timeline evidence over assuming the newest measurement represents current audio.")
    if dropped and max(dropped) > 0:
        warnings.append("At least one Analyzer has dropped audio blocks; inspect data_quality before fine-grained comparisons.")

    reference = next((item for item in instances if _is_master(item["runtime_id"])), instances[0] if instances else None)
    passes = [] if reference is None else _pass_summaries(str(reference["runtime_id"]))
    return {
        "transport_ready": bool(instances) and len(supported) == len(instances),
        "song_memory_ready": any(item["remembered_bin_count"] > 0 for item in instances),
        "instance_count": len(instances),
        "transport_supported_count": len(supported),
        "epoch_counters_consistent": len(epochs_now) <= 1,
        "max_estimated_analysis_lag_ms": None if not lag_values else round(max(lag_values), 3),
        "max_dropped_blocks": 0 if not dropped else max(dropped),
        "reference_instance": reference,
        "continuous_passes": passes,
        "instances": instances,
        "warnings": warnings,
        "semantics": {
            "transport_epoch": "Instance-local continuous playback pass. Playback start, seek, loop jump, or another detected discontinuity starts a new epoch and resets pass-dependent Analyzer state.",
            "song_memory": "One-second in-memory DAW-time bins retained independently of LLM response latency and queryable at coarser resolutions.",
            "coverage_ratio": "Fraction of requested DAW time represented by observed 100 ms timeline slots; missing slots remain missing after coarse aggregation.",
            "estimated_analysis_lag_ms": "Analyzer FIFO/window backlog estimate, not network, tool-call, or LLM latency.",
        },
    }


@core.mcp.tool()
def audio_song_timeline(
    track: str,
    resolution_seconds: int = 5,
    transport_epoch: int | None = None,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    max_bins: int = 240,
) -> dict[str, Any]:
    """Return one track's remembered DAW-time timeline for one playback pass."""
    runtime_id = core._resolve_track(track)
    resolution = min(RESOLUTIONS_SECONDS, key=lambda value: abs(value - int(resolution_seconds)))
    max_bins = max(1, min(int(max_bins), 500))
    epochs = _available_epochs(runtime_id)
    if not epochs:
        return {
            "available": False,
            "id": runtime_id,
            "track": _display_name(runtime_id),
            "reason": "No transport-aligned song-memory bins have been captured. Start DAW playback with an Analyzer exposing protocol 1.2 transport fields.",
        }

    epoch = epochs[-1] if transport_epoch is None else int(transport_epoch)
    rows = _bins_for(runtime_id, epoch)
    if not rows:
        return {
            "available": False,
            "id": runtime_id,
            "track": _display_name(runtime_id),
            "requested_transport_epoch": epoch,
            "available_epochs": epochs[-12:],
            "reason": "The requested transport epoch is not present in retained song memory.",
        }

    if start_seconds is not None:
        rows = [row for row in rows if float(row["end_seconds"]) > float(start_seconds)]
    if end_seconds is not None:
        rows = [row for row in rows if float(row["start_seconds"]) < float(end_seconds)]
    if not rows:
        return {
            "available": False,
            "id": runtime_id,
            "track": _display_name(runtime_id),
            "transport_epoch": epoch,
            "reason": "No retained timeline bins overlap the requested DAW-time range.",
        }

    grouped: OrderedDict[int, list[dict[str, Any]]] = OrderedDict()
    for row in rows:
        group = int(math.floor(float(row["start_seconds"]) / resolution))
        grouped.setdefault(group, []).append(row)

    result_bins: list[dict[str, Any]] = []
    for group, group_rows in list(grouped.items())[:max_bins]:
        group_start = float(group * resolution)
        result_bins.append(_finalize_rows(
            group_rows,
            start_seconds=group_start,
            end_seconds=group_start + resolution,
            expected_seconds=float(resolution),
        ))

    return {
        "available": True,
        "id": runtime_id,
        "track": _display_name(runtime_id),
        "selector": _binding_selector(runtime_id),
        "transport_epoch": epoch,
        "available_epochs": epochs[-12:],
        "resolution_seconds": resolution,
        "returned_bins": len(result_bins),
        "truncated": len(grouped) > max_bins,
        "bins": result_bins,
        "note": "Timeline memory is transport-anchored and survives LLM/tool latency inside the running MCP session. coverage_ratio preserves missing 100 ms slots when bins are aggregated.",
    }


@core.mcp.tool()
def audio_song_overview(transport_epoch: int | None = None, max_tracks: int = 32) -> dict[str, Any]:
    """Summarize a remembered continuous song pass across Analyzer tracks."""
    max_tracks = max(1, min(int(max_tracks), 64))
    with core._lock:
        runtime_ids = list(core._tracks)
    runtime_ids = sorted(runtime_ids, key=_runtime_sort_key)[:max_tracks]

    tracks: list[dict[str, Any]] = []
    selected_epochs: set[int] = set()
    for runtime_id in runtime_ids:
        epochs = _available_epochs(runtime_id)
        if not epochs:
            continue
        epoch = epochs[-1] if transport_epoch is None else int(transport_epoch)
        rows = _bins_for(runtime_id, epoch)
        if not rows:
            continue
        summary = _finalize_rows(rows)
        summary.update({
            "runtime_id": runtime_id,
            "selector": _binding_selector(runtime_id),
            "display_name": _display_name(runtime_id),
            "is_master": _is_master(runtime_id),
            "observed_bins": len(rows),
            "available_epochs": epochs[-12:],
        })
        tracks.append(summary)
        selected_epochs.add(epoch)

    if not tracks:
        return {"available": False, "reason": "No transport-aligned song memory is available for the requested pass."}

    start = min(float(item["start_seconds"]) for item in tracks)
    end = max(float(item["end_seconds"]) for item in tracks)
    master = next((item for item in tracks if item["is_master"]), None)
    lag_values = [
        float(item["data_quality"]["max_estimated_analysis_lag_ms"])
        for item in tracks
        if item["data_quality"]["max_estimated_analysis_lag_ms"] is not None
    ]
    warnings: list[str] = []
    if transport_epoch is None and len(selected_epochs) > 1:
        warnings.append("Latest instance-local transport epochs differ. Compare DAW-time spans before treating the rows as one exact synchronized pass.")
    if lag_values and max(lag_values) >= 250.0:
        warnings.append("Some remembered evidence was captured with >=250 ms estimated Analyzer backlog; prefer coarse section/pass judgments over transient-level timing claims.")
    partial = [item["selector"] for item in tracks if float(item["data_quality"].get("coverage_ratio") or 0.0) < 0.9]
    if partial:
        warnings.append("Some tracks have <90% timeline coverage for their remembered span; missing time remains explicit and must not be treated as measured silence.")

    return {
        "available": True,
        "requested_transport_epoch": transport_epoch,
        "instance_epochs_consistent": len(selected_epochs) <= 1,
        "selected_transport_epochs": sorted(selected_epochs),
        "span_seconds": round(max(0.0, end - start), 3),
        "start_seconds": round(start, 3),
        "end_seconds": round(end, 3),
        "track_count": len(tracks),
        "master": master,
        "tracks": tracks,
        "warnings": warnings,
        "note": "Latency-resilient whole-pass summary from retained one-second DAW-time bins. It does not infer Verse/Chorus labels yet; section detection is a later layer on the same timeline.",
    }
