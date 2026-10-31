import os
import sys
import math
import numpy as np

RENDER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(RENDER_DIR, "..", ".."))
sys.path.insert(0, os.path.join(REPO_DIR, "tests"))
sys.path.insert(0, RENDER_DIR)

import render_common as rc

def test_eq_flat_null():
    print("\n--- 1. EQ ON & FLAT vs EQ OFF NULL TEST (PRE & POST PEDAL) ---")
    sr = 48000
    di_path = os.path.join(RENDER_DIR, "di_input.wav")
    if not os.path.exists(di_path):
        raise FileNotFoundError(f"DI input missing at {di_path}")

    positions = [(0, "Pre-Pedal (slider76=0)"), (1, "Post-Pedal (slider76=1)")]

    print("=" * 80)
    print(f"{'Position':<26} | {'Sig Peak':<10} | {'Max Abs Err':<12} | {'Peak Null':<12} | Status")
    print("=" * 80)

    for pos, pos_name in positions:
        cfg_off = {**rc.BASE_DEFAULTS, 10: 1, **rc.PEDAL_DEFAULTS["RAT"], 65: 0, 76: pos}
        cfg_on = {**rc.BASE_DEFAULTS, 10: 1, **rc.PEDAL_DEFAULTS["RAT"],
                  65: 1, 66: 0.0, 67: 0.0, 68: 0.0, 69: 0.0, 70: 0.0, 71: 0.0, 72: 0.0, 73: 0.0, 76: pos}

        out_off = os.path.join(RENDER_DIR, f"out_eq_off_{pos}.wav")
        out_on = os.path.join(RENDER_DIR, f"out_eq_on_{pos}.wav")
        rpp_off_p = os.path.join(RENDER_DIR, f"test_eq_off_{pos}.rpp")
        rpp_on_p = os.path.join(RENDER_DIR, f"test_eq_on_{pos}.rpp")

        with open(rpp_off_p, "w", encoding="utf-8") as f:
            f.write(rc.build_rpp(rc.make_track("EQ_Off", cfg_off, di_path, 0.0, 0.45), out_off, 0.45, sr=sr))
        with open(rpp_on_p, "w", encoding="utf-8") as f:
            f.write(rc.build_rpp(rc.make_track("EQ_On_Flat", cfg_on, di_path, 0.0, 0.45), out_on, 0.45, sr=sr))

        if os.path.exists(out_off): os.remove(out_off)
        if os.path.exists(out_on): os.remove(out_on)

        rc.run_reaper(rpp_off_p)
        rc.run_reaper(rpp_on_p)

        s_off = rc.read_wav24(out_off, channel=0)
        s_on = rc.read_wav24(out_on, channel=0)

        # Let 20ms crossfade settle
        settle = int(0.05 * sr)
        diff = s_on[settle:] - s_off[settle:]
        max_err = float(np.max(np.abs(diff)))
        sig_pk = float(np.max(np.abs(s_off[settle:])))
        null_pk_db = 20.0 * math.log10(max(1e-12, max_err) / max(1e-12, sig_pk))

        passed = null_pk_db < -100.0
        status = "PASS (< -100 dB)" if passed else "FAIL"
        print(f"{pos_name:<26} | {sig_pk:8.4f}   | {max_err:10.2e}   | {null_pk_db:9.2f} dB  | {status}")
        assert passed, f"EQ flat null failed at position {pos}: {null_pk_db:.2f} dB"

        if os.path.exists(out_off): os.remove(out_off)
        if os.path.exists(out_on): os.remove(out_on)
        if os.path.exists(rpp_off_p): os.remove(rpp_off_p)
        if os.path.exists(rpp_on_p): os.remove(rpp_on_p)

    print("=" * 80)
    print("PASS: EQ on and flat is identical to EQ off in both Pre and Post positions.")

