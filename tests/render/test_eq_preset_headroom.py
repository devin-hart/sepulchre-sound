import os
import sys
import math
import numpy as np

RENDER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(RENDER_DIR, "..", ".."))
sys.path.insert(0, os.path.join(REPO_DIR, "tests"))
sys.path.insert(0, RENDER_DIR)

import render_common as rc

# Limiter knee definition from sepulchre_dsp_core.jsfx-inc
# k = 0.70 (-3.10 dBFS), Ceiling L = 0.89125 (-1.00 dBFS)
KNEE_DBFS = 20.0 * math.log10(0.70) # -3.10 dBFS

EQ_PRESETS = [
    # id, name, 100, 200, 400, 800, 1.6k, 3.2k, 6.4k, Level
    (1, "Bathory '84", -2.5, -12.5, -6.0, -2.5, 12.5, 9.0, 3.0, 3.0),
    (2, "Deathcrush '87", 5.0, -2.0, -1.0, 5.5, -7.0, 12.0, -3.0, 3.5),
    (3, "Transilvanian '94", -9.0, -2.0, 0.0, 12.0, -2.0, 9.0, -3.5, 3.0),
    (4, "Nightside '94", 3.0, 7.0, -5.0, -4.0, 5.5, 7.5, -2.0, 3.0),
    (5, "Filosofem '96", 3.5, 4.0, -5.0, 9.5, 12.5, 3.5, 14.0, 3.0),
    (6, "In Sorte '07", 0.0, -3.5, -1.5, 3.5, 6.0, 3.5, 3.0, 3.0),
    (7, "Evangelion '09", 4.0, 0.0, -1.0, 8.0, 10.0, 1.0, 9.5, 3.0),
]

def run_eq_preset_headroom():
    sr = 48000
    di_path = os.path.join(RENDER_DIR, "di_input.wav")
    if not os.path.exists(di_path):
        raise FileNotFoundError(f"Missing {di_path}")

    # Base configuration: default chain, EQ in Slot B (after Distortion in Slot A)
    # Distortion: Metal Zone (default pedal slider 11 = 2) at default knobs
    base = {
        1: 0.0, 2: 105.0, 3: -52.0, 4: 1, # Input & Gate
        5: 0, 6: 4, 7: 1, 8: 2, 74: 3,    # Dist -> EQ -> Chorus -> Delay -> Reverb
        10: 1,                            # Distortion on
        **rc.PEDAL_DEFAULTS["Metal Zone"],# Default pedal: Metal Zone
        13: 50.0, 14: 50.0, 15: 50.0, 16: 0.0,
        20: 0, 30: 0, 40: 0,              # Chorus, Delay, Reverb bypassed for dry measurement
        49: 1, 50: 0, 51: -0.5,           # Cab on, Profile 0, Master -0.5 dB
        52: 1, 53: 0,                     # WAV IR mode, slot 0 (01 BlackWizard Center)
        54: 1, 55: 54.0, 56: 44.0, 57: 62.0, 58: 64.0, # Tube amp default
        65: 1,                            # EQ Enabled
        75: 0,                            # EQ preset id
    }

    item_len = 0.45
    item_gap = 0.50
    total_len = round((len(EQ_PRESETS) + 1) * item_gap + 0.2, 2)

    tracks_xml = []

    # Reference baseline: EQ Flat (0 dB on all bands and level)
    flat_cfg = dict(base)
    for b in range(66, 74): flat_cfg[b] = 0.0
    tracks_xml.append(rc.make_track("EQ_Flat_Ref", flat_cfg, di_path, 0.0, item_len))

    # 7 Presets
    for idx, (p_id, name, b1, b2, b3, b4, b5, b6, b7, lvl) in enumerate(EQ_PRESETS, start=1):
        p_cfg = dict(base)
        p_cfg[75] = p_id
        p_cfg[66] = b1
        p_cfg[67] = b2
        p_cfg[68] = b3
        p_cfg[69] = b4
        p_cfg[70] = b5
        p_cfg[71] = b6
        p_cfg[72] = b7
        p_cfg[73] = lvl
        tracks_xml.append(rc.make_track(f"EQ_P{p_id}_{name.replace(' ', '_')}", p_cfg, di_path, round(idx * item_gap, 2), item_len))

    out_wav = os.path.join(RENDER_DIR, "out_eq_presets_headroom.wav")
    rpp_path = os.path.join(RENDER_DIR, "test_eq_presets_headroom.rpp")

    with open(rpp_path, "w", encoding="utf-8") as f:
        f.write(rc.build_rpp(tracks_xml, out_wav, total_len, sr=sr))

    if os.path.exists(out_wav): os.remove(out_wav)
    print("Rendering GE-7 Record EQ presets in live REAPER host...")
    rc.run_reaper(rpp_path)

    samples = rc.read_wav24(out_wav, channel=0)
    seg_spl = int(0.40 * sr)

    print("\n" + "=" * 90)
    print(f"{'Preset':<22} | {'Album (Year)':<24} | {'Peak dBFS':<10} | {'Delta to Flat':<14} | Limiter Status (Knee: -3.10 dBFS)")
    print("=" * 90)

    # Reference flat
    seg_ref = samples[int(0.03 * sr) : int(0.03 * sr) + seg_spl]
    pk_ref = rc.calc_peak_db(seg_ref)
    print(f"{'0: Flat Baseline':<22} | {'-':<24} | {pk_ref:6.2f} dBFS | {'0.00 dB (REF)':<14} | Clean ({abs(pk_ref - KNEE_DBFS):.2f} dB below knee)")

    results = []
    for idx, (p_id, name, b1, b2, b3, b4, b5, b6, b7, lvl) in enumerate(EQ_PRESETS, start=1):
        start_t = idx * item_gap + 0.03
        seg = samples[int(start_t * sr) : int(start_t * sr) + seg_spl]
        pk = rc.calc_peak_db(seg)
        delta_ref = pk - pk_ref

        if pk >= KNEE_DBFS:
            headroom = pk - KNEE_DBFS
            status = f"**ENGAGED** (+{headroom:.2f} dB into knee)"
        else:
            headroom = KNEE_DBFS - pk
            status = f"Clean ({headroom:.2f} dB below knee)"

        album_info = {
            1: "Bathory (1984)",
            2: "Deathcrush (1987)",
            3: "Transilvanian Hunger ('94)",
            4: "In the Nightside ('94)",
            5: "Filosofem (1996)",
            6: "In Sorte Diaboli ('07)",
            7: "Evangelion (2009)",
        }.get(p_id, "")

        print(f"{p_id}: {name:<19} | {album_info:<24} | {pk:6.2f} dBFS | {delta_ref:+6.2f} dB     | {status}")
        results.append((p_id, name, album_info, pk, delta_ref, status))

    print("=" * 90)
    return results

if __name__ == "__main__":
    run_eq_preset_headroom()
