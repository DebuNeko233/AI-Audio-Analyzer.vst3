#!/usr/bin/env python3
"""Synthetic MCP regression suite used by development CI.

This is repository test code, not shipped in beginner Releases.
"""

from __future__ import annotations

import asyncio
import copy
import sys
from importlib.metadata import version

sys.path.insert(0, "bridge")

import analyzer_core as core  # noqa: E402
import masking_tools as masking  # noqa: E402
import project_tools as project  # noqa: E402
import semantic_tools as semantic  # noqa: E402
import server as entry  # noqa: E402
import stereo_tools as stereo  # noqa: E402
import temporal_tools as temporal  # noqa: E402
import verification_tools as verification  # noqa: E402
from mcp.server import MCPServer  # noqa: E402


def synthetic_frame(
    name: str,
    runtime_id: str,
    timestamp: float,
    bands: list[float],
    *,
    peak: float = -14.0,
    rms: float = -24.0,
    flux: float = 0.08,
    rise: float = 1.0,
    side_offset_db: float = -12.0,
    side_to_mid_db: float = -9.0,
    negative_cross: float = 0.08,
    low_corr: float = 0.92,
    low_side_to_mid_db: float = -15.0,
    chroma: list[float],
    chroma_energy_ratio: float = 0.72,
    harmonic_ratio: float = 0.58,
    harmonic_f0_hz: float = 130.81,
) -> list[object]:
    prefix: list[object] = [
        name,
        48000.0,
        timestamp,
        peak,
        rms,
        peak - rms,
        700.0,
        6000.0,
        0.15,
        0.75,
        0.25,
    ] + list(bands)
    v02: list[object] = [-18.0, -14.0, -1.0, -0.5] + [0.85] * 8
    v03: list[object] = [1, peak, 0.0, runtime_id]
    v06: list[object] = [0.1, flux * 0.5, flux, rise, -28.0, "0.6"]
    side_bands = [float(value) + side_offset_db for value in bands]
    band_side_mid = [-18.0, -16.0, -14.0, -12.0, -10.0, -8.0, -6.0, -4.0]
    v08: list[object] = [
        rms - 1.0,
        rms - 10.0,
        side_to_mid_db,
        negative_cross,
        low_corr,
        low_side_to_mid_db,
    ] + side_bands + band_side_mid + ["0.8"]
    v09: list[object] = list(chroma) + [
        chroma_energy_ratio,
        harmonic_ratio,
        harmonic_f0_hz,
        "0.9",
    ]
    return prefix + v02 + v03 + v06 + v08 + v09


def reset_state() -> None:
    with core._lock:
        core._tracks.clear()
        core._history.clear()
        core._bindings.clear()
        core._identify_events.clear()
        core._identify_sequence = 0
    with project._snapshot_lock:
        project._project_snapshots.clear()
    with verification._verification_lock:
        verification._verifications.clear()


def bind(runtime_id: str, name: str, track_index: int, slot: int = 9) -> None:
    core._on_identify(
        "/aianalyzer/identify",
        runtime_id,
        name,
        11.0 + track_index * 0.01,
        "0.4",
    )
    result = core.audio_bind_last_identified(track_index, name, slot)
    assert result["selector"] == f"mixer:{track_index}/slot:{slot}"
    assert core._resolve_track(result["selector"]) == runtime_id


