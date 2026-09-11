#!/usr/bin/env python3
"""P4b pair evidence over independently resolved historical Song Memory passes."""

from __future__ import annotations

import masking_tools as masking
import mono_compatibility_tools as mono
import song_tools as song
import temporal_tools as temporal
import historical_detail_store as store
import historical_detail_profile as profile

DETAIL_KEY = store.DETAIL_KEY
COUNT_ONSET_CANDIDATE = store.COUNT_ONSET_CANDIDATE
_finite = store._finite
_band_energy = profile._band_energy
_row_mid_spectrum = profile._row_mid_spectrum


def _common_rows(rows_a, rows_b):
    a = {int(r["bin_index"]): r for r in rows_a if isinstance(r.get(DETAIL_KEY), dict)}
    b = {int(r["bin_index"]): r for r in rows_b if isinstance(r.get(DETAIL_KEY), dict)}
    return [(a[i], b[i]) for i in sorted(set(a) & set(b))]


def _historical_temporal_band(row_pairs, low_hz, high_hz):
    values_a, values_b = [], []
    coactive = onset_a = onset_b = onset_both = 0
    for row_a, row_b in row_pairs:
        active_a = int(row_a.get("active_count", 0) or 0) > 0
        active_b = int(row_b.get("active_count", 0) or 0) > 0
        coactive += int(active_a and active_b)
        ea = _band_energy(_row_mid_spectrum(row_a), low_hz, high_hz)
        eb = _band_energy(_row_mid_spectrum(row_b), low_hz, high_hz)
        if ea is not None and eb is not None:
            values_a.append(ea)
            values_b.append(eb)
        ca = row_a[DETAIL_KEY]["scalar_count"]
        cb = row_b[DETAIL_KEY]["scalar_count"]
        ha = int(ca[COUNT_ONSET_CANDIDATE]) > 0
        hb = int(cb[COUNT_ONSET_CANDIDATE]) > 0
        onset_a += int(ha)
        onset_b += int(hb)
        onset_both += int(ha and hb)
    corr = temporal._pearson(values_a, values_b)
    overlap = temporal._normalized_overlap(values_a, values_b)
    count = len(row_pairs)
    return {
        "resolution_seconds": song.TIMELINE_BIN_SECONDS,
        "common_bins": count,
        "usable_energy_bins": len(values_a),
        "coactive_bin_ratio": None if count <= 0 else round(coactive / count, 6),
        "band_envelope_correlation": None if corr is None else round(corr, 6),
        "normalized_band_temporal_overlap": None if overlap is None else round(overlap, 6),
        "onset_candidate_bins_a": onset_a,
        "onset_candidate_bins_b": onset_b,
        "coincident_onset_candidate_bins": onset_both,
        "note": "Temporal alignment is by matching one-second DAW Song Memory bins, not recent-window subsecond frames.",
    }


