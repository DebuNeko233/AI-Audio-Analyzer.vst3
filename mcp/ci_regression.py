#!/usr/bin/env python3
"""Synthetic MCP regression suite used by development CI.

This is repository test code, not shipped in beginner Releases.
"""

from __future__ import annotations

import asyncio
import copy
import sys
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyzer_core as core  # noqa: E402
import masking_tools as masking  # noqa: E402
import performance_tools as performance  # noqa: E402
import project_tools as project  # noqa: E402
import section_tools as structure  # noqa: E402
import semantic_tools as semantic  # noqa: E402
import server as entry  # noqa: E402
import song_tools as song  # noqa: E402
import stereo_tools as stereo  # noqa: E402
import temporal_tools as temporal  # noqa: E402
import track_story_tools as story  # noqa: E402
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
    profile_index: int = 3,
    feature_mask: int = 63,
    worker_load_ratio: float = 0.22,
    fifo_fill_ratio: float = 0.01,
    fft_runs_per_second: float = 46.8,
    semantic_runs_per_second: float = 5.0,
    signal_present: bool = True,
    transport_supported: bool = True,
    transport_time_seconds: float | None = None,
    transport_ppq_position: float | None = None,
    transport_bpm: float = 120.0,
    transport_epoch: int = 1,
    transport_is_playing: bool = True,
    transport_is_recording: bool = False,
    transport_is_looping: bool = False,
    loop_start_ppq: float = 0.0,
    loop_end_ppq: float = 0.0,
    estimated_analysis_lag_ms: float = 42.0,
    dropped_blocks: int = 0,
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
    v03: list[object] = [1 if signal_present else 0, peak, 0.0, runtime_id]
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
    v11: list[object] = [
        profile_index,
        feature_mask,
        worker_load_ratio,
        fifo_fill_ratio,
        fft_runs_per_second,
        semantic_runs_per_second,
        "1.1",
    ]
    transport_time = timestamp if transport_time_seconds is None else transport_time_seconds
    transport_ppq = transport_time * transport_bpm / 60.0 if transport_ppq_position is None else transport_ppq_position
    v12: list[object] = [
        1 if transport_supported else 0,
        transport_time,
        transport_ppq,
        transport_bpm,
        4,
        4,
        1 if transport_is_playing else 0,
        1 if transport_is_recording else 0,
        1 if transport_is_looping else 0,
        loop_start_ppq,
        loop_end_ppq,
        transport_epoch,
        estimated_analysis_lag_ms,
        dropped_blocks,
        "1.2",
    ]
    return prefix + v02 + v03 + v06 + v08 + v09 + v11 + v12


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
    with song._song_lock:
        song._timeline.clear()
    with structure._section_lock:
        structure._section_maps.clear()


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
    assert entry.MCP_VERSION == "1.2"
    assert entry.OSC_PROTOCOL_VERSION == "1.2"
    assert entry.CONTROL_PROTOCOL_VERSION == "1"

    names = {tool.name for tool in asyncio.run(entry.mcp.list_tools())}
    assert names == entry.EXPECTED_TOOLS, sorted(names ^ entry.EXPECTED_TOOLS)
    assert len(names) == 43
    assert "audio_dynamics_distribution" in names

    identity = entry.project_identity.audio_project_identity_status()
    assert identity["stable_project_id"] is None
    assert identity["project_identity_confidence"] == "UNRESOLVED"
    assert identity["runtime_id"]["persistent"] is False
    assert identity["runtime_id"]["stable_when_same_project_is_reopened"] is False
    assert identity["retained_state"]["cross_project_isolation_guaranteed"] is False

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
                worker_load_ratio=0.18,
                fifo_fill_ratio=0.01,
                estimated_analysis_lag_ms=38.0,
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
                worker_load_ratio=0.24,
                fifo_fill_ratio=0.02,
                estimated_analysis_lag_ms=55.0,
            ),
        )

    frame_a = core._tracks["uuid-a"]
    assert frame_a["temporal_supported"] is True
    assert frame_a["stereo_v08_supported"] is True
    assert frame_a["semantic_v09_supported"] is True
    assert frame_a["semantic_v09_valid"] is True
    assert frame_a["adaptive_analysis_supported"] is True
    assert frame_a["analysis_profile"] == "full"
    assert frame_a["analysis_features"]["semantic"] is True
    assert frame_a["transport_v12_supported"] is True
    assert frame_a["transport_epoch"] == 1
    assert frame_a["transport_is_playing"] is True
    assert frame_a["estimated_analysis_lag_ms"] == 38.0
    assert frame_a["schema_version"] == "1.2"
    assert len(frame_a["side_bands_db"]) == 32
    assert len(frame_a["band_side_to_mid_db"]) == 8
    assert len(frame_a["chroma"]) == 12
    assert abs(sum(frame_a["chroma"]) - 1.0) < 1e-6

    bind("uuid-a", "Bass A", 7)
    bind("uuid-b", "Bass B", 8)
    project_status = project.audio_project_status()
    assert project_status["project_ready"] is True
    assert project_status["bound_count"] == 2

    perf_a = performance.audio_analysis_status("mixer:7/slot:9")
    assert perf_a["adaptive_analysis_supported"] is True
    assert perf_a["profile"] == "full"
    assert perf_a["features"]["semantic"] is True
    assert perf_a["control_parameter"]["parameter_id"] == "analysis_profile"
    project_perf = performance.audio_project_performance()
    assert project_perf["instance_count"] == 2
    assert project_perf["profile_counts"]["full"] == 2
    assert project_perf["max_worker_load_ratio"] is not None

    song_status = song.audio_song_status()
    assert song_status["transport_ready"] is True
    assert song_status["song_memory_ready"] is True
    assert song_status["max_estimated_analysis_lag_ms"] == 55.0
    timeline = song.audio_song_timeline("mixer:7/slot:9", 5)
    assert timeline["available"] is True
    assert timeline["transport_epoch"] == 1
    assert timeline["returned_bins"] >= 1
    assert timeline["bins"][0]["data_quality"]["max_estimated_analysis_lag_ms"] == 38.0
    song_overview = song.audio_song_overview()
    assert song_overview["available"] is True
    assert song_overview["track_count"] == 2
    assert song_overview["instance_epochs_consistent"] is True

    temporal_profile = temporal.audio_temporal_profile("uuid-a", 5.0)
    assert temporal_profile["available"] is True
    assert temporal_profile["onset_candidate_frames"] >= 1

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
    assert stereo_b["full_band"]["side_to_mid_db"] > stereo_a["full_band"]["side_to_mid_db"]

    stereo_delta = stereo.audio_stereo_compare("uuid-a", "uuid-b", 5.0)
    assert stereo_delta["available"] is True
    assert stereo_delta["deltas_b_minus_a"]["side_to_mid_db"] is not None

    tonal_a = semantic.audio_tonal_profile("uuid-a", 5.0)
    tonal_b = semantic.audio_tonal_profile("uuid-b", 5.0)
    assert tonal_a["available"] is True
    assert tonal_b["available"] is True
    assert len(tonal_a["chroma"]["normalized_power"]) == 12
    assert tonal_a["tonal_center_evidence"]["top_candidates"][0]["label"] == "C major"
    assert tonal_a["tonal_center_evidence"]["top2_margin"] is not None

    tonal_delta = semantic.audio_tonal_compare("uuid-a", "uuid-b", 5.0)
    assert tonal_delta["available"] is True
    assert tonal_delta["pitch_class_comparison"]["cosine_similarity"] is not None
    assert tonal_delta["pitch_class_comparison"]["jensen_shannon_divergence"] is not None

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
                worker_load_ratio=0.19,
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
                worker_load_ratio=0.25,
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
    assert result["closed_loop_complete"] is True
    assert result["external_change"]["readback_supplied"] is True
    assert len(result["comparison"]["targets"]) == 2

    verification_status = verification.audio_verification_status(verification_id)
    assert verification_status["status"] == "completed"
    assert verification_status["result"]["closed_loop_complete"] is True

    before_state = copy.deepcopy(verification._verifications[verification_id]["before_state"])
    good_after_state = copy.deepcopy(verification._verifications[verification_id]["after_state"])

    topology_drift_state = copy.deepcopy(good_after_state)
    topology_drift_state["tracks"].pop("mixer:8/slot:9")
    topology_drift = verification._comparison_for_states(
        before_state,
        topology_drift_state,
        ["mixer:7/slot:9", "mixer:8/slot:9"],
        baseline_ready=True,
    )
    assert topology_drift["controlled_comparison"] is False
    assert topology_drift["comparability"]["topology_unchanged"] is False

    coverage_mismatch_state = copy.deepcopy(good_after_state)
    coverage_mismatch_state["tracks"]["mixer:7/slot:9"]["active_ratio"] = 0.1
    coverage_mismatch = verification._comparison_for_states(
        before_state,
        coverage_mismatch_state,
        ["mixer:7/slot:9"],
        baseline_ready=True,
    )
    assert coverage_mismatch["controlled_comparison"] is False
    assert "mixer:7/slot:9" in coverage_mismatch["comparability"]["coverage_mismatch_targets"]

    blocked_baseline = verification._comparison_for_states(
        before_state,
        good_after_state,
        ["mixer:7/slot:9"],
        baseline_ready=False,
    )
    assert blocked_baseline["controlled_comparison"] is False
    assert blocked_baseline["comparability"]["baseline_ready"] is False

    # Adaptive-profile validity regression: deliberately provide realistic old
    # tail numbers but declare Eco/core-only. The parser must make disabled
    # evidence unavailable instead of letting downstream tools interpret zeros
    # or stale values as measurements. Transport/core context remains available.
    core._on_frame(
        "/aianalyzer/frame",
        *synthetic_frame(
            "Eco Probe",
            "uuid-eco",
            20.0,
            shape_a,
            chroma=chroma_c_major,
            profile_index=0,
            feature_mask=1,
            worker_load_ratio=0.03,
            fifo_fill_ratio=0.0,
            fft_runs_per_second=0.0,
            semantic_runs_per_second=0.0,
        ),
    )
    eco = core._tracks["uuid-eco"]
    assert eco["analysis_profile"] == "eco"
    assert eco["spectrum_valid"] is False
    assert eco["stereo_valid"] is False
    assert eco["temporal_valid"] is False
    assert eco["semantic_v09_valid"] is False
    assert eco["chroma"] is None
    assert eco["transport_v12_supported"] is True
    eco_status = performance.audio_analysis_status("uuid-eco")
    assert eco_status["features"] == {
        "core": True,
        "loudness": False,
        "spectrum": False,
        "stereo": False,
        "temporal": False,
        "semantic": False,
    }
    assert eco_status["fft_runs_per_second"] == 0.0

    with core._lock:
        core._tracks.pop("uuid-eco", None)
        core._history.pop("uuid-eco", None)
    with song._song_lock:
        song._timeline.pop("uuid-eco", None)

    # New epoch regression: a later continuous pass must remain separately
    # addressable rather than being merged into the previous song timeline.
    core._on_frame(
        "/aianalyzer/frame",
        *synthetic_frame(
            "Bass A",
            "uuid-a",
            30.0,
            shape_a,
            chroma=chroma_c_major,
            transport_epoch=2,
            transport_time_seconds=3.0,
            estimated_analysis_lag_ms=65.0,
        ),
    )
    pass_status = song.audio_song_status()
    bass_a_status = next(item for item in pass_status["instances"] if item["runtime_id"] == "uuid-a")
    assert bass_a_status["remembered_epochs"] == [1, 2]
    second_pass = song.audio_song_timeline("uuid-a", 1, 2)
    assert second_pass["available"] is True
    assert second_pass["transport_epoch"] == 2
    assert second_pass["bins"][0]["start_seconds"] == 3.0

    # End-to-end structure regression through the real OSC parser and Song
    # Memory. Reference and supporting tracks intentionally use different epoch
    # numbers so structure analysis must align them by DAW-time overlap.
    reset_state()
    for second in range(72):
        family_a = second < 24 or second >= 48
        master_bands = [value + (0.0 if family_a else 9.0) for value in shape_a]
        section_chroma = chroma_c_major if family_a else chroma_g_major
        for offset in (0.05, 0.15, 0.25, 0.35):
            t = second + offset
            core._on_frame(
                "/aianalyzer/frame",
                *synthetic_frame(
                    "Master",
                    "uuid-master",
                    100.0 + t,
                    master_bands,
                    peak=-12.0 if family_a else -7.0,
                    rms=-24.0 if family_a else -15.0,
                    flux=0.04 if family_a else 0.20,
                    chroma=section_chroma,
                    transport_epoch=7,
                    transport_time_seconds=t,
                    estimated_analysis_lag_ms=35.0,
                ),
            )
            core._on_frame(
                "/aianalyzer/frame",
                *synthetic_frame(
                    "Kick",
                    "uuid-kick",
                    200.0 + t,
                    master_bands,
                    rms=-28.0 if family_a else -16.0,
                    chroma=section_chroma,
                    signal_present=not family_a,
                    transport_epoch=3,
                    transport_time_seconds=t,
                ),
            )
            core._on_frame(
                "/aianalyzer/frame",
                *synthetic_frame(
                    "Vocal",
                    "uuid-vocal",
                    300.0 + t,
                    master_bands,
                    rms=-19.0 if family_a else -27.0,
                    chroma=section_chroma,
                    signal_present=family_a,
                    transport_epoch=11,
                    transport_time_seconds=t,
                ),
            )

    bind("uuid-master", "Master", 0)
    bind("uuid-kick", "Kick", 1)
    bind("uuid-vocal", "Vocal", 2)
    section_map = structure.audio_section_map(
        "mixer:0/slot:9",
        transport_epoch=7,
        min_section_seconds=8,
        sensitivity=0.45,
        family_similarity=0.78,
        max_sections=12,
        max_tracks=8,
    )
    assert section_map["available"] is True
    assert section_map["section_count"] == 3, section_map
    boundary_times = [float(item["time_seconds"]) for item in section_map["boundaries"]]
    assert any(abs(value - 24.0) <= 2.0 for value in boundary_times), boundary_times
    assert any(abs(value - 48.0) <= 2.0 for value in boundary_times), boundary_times
    assert section_map["sections"][0]["family_id"] == section_map["sections"][2]["family_id"]
    assert section_map["sections"][0]["family_id"] != section_map["sections"][1]["family_id"]
    assert section_map["track_activity_source_count"] == 3

    section_profile = structure.audio_section_profile("S02", section_map["map_id"], 8, 8)
    assert section_profile["available"] is True
    assert section_profile["family_id"] == section_map["sections"][1]["family_id"]
    assert len(section_profile["track_profiles"]) == 3
    kick_profile = next(item for item in section_profile["track_profiles"] if item["runtime_id"] == "uuid-kick")
    vocal_profile = next(item for item in section_profile["track_profiles"] if item["runtime_id"] == "uuid-vocal")
    assert kick_profile["selected_transport_epoch"] == 3
    assert vocal_profile["selected_transport_epoch"] == 11
    assert float(kick_profile["active_ratio"]) > float(vocal_profile["active_ratio"])

    kick_story = story.audio_track_story("mixer:1/slot:9", section_map["map_id"])
    assert kick_story["available"] is True
    assert kick_story["selected_transport_epoch"] == 3
    assert kick_story["section_count"] == 3
    assert kick_story["sufficient_coverage_section_count"] == 3
    assert kick_story["sections"][0]["family_id"] == kick_story["sections"][2]["family_id"]
    assert kick_story["sections"][1]["delta_from_previous"] is not None
    assert float(kick_story["sections"][1]["active_ratio"]) > float(kick_story["sections"][0]["active_ratio"])
    recurring_family = next(
        item for item in kick_story["family_consistency"]
        if item["family_id"] == kick_story["sections"][0]["family_id"]
    )
    assert recurring_family["occurrence_count"] == 2
    assert recurring_family["sufficient_coverage_count"] == 2

    vocal_story = story.audio_track_story("mixer:2/slot:9", section_map["map_id"])
    assert vocal_story["available"] is True
    assert vocal_story["selected_transport_epoch"] == 11
    assert float(vocal_story["sections"][0]["active_ratio"]) > float(vocal_story["sections"][1]["active_ratio"])

    print(
        f"AI Audio Analyzer MCP SDK {mcp_sdk_version}: 43 tools; "
        "V0.4 mapping + project identity disclosure + project A/B + temporal + masking + stereo + tonal + "
        "V1.0 verification + V1.1 adaptive performance + V1.2 transport/song-memory + "
        "Analyzer-owned profile control + explainable section structure + Track Story regressions OK"
    )


if __name__ == "__main__":
    main()
