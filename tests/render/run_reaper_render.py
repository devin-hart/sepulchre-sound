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

def run_main_reaper_renders():
    sr = 48000
    di_path = os.path.join(RENDER_DIR, "di_input.wav")
    sine_path = os.path.join(RENDER_DIR, "sine_2578.wav")
    out_path = os.path.join(RENDER_DIR, "out_main_render.wav")
    rpp_path = os.path.join(RENDER_DIR, "test_main_render.rpp")

    # Generate test DI input if missing
    if not os.path.exists(di_path):
        n_di = int(0.45 * sr)
        t = np.arange(n_di) / sr
        env = np.exp(-t * 4.5) * (1.0 - np.exp(-t * 250.0))
        sig = 0.25 * env * (
            0.6 * np.sin(2 * np.pi * 82.41 * t)
            + 0.4 * np.sin(2 * np.pi * 164.82 * t)
            + 0.3 * np.sin(2 * np.pi * 247.23 * t)
        )
        rc.write_wav24(di_path, sig, sr=sr)

    # Generate bin-centered 2578.125 Hz sine for pre-cab aliasing test if missing
    if not os.path.exists(sine_path):
        n_sine = int(0.45 * sr)
        t = np.arange(n_sine) / sr
        f0 = 55.0 * sr / 1024.0
        sig_sine = 0.25 * np.sin(2.0 * np.pi * f0 * t)
        rc.write_wav24(sine_path, sig_sine, sr=sr)

    presets_path = os.path.join(REPO_DIR, "sepulchre_presets.jsfx-inc")
    with open(presets_path, "r", encoding="utf-8") as f:
        presets = v.parse_global_presets(f.read())

    test_preset_indices = [0, 1, 2, 3, 4, 6]
    tracks_xml = []
    for slot, idx in enumerate(test_preset_indices):
        p = dict(presets[idx])
        # Disable time-based FX tail bleed across sequential slots
        p[20] = 0; p[30] = 0; p[40] = 0
        tracks_xml.append(rc.make_track(f"Preset_{idx}", p, di_path, pos=round(slot * 0.5, 2)))

    # Track: Pre-cabinet 8x oversampling sine aliasing test for Metal Zone
    p_alias_mt2 = dict(presets[0])
    p_alias_mt2[4] = 0; p_alias_mt2[16] = 0; p_alias_mt2[20] = 0; p_alias_mt2[30] = 0; p_alias_mt2[40] = 0
    p_alias_mt2[49] = 0; p_alias_mt2[51] = 0.0; p_alias_mt2[52] = 0; p_alias_mt2[54] = 0; p_alias_mt2[58] = 50.0
    tracks_xml.append(rc.make_track("PreCab_Alias_MT2", p_alias_mt2, sine_path, pos=3.0))

    # Track: Pre-cabinet 8x oversampling sine aliasing test for HM-2 (all on 10)
    p_alias_hm2 = dict(presets[4])
    p_alias_hm2[4] = 0; p_alias_hm2[16] = 0; p_alias_hm2[20] = 0; p_alias_hm2[30] = 0; p_alias_hm2[40] = 0
    p_alias_hm2[49] = 0; p_alias_hm2[51] = 0.0; p_alias_hm2[52] = 0; p_alias_hm2[54] = 0; p_alias_hm2[58] = 50.0
    tracks_xml.append(rc.make_track("PreCab_Alias_HM2", p_alias_hm2, sine_path, pos=3.5))

    total_len = 4.0
    rpp_content = rc.build_rpp(tracks_xml, out_path, total_len=total_len, sr=sr)
    with open(rpp_path, "w", encoding="utf-8") as f:
        f.write(rpp_content)

    if os.path.exists(out_path):
        os.remove(out_path)

    print("Rendering main test project in REAPER (single-pass)...")
    rc.run_reaper(rpp_path)

    w = rc.read_wav24(out_path, channel=0)

    print("\n--- LIVE REAPER IIR PRESET HEADROOM & DC OFFSET REPORT ---")
    for slot, idx in enumerate(test_preset_indices):
        seg = w[int((slot * 0.5 + 0.03) * sr) : int((slot * 0.5 + 0.44) * sr)]
        pk = np.max(np.abs(seg))
        pk_db = 20.0 * math.log10(pk)
        dc = abs(float(np.mean(seg)))
        print(f"LIVE REAPER Preset {idx} -> Peak: {pk_db:+.2f} dBFS | DC: {dc:.5f}")
        assert -10.0 <= pk_db <= -8.0, f"Live REAPER Preset {idx} peak {pk_db:.2f} outside [-10, -8] dBFS"
        assert dc < 0.004, f"Live REAPER Preset {idx} DC {dc:.5f} >= 0.004"

    def measure_aliasing(start_time, label):
        start_s = int(start_time * sr) + 4096
        n = 1024
        seg_a = w[start_s : start_s + n]
        hb = {55 * k for k in range(1, (n // 2) // 55 + 1)}
        bin_8k = int(8000.0 * n / sr)
        harm_all = alias_all = harm_8k = alias_8k = 0.0
        for k in range(1, n // 2):
            re_s = float(np.sum(seg_a * np.cos(2.0 * np.pi * k * np.arange(n) / n)))
            im_s = float(np.sum(seg_a * np.sin(2.0 * np.pi * k * np.arange(n) / n)))
            pwr = (re_s * re_s + im_s * im_s) / (n * n)
            if k in hb:
                harm_all += pwr
                if k <= bin_8k: harm_8k += pwr
            else:
                alias_all += pwr
                if k <= bin_8k: alias_8k += pwr
        all_db = 10.0 * math.log10(alias_all / harm_all)
        inband_db = 10.0 * math.log10(alias_8k / harm_8k)
        print(f"LIVE REAPER Pre-Cab Alias ({label}) -> All bins: {all_db:+.2f} dB | 20Hz-8kHz: {inband_db:+.2f} dB")
        return all_db, inband_db

    print("\n--- LIVE REAPER PRE-CABINET ALIASING REPORT ---")
    mt2_all, mt2_in = measure_aliasing(3.0, "Metal Zone")
    hm2_all, hm2_in = measure_aliasing(3.5, "HM-2 all 10")
    assert mt2_in <= -40.0, f"Metal Zone aliasing {mt2_in:.2f} dB exceeded -40 dB!"
    assert hm2_in <= -40.0, f"HM-2 aliasing {hm2_in:.2f} dB exceeded -40 dB!"
    print("ALL LIVE REAPER CLI RENDER CHECKS PASSED.")

    # Clean up project files
    if os.path.exists(rpp_path):
        os.remove(rpp_path)
    if os.path.exists(out_path):
        os.remove(out_path)

if __name__ == "__main__":
    run_main_reaper_renders()