def main() -> None:
    mcp_sdk_version = version("mcp")
    assert mcp_sdk_version.split(".", 1)[0] == "2", mcp_sdk_version
    assert isinstance(entry.mcp, MCPServer)
    assert entry.mcp is core.mcp
    assert entry.MCP_VERSION == "1.0"
    assert entry.OSC_PROTOCOL_VERSION == "0.9"

    names = {tool.name for tool in asyncio.run(entry.mcp.list_tools())}
    assert names == entry.EXPECTED_TOOLS, sorted(names ^ entry.EXPECTED_TOOLS)
    assert len(names) == 27

    reset_state()

    major = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    total_major = sum(major)
    chroma_c_major = [value / total_major for value in major]
    g_major_raw = major[5:] + major[:5]
    total_g = sum(g_major_raw)
    chroma_g_major = [value / total_g for value in g_major_raw]

    shape_a = [-55.0 + min(i, 12) * 1.8 for i in range(32)]
    shape_b = [value + 2.0 for value in shape_a]

    for i in range(8):
        swing = [0.0, 3.0, 8.0, 4.0, -1.0, 6.0, 2.0, 0.0][i]
        bands_a = [value + swing for value in shape_a]
        bands_b = [value + swing * 0.9 + 1.5 for value in shape_b]
        flux = 0.24 if i in (2, 5) else 0.06
        rise = 5.0 if i in (2, 5) else 0.8
        core._on_frame(
            "/aianalyzer/frame",
            *synthetic_frame(
                "Bass A",
                "uuid-a",
                10.0 + i * 0.1,
                bands_a,
                flux=flux,
                rise=rise,
                negative_cross=0.05 + i * 0.005,
                low_corr=0.94 - i * 0.005,
                chroma=chroma_c_major,
                chroma_energy_ratio=0.74,
                harmonic_ratio=0.62 - i * 0.01,
                harmonic_f0_hz=130.81,
            ),
        )
        core._on_frame(
            "/aianalyzer/frame",
            *synthetic_frame(
                "Bass B",
                "uuid-b",
                10.01 + i * 0.1,
                bands_b,
                peak=-16.0,
                rms=-26.0,
                flux=flux * 0.9,
                rise=rise * 0.9,
                side_offset_db=-7.0,
                side_to_mid_db=-5.0,
                negative_cross=0.22 + i * 0.01,
                low_corr=0.70 - i * 0.01,
                low_side_to_mid_db=-9.0,
                chroma=chroma_g_major,
                chroma_energy_ratio=0.68,
                harmonic_ratio=0.48 + i * 0.005,
                harmonic_f0_hz=98.0,
            ),
        )

    assert core._tracks["uuid-a"]["temporal_supported"] is True
    assert core._tracks["uuid-a"]["stereo_v08_supported"] is True
    assert core._tracks["uuid-a"]["semantic_v09_supported"] is True
    assert core._tracks["uuid-a"]["semantic_v09_valid"] is True
    assert core._tracks["uuid-a"]["schema_version"] == "0.9"
    assert len(core._tracks["uuid-a"]["side_bands_db"]) == 32
    assert len(core._tracks["uuid-a"]["band_side_to_mid_db"]) == 8
    assert len(core._tracks["uuid-a"]["chroma"]) == 12
    assert abs(sum(core._tracks["uuid-a"]["chroma"]) - 1.0) < 1e-6

    bind("uuid-a", "Bass A", 7)
    bind("uuid-b", "Bass B", 8)
    project_status = project.audio_project_status()
    assert project_status["project_ready"] is True
    assert project_status["bound_count"] == 2

    profile = temporal.audio_temporal_profile("uuid-a", 5.0)
    assert profile["available"] is True
    assert profile["onset_candidate_frames"] >= 1

    temporal_pair = temporal.audio_temporal_compare(
        "uuid-a", "uuid-b", 5.0, 40.0, 160.0, 80.0
    )
    assert temporal_pair["available"] is True
    assert temporal_pair["aligned_pairs"] >= 6
    assert temporal_pair["normalized_band_temporal_overlap"] is not None

    evidence = masking.audio_masking_evidence("uuid-a", "uuid-b", 5.0, 80.0, 6)
    assert evidence["available"] is True
    assert evidence["auditory_band_model"]["type"] == "equal-erb-rate-rebinning"
    assert evidence["auditory_band_model"]["filterbank"] is False
    assert len(evidence["strongest_regions"]) == 6
    assert evidence["strongest_regions"][0]["combined_evidence_a_over_b"] is not None
    assert evidence["masking_evidence_score"] is not None

    scan = masking.audio_project_masking_scan(5.0, 4, 80.0)
    assert scan["candidate_pair_count"] >= 1
    assert scan["pairs"][0]["top_region"] is not None

    stereo_a = stereo.audio_stereo_profile("uuid-a", 5.0)
    stereo_b = stereo.audio_stereo_profile("uuid-b", 5.0)
    assert stereo_a["available"] is True
    assert stereo_b["available"] is True
    assert len(stereo_a["mid_spectrum_db"]) == 32
    assert len(stereo_a["side_spectrum_db"]) == 32
    assert len(stereo_a["frequency_dependent_stereo"]) == 8
    assert stereo_a["full_band"]["decorrelation_proxy_mean"] is not None
    assert stereo_a["full_band"]["negative_cross_energy_ratio_mean"] is not None
    assert stereo_b["full_band"]["side_to_mid_db"] > stereo_a["full_band"]["side_to_mid_db"]

    stereo_delta = stereo.audio_stereo_compare("uuid-a", "uuid-b", 5.0)
    assert stereo_delta["available"] is True
    assert stereo_delta["deltas_b_minus_a"]["side_to_mid_db"] is not None
    assert len(stereo_delta["frequency_dependent_deltas"]) == 8

    tonal_a = semantic.audio_tonal_profile("uuid-a", 5.0)
    tonal_b = semantic.audio_tonal_profile("uuid-b", 5.0)
    assert tonal_a["available"] is True
    assert tonal_b["available"] is True
    assert len(tonal_a["chroma"]["normalized_power"]) == 12
    assert tonal_a["tonal_center_evidence"]["top_candidates"][0]["label"] == "C major"
    assert tonal_a["tonal_center_evidence"]["top2_margin"] is not None
    assert tonal_a["chroma"]["normalized_entropy"] is not None
    assert tonal_a["harmonic_alignment"]["single_f0_harmonic_energy_ratio_mean"] is not None

    tonal_delta = semantic.audio_tonal_compare("uuid-a", "uuid-b", 5.0)
    assert tonal_delta["available"] is True
    assert tonal_delta["pitch_class_comparison"]["cosine_similarity"] is not None
    assert tonal_delta["pitch_class_comparison"]["jensen_shannon_divergence"] is not None
    assert len(tonal_delta["pitch_class_comparison"]["normalized_power_delta_b_minus_a"]) == 12

    before = project.audio_capture_snapshot("before", 5.0)
    assert before["track_count"] == 2
    assert project.audio_list_snapshots()["count"] == 1

    verification_started = verification.audio_begin_verification(
        "CI gain/readback check",
        5.0,
        ["mixer:7/slot:9", "mixer:8/slot:9"],
    )
    assert verification_started["ready_for_external_change"] is True
    verification_id = verification_started["verification_id"]

    for i in range(4):
        core._on_frame(
            "/aianalyzer/frame",
            *synthetic_frame(
                "Bass A",
                "uuid-a",
                12.0 + i * 0.1,
                [value + 1.0 for value in shape_a],
                peak=-12.5,
                rms=-22.5,
                chroma=chroma_c_major,
                harmonic_ratio=0.60,
            ),
        )
        core._on_frame(
            "/aianalyzer/frame",
            *synthetic_frame(
                "Bass B",
                "uuid-b",
                12.01 + i * 0.1,
                [value - 0.5 for value in shape_b],
                peak=-17.0,
                rms=-27.0,
                side_offset_db=-7.0,
                side_to_mid_db=-5.0,
                negative_cross=0.22,
                low_corr=0.70,
                low_side_to_mid_db=-9.0,
                chroma=chroma_g_major,
                harmonic_ratio=0.50,
                harmonic_f0_hz=98.0,
            ),
        )

    verification_done = verification.audio_complete_verification(
        verification_id,
        0.0,
        "Synthetic external gain change",
        "FL Studio control MCP readback confirmed the intended parameter values.",
    )
    result = verification_done["result"]
    assert result["comparison"]["controlled_comparison"] is True
    assert result["comparison"]["comparability"]["topology_unchanged"] is True
    assert result["external_change"]["readback_supplied"] is True
    assert result["audit"]["measurement_only"] is True
    assert len(result["comparison"]["targets"]) == 2
    assert result["comparison"]["targets"][0]["delta"]["rms_db"] is not None

    verification_status = verification.audio_verification_status(verification_id)
    assert verification_status["status"] == "completed"
    assert verification_status["result"]["comparison"]["controlled_comparison"] is True
    assert verification.audio_verification_status()["count"] == 1

    before_state = copy.deepcopy(verification._verifications[verification_id]["before_state"])
    good_after_state = copy.deepcopy(verification._verifications[verification_id]["after_state"])

    topology_drift_state = copy.deepcopy(good_after_state)
    topology_drift_state["tracks"].pop("mixer:8/slot:9")
    topology_drift = verification._comparison_for_states(
        before_state,
        topology_drift_state,
        ["mixer:7/slot:9", "mixer:8/slot:9"],
    )
    assert topology_drift["controlled_comparison"] is False
    assert topology_drift["comparability"]["topology_unchanged"] is False
    assert "mixer:8/slot:9" in topology_drift["comparability"]["missing_targets"]

    coverage_mismatch_state = copy.deepcopy(good_after_state)
    coverage_mismatch_state["tracks"]["mixer:7/slot:9"]["active_ratio"] = 0.1
    coverage_mismatch = verification._comparison_for_states(
        before_state,
        coverage_mismatch_state,
        ["mixer:7/slot:9"],
    )
    assert coverage_mismatch["controlled_comparison"] is False
    assert "mixer:7/slot:9" in coverage_mismatch["comparability"]["coverage_mismatch_targets"]

    print(
        f"AI Audio Analyzer MCP SDK {mcp_sdk_version}: {len(names)} tools; "
        "V0.4 mapping + V0.5 project A/B + V0.6 temporal + V0.7 masking + "
        "V0.8 stereo + V0.9 tonal + V1.0 closed-loop verification regressions OK"
    )


if __name__ == "__main__":
    main()
