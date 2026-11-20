import os
import sys
import math
import numpy as np

# Path resolution
RENDER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(RENDER_DIR, "..", ".."))
sys.path.insert(0, os.path.join(REPO_DIR, "tests"))
sys.path.insert(0, RENDER_DIR)

import render_common as rc

def bq_hp(freq, q, sr):
    w0 = 2 * math.pi * freq / sr
    alpha = math.sin(w0) / (2 * q)
    cosw0 = math.cos(w0)
    b0 = (1 + cosw0) / 2
    b1 = -(1 + cosw0)
    b2 = (1 + cosw0) / 2
    a0 = 1 + alpha
    a1 = -2 * cosw0
    a2 = 1 - alpha
    return np.array([b0/a0, b1/a0, b2/a0, a1/a0, a2/a0])

def bq_lp(freq, q, sr):
    w0 = 2 * math.pi * freq / sr
    alpha = math.sin(w0) / (2 * q)
    cosw0 = math.cos(w0)
    b0 = (1 - cosw0) / 2
    b1 = 1 - cosw0
    b2 = (1 - cosw0) / 2
    a0 = 1 + alpha
    a1 = -2 * cosw0
    a2 = 1 - alpha
    return np.array([b0/a0, b1/a0, b2/a0, a1/a0, a2/a0])

def bq_ls(freq, gain_db, sr):
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2 * math.pi * freq / sr
    cosw0 = math.cos(w0)
    sinw0 = math.sin(w0)
    alpha = sinw0 / 2.0 * math.sqrt(2.0)
    b0 = A * ((A + 1) - (A - 1) * cosw0 + 2 * math.sqrt(A) * alpha)
    b1 = 2 * A * ((A - 1) - (A + 1) * cosw0)
    b2 = A * ((A + 1) - (A - 1) * cosw0 - 2 * math.sqrt(A) * alpha)
    a0 = (A + 1) + (A - 1) * cosw0 + 2 * math.sqrt(A) * alpha
    a1 = -2 * ((A - 1) + (A + 1) * cosw0)
    a2 = (A + 1) + (A - 1) * cosw0 - 2 * math.sqrt(A) * alpha
    return np.array([b0/a0, b1/a0, b2/a0, a1/a0, a2/a0])

def apply_bq(b, x):
    y = np.zeros_like(x)
    s1 = s2 = 0.0
    for i in range(len(x)):
        v = x[i]
        out = b[0] * v + s1
        s1 = b[1] * v - b[3] * out + s2
        s2 = b[2] * v - b[4] * out
        y[i] = out
    return y

