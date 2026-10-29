import os
import sys
import math
import numpy as np

RENDER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(RENDER_DIR, "..", ".."))
sys.path.insert(0, os.path.join(REPO_DIR, "tests"))
sys.path.insert(0, RENDER_DIR)

import verify_jsfx as v
import render_common as rc

def measure_all_ir_slots():
    sr = 48000
    di_path = os.path.join(RENDER_DIR, "di_input.wav")

    presets_path = os.path.join(REPO_DIR, "sepulchre_presets.jsfx-inc")
    with open(presets_path, "r", encoding="utf-8") as f:
        presets = v.parse_global_presets(f.read())
    base = dict(presets[0]) # Preset 0: Tight Rhythm (MT-2, Amp on, Cab on)
    base[20] = 0; base[30] = 0; base[40] = 0

    tracks_xml = []
    track_names = ["IIR_Cab0"] + [f"WAV_IR_Slot{i}" for i in range(10)]

    p_iir = dict(base)
    p_iir[49] = 1; p_iir[50] = 0; p_iir[52] = 0
    tracks_xml.append(rc.make_track("IIR_Cab0", p_iir, di_path, 0.0))

    for slot in range(10):
        p_slot = dict(base)
        p_slot[49] = 1; p_slot[52] = 1; p_slot[53] = slot
        tracks_xml.append(rc.make_track(f"WAV_IR_Slot{slot}", p_slot, di_path, round((slot + 1) * 0.5, 2)))

    out_p = os.path.join(RENDER_DIR, "out_slots.wav")
    rpp_p = os.path.join(RENDER_DIR, "test_slots.rpp")
    total_len = round(11 * 0.5 + 0.2, 2)

    with open(rpp_p, "w", encoding="utf-8") as f:
        f.write(rc.build_rpp(tracks_xml, out_p, total_len, sr=sr))

    if os.path.exists(out_p):
        os.remove(out_p)

    print("Rendering 10 WAV IR Slots + IIR Cab in REAPER...")
    rc.run_reaper(rpp_p)

    samples = rc.read_wav24(out_p, channel=0)
    seg_len = int(0.40 * sr)

    print("\n" + "="*80)
    print(f"{'Slot / Mode':<20} | {'LUFS':<10} | {'Peak dBFS':<10} | {'Delta to IIR':<12}")
    print("="*80)

    # Slot 0 = IIR
    seg0 = samples[int(0.03 * sr) : int(0.03 * sr) + seg_len]
    lufs_ref = rc.calc_lufs(seg0)
    pk_ref = rc.calc_peak_db(seg0)
    print(f"{'0: IIR Cab 0':<20} | {lufs_ref:6.2f} LUFS | {pk_ref:6.2f} dBFS | {'0.00 dB (REF)':<12}")

    for slot in range(10):
        st = int(((slot + 1) * 0.5 + 0.03) * sr)
        seg = samples[st : st + seg_len]
        lufs = rc.calc_lufs(seg)
        pk = rc.calc_peak_db(seg)
        delta = lufs - lufs_ref
        print(f"Slot {slot:<15} | {lufs:6.2f} LUFS | {pk:6.2f} dBFS | {delta:+6.2f} dB")
    print("="*80)

if __name__ == "__main__":
    measure_all_ir_slots()
