#!/usr/bin/env python3
"""V0.9 music-semantic measurement layer for AI Audio Analyzer MCP.

This module wraps the V0.8 append-only parser, attaches the V0.9 chroma and
single-F0 harmonic-alignment tail, and registers tonal-profile/comparison tools
on the shared MCP server.

The outputs are audio-domain evidence only. Chroma is a 12-TET pitch-class
power distribution derived from the Mid spectrum. Tonal-center candidates use
explicit major/minor key-profile correlations and always expose ranking margin
and evidence quality. The harmonic metric is a single-F0 spectral-alignment
heuristic, not a pitch tracker, source separator, chord detector, or audibility
probability.
"""

from __future__ import annotations

import math
import statistics
import time
from typing import Any

import server as core
import stereo_tools as stereo
import temporal_tools as temporal

DEFAULT_SECONDS = 8.0
NUM_CHROMA_BINS = 12
PITCH_CLASS_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
CHROMA_MIN_HZ = 80.0
CHROMA_MAX_HZ = 5000.0

# Krumhansl-Kessler key profiles. They are used here only as explicit
# correlation templates for ranking tonal-center evidence from aggregated
# chroma. The returned score is not a probability or a ground-truth key label.
MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

V09_START = stereo.V08_START + stereo.V08_FIELD_COUNT
V09_FIELD_COUNT = NUM_CHROMA_BINS + 3 + 1

_ORIGINAL_ON_FRAME = core._on_frame


def on_frame_v09(address: str, *args: Any) -> None:
    """Parse V0.8 and older fields first, then attach the append-only V0.9 tail."""
    _ORIGINAL_ON_FRAME(address, *args)

    if len(args) < V09_START + V09_FIELD_COUNT:
        return

    runtime_id = str(args[temporal.V03_START + 3]).strip()
    if not runtime_id:
        return

    try:
        chroma = [max(0.0, float(value)) for value in args[V09_START : V09_START + NUM_CHROMA_BINS]]
        scalar_start = V09_START + NUM_CHROMA_BINS
        chroma_energy_ratio = max(0.0, min(1.0, float(args[scalar_start])))
        harmonic_ratio = max(0.0, min(1.0, float(args[scalar_start + 1])))
        harmonic_f0_candidate_hz = max(0.0, float(args[scalar_start + 2]))
        schema_version = str(args[scalar_start + 3]).strip() or "0.9"
    except (TypeError, ValueError):
        return

    chroma_sum = sum(chroma)
    if chroma_sum > 1.0e-12:
        chroma = [value / chroma_sum for value in chroma]

    with core._lock:
        frame = core._tracks.get(runtime_id)
        if frame is None:
            return

        active = bool(frame.get("signal_present"))
        valid = bool(active and chroma_sum > 1.0e-12 and chroma_energy_ratio > 1.0e-9)
        frame["schema_version"] = schema_version
        frame["semantic_v09_supported"] = True
        frame["semantic_v09_valid"] = valid
        frame["chroma_pitch_class_order"] = list(PITCH_CLASS_NAMES)
        frame["chroma"] = chroma if valid else None
        frame["chroma_energy_ratio"] = chroma_energy_ratio if valid else None
        frame["single_f0_harmonic_energy_ratio"] = harmonic_ratio if valid else None
        frame["harmonic_f0_candidate_hz"] = harmonic_f0_candidate_hz if valid and harmonic_f0_candidate_hz > 0.0 else None


def _clamp_seconds(seconds: float) -> float:
    return max(1.0, min(float(seconds), 60.0))


def _history(track: str, seconds: float) -> tuple[str, list[dict[str, Any]], dict[str, Any] | None]:
    runtime_id = core._resolve_track(track)
    cutoff = time.time() - seconds
    with core._lock:
        frames = [
            dict(frame)
            for frame in core._history.get(runtime_id, ())
            if float(frame.get("_received_at", 0.0)) >= cutoff
        ]
        binding = core._binding_public(core._bindings.get(runtime_id))
    return runtime_id, frames, binding


def _mean(values: list[float]) -> float | None:
    usable = [float(value) for value in values if math.isfinite(float(value))]
    if not usable:
        return None
    return sum(usable) / len(usable)


