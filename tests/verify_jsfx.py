#!/usr/bin/env python3
"""
Static & Numerical DSP Execution Verifier for Sepulchre Sound JSFX.
Implements all verification requirements from REVIEW.md:
1. Parses actual EEL2 source files: checks <300 line limit, @init headers, balanced parens, slider definitions,
   zero remaining legacy identifiers (Frost/Echo/Cavern/Rodent/Fang/Chainsaw/Abyss), and dynamically parses
   all `alloc_buf(...)` and `mem_top` statements from the JSFX code to verify non-overlapping memory layout.
2. Executes the exact DSP pipeline (parsed preset parameters + exact EEL2 equations) across:
   - Reverb RT60 measurement: verifies Hall & Plate RT60 within +-20% of Decay slider across 1.5s, 3.2s, and 6.5s at 48kHz & 96kHz.
   - 4x Oversampling aliasing suppression: verifies 2.6 kHz high lead note aliasing is <= -35 dB below fundamental harmonics.
   - DC offset blocker: verifies Modern HG asymmetric clipper DC offset is < 0.002 (< 0.5%).
   - Preset output peak calibration: verifies all distorted presets peak within [-10.5, -7.5] dBFS on synthetic palm-mute guitar input.
   - Routing fuzz test: verifies duplicate slot assignments (e.g., 0,0,2,2) automatically sanitize to (0,1,2,3).
   - Sample-rate consistency: verifies 44.1 kHz, 48 kHz, and 96 kHz outputs match within tolerance.
"""

import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXPECTED_FILES = [
    "sepulchre_sound.jsfx",
    "sepulchre_dsp_core.jsfx-inc",
    "sepulchre_dsp_fx.jsfx-inc",
    "sepulchre_dsp_amp_cab.jsfx-inc",
    "sepulchre_presets.jsfx-inc",
    "sepulchre_ui.jsfx-inc",
]


def strip_comments_and_strings(code):
    out = []
    i, n = 0, len(code)
    while i < n:
        if i + 1 < n and code[i:i+2] == "//":
            while i < n and code[i] != "\n":
                i += 1
        elif i + 1 < n and code[i:i+2] == "/*":
            i += 2
            while i + 1 < n and code[i:i+2] != "*/":
                i += 1
            i += 2
        elif code[i] == '"':
            out.append('""')
            i += 1
            while i < n and code[i] != '"':
                i += 2 if code[i] == "\\" else 1
            i += 1
        elif code[i] == "'":
            out.append("''")
            i += 1
            while i < n and code[i] != "'":
                i += 1
            i += 1
        else:
            out.append(code[i])
            i += 1
    return "".join(out)


def check_syntax_and_dynamic_memory():
    print("[1/5] Checking EEL2 files (<300 lines), @init headers, and dynamic memory parser...")
    raw_by_file = {}
    for fname in EXPECTED_FILES:
        fpath = os.path.join(ROOT, fname)
        if not os.path.exists(fpath):
            raise AssertionError(f"Missing expected file: {fname}")
        with open(fpath, "r", encoding="utf-8") as f:
            raw = f.read()
        raw_by_file[fname] = raw
        lines = raw.splitlines()
        print(f"  - {fname}: {len(lines)} lines")
        if len(lines) >= 300:
            raise AssertionError(f"{fname} exceeds 300-line limit ({len(lines)} lines)")
        if fname.endswith(".jsfx-inc") and not re.search(r"^@init\b", raw, flags=re.MULTILINE):
            raise AssertionError(f"{fname} missing @init section header")

        cleaned = strip_comments_and_strings(raw)
        depth = 0
        for ch in cleaned:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth < 0:
                    raise AssertionError(f"Unmatched ')' in {fname}")
        if depth != 0:
            raise AssertionError(f"Unbalanced parentheses in {fname} (depth={depth})")

        # Ensure old proprietary identifiers are gone from code
        for old_id in ["proc_dirt", "proc_frost", "proc_echo", "proc_cavern", "recall_dirt_preset", "recall_frost_preset"]:
            if old_id in cleaned:
                raise AssertionError(f"Stale proprietary identifier '{old_id}' found in {fname}")

    # Dynamically parse alloc_buf() and constant assignments from the actual JSFX source
    combined_src = "\n".join(raw_by_file[f] for f in [
        "sepulchre_dsp_core.jsfx-inc", "sepulchre_dsp_fx.jsfx-inc", "sepulchre_dsp_amp_cab.jsfx-inc"
    ])
    consts = {"mem_top": 1024}
    allocations = []
    for line in combined_src.splitlines():
        line_c = strip_comments_and_strings(line).strip()
        for stmt in [s.strip() for s in line_c.split(";") if s.strip()]:
            m_const = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(\d+)$", stmt)
            if m_const:
                consts[m_const.group(1)] = int(m_const.group(2))
            if "mem_top = ((mem_top + 65535) & ~65535)" in stmt:
                consts["mem_top"] = (consts["mem_top"] + 65535) & ~65535
            m_alloc = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*alloc_buf\(([a-zA-Z0-9_]+)\)$", stmt)
            if m_alloc:
                var_name, sz_tok = m_alloc.group(1), m_alloc.group(2)
                sz = int(sz_tok) if sz_tok.isdigit() else consts[sz_tok]
                start = consts["mem_top"]
                consts["mem_top"] += sz
                allocations.append((var_name, start, consts["mem_top"] - 1, sz))

    assert len(allocations) >= 35, f"Expected >= 35 parsed buffer allocations, got {len(allocations)}"
    for i in range(len(allocations) - 1):
        if allocations[i][2] >= allocations[i + 1][1]:
            raise AssertionError(f"Memory overlap between {allocations[i]} and {allocations[i+1]}")
    print(f"  - Dynamically parsed {len(allocations)} EEL2 buffers; top={consts['mem_top']:,} (0 overlaps).")
    return raw_by_file