def test_exact_ir_null_and_continuity():
    srate = 48000.0
    ir_slot0_path = os.path.join(rc.IR_DIR, "01_BlackWizard_Center.wav")
    if not os.path.exists(ir_slot0_path):
        raise FileNotFoundError(f"Slot 0 IR WAV not found at {ir_slot0_path}")

    # 1. Load slot 0 raw IR (matching load_ir_slot's 8192-sample raw cap)
    raw_ir = rc.read_wav24(ir_slot0_path, channel=0)[:8192]
    ir_srate = 44100.0
    isc = ir_srate / srate
    ir_len = min(8192, min(2048, int(len(raw_ir) / isc)))

    # Linear interpolation resampler + 2.5 ms raised-cosine truncation fade-out matching prepare_ir_fft()
    resampled_ir = np.zeros(ir_len)
    for i in range(ir_len):
        ipos = int(i * isc)
        frac = i * isc - ipos
        p0 = raw_ir[ipos]
        p1 = raw_ir[min(len(raw_ir) - 1, ipos + 1)]
        resampled_ir[i] = p0 * (1.0 - frac) + p1 * frac

    fade_n = min(int(0.0025 * srate), int(ir_len * 0.1))
    if fade_n > 1 and int(len(raw_ir) / isc) > ir_len:
        for fi in range(fade_n):
            resampled_ir[ir_len - fade_n + fi] *= 0.5 * (1.0 + math.cos(math.pi * (fi + 1) / fade_n))

    # Exactly reproduce prepare_ir_fft energy calculation
    n = ir_len + 2048
    scratch = np.zeros(n)
    scratch[:ir_len] = resampled_ir
    cab_hp = bq_hp(85.0, 0.7071, srate)
    irw1 = bq_hp(90.0, 0.7071, srate)
    irw2 = bq_ls(500.0, 12.0, srate)
    irw3 = bq_lp(6000.0, 0.7071, srate)

    scratch = apply_bq(cab_hp, scratch)
    scratch = apply_bq(irw1, scratch)
    scratch = apply_bq(irw2, scratch)
    scratch = apply_bq(irw3, scratch)

    e = np.sum(scratch ** 2)
    IR_E48 = 0.232396
    norm_g = math.sqrt(IR_E48 * (48000.0 / srate) / e) if e > 1e-10 else 1.0

    # Round 68: generic IR_E48 + ear-match offset (+3.8 dB); per-slot trim table removed for user-loadable IRs
    norm_g *= 10.0 ** (3.8 / 20.0)

    # Base clean track settings for IR test (valid sliders only)
    base_clean = {
        1: 0.0, 2: 40.0, 4: 0, 10: 0, 20: 0, 40: 0,
        49: 1, 51: 0.0, 53: "01_BlackWizard_Center.wav", 54: 0, 58: 50.0, 65: 0, 76: 1
    }

    # Render impulse test
    impulse_wav = os.path.join(RENDER_DIR, "impulse.wav")
    if not os.path.exists(impulse_wav):
        imp_data = np.zeros(int(0.25 * srate))
        imp_data[0] = 0.707
        rc.write_wav24(impulse_wav, imp_data, sr=int(srate))

    out_impulse = os.path.join(RENDER_DIR, "out_impulse.wav")
    rpp_imp = rc.build_rpp(rc.make_track("Impulse_Slot0", base_clean, impulse_wav, pos=0.0, length=0.25), out_impulse, 0.25)
    rpp_imp_path = os.path.join(RENDER_DIR, "test_impulse.rpp")
    with open(rpp_imp_path, "w", encoding="utf-8") as f:
        f.write(rpp_imp)

    if os.path.exists(out_impulse):
        os.remove(out_impulse)
    rc.run_reaper(rpp_imp_path)

    # Input signal: impulse from impulse.wav through bq_in_hp (40 Hz HPF)
    x_in = np.zeros(4096)
    x_in[0] = rc.read_wav24(impulse_wav, channel=0)[0]
    in_hp = bq_hp(40.0, 0.7071, srate)
    x_filtered = apply_bq(in_hp, x_in)

    # Direct convolution with normalized IR and post-convolution cab_hp (85 Hz)
    conv_out = np.convolve(x_filtered, resampled_ir * norm_g)[:4096]
    expected = apply_bq(cab_hp, conv_out)

    # In REAPER with PDC delay compensation active (pdc_delay = 128),
    # rendered signal aligns perfectly starting at sample 0.
    # Note: Round 35 added 0.84 scaling for Amp OFF (slider54 = 0) in proc_amp().
    rendered = rc.read_wav24(out_impulse, channel=0) / 0.84
    rend_seg = rendered[:2048]
    exp_seg = expected[:2048]

    diff = rend_seg - exp_seg
    max_err = float(np.max(np.abs(diff)))
    sig_peak = float(np.max(np.abs(exp_seg)))
    null_db = 20.0 * math.log10(max(1e-12, max_err) / max(1e-12, sig_peak))
    rms_diff = math.sqrt(np.mean(diff ** 2))
    rms_sig = math.sqrt(np.mean(exp_seg ** 2))
    null_rms_db = 20.0 * math.log10(max(1e-12, rms_diff) / max(1e-12, rms_sig))

    print("\n--- UPOLS EXACT IMPULSE NULL REPORT ---")
    print(f"Signal Peak:                 {sig_peak:.6f}")
    print(f"Max Absolute Error:          {max_err:.3e}")
    print(f"Peak Null vs Expected:       {null_db:.2f} dB")
    print(f"RMS Null vs Expected:        {null_rms_db:.2f} dB")
    assert null_db < -100.0, f"Impulse null failed: peak null={null_db:.2f} dB"

    # 2. Block-Boundary Continuity tests (100 Hz and 2578 Hz)
    print("\n--- UPOLS 128-SAMPLE BLOCK BOUNDARY CONTINUITY REPORT ---")
    for f_hz in [100, 2578]:
        sine_wav = os.path.join(RENDER_DIR, f"sine_{f_hz}.wav")
        if not os.path.exists(sine_wav):
            t = np.arange(int(0.25 * srate)) / srate
            s_data = 0.25 * np.sin(2.0 * math.pi * f_hz * t)
            rc.write_wav24(sine_wav, s_data, sr=int(srate))

        out_sine = os.path.join(RENDER_DIR, f"out_sine_{f_hz}.wav")
        rpp_sine = rc.build_rpp(rc.make_track(f"Sine_{f_hz}", base_clean, sine_wav, pos=0.0, length=0.25), out_sine, 0.25)
        rpp_sine_path = os.path.join(RENDER_DIR, f"test_sine_{f_hz}.rpp")
        with open(rpp_sine_path, "w", encoding="utf-8") as f:
            f.write(rpp_sine)

        if os.path.exists(out_sine):
            os.remove(out_sine)
        rc.run_reaper(rpp_sine_path)

        sine_s = rc.read_wav24(out_sine, channel=0)
        boundary_jumps = []
        normal_jumps = []
        for i in range(512, len(sine_s) - 1):
            jump = abs(sine_s[i+1] - sine_s[i])
            if (i + 1) % 128 == 0:
                boundary_jumps.append(jump)
            else:
                normal_jumps.append(jump)
        max_b = max(boundary_jumps)
        max_n = max(normal_jumps)
        print(f"Continuity {f_hz:4d} Hz -> Max jump at 128-spl boundary: {max_b:.6f} vs Max normal jump: {max_n:.6f} (Clean)")
        assert max_b <= max_n * 1.05, f"Discontinuity at 128-sample UPOLS block boundary for {f_hz} Hz!"

    # Clean up test RPPs and WAVs
    for p in [rpp_imp_path, os.path.join(RENDER_DIR, "test_sine_100.rpp"), os.path.join(RENDER_DIR, "test_sine_2578.rpp"),
              out_impulse, os.path.join(RENDER_DIR, "out_sine_100.wav"), os.path.join(RENDER_DIR, "out_sine_2578.wav")]:
        if os.path.exists(p):
            os.remove(p)

    print("\nALL UPOLS IMPULSE NULL AND BLOCK CONTINUITY CHECKS PASSED.")

if __name__ == "__main__":
    test_exact_ir_null_and_continuity()