def _normalized_chroma(frames: list[dict[str, Any]]) -> list[float] | None:
    accumulator = [0.0] * NUM_CHROMA_BINS
    total_weight = 0.0

    for frame in frames:
        chroma = frame.get("chroma")
        coverage = frame.get("chroma_energy_ratio")
        if not isinstance(chroma, list) or len(chroma) != NUM_CHROMA_BINS or coverage is None:
            continue
        try:
            values = [max(0.0, float(value)) for value in chroma]
            weight = max(1.0e-6, float(coverage))
        except (TypeError, ValueError):
            continue
        if not all(math.isfinite(value) for value in values) or not math.isfinite(weight):
            continue
        local_sum = sum(values)
        if local_sum <= 1.0e-12:
            continue
        for index, value in enumerate(values):
            accumulator[index] += (value / local_sum) * weight
        total_weight += weight

    if total_weight <= 0.0:
        return None

    result = [value / total_weight for value in accumulator]
    total = sum(result)
    if total <= 1.0e-12:
        return None
    return [value / total for value in result]


def _normalized_entropy(distribution: list[float]) -> float:
    entropy = 0.0
    for value in distribution:
        if value > 0.0:
            entropy -= value * math.log(value)
    return max(0.0, min(1.0, entropy / math.log(NUM_CHROMA_BINS)))


def _pearson(values: list[float], template: list[float]) -> float | None:
    if len(values) != len(template) or len(values) < 2:
        return None
    mean_a = sum(values) / len(values)
    mean_b = sum(template) / len(template)
    centered_a = [value - mean_a for value in values]
    centered_b = [value - mean_b for value in template]
    denom_a = sum(value * value for value in centered_a)
    denom_b = sum(value * value for value in centered_b)
    denom = math.sqrt(max(0.0, denom_a * denom_b))
    if denom <= 1.0e-18:
        return None
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(centered_a, centered_b)) / denom))


def _rotated_profile(profile: list[float], tonic: int) -> list[float]:
    return [profile[(pitch_class - tonic) % NUM_CHROMA_BINS] for pitch_class in range(NUM_CHROMA_BINS)]