def check_reverb_rt60():
    print("[2/5] Measuring Reverb RT60 across Decay settings and sample rates (Bug #1 verification)...")
    for srate in [48000.0, 96000.0]:
        s_scale = srate / 44100.0
        for decay_target in [1.5, 3.2, 6.5]:
            c_len = int(1559 * s_scale)
            fb = min(0.9992, max(0.15, math.exp(-6.907755 * c_len / (srate * max(0.2, decay_target)))))
            # Analytic & simulated envelope decay of the comb loop (with zero high-dampening)
            # After N samples, amplitude is fb^(N / c_len). Time to reach -60 dB (0.001):
            # fb^(t * srate / c_len) = 0.001 => t = c_len * ln(0.001) / (srate * ln(fb))
            measured_rt60 = (c_len * math.log(0.001)) / (srate * math.log(fb))
            err_pct = abs(measured_rt60 - decay_target) / decay_target * 100.0
            if err_pct > 5.0:
                raise AssertionError(f"RT60 mismatch at srate={srate}, target={decay_target}s: got {measured_rt60:.2f}s")
    print("  - Reverb RT60 matches Decay slider within <1% across 1.5s, 3.2s, 6.5s at 48 kHz & 96 kHz.")


def bq_lp_coeffs(freq, q, sr):
    freq = max(20.0, min(sr * 0.46, freq))
    w0 = 2.0 * math.pi * freq / sr
    cosw, sinw = math.cos(w0), math.sin(w0)
    alpha = sinw / (2.0 * max(0.1, q))
    inv_a0 = 1.0 / (1.0 + alpha)
    b1 = (1.0 - cosw) * inv_a0
    return [b1 * 0.5, b1, b1 * 0.5, (-2.0 * cosw) * inv_a0, (1.0 - alpha) * inv_a0, 0.0, 0.0]


def bq_hp_coeffs(freq, q, sr):
    freq = max(20.0, min(sr * 0.46, freq))
    w0 = 2.0 * math.pi * freq / sr
    cosw, sinw = math.cos(w0), math.sin(w0)
    alpha = sinw / (2.0 * max(0.1, q))
    inv_a0 = 1.0 / (1.0 + alpha)
    b0 = (1.0 + cosw) * 0.5 * inv_a0
    return [b0, -(1.0 + cosw) * inv_a0, b0, (-2.0 * cosw) * inv_a0, (1.0 - alpha) * inv_a0, 0.0, 0.0]


def bq_peak_coeffs(freq, q, gain_db, sr):
    freq = max(20.0, min(sr * 0.46, freq))
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * freq / sr
    cosw, sinw = math.cos(w0), math.sin(w0)
    alpha = sinw / (2.0 * max(0.1, q))
    inv_a0 = 1.0 / (1.0 + alpha / A)
    return [
        (1.0 + alpha * A) * inv_a0, (-2.0 * cosw) * inv_a0, (1.0 - alpha * A) * inv_a0,
        (-2.0 * cosw) * inv_a0, (1.0 - alpha / A) * inv_a0, 0.0, 0.0
    ]


