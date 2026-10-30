import os
import sys
import math
import numpy as np

RENDER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(RENDER_DIR, "..", ".."))
sys.path.insert(0, os.path.join(REPO_DIR, "tests"))
sys.path.insert(0, RENDER_DIR)

import render_common as rc

KNEE_DBFS = 20.0 * math.log10(0.70) # -3.10 dBFS

EQ_PRESETS = [
    # id, name, 100, 200, 400, 800, 1.6k, 3.2k, 6.4k, Level (Round 39 re-centred)
    (1, "Bathory '84", -2.5, -12.5, -6.0, -2.5, 12.5, 9.0, 3.0, -3.5),
    (2, "Deathcrush '87", 5.0, -2.0, -1.0, 5.5, -7.0, 12.0, -3.0, -1.5),
    (3, "Transilvanian '94", -9.0, -2.0, 0.0, 12.0, -2.0, 9.0, -3.5, -0.5),
    (4, "Nightside '94", 3.0, 7.0, -5.0, -4.0, 5.5, 7.5, -2.0, -4.5),
    (5, "Filosofem '96", 3.5, 4.0, -5.0, 9.5, 12.5, 3.5, 14.0, -6.0),
    (6, "In Sorte '07", 0.0, -3.5, -1.5, 3.5, 6.0, 3.5, 3.0, 0.5),
    (7, "Evangelion '09", 4.0, 0.0, -1.0, 8.0, 10.0, 1.0, 9.5, -3.5),
]

def run_eq_preset_headroom():
    sr = 48000
    di_path = os.path.join(RENDER_DIR, "di_input.wav")
    if not os.path.exists(di_path):
        raise FileNotFoundError(f"Missing {di_path}")

    # WAV IR only (Slot 0 BlackWizard), EQ explicitly Post-Pedal (slider76=1)
    base = {
        1: 0.0, 2: 105.0, 3: -52.0, 4: 1,
        10: 1,
        **rc.PEDAL_DEFAULTS["Metal Zone"],
        20: 0, 40: 0,
        49: 1, 51: -0.5, 53: 0,
        54: 1, 55: 54.0, 56: 44.0, 57: 62.0, 58: 64.0,
        65: 1,
        75: 0,
        76: 1,
    }

    item_len = 0.45
    item_gap = 0.50
    offset_idx = len(EQ_PRESETS) + 1
    total_items = (len(EQ_PRESETS) + 1) * 2
    total_len = round(total_items * item_gap + 0.5, 2)

    tracks_xml = []
    # Pass 1: Amp Tube Head (slider54 = 1)
    flat_tube = dict(base)
    flat_tube[54] = 1
    for b in range(66, 74): flat_tube[b] = 0.0
    tracks_xml.append(rc.make_track("Tube_Flat_Ref", flat_tube, di_path, 0.0, item_len))

    for idx, (p_id, name, b1, b2, b3, b4, b5, b6, b7, lvl) in enumerate(EQ_PRESETS, start=1):
        p_cfg = dict(base)
        p_cfg[54] = 1
        p_cfg[75] = p_id
        for b_idx, val in enumerate([b1, b2, b3, b4, b5, b6, b7, lvl], start=66): p_cfg[b_idx] = val
        tracks_xml.append(rc.make_track(f"Tube_P{p_id}_{name.replace(' ', '_')}", p_cfg, di_path, round(idx * item_gap, 2), item_len))

    # Pass 2: Amp OFF (slider54 = 0)
    flat_off = dict(base)
    flat_off[54] = 0
    for b in range(66, 74): flat_off[b] = 0.0
    tracks_xml.append(rc.make_track("Off_Flat_Ref", flat_off, di_path, round(offset_idx * item_gap, 2), item_len))

    for idx, (p_id, name, b1, b2, b3, b4, b5, b6, b7, lvl) in enumerate(EQ_PRESETS, start=1):
        p_cfg = dict(base)
        p_cfg[54] = 0
        p_cfg[75] = p_id
        for b_idx, val in enumerate([b1, b2, b3, b4, b5, b6, b7, lvl], start=66): p_cfg[b_idx] = val
        tracks_xml.append(rc.make_track(f"Off_P{p_id}_{name.replace(' ', '_')}", p_cfg, di_path, round((offset_idx + idx) * item_gap, 2), item_len))

    out_wav = os.path.join(RENDER_DIR, "out_eq_presets_headroom.wav")
    rpp_path = os.path.join(RENDER_DIR, "test_eq_presets_headroom.rpp")

    with open(rpp_path, "w", encoding="utf-8") as f:
        f.write(rc.build_rpp(tracks_xml, out_wav, total_len, sr=sr))

    if os.path.exists(out_wav): os.remove(out_wav)
    print("Rendering GE-7 Record EQ presets in live REAPER host: WAV IR (Slot 0 BlackWizard)...")
    rc.run_reaper(rpp_path)

    samples = rc.read_wav24(out_wav, channel=0)
    seg_spl = int(0.40 * sr)

    def analyze_pass(pass_name, start_index):
        print("\n" + "=" * 105)
        print(f"--- {pass_name} (WAV IR Slot 0, Post-Pedal EQ) ---")
        print(f"{'Preset':<22} | {'Album (Year)':<24} | {'LUFS':<10} | {'Delta LUFS':<12} | {'Peak dBFS':<10} | Limiter Status (Knee: -3.10 dBFS)")
        print("=" * 105)

        ref_start = start_index * item_gap + 0.03
        seg_ref = samples[int(ref_start * sr) : int(ref_start * sr) + seg_spl]
        pk_ref = rc.calc_peak_db(seg_ref)
        lufs_ref = rc.calc_lufs(seg_ref)

        print(f"{'0: Flat Baseline':<22} | {'-':<24} | {lufs_ref:6.2f} LUFS| {'0.00 dB':<12} | {pk_ref:6.2f} dBFS | Clean ({abs(pk_ref - KNEE_DBFS):.2f} dB below knee)")

        pass_results = []
        for idx, (p_id, name, b1, b2, b3, b4, b5, b6, b7, lvl) in enumerate(EQ_PRESETS, start=1):
            start_t = (start_index + idx) * item_gap + 0.03
            seg = samples[int(start_t * sr) : int(start_t * sr) + seg_spl]
            pk = rc.calc_peak_db(seg)
            lufs = rc.calc_lufs(seg)
            delta_lufs = lufs - lufs_ref

            assert pk < KNEE_DBFS, f"Preset {name} exceeded limiter knee: peak {pk:.2f} dBFS >= {KNEE_DBFS:.2f} dBFS"
            assert abs(delta_lufs) <= 1.1, f"Preset {name} delta LUFS {delta_lufs:+.2f} dB exceeded +/-1.1 dB target"

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

            print(f"{p_id}: {name:<19} | {album_info:<24} | {lufs:6.2f} LUFS| {delta_lufs:+6.2f} dB     | {pk:6.2f} dBFS | {status}")
            pass_results.append((p_id, name, album_info, lufs, delta_lufs, pk, status))

        print("=" * 105)
        return lufs_ref, pk_ref, pass_results

    tube_ref_lufs, tube_ref_pk, tube_results = analyze_pass("AMP TUBE HEAD (slider54 = 1)", 0)
    off_ref_lufs, off_ref_pk, off_results = analyze_pass("AMP OFF (slider54 = 0)", offset_idx)

    # Clean up test files
    if os.path.exists(out_wav): os.remove(out_wav)
    if os.path.exists(rpp_path): os.remove(rpp_path)

    return tube_results, off_results

if __name__ == "__main__":
    run_eq_preset_headroom()