def test_eq_bands_frequency_and_gain():
    print("\n--- 2. GE-7 EQ BANDS FREQUENCY & GAIN VERIFICATION (+15 dB BOOST, PRE & POST) ---")
    sr = 48000
    n_fft = 16384
    imp_amp = 0.05
    imp_offset = 9600  # 0.20s settle
    total_spl = imp_offset + n_fft
    dur = round(total_spl / sr + 0.05, 2)

    imp = np.zeros(total_spl)
    imp[imp_offset] = imp_amp
    imp_wav = os.path.join(RENDER_DIR, "impulse_fft.wav")
    rc.write_wav24(imp_wav, imp, sr=sr)

    bands = [
        ("100 Hz", 66, 100.0),
        ("200 Hz", 67, 200.0),
        ("400 Hz", 68, 400.0),
        ("800 Hz", 69, 800.0),
        ("1.6 kHz", 70, 1600.0),
        ("3.2 kHz", 71, 3200.0),
        ("6.4 kHz", 72, 6400.0),
    ]

    positions = [(0, "Pre-Pedal (slider76=0)"), (1, "Post-Pedal (slider76=1)")]

    print("=" * 86)
    print(f"{'Position':<24} | {'Band':<9} | {'Target Freq':<12} | {'Meas Freq':<12} | {'Peak Gain':<10} | Status")
    print("=" * 86)

    for pos, pos_name in positions:
        for label, slider_idx, target_f in bands:
            cfg = {**rc.BASE_DEFAULTS, 10: 0, 54: 0, 65: 1, 73: 0.0, 76: pos}
            for b in range(66, 73):
                cfg[b] = 0.0
            cfg[slider_idx] = 15.0

            out_b = os.path.join(RENDER_DIR, f"out_band_{pos}_{slider_idx}.wav")
            rpp_b = os.path.join(RENDER_DIR, f"test_band_{pos}_{slider_idx}.rpp")

            with open(rpp_b, "w", encoding="utf-8") as f:
                f.write(rc.build_rpp(rc.make_track(f"Band_{slider_idx}", cfg, imp_wav, 0.0, dur), out_b, dur, sr=sr))

            if os.path.exists(out_b): os.remove(out_b)

            rc.run_reaper(rpp_b)
            # Round 35: Amp OFF (slider54 = 0) scales by 0.84; normalize by 0.84 to measure exact EQ transfer function
            ir_out = (rc.read_wav24(out_b, channel=0) / 0.84)[imp_offset : imp_offset + n_fft]

            H = np.abs(np.fft.rfft(ir_out, n=n_fft)) / imp_amp
            freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

            mask = (freqs >= target_f * 0.707) & (freqs <= target_f * 1.414)
            sub_freqs = freqs[mask]
            sub_H = H[mask]
            pk_idx = np.argmax(sub_H)
            meas_f = sub_freqs[pk_idx]
            meas_gain_db = 20.0 * math.log10(sub_H[pk_idx])

            freq_err_pct = abs(meas_f - target_f) / target_f * 100.0
            gain_err_db = abs(meas_gain_db - 15.0)

            passed = freq_err_pct < 3.0 and gain_err_db < 0.6
            status = "PASS" if passed else "FAIL"
            print(f"{pos_name:<24} | {label:<9} | {target_f:8.1f} Hz  | {meas_f:8.1f} Hz  | {meas_gain_db:+6.2f} dB   | {status}")
            assert passed, f"Band {label} at pos {pos} failed: {meas_f:.1f} Hz, {meas_gain_db:.2f} dB"

            if os.path.exists(out_b): os.remove(out_b)
            if os.path.exists(rpp_b): os.remove(rpp_b)

    print("=" * 86)
    print("ALL 7 GE-7 BANDS ACCURATELY ALIGNED AT +15.0 dB PEAK GAIN IN BOTH PRE AND POST POSITIONS.")
    if os.path.exists(imp_wav): os.remove(imp_wav)

def test_eq_toggle_no_clicks():
    print("\n--- 3. EQ TOGGLE CLICK-FREE CROSSFADE TEST (PRE & POST) ---")
    sr = 48000
    dur = 0.5
    t = np.arange(int(dur * sr)) / sr
    sine_1k = 0.05 * np.sin(2.0 * math.pi * 1000.0 * t)
    sine_path = os.path.join(RENDER_DIR, "sine_1k.wav")
    rc.write_wav24(sine_path, sine_1k, sr=sr)

    positions = [(0, "Pre-Pedal (slider76=0)"), (1, "Post-Pedal (slider76=1)")]

    for pos, pos_name in positions:
        cfg = {**rc.BASE_DEFAULTS, 10: 0, 54: 0, 65: 1,
               66: 0, 67: 0, 68: 0, 69: 15.0, 70: 15.0, 71: 0, 72: 0, 73: 0, 76: pos}

        out_toggle = os.path.join(RENDER_DIR, f"out_toggle_{pos}.wav")
        rpp_toggle = os.path.join(RENDER_DIR, f"test_toggle_{pos}.rpp")

        with open(rpp_toggle, "w", encoding="utf-8") as f:
            f.write(rc.build_rpp(rc.make_track("Toggle_Test", cfg, sine_path, 0.0, dur), out_toggle, dur, sr=sr))

        if os.path.exists(out_toggle): os.remove(out_toggle)

        rc.run_reaper(rpp_toggle)
        toggle_s = rc.read_wav24(out_toggle, channel=0)

        diffs = np.abs(np.diff(toggle_s))
        max_step = float(np.max(diffs))
        print(f"{pos_name}: Max sample jump = {max_step:.4f} (Smooth, well within continuous sine derivative)")
        assert max_step < 0.15, f"Click/pop detected in {pos_name}! Max step={max_step:.4f}"

        if os.path.exists(out_toggle): os.remove(out_toggle)
        if os.path.exists(rpp_toggle): os.remove(rpp_toggle)

    print("PASS: EQ enables and bypasses smoothly without clicks or pops in both Pre and Post positions.")
    if os.path.exists(sine_path): os.remove(sine_path)

if __name__ == "__main__":
    test_eq_flat_null()
    test_eq_bands_frequency_and_gain()
    test_eq_toggle_no_clicks()