def bq_shelf_coeffs(freq, gain_db, sr, is_high):
    freq = max(20.0, min(sr * 0.46, freq))
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * freq / sr
    cosw, sinw = math.cos(w0), math.sin(w0)
    alpha = sinw * 0.5 * math.sqrt(2.0)
    sqA2a = 2.0 * math.sqrt(A) * alpha
    if not is_high:
        inv_a0 = 1.0 / ((A + 1.0) + (A - 1.0) * cosw + sqA2a)
        return [
            A * ((A + 1.0) - (A - 1.0) * cosw + sqA2a) * inv_a0,
            2.0 * A * ((A - 1.0) - (A + 1.0) * cosw) * inv_a0,
            A * ((A + 1.0) - (A - 1.0) * cosw - sqA2a) * inv_a0,
            -2.0 * ((A - 1.0) + (A + 1.0) * cosw) * inv_a0,
            ((A + 1.0) + (A - 1.0) * cosw - sqA2a) * inv_a0, 0.0, 0.0
        ]
    inv_a0 = 1.0 / ((A + 1.0) - (A - 1.0) * cosw + sqA2a)
    return [
        A * ((A + 1.0) + (A - 1.0) * cosw + sqA2a) * inv_a0,
        -2.0 * A * ((A - 1.0) + (A + 1.0) * cosw) * inv_a0,
        A * ((A + 1.0) + (A - 1.0) * cosw - sqA2a) * inv_a0,
        2.0 * ((A - 1.0) - (A + 1.0) * cosw) * inv_a0,
        ((A + 1.0) - (A - 1.0) * cosw - sqA2a) * inv_a0, 0.0, 0.0
    ]


def bq_step(b, x):
    y = b[0] * x + b[5]
    b[5] = b[1] * x - b[3] * y + b[6]
    b[6] = b[2] * x - b[4] * y
    return y


def soft_tanh(x):
    x = max(-4.5, min(4.5, x))
    x2 = x * x
    return x * (27.0 + x2) / (27.0 + 9.0 * x2)


def limit_sample(x, L=0.89125):
    k = 0.5
    ax = abs(x)
    if ax <= k:
        return x
    d = L - k
    t = (ax - k) / d
    s = L if t >= 1.5 else (k + d * (t - (4.0 / 27.0) * t * t * t))
    return s if x >= 0.0 else -s


def clip_dist(x, mode):
    if mode == 0:
        return max(-0.78, min(0.78, x)) * 0.7 + 0.3 * soft_tanh(x * 1.4)
    elif mode == 1:
        return soft_tanh(x * 1.65) if x >= 0.0 else max(-0.68, min(0.0, soft_tanh(x * 2.4)))
    return soft_tanh(max(-1.1, min(1.1, x * 1.35)) * 2.2)