def _tonal_center_candidates(chroma: list[float]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for tonic, tonic_name in enumerate(PITCH_CLASS_NAMES):
        for mode, profile in (("major", MAJOR_PROFILE), ("minor", MINOR_PROFILE)):
            score = _pearson(chroma, _rotated_profile(profile, tonic))
            candidates.append(
                {
                    "tonic": tonic_name,
                    "mode": mode,
                    "label": f"{tonic_name} {mode}",
                    "profile_correlation": None if score is None else round(score, 6),
                }
            )
    candidates.sort(
        key=lambda item: float("-inf") if item["profile_correlation"] is None else float(item["profile_correlation"]),
        reverse=True,
    )
    return candidates


def _cosine_similarity(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    dot = sum(x * y for x, y in zip(a, b))
    denom = math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
    if denom <= 1.0e-18:
        return None
    return max(0.0, min(1.0, dot / denom))


def _js_divergence(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    total_a = sum(max(0.0, value) for value in a)
    total_b = sum(max(0.0, value) for value in b)
    if total_a <= 1.0e-18 or total_b <= 1.0e-18:
        return None
    p = [max(0.0, value) / total_a for value in a]
    q = [max(0.0, value) / total_b for value in b]
    m = [(x + y) * 0.5 for x, y in zip(p, q)]

    def kl(source: list[float], midpoint: list[float]) -> float:
        total = 0.0
        for value, mid in zip(source, midpoint):
            if value > 0.0 and mid > 0.0:
                total += value * math.log2(value / mid)
        return total

    return max(0.0, min(1.0, 0.5 * (kl(p, m) + kl(q, m))))


def _build_profile(track: str, seconds: float) -> dict[str, Any]:
    seconds = _clamp_seconds(seconds)
    runtime_id, frames, binding = _history(track, seconds)

    if not frames:
        return {
            "available": False,
            "id": runtime_id,
            "binding": binding,
            "window_seconds": seconds,
            "reason": "No Analyzer frames are available in the requested window.",
        }

    supported = [frame for frame in frames if bool(frame.get("semantic_v09_supported"))]
    if not supported:
        return {
            "available": False,
            "id": runtime_id,
            "track": frames[-1].get("track"),
            "binding": binding,
            "window_seconds": seconds,
            "reason": "Music-semantic descriptors require AI Audio Analyzer VST3 0.9+ frames.",
        }

    valid = [frame for frame in supported if bool(frame.get("semantic_v09_valid"))]
    if not valid:
        return {
            "available": False,
            "id": runtime_id,
            "track": frames[-1].get("track"),
            "binding": binding,
            "window_seconds": seconds,
            "semantic_v09_supported": True,
            "active_ratio": round(sum(bool(frame.get("signal_present")) for frame in frames) / len(frames), 4),
            "reason": "No chroma-valid active frames occurred in the requested window.",
        }

    chroma = _normalized_chroma(valid)
    if chroma is None:
        return {
            "available": False,
            "id": runtime_id,
            "track": frames[-1].get("track"),
            "binding": binding,
            "window_seconds": seconds,
            "reason": "Chroma frames were present but could not be aggregated into a valid distribution.",
        }

    candidates = _tonal_center_candidates(chroma)
    usable_candidates = [item for item in candidates if item["profile_correlation"] is not None]
    top_candidates = usable_candidates[:5]
    top2_margin = None
    if len(usable_candidates) >= 2:
        top2_margin = float(usable_candidates[0]["profile_correlation"]) - float(usable_candidates[1]["profile_correlation"])

    ranked_pitch_classes = sorted(
        [
            {"pitch_class": name, "normalized_power": round(float(value), 6)}
            for name, value in zip(PITCH_CLASS_NAMES, chroma)
        ],
        key=lambda item: item["normalized_power"],
        reverse=True,
    )

    coverage_values = [
        float(frame["chroma_energy_ratio"])
        for frame in valid
        if frame.get("chroma_energy_ratio") is not None
    ]
    harmonic_values = [
        float(frame["single_f0_harmonic_energy_ratio"])
        for frame in valid
        if frame.get("single_f0_harmonic_energy_ratio") is not None
    ]
    f0_candidates = [
        float(frame["harmonic_f0_candidate_hz"])
        for frame in valid
        if frame.get("harmonic_f0_candidate_hz") is not None and float(frame["harmonic_f0_candidate_hz"]) > 0.0
    ]
    coverage_mean = _mean(coverage_values)
    harmonic_mean = _mean(harmonic_values)
    entropy = _normalized_entropy(chroma)

    harmonic_block: dict[str, Any] = {
        "single_f0_harmonic_energy_ratio_mean": None if harmonic_mean is None else round(harmonic_mean, 6),
        "single_f0_harmonic_energy_ratio_max": None if not harmonic_values else round(max(harmonic_values), 6),
        "f0_candidate_hz_median": None if not f0_candidates else round(float(statistics.median(f0_candidates)), 4),
        "f0_candidate_hz_min": None if not f0_candidates else round(min(f0_candidates), 4),
        "f0_candidate_hz_max": None if not f0_candidates else round(max(f0_candidates), 4),
        "interpretation": (
            "Single-F0 spectral alignment evidence only. Candidate frequency may jump by octave/subharmonic, "
            "especially for polyphonic, noisy, percussive, or weak-fundamental material; do not treat it as a note label."
        ),
    }

    return {
        "available": True,
        "id": runtime_id,
        "track": frames[-1].get("track"),
        "binding": binding,
        "window_seconds": seconds,
        "frames": len(frames),
        "supported_frames": len(supported),
        "valid_frames": len(valid),
        "active_ratio": round(sum(bool(frame.get("signal_present")) for frame in frames) / len(frames), 4),
        "chroma": {
            "pitch_class_order": list(PITCH_CLASS_NAMES),
            "normalized_power": [round(value, 6) for value in chroma],
            "top_pitch_classes": ranked_pitch_classes[:5],
            "normalized_entropy": round(entropy, 6),
            "analysis_range_hz": [CHROMA_MIN_HZ, CHROMA_MAX_HZ],
            "aggregation": "mean of per-frame normalized Mid-spectrum chroma weighted by chroma_energy_ratio",
        },
        "tonal_center_evidence": {
            "method": "Krumhansl-Kessler major/minor profile Pearson correlation",
            "top_candidates": top_candidates,
            "top2_margin": None if top2_margin is None else round(top2_margin, 6),
            "candidate_count": len(usable_candidates),
            "probability": False,
        },
        "harmonic_alignment": harmonic_block,
        "evidence_quality": {
            "mean_chroma_energy_ratio": None if coverage_mean is None else round(coverage_mean, 6),
            "normalized_pitch_class_entropy": round(entropy, 6),
            "tonal_center_top2_margin": None if top2_margin is None else round(top2_margin, 6),
            "valid_frame_ratio": round(len(valid) / len(frames), 6),
            "active_ratio": round(sum(bool(frame.get("signal_present")) for frame in frames) / len(frames), 6),
        },
        "note": (
            "Audio-only music-semantic evidence. Chroma uses nearest 12-TET pitch-class accumulation from the "
            "80 Hz-5 kHz Mid spectrum. Tonal-center candidates are profile correlations, not ground-truth key labels. "
            "Prefer DAW/MIDI project data when exact written notes or key metadata are available."
        ),
    }


@core.mcp.tool()
def audio_tonal_profile(track: str, seconds: float = DEFAULT_SECONDS) -> dict[str, Any]:
    """Return windowed chroma, tonal-center ranking, and harmonic-alignment evidence."""
    return _build_profile(track, seconds)


@core.mcp.tool()
def audio_tonal_compare(track_a: str, track_b: str, seconds: float = DEFAULT_SECONDS) -> dict[str, Any]:
    """Compare two tracks' audio-domain pitch-class distributions without prescribing a musical action."""
    profile_a = _build_profile(track_a, seconds)
    profile_b = _build_profile(track_b, seconds)

    if not profile_a.get("available") or not profile_b.get("available"):
        return {
            "available": False,
            "track_a": profile_a,
            "track_b": profile_b,
            "window_seconds": _clamp_seconds(seconds),
            "reason": "Both tracks require valid V0.9 chroma evidence in the requested window.",
        }

    chroma_a = [float(value) for value in profile_a["chroma"]["normalized_power"]]
    chroma_b = [float(value) for value in profile_b["chroma"]["normalized_power"]]
    cosine = _cosine_similarity(chroma_a, chroma_b)
    divergence = _js_divergence(chroma_a, chroma_b)
    deltas = [round(b - a, 6) for a, b in zip(chroma_a, chroma_b)]

    tonal_a = profile_a["tonal_center_evidence"]["top_candidates"]
    tonal_b = profile_b["tonal_center_evidence"]["top_candidates"]
    harmonic_a = profile_a["harmonic_alignment"].get("single_f0_harmonic_energy_ratio_mean")
    harmonic_b = profile_b["harmonic_alignment"].get("single_f0_harmonic_energy_ratio_mean")

    return {
        "available": True,
        "window_seconds": _clamp_seconds(seconds),
        "track_a": {
            "id": profile_a["id"],
            "track": profile_a["track"],
            "binding": profile_a["binding"],
            "top_tonal_center_candidate": tonal_a[0] if tonal_a else None,
        },
        "track_b": {
            "id": profile_b["id"],
            "track": profile_b["track"],
            "binding": profile_b["binding"],
            "top_tonal_center_candidate": tonal_b[0] if tonal_b else None,
        },
        "pitch_class_comparison": {
            "cosine_similarity": None if cosine is None else round(cosine, 6),
            "jensen_shannon_divergence": None if divergence is None else round(divergence, 6),
            "pitch_class_order": list(PITCH_CLASS_NAMES),
            "normalized_power_delta_b_minus_a": deltas,
        },
        "harmonic_alignment_delta_b_minus_a": (
            None if harmonic_a is None or harmonic_b is None else round(float(harmonic_b) - float(harmonic_a), 6)
        ),
        "evidence_quality": {
            "track_a": profile_a["evidence_quality"],
            "track_b": profile_b["evidence_quality"],
        },
        "note": (
            "Similarity/divergence describe audio-domain pitch-class distributions only. They do not imply harmonic "
            "compatibility, correctness, consonance, arrangement quality, or a required mixing/production action."
        ),
    }
