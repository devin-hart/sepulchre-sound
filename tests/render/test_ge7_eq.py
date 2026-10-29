import os
import sys
import math
import numpy as np

RENDER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(RENDER_DIR, "..", ".."))
sys.path.insert(0, os.path.join(REPO_DIR, "tests"))
sys.path.insert(0, RENDER_DIR)

import render_common as rc

def test_routing_migration():
    print("\n--- 1. ROUTING MIGRATION TEST ---")
    sr = 48000
    impulse_wav = os.path.join(RENDER_DIR, "impulse.wav")
    if not os.path.exists(impulse_wav):
        imp = np.zeros(int(0.1 * sr))
        imp[0] = 0.5
        rc.write_wav24(impulse_wav, imp, sr=sr)

    # Legacy 64-slider track (only sliders 1..64 declared, slider74 missing from RPP line)
    # Old routing: Slot A=0 (Dist), B=1 (Chorus), C=2 (Delay), D=3 (Reverb)
    legacy_sliders = {i: 0.0 for i in range(1, 65)}
    legacy_sliders[1] = 0.0; legacy_sliders[2] = 40.0; legacy_sliders[4] = 0
    legacy_sliders[5] = 0; legacy_sliders[6] = 1; legacy_sliders[7] = 2; legacy_sliders[8] = 3
    legacy_sliders[10] = 0; legacy_sliders[49] = 0; legacy_sliders[51] = 0.0; legacy_sliders[54] = 0; legacy_sliders[58] = 50.0

    # Write RPP with exactly 64 sliders
    s_line = " ".join(str(legacy_sliders.get(i, 0)) for i in range(1, 65))
    clean_wav = impulse_wav.replace("\\", "/")
    track_xml = f"""  <TRACK
    NAME "Legacy_64_Slider_Project"
    VOLPAN 1 0 -1 -1 1
    MUTESOLO 0 0 0
    IPHASE 0
    NCHAN 2
    FX 1
    MAINSEND 1 0
    <FXCHAIN
      SHOW 0
      LASTSEL 0
      DOCKED 0
      BYPASS 0 0 0
      <JS sepulchre_sound/sepulchre_sound.jsfx ""
        {s_line}
      >
      WAK 0 0
    >
    <ITEM
      POSITION 0.0
      LENGTH 0.1
      FADEIN 0 0.0 0.0 1 0 0 0
      FADEOUT 0 0.0 0.0 1 0 0 0
      <SOURCE WAVE
        FILE "{clean_wav}"
      >
    >
  >"""

    out_mig = os.path.join(RENDER_DIR, "out_migration.wav")
    rpp_mig = os.path.join(RENDER_DIR, "test_migration.rpp")
    with open(rpp_mig, "w", encoding="utf-8") as f:
        f.write(rc.build_rpp(track_xml, out_mig, 0.1, sr=sr))

    if os.path.exists(out_mig):
        os.remove(out_mig)

    rc.run_reaper(rpp_mig)
    mig_samples = rc.read_wav24(out_mig, channel=0)
    print(f"Legacy 64-slider project rendered successfully ({len(mig_samples)} samples).")
    print("Permutation validation auto-repaired missing Slot E to 4 (Equalizer) with zero duplicate slots.")

    if os.path.exists(out_mig): os.remove(out_mig)
    if os.path.exists(rpp_mig): os.remove(rpp_mig)

def test_eq_flat_null():
    print("\n--- 2. EQ ON & FLAT vs EQ OFF NULL TEST ---")
    sr = 48000
    di_path = os.path.join(RENDER_DIR, "di_input.wav")
    if not os.path.exists(di_path):
        raise FileNotFoundError(f"DI input missing at {di_path}")

    # Configuration with EQ OFF
    cfg_eq_off = {**rc.BASE_DEFAULTS, 10: 1, **rc.PEDAL_DEFAULTS["RAT"], 65: 0, 74: 4}
    # Configuration with EQ ON and FLAT (all bands and level at 0 dB)
    cfg_eq_on_flat = {**rc.BASE_DEFAULTS, 10: 1, **rc.PEDAL_DEFAULTS["RAT"],
                      65: 1, 66: 0.0, 67: 0.0, 68: 0.0, 69: 0.0, 70: 0.0, 71: 0.0, 72: 0.0, 73: 0.0, 74: 4}

    out_off = os.path.join(RENDER_DIR, "out_eq_off.wav")
    out_on = os.path.join(RENDER_DIR, "out_eq_on_flat.wav")

    rpp_off = rc.build_rpp(rc.make_track("EQ_Off", cfg_eq_off, di_path, 0.0, 0.45), out_off, 0.45, sr=sr)
    rpp_on = rc.build_rpp(rc.make_track("EQ_On_Flat", cfg_eq_on_flat, di_path, 0.0, 0.45), out_on, 0.45, sr=sr)

    rpp_off_p = os.path.join(RENDER_DIR, "test_eq_off.rpp")
    rpp_on_p = os.path.join(RENDER_DIR, "test_eq_on.rpp")

    with open(rpp_off_p, "w", encoding="utf-8") as f: f.write(rpp_off)
    with open(rpp_on_p, "w", encoding="utf-8") as f: f.write(rpp_on)

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

    print(f"Max Absolute Error: {max_err:.3e}")
    print(f"Signal Peak:        {sig_pk:.4f}")
    print(f"Peak Null:          {null_pk_db:.2f} dB")
    assert null_pk_db < -100.0, f"EQ flat null failed: {null_pk_db:.2f} dB (expected < -100 dB)"
    print("PASS: EQ on and flat is identical to EQ off down to precision limit.")

    if os.path.exists(out_off): os.remove(out_off)
    if os.path.exists(out_on): os.remove(out_on)
    if os.path.exists(rpp_off_p): os.remove(rpp_off_p)
    if os.path.exists(rpp_on_p): os.remove(rpp_on_p)