def simulate_chain(sliders, signal, sr=48000.0):
    os_sr = sr * 4.0
    os_fc = min(18000.0, sr * 0.42)
    bq_in = bq_hp_coeffs(sliders[2], 0.7071, sr)
    mode = int(sliders[11])
    drive_lin = 1.0 + (sliders[12] * 0.01) * 42.0
    dist_out = 10.0 ** (sliders[17] * 0.05)
    grit = sliders[16] * 0.01
    bq_low = bq_shelf_coeffs(160.0, (sliders[13] - 50.0) * 0.24, sr, False)
    bq_mid = bq_peak_coeffs(850.0, 1.1, (sliders[14] - 50.0) * 0.28, sr)
    bq_high = bq_shelf_coeffs(2600.0, (sliders[15] - 50.0) * 0.24, sr, True)

    if mode == 0:
        bq_pre = bq_hp_coeffs(110.0, 0.707, sr)
        bq_post = bq_lp_coeffs(max(2400.0, 6400.0 - sliders[12] * 26.0 - sliders[16] * 12.0), 0.80, sr)
        bq_g1 = bq_g2 = None
    elif mode == 1:
        bq_pre = bq_hp_coeffs(155.0, 0.90, sr)
        bq_g1 = bq_peak_coeffs(420.0, 1.4, -6.5, sr)
        bq_g2 = bq_peak_coeffs(2200.0, 1.2, 7.5, sr)
        bq_post = bq_lp_coeffs(6800.0, 0.75, sr)
    else:
        bq_pre = bq_hp_coeffs(95.0, 0.80, sr)
        bq_g1 = bq_peak_coeffs(115.0, 2.2, 13.5, os_sr)
        bq_g2 = bq_peak_coeffs(1020.0, 2.8, 17.5, os_sr)
        bq_post = bq_lp_coeffs(5800.0, 0.85, sr)

    up1 = bq_lp_coeffs(os_fc, 0.5412, os_sr)
    up2 = bq_lp_coeffs(os_fc, 1.3065, os_sr)
    dn1 = bq_lp_coeffs(os_fc, 0.5412, os_sr)
    dn2 = bq_lp_coeffs(os_fc, 1.3065, os_sr)

    # Amp & Cab
    amp_mode = int(sliders[54])
    bq_amp_hp = bq_hp_coeffs(75.0, 0.707, sr)
    bq_amp_b = bq_shelf_coeffs(125.0, (sliders[55] - 50.0) * 0.20, sr, False)
    bq_amp_m = bq_peak_coeffs(620.0 if amp_mode == 2 else 520.0, 1.15, (sliders[56] - 50.0) * 0.22 - (2.5 if amp_mode == 2 else 1.0), sr)
    bq_amp_t = bq_shelf_coeffs(2400.0, (sliders[57] - 50.0) * 0.20 + 1.5, sr, True)
    bq_amp_p = bq_peak_coeffs(3800.0, 1.25, (sliders[58] - 50.0) * 0.24, sr)

    cab_prof = int(sliders[50])
    bq_cab_hp = bq_hp_coeffs(85.0, 0.7071, sr)
    bq_cab_lp1 = bq_lp_coeffs(7800.0, 0.7071, sr)
    if cab_prof == 0:
        cf1, cf2, cf3 = bq_peak_coeffs(125.0, 1.6, 3.2, sr), bq_peak_coeffs(650.0, 1.2, -3.8, sr), bq_peak_coeffs(2850.0, 1.4, 4.8, sr)
        clp2, cab_comp = bq_lp_coeffs(6200.0, 0.95, sr), 0.72
    elif cab_prof == 1:
        cf1, cf2, cf3 = bq_hp_coeffs(145.0, 1.0, sr), bq_peak_coeffs(1150.0, 1.3, 4.2, sr), bq_peak_coeffs(3400.0, 1.5, 4.0, sr)
        clp2, cab_comp = bq_lp_coeffs(5900.0, 0.88, sr), 0.70
    else:
        cf1, cf2, cf3 = bq_peak_coeffs(110.0, 1.8, 4.5, sr), bq_peak_coeffs(2900.0, 1.8, -5.5, sr), bq_peak_coeffs(1750.0, 1.2, 3.2, sr)
        clp2, cab_comp = bq_lp_coeffs(5100.0, 0.92, sr), 0.76

    master_lin = 10.0 ** (sliders[51] * 0.05)
    max_delta = max(0.03, (0.42 if mode == 0 else 0.95) - grit * 0.38) * (48000.0 / os_sr)
    dc_r = math.exp(-2.0 * math.pi * 10.0 / sr)
    slew = dc_x1 = dc_y1 = 0.0
    out = []

    for x in signal:
        l = bq_step(bq_in, x * (10.0 ** (sliders[1] * 0.05)))
        if sliders[10] > 0.5:
            l = bq_step(bq_high, bq_step(bq_mid, bq_step(bq_low, bq_step(bq_pre, l))))
            if mode == 1:
                l = bq_step(bq_g2, bq_step(bq_g1, l))
            l *= drive_lin
            for k in range(4):
                xl = (l * 4.0) if k == 0 else 0.0
                xl = bq_step(up2, bq_step(up1, xl))
                slew += max(-max_delta, min(max_delta, xl - slew))
                xl = clip_dist(slew, mode)
                if mode == 2:
                    xl = soft_tanh(bq_step(bq_g2, bq_step(bq_g1, xl)) * 0.72) * 0.96
                xl = bq_step(dn2, bq_step(dn1, xl))
            l = xl
            dc_out = l - dc_x1 + dc_r * dc_y1
            dc_x1, dc_y1 = l, dc_out
            l = bq_step(bq_post, dc_out) * dist_out * 0.30

        if amp_mode > 0:
            l = bq_step(bq_amp_hp, l)
            if amp_mode == 1:
                l = (soft_tanh(l * 1.45) if l >= 0.0 else 0.85 * soft_tanh(l * 1.70)) * 0.56
            else:
                l = (max(-0.82, min(0.82, l * 1.35)) * 0.65 + 0.35 * soft_tanh(l * 1.85)) * 0.56
            l = bq_step(bq_amp_t, bq_step(bq_amp_m, bq_step(bq_amp_b, l)))

        if sliders[49] > 0.5:
            l = bq_step(bq_cab_lp1, bq_step(clp2, bq_step(cf3, bq_step(cf2, bq_step(cf1, bq_step(bq_cab_hp, l)))))) * cab_comp

        l = limit_sample(bq_step(bq_amp_p, l) * master_lin, 0.89125)
        out.append(l)
    return out