def _pair_evidence(profile_a, profile_b, rows_a, rows_b, max_regions, temporal_low_hz, temporal_high_hz):
    if not (profile_a.get("detail_available") and profile_b.get("detail_available")):
        return {"available": False, "reason": "P4b retained detail is unavailable on one or both selected passes."}
    row_pairs = _common_rows(rows_a, rows_b)
    auditory_a = masking._auditory_bands((profile_a.get("spectrum") or {}).get("mid_spectrum_db"))
    auditory_b = masking._auditory_bands((profile_b.get("spectrum") or {}).get("mid_spectrum_db"))
    finite_a = [float(x["energy_db"]) for x in auditory_a if x.get("energy_db") is not None]
    finite_b = [float(x["energy_db"]) for x in auditory_b if x.get("energy_db") is not None]
    regions = []
    if finite_a and finite_b:
        max_a, max_b = max(finite_a), max(finite_b)
        for ba, bb in zip(auditory_a, auditory_b):
            if ba.get("energy_db") is None or bb.get("energy_db") is None:
                continue
            ea, eb = float(ba["energy_db"]), float(bb["energy_db"])
            spectral_overlap = min(10.0 ** ((ea - max_a) / 10.0), 10.0 ** ((eb - max_b) / 10.0))
            level_delta = ea - eb
            da = masking._direction_weight(level_delta)
            db = 1.0 - da
            t = _historical_temporal_band(row_pairs, float(ba["low_hz"]), float(ba["high_hz"]))
            overlap = t.get("normalized_band_temporal_overlap")
            sa, sb = spectral_overlap * da, spectral_overlap * db
            ca = None if overlap is None else sa * (0.25 + 0.75 * float(overlap))
            cb = None if overlap is None else sb * (0.25 + 0.75 * float(overlap))
            rank = max(sa if ca is None else ca, sb if cb is None else cb)
            regions.append({
                "index": ba["index"], "low_hz": ba["low_hz"], "high_hz": ba["high_hz"], "center_hz": ba["center_hz"],
                "a_db": round(ea, 4), "b_db": round(eb, 4), "level_delta_a_minus_b_db": round(level_delta, 4),
                "relative_spectral_overlap": round(spectral_overlap, 6),
                "spectral_level_evidence_a_over_b": round(sa, 6), "spectral_level_evidence_b_over_a": round(sb, 6),
                "normalized_band_temporal_overlap": overlap,
                "combined_evidence_a_over_b": None if ca is None else round(ca, 6),
                "combined_evidence_b_over_a": None if cb is None else round(cb, 6), "_rank": rank,
            })
        regions.sort(key=lambda x: float(x["_rank"]), reverse=True)
        regions = regions[:max_regions]
        for x in regions:
            x.pop("_rank", None)

    fa = (profile_a.get("stereo") or {}).get("frequency_dependent_stereo", [])
    fb = (profile_b.get("stereo") or {}).get("frequency_dependent_stereo", [])
    stereo_delta = []
    for a, b in zip(fa, fb):
        ca, cb = _finite(a.get("correlation")), _finite(b.get("correlation"))
        sa, sb = _finite(a.get("side_to_mid_db")), _finite(b.get("side_to_mid_db"))
        stereo_delta.append({
            "range": a.get("range"),
            "correlation_delta_b_minus_a": None if ca is None or cb is None else round(cb - ca, 6),
            "side_to_mid_db_delta_b_minus_a": None if sa is None or sb is None else round(sb - sa, 4),
        })
    ma = _finite((((profile_a.get("mono_compatibility") or {}).get("full_band") or {}).get("mono_fold_rms_delta_db")))
    mb = _finite((((profile_b.get("mono_compatibility") or {}).get("full_band") or {}).get("mono_fold_rms_delta_db")))
    return {
        "available": bool(row_pairs),
        "comparability": {
            "same_effective_daw_range": profile_a.get("effective_range") == profile_b.get("effective_range"),
            "adequate_coverage_a": bool(profile_a.get("adequate_coverage")),
            "adequate_coverage_b": bool(profile_b.get("adequate_coverage")),
            "common_one_second_bins": len(row_pairs),
            "controlled_comparison": bool(row_pairs and profile_a.get("adequate_coverage") and profile_b.get("adequate_coverage") and profile_a.get("effective_range") == profile_b.get("effective_range")),
        },
        "masking": {
            "available": bool(regions),
            "strongest_regions": regions,
            "auditory_band_model": {"type": "equal-erb-rate-rebinning", "band_count": masking.ERB_BAND_COUNT, "source": "P4b retained 32-band Mid spectrum", "filterbank": False},
            "temporal_component_resolution_seconds": song.TIMELINE_BIN_SECONDS,
            "note": "Heuristic evidence only; historical temporal modulation is one-second scale.",
        },
        "stereo": {"frequency_dependent_delta_b_minus_a": stereo_delta},
        "mono_compatibility": {"mono_fold_rms_delta_db_b_minus_a": None if ma is None or mb is None else round(mb - ma, 4)},
        "temporal": {"custom_band_hz": [round(temporal_low_hz, 3), round(temporal_high_hz, 3)], **_historical_temporal_band(row_pairs, temporal_low_hz, temporal_high_hz)},
    }