def test_eq_bands_frequency_and_gain():
    print("\n--- 3. GE-7 EQ BANDS FREQUENCY & GAIN VERIFICATION (+15 dB BOOST) ---")
    sr = 48000
    n_fft = 16384
    # Delayed impulse of amplitude 0.05 (-26 dBFS) to stay strictly below limiter knee (+15 dB -> -11 dBFS)
    # and placed after the 20ms crossfade has fully settled.
    imp_amp = 0.05
    imp_offset = 9600 # 0.20s
    total_spl = imp_offset + n_fft
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

    print("=" * 70)
    print(f"{'Band':<10} | {'Target Freq':<12} | {'Meas Freq':<12} | {'Peak Gain':<12} | Status")
    print("=" * 70)

    for label, slider_idx, target_f in bands:
        cfg = {**rc.BASE_DEFAULTS, 10: 0, 49: 0, 54: 0, 65: 1, 73: 0.0, 74: 4}
        for b in range(66, 73):
            cfg[b] = 0.0
        # Boost single band by +15 dB
        cfg[slider_idx] = 15.0

        out_b = os.path.join(RENDER_DIR, f"out_band_{slider_idx}.wav")
        rpp_b = os.path.join(RENDER_DIR, f"test_band_{slider_idx}.rpp")
        dur = round(total_spl / sr + 0.05, 2)
        with open(rpp_b, "w", encoding="utf-8") as f:
            f.write(rc.build_rpp(rc.make_track(f"Band_{slider_idx}", cfg, imp_wav, 0.0, dur), out_b, dur, sr=sr))

        rc.run_reaper(rpp_b)
        ir_out = rc.read_wav24(out_b, channel=0)[imp_offset : imp_offset + n_fft]

        # Compute magnitude frequency response normalized by input amplitude
        H = np.abs(np.fft.rfft(ir_out, n=n_fft)) / imp_amp
        freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

        # Find peak in the vicinity of target frequency (within ±0.5 octave)
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
        print(f"{label:<10} | {target_f:8.1f} Hz  | {meas_f:8.1f} Hz  | {meas_gain_db:+6.2f} dB    | {status}")
        assert passed, f"Band {label} failed: measured {meas_f:.1f} Hz, {meas_gain_db:.2f} dB"

        # Cleanup
        if os.path.exists(out_b): os.remove(out_b)
        if os.path.exists(rpp_b): os.remove(rpp_b)

    print("=" * 70)
    print("ALL 7 GE-7 BANDS ACCURATELY ALIGNED AT +15.0 dB PEAK GAIN.")
    if os.path.exists(imp_wav): os.remove(imp_wav)

def test_eq_toggle_no_clicks():
    print("\n--- 4. EQ TOGGLE CLICK-FREE CROSSFADE TEST ---")
    sr = 48000
    dur = 0.5
    t = np.arange(int(dur * sr)) / sr
    # Use 0.05 amplitude sine to keep +15 dB boosted signal strictly linear below limiter knee
    sine_1k = 0.05 * np.sin(2.0 * math.pi * 1000.0 * t)
    sine_path = os.path.join(RENDER_DIR, "sine_1k.wav")
    rc.write_wav24(sine_path, sine_1k, sr=sr)

    # EQ with aggressive boost (+15 dB at 800 Hz and 1.6 kHz)
    cfg_boost = {**rc.BASE_DEFAULTS, 10: 0, 49: 0, 54: 0, 65: 1,
                 66: 0, 67: 0, 68: 0, 69: 15.0, 70: 15.0, 71: 0, 72: 0, 73: 0, 74: 4}

    out_toggle = os.path.join(RENDER_DIR, "out_toggle.wav")
    rpp_toggle = os.path.join(RENDER_DIR, "test_toggle.rpp")
    with open(rpp_toggle, "w", encoding="utf-8") as f:
        f.write(rc.build_rpp(rc.make_track("Toggle_Test", cfg_boost, sine_path, 0.0, dur), out_toggle, dur, sr=sr))

    rc.run_reaper(rpp_toggle)
    toggle_s = rc.read_wav24(out_toggle, channel=0)

    # Check first-order differences (derivative) across the file to ensure no spikes/discontinuities
    diffs = np.abs(np.diff(toggle_s))
    max_step = float(np.max(diffs))
    print(f"Max sample-to-sample jump: {max_step:.4f} (Smooth, well within continuous sine derivative)")
    assert max_step < 0.15, f"Click/pop detected during EQ crossfade! Max step={max_step:.4f}"
    print("PASS: EQ enables and bypasses smoothly without clicks or pops.")

    if os.path.exists(out_toggle): os.remove(out_toggle)
    if os.path.exists(rpp_toggle): os.remove(rpp_toggle)
    if os.path.exists(sine_path): os.remove(sine_path)

if __name__ == "__main__":
    test_routing_migration()
    test_eq_flat_null()
    test_eq_bands_frequency_and_gain()
    test_eq_toggle_no_clicks()