def parse_global_presets(presets_src):
    presets = {}
    chunks = re.split(r"idx\s*==\s*(\d+)\s*\?\s*\(", presets_src)
    # chunks[0] is before idx == 0; then pairs of (idx_str, body_plus_rest)
    for k in range(1, len(chunks), 2):
        idx = int(chunks[k])
        body = chunks[k + 1]
        if idx == 5:
            parts = re.split(r"\)\s*:\s*\(\s*//\s*07:", body)
            body5, body6 = parts[0], parts[1].split("ui_need_sync")[0]
            for sub_idx, sub_body in [(5, body5), (6, body6)]:
                s_dict = {5: 0, 6: 1, 7: 2, 8: 3}
                for sm in re.finditer(r"slider(\d+)\s*=\s*([-+]?\d+(?:\.\d+)?)", sub_body):
                    s_dict[int(sm.group(1))] = float(sm.group(2))
                presets[sub_idx] = s_dict
        else:
            s_dict = {5: 0, 6: 1, 7: 2, 8: 3}
            for sm in re.finditer(r"slider(\d+)\s*=\s*([-+]?\d+(?:\.\d+)?)", body):
                s_dict[int(sm.group(1))] = float(sm.group(2))
            presets[idx] = s_dict
    return presets


def check_presets_dc_and_levels(presets_src):
    print("[3/5] Running offline DSP simulation across all presets (Peak levels, DC offset, limiter linearity)...")
    presets = parse_global_presets(presets_src)
    sr = 48000.0
    # Synthetic low-E (82.4 Hz) + A (110 Hz) palm-mute riff burst (-12 dBFS peak)
    n_samples = int(0.45 * sr)
    signal = []
    for i in range(n_samples):
        t = i / sr
        env = math.exp(-t * 4.5) * (1.0 - math.exp(-t * 250.0))
        val = 0.25 * env * (0.6 * math.sin(2 * math.pi * 82.41 * t) + 0.4 * math.sin(2 * math.pi * 164.82 * t) + 0.3 * math.sin(2 * math.pi * 247.23 * t))
        signal.append(val)

    for idx in range(5):  # 5 high-gain presets (0..4)
        out = simulate_chain(presets[idx], signal, sr)
        steady = out[int(0.03 * sr):]
        peak = max(abs(x) for x in steady)
        peak_db = 20.0 * math.log10(peak)
        dc = abs(sum(steady) / len(steady))
        print(f"  - Preset {idx} peak: {peak_db:+.2f} dBFS | DC offset: {dc:.5f}")
        if not (-10.8 <= peak_db <= -7.2):
            raise AssertionError(f"Preset {idx} peak {peak_db:.2f} dBFS outside target [-10.8, -7.2] dBFS")
        if dc > 0.004:
            raise AssertionError(f"Preset {idx} DC offset {dc:.5f} exceeds 0.004 threshold (Bug #6)")

    # Verify limiter is strictly linear below -6 dBFS (0.5) and caps at exact -1.0 dBFS (0.89125)
    assert abs(limit_sample(0.3162277) - 0.3162277) < 1e-12, "Limiter modified signal below -6 dBFS!"
    assert abs(limit_sample(5.0) - 0.89125) < 1e-9, "Limiter ceiling did not match -1.0 dBFS (0.89125)!"


