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

def run_per_pedal_loudness_comparison():
    sr = 48000
    di_path = os.path.join(RENDER_DIR, "di_input.wav")

    presets_path = os.path.join(REPO_DIR, "sepulchre_presets.jsfx-inc")
    with open(presets_path, "r", encoding="utf-8") as f:
        presets = v.parse_global_presets(f.read())

    # Default base configuration
    base = {
        1: 0.0, 2: 105.0, 3: -52.0, 4: 1,
        5: 0, 6: 1, 7: 2, 8: 3,
        10: 1, 13: 50.0, 14: 50.0, 15: 50.0, 16: 0.0,
        20: 0, 30: 0, 40: 0, # Disable delay/reverb for clean dry loudness
        49: 1, 50: 0, 51: -0.5, 54: 1, 55: 54.0, 56: 44.0, 57: 62.0, 58: 64.0
    }

    # 1. RAT default
    rat_def = {**base, **rc.PEDAL_DEFAULTS["RAT"]}

    # 2. DS-1 default
    ds1_def = {**base, **rc.PEDAL_DEFAULTS["DS-1"]}

    # 3. Metal Zone default
    mt2_def = {**base, **rc.PEDAL_DEFAULTS["Metal Zone"]}

    # 4. HM-2 default
    hm2_def = {**base, **rc.PEDAL_DEFAULTS["HM-2"]}

    test_cases = [
        ("Default RAT", rat_def),
        ("Default DS-1", ds1_def),
        ("Default Metal Zone", mt2_def),
        ("Default HM-2", hm2_def),
        ("Preset 0 (Tight Rhythm, MT-2)", dict(presets[0])),
        ("Preset 1 (Cold Lead, RAT)", dict(presets[1])),
        ("Preset 2 (Doom Wall, HM-2)", dict(presets[2])),
        ("Preset 3 (Raw 4-Track, DS-1)", dict(presets[3])),
        ("Preset 4 (Swedish Chainsaw, HM-2)", dict(presets[4])),
        ("Preset 6 (Ambient Swell, Clean)", dict(presets[6])),
    ]

    # Ensure no time-based FX bleed
    for name, d in test_cases:
        d[20] = 0; d[30] = 0; d[40] = 0; d[49] = 1; d[50] = 0

    # Render 1: IIR mode (slider52 = 0)
    tracks_iir = []
    for i, (name, d) in enumerate(test_cases):
        cfg = dict(d); cfg[52] = 0
        tracks_iir.append(rc.make_track(f"{name}_IIR", cfg, di_path, round(i * 0.5, 2)))

    out_iir_p = os.path.join(RENDER_DIR, "out_cmp_iir.wav")
    total_len = round(len(test_cases) * 0.5 + 0.2, 2)
    rpp_iir_p = os.path.join(RENDER_DIR, "test_cmp_iir.rpp")
    with open(rpp_iir_p, "w", encoding="utf-8") as f:
        f.write(rc.build_rpp(tracks_iir, out_iir_p, total_len, sr=sr))

    # Render 2: WAV IR mode (slider52 = 1, slider53 = 0)
    tracks_wav = []
    for i, (name, d) in enumerate(test_cases):
        cfg = dict(d); cfg[52] = 1; cfg[53] = 0
        tracks_wav.append(rc.make_track(f"{name}_WAV", cfg, di_path, round(i * 0.5, 2)))

    out_wav_p = os.path.join(RENDER_DIR, "out_cmp_wav.wav")
    rpp_wav_p = os.path.join(RENDER_DIR, "test_cmp_wav.rpp")
    with open(rpp_wav_p, "w", encoding="utf-8") as f:
        f.write(rc.build_rpp(tracks_wav, out_wav_p, total_len, sr=sr))

    if os.path.exists(out_iir_p):
        os.remove(out_iir_p)
    if os.path.exists(out_wav_p):
        os.remove(out_wav_p)

    print("Rendering IIR Cab test cases in REAPER...")
    rc.run_reaper(rpp_iir_p)

    print("Rendering WAV IR (Slot 0) test cases in REAPER...")
    rc.run_reaper(rpp_wav_p)

    s_iir = rc.read_wav24(out_iir_p, channel=0)
    s_wav = rc.read_wav24(out_wav_p, channel=0)

    seg_len = int(0.40 * sr)

    print("\n" + "="*95)
    print(f"{'Test Case':<32} | {'IIR LUFS':<9} | {'IIR Peak':<9} | {'WAV LUFS':<9} | {'WAV Peak':<9} | {'Delta LUFS':<10} | {'Limiter?':<8}")
    print("="*95)

    rows = []
    for i, (name, _) in enumerate(test_cases):
        st = int((i * 0.5 + 0.03) * sr)
        seg_i = s_iir[st : st + seg_len]
        seg_w = s_wav[st : st + seg_len]
        
        lufs_i = rc.calc_lufs(seg_i)
        pk_i = rc.calc_peak_db(seg_i)
        
        lufs_w = rc.calc_lufs(seg_w)
        pk_w = rc.calc_peak_db(seg_w)
        
        delta_lufs = lufs_w - lufs_i
        knee_flag = "EXCEEDED" if pk_w > -3.1 else "clean"
        
        print(f"{name:<32} | {lufs_i:6.2f} LUFS | {pk_i:6.2f} dBFS | {lufs_w:6.2f} LUFS | {pk_w:6.2f} dBFS | {delta_lufs:+6.2f} dB    | {knee_flag}")
        rows.append((name, lufs_i, pk_i, lufs_w, pk_w, delta_lufs, knee_flag))
    print("="*95)
    return rows

if __name__ == "__main__":
    run_per_pedal_loudness_comparison()