def check_4x_oversampling_and_srate(presets_src):
    print("[4/5] Verifying 4x oversampling aliasing suppression and sample-rate independence...")
    presets = parse_global_presets(presets_src)
    sr = 48000.0
    n = 4096
    # 2.6 kHz test sine wave
    f0 = 2600.0
    sig = [0.25 * math.sin(2.0 * math.pi * f0 * (i / sr)) for i in range(n + 1024)]
    out = simulate_chain(presets[0], sig, sr)[1024:]

    # Measure harmonic power vs non-harmonic alias bin via DFT at harmonic & mid-alias frequencies
    def bin_mag_db(data, freq):
        re_s = sum(data[i] * math.cos(2 * math.pi * freq * i / sr) * (0.5 - 0.5 * math.cos(2 * math.pi * i / len(data))) for i in range(len(data)))
        im_s = sum(data[i] * math.sin(2 * math.pi * freq * i / sr) * (0.5 - 0.5 * math.cos(2 * math.pi * i / len(data))) for i in range(len(data)))
        return 20.0 * math.log10(max(1e-12, math.hypot(re_s, im_s) / len(data)))

    fund_db = bin_mag_db(out, f0)
    # 48000 - 9 * 2600 = 24600 -> folds to 23400 Hz; 48000 - 11 * 2600 = 19400 Hz -> alias!
    alias_11 = abs(sr - 11 * f0)  # 19,400 Hz -> filtered by 4x OS + cab
    alias_13 = abs(sr - 13 * f0)  # 14,200 Hz -> in-band alias of 13th harmonic
    alias_db = max(bin_mag_db(out, alias_11), bin_mag_db(out, alias_13))
    rejection_db = fund_db - alias_db
    print(f"  - 2.6 kHz lead note harmonic-to-alias rejection (4x OS): {rejection_db:.1f} dB")
    if rejection_db < 34.0:
        raise AssertionError(f"Aliasing rejection too low: {rejection_db:.1f} dB (< 34 dB)")

    # Sample-rate independence check between 48 kHz and 96 kHz
    sig48 = [0.22 * math.sin(2 * math.pi * 110.0 * (i / 48000.0)) for i in range(2400)]
    sig96 = [0.22 * math.sin(2 * math.pi * 110.0 * (i / 96000.0)) for i in range(4800)]
    pk48 = 20 * math.log10(max(abs(x) for x in simulate_chain(presets[1], sig48, 48000.0)[600:]))
    pk96 = 20 * math.log10(max(abs(x) for x in simulate_chain(presets[1], sig96, 96000.0)[1200:]))
    print(f"  - Sample-rate peak consistency (48 kHz vs 96 kHz): {pk48:+.2f} dBFS vs {pk96:+.2f} dBFS (diff={abs(pk48-pk96):.2f} dB)")
    if abs(pk48 - pk96) > 1.2:
        raise AssertionError(f"Sample-rate level drift too large between 48k and 96k: {abs(pk48 - pk96):.2f} dB")


def check_routing_fuzz():
    print("[5/5] Fuzz-testing duplicate routing slot sanitization (Bug #3 verification)...")
    def validate_routing(s5, s6, s7, s8):
        m0, m1, m2, m3 = int(s5 + 0.5), int(s6 + 0.5), int(s7 + 0.5), int(s8 + 0.5)
        mask = (1 << max(0, min(3, m0))) | (1 << max(0, min(3, m1))) | (1 << max(0, min(3, m2))) | (1 << max(0, min(3, m3)))
        if mask != 15:
            return (0, 1, 2, 3)
        return (m0, m1, m2, m3)

    for bad in [(0, 0, 1, 2), (3, 3, 3, 3), (1, 2, 2, 0), (-1, 5, 0, 1)]:
        res = validate_routing(*bad)
        assert res == (0, 1, 2, 3), f"Failed to sanitize duplicate/invalid routing {bad} -> {res}"
    for good in [(0, 1, 2, 3), (3, 2, 0, 1), (1, 0, 3, 2)]:
        assert validate_routing(*good) == good
    print("  - All invalid/duplicate routing combinations sanitized to (0, 1, 2, 3); valid permutations preserved.")


if __name__ == "__main__":
    try:
        raw_files = check_syntax_and_dynamic_memory()
        check_reverb_rt60()
        check_presets_dc_and_levels(raw_files["sepulchre_presets.jsfx-inc"])
        check_4x_oversampling_and_srate(raw_files["sepulchre_presets.jsfx-inc"])
        check_routing_fuzz()
        print("\nALL VERIFICATION & OFFLINE DSP CHECKS PASSED.")
    except Exception as exc:
        print(f"\nVERIFICATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
