#!/usr/bin/env python3
"""
Static checks and offline DSP mirror for Sepulchre Sound (run before every commit).
1. Source checks: every JSFX file < 300 lines, @init headers, balanced parentheses, no unary '~', declared UI assets
   exist, non-overlapping alloc_buf() memory map, and the Round 2 invariants (no preset recall in @init,
   pdc_delay in @block, IR reload handler, no file I/O in coefficient updates, slider
   automation masks).
2. Python mirror of the pedals (8x oversampled), amp, IIR cab and limiter:
   - Round 59: loudness through the real slot-0 IR (read from outside the repo; skipped if absent), check [8/8];
   - every preset peaks below the -3.1 dBFS limiter knee with DC < 0.004 (IIR cab path); Round 58: preset loudness is
     calibrated from REAPER renders (WAV IR, chorus / reverb), not by this mirror;
   - in-band aliasing per pedal (2578 Hz tone);
   - no pedal filter with pole Q > 3.5 at any knob extreme (no ringing);
   - IR_E48 matches the IIR cab's weighted energy;
   - high-gain saturation curve (Metal Zone preset).
Round 30: the reverb RT60 and delay-bypass simulations were removed. They re-implemented formulas in Python without
reading the EEL2 source, so they could never catch a regression in the plugin.
"""

import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXPECTED_FILES = [
    "sepulchre_sound.jsfx",
    "sepulchre_dsp_core.jsfx-inc",
    "sepulchre_dsp_dist.jsfx-inc",
    "sepulchre_dsp_fx.jsfx-inc",
    "sepulchre_dsp_ir.jsfx-inc",
    "sepulchre_dsp_amp_cab.jsfx-inc",
    "sepulchre_presets.jsfx-inc",
    "sepulchre_ui.jsfx-inc",
    "sepulchre_ui_panels.jsfx-inc",
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


def check_syntax_and_r2_fixes():
    print("[1/9] Checking EEL2 files (<300 lines), dynamic memory map, and Round 2 bug-fix invariants...")
    raw_by_file = {}
    cleaned_by_file = {}
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
        cleaned_by_file[fname] = cleaned
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

    # Verify Round 2 & Round 3 invariants in cleaned EEL2 code:
    main_c = cleaned_by_file["sepulchre_sound.jsfx"]
    init_sec = main_c.split("@init")[1].split("@slider")[0]
    block_sec = main_c.split("@block")[1].split("@sample")[0]
    sample_sec = main_c.split("@sample")[1].split("@serialize")[0]
    assert "recall_global_preset" not in init_sec, "R2-1 regression: recall_global_preset called in @init!"
    assert "pdc_delay = ir_chunk_size" in block_sec, "R2-3 regression: pdc_delay not set in @block!"
    assert "load_ir" not in block_sec and "file_open" not in block_sec, "R71 regression: IR file I/O in @block!"
    assert "load_ir" not in sample_sec and "file_open" not in sample_sec, "R71 regression: IR file I/O in @sample!"
    assert "load_ir" not in cleaned_by_file["sepulchre_dsp_amp_cab.jsfx-inc"].split("update_amp_cab_coeffs")[1], \
        "R2-6 regression: IR file load called inside update_amp_cab_coeffs!"
    assert "slider_automate(2 ^ (id - 1), end_touch)" in cleaned_by_file["sepulchre_ui.jsfx-inc"], \
        "R2-5 regression: bitmask slider_automate missing in sepulchre_ui.jsfx-inc!"
    assert "slider_automate(slider51, end_touch)" in cleaned_by_file["sepulchre_ui.jsfx-inc"], \
        "R2-5 regression: direct sliderN reference for id > 30 missing in sepulchre_ui.jsfx-inc!"
    for fname, cl in cleaned_by_file.items():
        assert "& ~" not in cl, f"Invalid EEL2 unary '~' operator in {fname} ('~' is binary XOR in EEL2)!"

    # Verify all filename:N,<asset> image declarations in sepulchre_sound.jsfx exist on disk
    for m_fn in re.finditer(r"^filename:\d+,([^\r\n]+)$", raw_by_file["sepulchre_sound.jsfx"], flags=re.MULTILINE):
        asset_name = m_fn.group(1).strip()
        asset_path = os.path.join(ROOT, asset_name)
        assert os.path.exists(asset_path), f"Missing declared UI asset file: {asset_name}"

    # Dynamically parse alloc_buf() and constant assignments from the actual JSFX source
    combined_src = "\n".join(raw_by_file[f] for f in [
        "sepulchre_dsp_core.jsfx-inc", "sepulchre_dsp_dist.jsfx-inc", "sepulchre_dsp_fx.jsfx-inc",
        "sepulchre_dsp_amp_cab.jsfx-inc", "sepulchre_dsp_ir.jsfx-inc"
    ])
    consts = {"mem_top": 1024}
    allocations = []
    for line in combined_src.splitlines():
        line_c = strip_comments_and_strings(line).strip()
        for stmt in [s.strip() for s in line_c.split(";") if s.strip()]:
            m_const = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(\d+)$", stmt)
            if m_const:
                consts[m_const.group(1)] = int(m_const.group(2))
            if "mem_top = floor((mem_top + 65535) / 65536) * 65536" in stmt:
                consts["mem_top"] = ((consts["mem_top"] + 65535) // 65536) * 65536
            m_alloc = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*alloc_buf\(([a-zA-Z0-9_]+)\)$", stmt)
            if m_alloc:
                var_name, sz_tok = m_alloc.group(1), m_alloc.group(2)
                sz = int(sz_tok) if sz_tok.isdigit() else consts[sz_tok]
                start = consts["mem_top"]
                consts["mem_top"] += sz
                allocations.append((var_name, start, consts["mem_top"] - 1, sz))

    assert len(allocations) >= 40, f"Expected >= 40 parsed buffer allocations, got {len(allocations)}"
    for i in range(len(allocations) - 1):
        if allocations[i][2] >= allocations[i + 1][1]:
            raise AssertionError(f"Memory overlap between {allocations[i]} and {allocations[i+1]}")
    print(f"  - Dynamically parsed {len(allocations)} EEL2 buffers; top={consts['mem_top']:,} (0 overlaps).")
    print("  - Verified R2-1..R2-6 invariants in EEL2 AST.")
    return raw_by_file


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
    x = max(-3.0, min(3.0, x))
    x2 = x * x
    return x * (27.0 + x2) / (27.0 + 9.0 * x2)


def limit_sample(x, L=0.89125):
    k = 0.7
    ax = abs(x)
    if ax <= k:
        return x
    d = L - k
    t = (ax - k) / d
    s = L if t >= 1.5 else (k + d * (t - (4.0 / 27.0) * t * t * t))
    return s if x >= 0.0 else -s


# ---------- Pedal models: line-for-line mirror of sepulchre_dsp_dist.jsfx-inc (8x oversampled) ----------
DIST_OS = 8
SLIDER_DEFAULTS = {}


def load_slider_defaults():
    src = open(os.path.join(ROOT, "sepulchre_sound.jsfx"), "r", encoding="utf-8").read()
    for m in re.finditer(r"^slider(\d+):([-+]?\d+(?:\.\d+)?)<", src, flags=re.MULTILINE):
        SLIDER_DEFAULTS[int(m.group(1))] = float(m.group(2))


def a_taper(k):
    return (10.0 ** (2.0 * k) - 1.0) / 99.0


def sclip(x, v):
    y = x / v
    return v * y / (1.0 + y * y * y * y) ** 0.25


def dclip(x, v, p):
    y = x / v
    return v * y / (1.0 + abs(y) ** p) ** (1.0 / p)


def aclip(x, vp, vn):
    return sclip(x, vp) if x >= 0 else sclip(x, vn)


def gyro_peak_coeffs(f, qg, db, sr):
    return bq_peak_coeffs(f, qg / 10.0 ** (abs(db) / 40.0), db, sr)


MT_MK, HM_MK = 0.54, 1.6


def unity():
    return [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def pedal_setup(s, sr):
    os_sr = sr * DIST_OS
    c1x = lambda fc: math.exp(-2 * math.pi * min(fc, 0.45 * os_sr) / os_sr)
    c1b = lambda fc: math.exp(-2 * math.pi * min(fc, 0.45 * sr) / sr)
    P = {"ped": int(s[11] + 0.5), "post": [unity() for _ in range(6)]}
    if P["ped"] == 0:
        rd = 100000 * a_taper(s[26] * 0.1)
        P.update(kA=rd / 560, kB=rd / 47, a60=c1x(60), a15=c1x(1540), slew=300000 / os_sr,
                 aA=c1x(min(316000 / (1 + rd / 560), 1 / (2 * math.pi * rd * 1e-10)) if rd > 0 else 1e9),
                 aB=c1x(min(316000 / (1 + rd / 43), 1 / (2 * math.pi * rd * 1e-10)) if rd > 0 else 1e9),
                 af=c1b(1 / (2 * math.pi * (1500 + 100000 * a_taper(s[27] * 0.1)) * 3.3e-9)),
                 mk=1.6 * a_taper(s[28] * 0.1))
    elif P["ped"] == 1:
        rd = 100000 * s[29] * 0.1
        P.update(k=rd / 4700, a33=c1x(33), a72=c1x(72), aC7=c1x(1 / (2 * math.pi * max(rd, 1) * 1e-10)), a72k=c1x(7200),
                 alp=c1b(234), ahp=c1b(1063), tone=s[37] * 0.1, mk=3.96 * a_taper(s[38] * 0.1))
    elif P["ped"] == 2:
        rd = 1000 + 250000 * a_taper(s[39] * 0.1)
        P.update(G=1 + rd / 1000, a106=c1x(106), a72k=c1x(7200), a680=c1x(680), a48=c1x(48),
                 aC28=c1x(1 / (2 * math.pi * rd * 47e-12)), hump=gyro_peak_coeffs(960, 1.66, 36, os_sr),
                 dco=dclip(0.08, 0.65, 1.8), aP=c1b(5000), kP=0.316, mk=MT_MK * a_taper(s[61] * 0.1))
        P["post"] = [bq_lp_coeffs(9000, 0.707, sr), gyro_peak_coeffs(105, 1.0, 4, sr), gyro_peak_coeffs(4900, 1.0, 6, sr),
                     gyro_peak_coeffs(110, 1.5, (s[47] - 5) * 3.2, sr), bq_shelf_coeffs(3000, (s[46] - 5) * 3.2, sr, True),
                     gyro_peak_coeffs(300 * (4000 / 300) ** (s[59] * 0.1), 1.2, (s[48] - 5) * 2.4, sr)]
    else:
        t = a_taper(s[62] * 0.1)
        P.update(g1=1 + 2 * t, G=3 + 60 * t, K=1 + 9 * t, a40=c1x(40), a720=c1x(720), aT=c1x(9000), a16=c1x(8000),
                 mk=HM_MK * a_taper(s[9] * 0.1),
                 eq=[gyro_peak_coeffs(88, 1.2, (s[63] - 5) * 3.2, os_sr), gyro_peak_coeffs(920, 2.0, (s[64] - 5) * 1.8, os_sr),
                     gyro_peak_coeffs(1200, 2.0, (s[64] - 5) * 1.8, os_sr)])
    return P


def pedal_os(P, st, x):
    ped = P["ped"]
    if ped == 0:
        st[1] = (1 + P["a60"]) * 0.5 * (x - st[0]) + P["a60"] * st[1]; st[0] = x
        st[3] = (1 + P["a15"]) * 0.5 * (x - st[2]) + P["a15"] * st[3]; st[2] = x
        st[4] = st[1] * P["kA"] + P["aA"] * (st[4] - st[1] * P["kA"])
        st[5] = st[3] * P["kB"] + P["aB"] * (st[5] - st[3] * P["kB"])
        v = sclip(x + st[4] + st[5], 4.0)
        st[6] += max(-P["slew"], min(P["slew"], v - st[6]))
        return dclip(st[6], 0.6, 2.5)
    if ped == 1:
        st[1] = (1 + P["a33"]) * 0.5 * (x - st[0]) + P["a33"] * st[1]; st[0] = x
        b = aclip(st[1] * 56, 4.0, 3.0)
        st[3] = (1 + P["a72"]) * 0.5 * (b - st[2]) + P["a72"] * st[3]; st[2] = b
        v = b + P["k"] * st[3]
        st[4] = v + P["aC7"] * (st[4] - v)
        v = sclip(st[4], 4.0)
        st[5] = v + P["a72k"] * (st[5] - v)
        return dclip(st[5], 0.7, 2.5)
    if ped == 2:
        h = P["hump"]
        st[1] = (1 + P["a106"]) * 0.5 * (x - st[0]) + P["a106"] * st[1]; st[0] = x
        y = h[0] * st[1] + st[2]; st[2] = h[1] * st[1] - h[3] * y + st[3]; st[3] = h[2] * st[1] - h[4] * y
        st[4] = y + P["a72k"] * (st[4] - y)
        v = sclip(st[4], 4.0) * 0.5
        st[8] = v + P["a680"] * (st[8] - v); v = st[8]
        st[6] = (1 + P["a48"]) * 0.5 * (v - st[5]) + P["a48"] * st[6]; st[5] = v
        w = v + (P["G"] - 1) * st[6]
        st[7] = w + P["aC28"] * (st[7] - w)
        return dclip(sclip(st[7], 4.0) + 0.08, 0.65, 1.8) - P["dco"]
    st[1] = (1 + P["a40"]) * 0.5 * (x - st[0]) + P["a40"] * st[1]; st[0] = x
    v = aclip(st[1] * P["g1"], 4.0, 2.0)
    st[3] = (1 + P["a720"]) * 0.5 * (v - st[2]) + P["a720"] * st[3]; st[2] = v
    w = v + dclip(P["G"] * st[3], 0.6, 2.5)
    st[4] = w + P["aT"] * (st[4] - w); w = sclip(st[4] * P["K"], 4.0)
    w = w - 0.3 * soft_tanh(w / 0.3)
    st[5] = w + P["a16"] * (st[5] - w)
    w = dclip(st[5], 0.6, 2.5)
    for j, q in enumerate(P["eq"]):
        k = 6 + 2 * j
        y = q[0] * w + st[k]; st[k] = q[1] * w - q[3] * y + st[k + 1]; st[k + 1] = q[2] * w - q[4] * y; w = y
    return sclip(w, 3.5)


def simulate_chain(sliders_in, signal, sr=48000.0, include_amp_cab=True, ref_cab=False):
    if not SLIDER_DEFAULTS:
        load_slider_defaults()
    sliders = dict(SLIDER_DEFAULTS)
    sliders.update(sliders_in)
    os_sr = sr * DIST_OS
    os_fc = min(16500.0, sr * 0.36)
    bq_in = bq_hp_coeffs(sliders[2], 0.7071, sr)
    # Round 42: GE-7 EQ (slider65 on, slider76 0 = before pedal / 1 = after), replaces the Input Pre-EQ
    eq_on = sliders.get(65, 0) > 0.5
    eq_pre = sliders.get(76, 1) < 0.5
    eq_f = [bq_peak_coeffs(f, 1.0, sliders.get(66 + i, 0.0), sr) for i, f in enumerate((100, 200, 400, 800, 1600, 3200, 6400))]
    eq_lvl = 10.0 ** (sliders.get(73, 0.0) * 0.05)
    P = pedal_setup(sliders, sr)
    pst = [0.0] * 16
    tone_st = [0.0, 0.0, 0.0]
    qs = [0.5098, 0.6013, 0.9000, 2.5629]
    up_f = [bq_lp_coeffs(os_fc, q, os_sr) for q in qs]
    dn_f = [bq_lp_coeffs(os_fc, q, os_sr) for q in qs]

    amp_mode = int(sliders[54])
    bq_amp_hp = bq_hp_coeffs(75.0, 0.707, sr)
    bq_amp_b = bq_shelf_coeffs(125.0, (sliders[55] - 50.0) * 0.20, sr, False)
    bq_amp_m = bq_peak_coeffs(620.0 if amp_mode == 2 else 520.0, 1.15, (sliders[56] - 50.0) * 0.22 - (2.5 if amp_mode == 2 else 1.0), sr)
    bq_amp_t = bq_shelf_coeffs(2400.0, (sliders[57] - 50.0) * 0.20 + 1.5, sr, True)
    bq_amp_p = bq_peak_coeffs(3800.0, 1.25, (sliders[58] - 50.0) * 0.24, sr)

    # Built-in IIR 4x12 cab (Round 88 Candidate A: milder 850 Hz cut & smoother top; loudness-matched to IR_E48)
    bq_cab_hp = bq_hp_coeffs(85.0, 0.7071, sr)
    bq_cab_lp1 = bq_lp_coeffs(5550.0, 0.7071, sr)
    cf1, cf2, cf3 = bq_peak_coeffs(115.0, 1.35, 6.5, sr), bq_peak_coeffs(850.0, 0.80, -3.0, sr), bq_peak_coeffs(3100.0, 1.35, 4.5, sr)
    clp2, cab_comp = bq_lp_coeffs(4950.0, 0.85, sr), 0.7028 * (10.0 ** (1.0 / 20.0))  # cab_comp_lin * db2lin(CAB_TRIM_DB=1.0)
    ir_ped_g = 1.0 if sliders.get(10, 0) < 0.5 else 10.0 ** (({0: -0.8, 1: 3.1, 3: -0.6}.get(int(sliders.get(11, 0) + 0.5), 0.0)) / 20.0)

    master_lin = 10.0 ** (sliders[51] * 0.05)
    dc_r = math.exp(-2.0 * math.pi * 10.0 / sr)
    dc_x1 = dc_y1 = amp_dc_x1 = amp_dc_y1 = 0.0
    out = []

    for x in signal:
        l = bq_step(bq_in, x * (10.0 ** (sliders[1] * 0.05))) * 4.0   # Round 69: +12.04 dB input cal (1 Vp = -12.04 dBFS)
        if eq_on and eq_pre:
            for b in eq_f:
                l = bq_step(b, l)
            l *= eq_lvl
        if sliders[10] > 0.5:
            for k in range(DIST_OS):
                xl = (l * DIST_OS) if k == 0 else 0.0
                for uf in up_f:
                    xl = bq_step(uf, xl)
                xl = pedal_os(P, pst, xl)
                for df in dn_f:
                    xl = bq_step(df, xl)
            l = xl
            if P["ped"] == 0:
                tone_st[0] = l + P["af"] * (tone_st[0] - l); l = tone_st[0]
            elif P["ped"] == 1:
                tone_st[0] = l + P["alp"] * (tone_st[0] - l)
                tone_st[2] = (1 + P["ahp"]) * 0.5 * (l - tone_st[1]) + P["ahp"] * tone_st[2]; tone_st[1] = l
                l = ((1 - P["tone"]) * tone_st[0] + P["tone"] * tone_st[2]) * 0.25
            elif P["ped"] == 2:
                tone_st[0] = l + P["aP"] * (tone_st[0] - l); l = P["kP"] * l + (1 - P["kP"]) * tone_st[0]
            for b in P["post"]:
                l = bq_step(b, l)
            dc_out = l - dc_x1 + dc_r * dc_y1
            dc_x1, dc_y1 = l, dc_out
            l = dc_out * P["mk"]
        if eq_on and not eq_pre:
            for b in eq_f:
                l = bq_step(b, l)
            l *= eq_lvl

        if not include_amp_cab:
            out.append(l)
            continue

        if amp_mode > 0:
            l = bq_step(bq_amp_hp, l)
            if amp_mode == 1:
                l = (soft_tanh(l * 1.45) if l >= 0.0 else 0.85 * soft_tanh(l * 1.70)) * 0.56
            else:
                l = (max(-0.82, min(0.82, l * 1.35)) * 0.65 + 0.35 * soft_tanh(l * 1.85)) * 0.56
            adc = l - amp_dc_x1 + dc_r * amp_dc_y1
            amp_dc_x1, amp_dc_y1 = l, adc
            l = bq_step(bq_amp_t, bq_step(bq_amp_m, bq_step(bq_amp_b, adc)))
        else:
            l *= 0.84  # Round 35: Amp OFF level match

        if ref_cab or sliders.get(49, 0) > 0.5:
            l = bq_step(bq_cab_lp1, bq_step(clp2, bq_step(cf3, bq_step(cf2, bq_step(cf1, bq_step(bq_cab_hp, l)))))) * cab_comp * ir_ped_g

        l = limit_sample(bq_step(bq_amp_p, l) * master_lin, 0.89125)
        out.append(l)
    return out


def parse_global_presets(presets_src):
    # Round 55: generic parser. Applies recall_global_preset's reset block, then each 'idx == N ? (' branch, and
    # expands gp_eq(n) (record curve from eq_preset_vals, EQ on, after the pedal).
    sl = lambda body: {int(m.group(1)): float(m.group(2)) for m in re.finditer(r"slider(\d+)\s*=\s*([-+]?\d+(?:\.\d+)?)", body)}
    eqt = {}
    for m in re.finditer(r"i == (\d) \? eq_set8\(([^)]*)\)", presets_src):
        eqt[int(m.group(1))] = [float(v) for v in m.group(2).split(",")]
    rec = presets_src[presets_src.index("function recall_global_preset"):]
    chunks = re.split(r"idx\s*==\s*(\d+)\s*\?\s*\(", rec)
    reset = sl(chunks[0].split("preset_dirty = 0;")[1])
    presets = {}
    for k in range(1, len(chunks), 2):
        body = chunks[k + 1].split("eq_last_preset =")[0]
        d = dict(reset)
        g = re.search(r"gp_eq\((\d)\)", body)
        if g:
            n = int(g.group(1))
            d.update({66 + j: v for j, v in enumerate(eqt[n])}); d.update({65: 1.0, 76: 0.0 if n == 8 else 1.0, 75: float(n)})
        d.update(sl(body))
        presets[int(chunks[k])] = d
    return presets


def check_presets_dc_and_levels(presets_src):
    print("[2/9] Presets through the reference cab: peak below the -3.1 dBFS limiter knee, DC (loudness: REAPER renders)...")
    presets = parse_global_presets(presets_src)
    sr = 48000.0
    n_samples = int(0.45 * sr)
    signal = []
    for i in range(n_samples):
        t = i / sr
        env = math.exp(-t * 4.5) * (1.0 - math.exp(-t * 250.0))
        val = 0.25 * env * (0.6 * math.sin(2 * math.pi * 82.41 * t) + 0.4 * math.sin(2 * math.pi * 164.82 * t) + 0.3 * math.sin(2 * math.pi * 247.23 * t))
        signal.append(val)

    kshelf, khp = bq_shelf_coeffs(1681.0, 4.0, sr, True), bq_hp_coeffs(38.0, 0.5, sr)
    # Round 58: loudness is calibrated from REAPER renders (WAV IR + chorus / reverb; Antigravity's per-preset table), not
    # here: the Round 55 mirror match was off by up to 7.5 dB. The mirror's K-loudness is printed for reference only;
    # the checks are the limiter knee and DC.
    for idx in sorted(presets):
        out = simulate_chain(presets[idx], signal, sr, include_amp_cab=True, ref_cab=True)
        steady = out[int(0.03 * sr):]
        peak_db = 20.0 * math.log10(max(abs(x) for x in steady))
        a, b = list(kshelf), list(khp)
        kw = [bq_step(b, bq_step(a, x)) for x in steady]
        k_db = 10.0 * math.log10(sum(v * v for v in kw) / len(kw))
        dc = abs(sum(steady) / len(steady))
        print(f"  - Preset {idx + 1:02d} K-loudness {k_db:+.2f} dB | peak {peak_db:+.2f} dBFS | DC {dc:.5f}")
        raw = dict(presets[idx]); raw[49] = 0.0   # Round 58: also with the cab off (feeding an external IR loader)
        raw_db = 20.0 * math.log10(max(abs(x) for x in simulate_chain(raw, signal, sr)[int(0.03 * sr):]))
        print(f"      cab off peak {raw_db:+.2f} dBFS")
        if max(peak_db, raw_db) > -3.1:
            raise AssertionError(f"Preset {idx + 1:02d} peak {max(peak_db, raw_db):.2f} dBFS reaches the -3.1 dBFS limiter knee")
        if dc > 0.004:
            raise AssertionError(f"Preset {idx + 1:02d} DC offset {dc:.5f} exceeds 0.004 threshold")


def check_pre_cab_aliasing_all_bins(presets_src):
    # Round 9: every pedal model, at its preset settings, 8x oversampled. In-band (20 Hz - 8 kHz)
    # limit -40 dB for every pedal (Round 30: HM-2 tightened from -34 dB after its Round 23/27 rebuild measured -47 dB).
    print("[3/9] Measuring PRE-CABINET 8x oversampled aliasing per pedal (2578 Hz tone)...")
    presets = parse_global_presets(presets_src)
    sr = 48000.0
    n = 1024
    bin_f0 = 55  # 55 * 48000 / 1024 = 2578.125 Hz, bin-centred
    f0 = bin_f0 * sr / n
    sig = [0.25 * math.sin(2.0 * math.pi * f0 * (i / sr)) for i in range(n + 4096)]
    harmonic_bins = {bin_f0 * k for k in range(1, (n // 2) // bin_f0 + 1)}
    bin_8k = int(8000.0 * n / sr)
    by_ped = {int(p.get(11, 0) + 0.5): p for p in presets.values() if p.get(10, 0) > 0.5}
    hm10 = dict(by_ped[3]); hm10.update({62: 10.0, 63: 10.0, 64: 10.0})   # Round 55: HM-2 worst case, all knobs on 10
    for p0, name, limit in ((by_ped[0], "RAT", -40.0), (by_ped[1], "DS-1", -40.0), (by_ped[2], "Metal Zone", -40.0), (hm10, "HM-2 (all 10)", -40.0)):
        p = dict(p0)
        p[16] = 0.0
        out = simulate_chain(p, sig, sr, include_amp_cab=False)[4096:]
        harm_8k = alias_8k = 0.0
        for k in range(1, bin_8k + 1):
            re_s = sum(out[i] * math.cos(2.0 * math.pi * k * i / n) for i in range(n))
            im_s = sum(out[i] * math.sin(2.0 * math.pi * k * i / n) for i in range(n))
            pwr = (re_s * re_s + im_s * im_s) / (n * n)
            if k in harmonic_bins:
                harm_8k += pwr
            else:
                alias_8k += pwr
        ratio = 10.0 * math.log10(max(1e-18, alias_8k) / max(1e-18, harm_8k))
        print(f"  - {name:<14} in-band alias ratio: {ratio:+.2f} dB (limit {limit:+.0f})")
        if ratio > limit:
            raise AssertionError(f"{name} in-band aliasing {ratio:+.1f} dB exceeds {limit:+.0f} dB")


def pole_q(b):
    # biquad denominator 1 + a1 z^-1 + a2 z^-2 -> analog-equivalent pole Q (0 if real poles)
    a1, a2 = b[3], b[4]
    if a2 <= 0 or a1 * a1 >= 4 * a2:
        return 0.0
    r = math.sqrt(a2); th = math.acos(max(-1.0, min(1.0, -a1 / (2 * r))))
    return th / (2 * max(1e-9, -math.log(r)))


def check_no_resonant_filters():
    # Round 11 guard: the Round 9 MT-2 pre-hump (RBJ peak, Q 1.2 @ +30 dB) had pole Q ~6.7 and rang at 1 kHz
    # ('whistle'). Every pedal filter must keep pole Q <= 3.5 at every knob extreme.
    print("[4/9] Checking pedal + GE-7 filter pole Q (no ringing resonances) across knob extremes...")
    if not SLIDER_DEFAULTS:
        load_slider_defaults()
    worst = 0.0
    for ped in range(4):
        for k in (0.0, 5.0, 10.0):
            s = dict(SLIDER_DEFAULTS); s[11] = ped
            for i in (26, 27, 29, 37, 39, 46, 47, 48, 59, 62, 63, 64):
                s[i] = k
            P = pedal_setup(s, 48000.0)
            for b in P["post"] + ([P["hump"]] if "hump" in P else []) + P.get("eq", []):
                worst = max(worst, pole_q(b))
    for f in (100.0, 200.0, 400.0, 800.0, 1600.0, 3200.0, 6400.0):   # Round 31: GE-7 bands at +/-15 dB
        for db in (-15.0, 15.0):
            worst = max(worst, pole_q(bq_peak_coeffs(f, 1.0, db, 48000.0)))
    print(f"  - Worst pole Q: {worst:.2f} (limit 3.5)")
    if worst > 3.5:
        raise AssertionError(f"Pedal filter pole Q {worst:.2f} > 3.5: will ring")



def check_ir_loudness_constant():
    # Round 19 / Round 73 / Round 88 guard: IR_E48 in sepulchre_dsp_ir.jsfx-inc must equal the weighted energy of
    # the Built-in 4x12 IIR cab (Candidate A, cab_comp_lin = 0.7028) measured through the shared IR weighting filters.
    print("[5/9] Checking WAV IR loudness-match constant IR_E48 against Built-in 4x12 IIR cab...")
    src = open(os.path.join(ROOT, "sepulchre_dsp_ir.jsfx-inc"), "r", encoding="utf-8").read()
    m = re.search(r"^IR_E48 = ([0-9.]+);", src, flags=re.MULTILINE)
    if not m:
        raise AssertionError("IR_E48 constant not found")
    sr = 48000.0
    hp = bq_hp_coeffs(85.0, 0.7071, sr)
    chain = [hp, bq_peak_coeffs(115.0, 1.35, 6.5, sr), bq_peak_coeffs(850.0, 0.80, -3.0, sr), bq_peak_coeffs(3100.0, 1.35, 4.5, sr),
             bq_lp_coeffs(4950.0, 0.85, sr), bq_lp_coeffs(5550.0, 0.7071, sr)]
    weight = [bq_hp_coeffs(180.0, 0.7071, sr), bq_lp_coeffs(4200.0, 0.7071, sr), bq_peak_coeffs(900.0, 0.8, 3.0, sr)]
    x = [1.0] + [0.0] * 4094
    for b in chain:
        b = list(b); x = [bq_step(b, v) for v in x]
    x = [v * 0.7028 for v in x[:2047]] + [0.0] * 2048
    for b in weight:
        b = list(b); x = [bq_step(b, v) for v in x]
    e = sum(v * v for v in x)
    print(f"  - IR_E48 file {float(m.group(1)):.6f} vs computed {e:.6f}")
    if abs(float(m.group(1)) / e - 1.0) > 0.01:
        raise AssertionError("IR_E48 does not match the IIR profile 0 weighted energy")



def check_distortion_gain_curve(presets_src):
    # Round 7 guard: a high-gain stage must stay saturated as notes decay. At preset 0 settings, the
    # distortion-only output RMS for a -36 dBFS low-E note must be within 6 dB of the -12 dBFS output.
    print("[6/9] Verifying high-gain saturation curve (distortion output vs input level)...")
    presets = parse_global_presets(presets_src)
    sr = 48000.0
    n = int(0.25 * sr)
    note = [sum(math.sin(2 * math.pi * 82.41 * k * i / sr) / k for k in range(1, 25)) for i in range(n)]
    pk = max(abs(x) for x in note)
    rms = {}
    for lvl in (-12.0, -36.0):
        g = 10.0 ** (lvl / 20.0) / pk
        out = simulate_chain(presets[0], [x * g for x in note], sr, include_amp_cab=False)[int(0.05 * sr):]
        rms[lvl] = 10.0 * math.log10(sum(x * x for x in out) / len(out))
        print(f"  - Input {lvl:+.0f} dBFS -> distortion output RMS {rms[lvl]:+.1f} dB")
    drop = rms[-12.0] - rms[-36.0]
    if drop > 6.0:
        raise AssertionError(f"Distortion loses {drop:.1f} dB between -12 and -36 dBFS input (> 6 dB): not high-gain")

def check_defaults_match_preset_1(presets_src):
    # Round 55: a freshly inserted plugin must sound exactly like the preset its header shows (01, slider60 = 0)
    print("[7/9] Checking slider defaults == preset 01 (fresh insert)...")
    if not SLIDER_DEFAULTS:
        load_slider_defaults()
    p0 = parse_global_presets(presets_src)[0]
    bad = [(k, SLIDER_DEFAULTS.get(k), v) for k, v in sorted(p0.items()) if abs(SLIDER_DEFAULTS.get(k, 1e9) - v) > 1e-9]
    if SLIDER_DEFAULTS.get(60) != 0.0:
        bad.append((60, SLIDER_DEFAULTS.get(60), 0.0))
    print(f"  - {len(p0)} preset-01 sliders checked, {len(bad)} mismatches")
    if bad:
        raise AssertionError(f"slider defaults differ from preset 01: {bad}")
    # Round 67: also verify UI double-click defaults (ui_hslider / ui_hslider_db dflt_v) match slider defaults
    with open(os.path.join(ROOT, "sepulchre_ui_panels.jsfx-inc"), "r", encoding="utf-8") as f:
        panels_src = strip_comments_and_strings(f.read())
    ui_bad, ui_cnt = [], 0
    for m in re.finditer(r"ui_hslider(?:_db)?\(\s*(\d+)\s*,(?:[^,]+,){7}\s*([-0-9.]+)\s*,", panels_src):
        sid, dflt = int(m.group(1)), float(m.group(2))
        ui_cnt += 1
        if abs(SLIDER_DEFAULTS.get(sid, 1e9) - dflt) > 1e-9:
            ui_bad.append((sid, dflt, SLIDER_DEFAULTS.get(sid)))
    print(f"  - {ui_cnt} UI double-click defaults checked, {len(ui_bad)} mismatches")
    if ui_bad:
        raise AssertionError(f"UI double-click defaults differ from slider defaults: {ui_bad}")


def _strip_comments_only(code):
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL))


def check_tone_readouts_match_dsp(raw_files):
    # Round 80 (Task 10): verify every tone-control dB readout in sepulchre_ui_panels.jsfx-inc matches the DSP gain
    # at slider min, mid, and max (either via shared helper in ui_hslider_db or direct bip_k vs DSP expression).
    print("[8/9] Checking UI tone-control dB readouts against DSP gain expressions...")
    panels = _strip_comments_only(raw_files["sepulchre_ui_panels.jsfx-inc"])
    dsp_dist = _strip_comments_only(raw_files["sepulchre_dsp_dist.jsfx-inc"])
    dsp_amp = _strip_comments_only(raw_files["sepulchre_dsp_amp_cab.jsfx-inc"])
    dsp_all = dsp_dist + "\n" + dsp_amp

    checked = 0
    # 1. Shared-helper sliders: ui_hslider_db(sid, ..., fn(sliderN))
    for m in re.finditer(
        r"ui_hslider_db\(\s*(\d+)\s*,(?:[^,]+,){5}\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*,[^,]+,[^,]+,\s*([a-zA-Z_]\w*)\(\s*slider(\d+)\s*\)\s*\)",
        panels,
    ):
        sid, fn, ref_sid = int(m.group(1)), m.group(4), int(m.group(5))
        if sid != ref_sid:
            raise AssertionError(f"ui_hslider_db slider{sid} calls {fn}(slider{ref_sid})")
        if not re.search(rf"\bfunction\s+{re.escape(fn)}\s*\(", dsp_all):
            raise AssertionError(f"Shared dB helper {fn}() not defined in DSP files")
        if not re.search(rf"\b{re.escape(fn)}\(\s*slider{sid}\s*\)", dsp_all):
            raise AssertionError(f"DSP does not call shared helper {fn}(slider{sid})")
        checked += 1

    # 2. Direct bip_k dB sliders: ui_hslider(sid, ..., "%+.1f dB", bip_k) with bip_k > 0
    for m in re.finditer(
        r'ui_hslider\(\s*(\d+)\s*,(?:[^,]+,){5}\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*,[^,]+,[^,]+,\s*"%\+\.1f dB"\s*,\s*([-0-9.]+)\s*\)',
        panels,
    ):
        sid, min_v, max_v, bip_k = int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))
        if bip_k <= 0:
            continue
        mid_v = (min_v + max_v) * 0.5
        m_dsp = re.search(
            rf"(?:gyro_peak|bq_hshelf|bq_lshelf|bq_peak)\([^;]*,\s*([^,;]*\bslider{sid}\b[^,;]*)\)",
            dsp_all,
        ) or re.search(rf"\b[a-zA-Z_]\w*_db\s*=\s*([^;]*\bslider{sid}\b[^;]*);", dsp_all)
        if not m_dsp:
            raise AssertionError(f"No DSP dB expression found for UI slider{sid} (bip_k={bip_k})")
        expr = m_dsp.group(1).strip()
        for v in (min_v, mid_v, max_v):
            ui_db = (v - mid_v) * bip_k
            py_expr = re.sub(rf"\bslider{sid}\b", repr(float(v)), expr)
            if not re.fullmatch(r"[0-9.eE+\-*/() ]+", py_expr):
                raise AssertionError(f"Unsupported DSP dB expression for slider{sid}: {expr}")
            dsp_db = float(eval(py_expr, {"__builtins__": {}}, {}))
            if abs(ui_db - dsp_db) > 1e-9:
                raise AssertionError(
                    f"slider{sid} readout mismatch at val={v}: UI={ui_db:+.2f} dB vs DSP={dsp_db:+.2f} dB ({expr})"
                )
        checked += 1

    if checked < 7:
        raise AssertionError(f"Expected >= 7 tone dB readouts checked, got {checked}")
    print(f"  - {checked} tone-control dB readouts verified against DSP (shared helpers + min/mid/max).")


def _read_wav_mono(path):
    import wave
    import numpy as np
    w = wave.open(path)
    n, ch, sw = w.getnframes(), w.getnchannels(), w.getsampwidth()
    b = np.frombuffer(w.readframes(n), dtype=np.uint8)
    if sw == 3:
        b = b.reshape(-1, 3)
        v = b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16)
        v = np.where(v >= 2 ** 23, v - 2 ** 24, v) / 2.0 ** 23
    elif sw == 2:
        v = np.frombuffer(b.tobytes(), dtype=np.int16) / 32768.0
    else:
        v = np.frombuffer(b.tobytes(), dtype=np.int32) / 2.0 ** 31
    return v.reshape(-1, ch)[:, 0], w.getframerate()


def _bq_run(b, x):
    b = list(b)
    return [bq_step(b, v) for v in x]


def _lufs_ungated(x):
    # BS.1770 K-weighting at 48 kHz (same coefficients as tests/render/render_common.py), ungated mean square
    hs = [1.53512485958697, -2.69169618940638, 1.19839281085285, -1.69065929318241, 0.73248077421585, 0.0, 0.0]
    hp = [1.0, -2.0, 1.0, -1.99004745483398, 0.99007225035621, 0.0, 0.0]
    y = _bq_run(hp, _bq_run(hs, x))
    return -0.691 + 10.0 * math.log10(max(1e-12, sum(v * v for v in y) / len(y)))


def check_real_ir_loudness(presets_src, raw_files):
    # Round 59: the presets' loudness through the REAL cab IR (slot 0), mirroring prepare_ir_fft() / proc_cab_out().
    # Validated in Round 59 against Antigravity's Round 57 REAPER renders: within 0.05..0.8 dB for presets with little or
    # no chorus / reverb (the mirror has neither). Those presets must sit within 1 dB of the bank target; FX-heavy ones
    # are printed only (their loudness gate is the REAPER render test). The Ugritone IRs are NOT in the repo: they are
    # read from SEPULCHRE_IR_DIR or %APPDATA%\REAPER\Data\sepulchre_irs, and the check is skipped without them.
    print("[9/9] Preset loudness through the real slot-0 IR (di_input.wav, BS.1770 ungated)...")
    try:
        import numpy as np
    except ImportError:
        print("  - SKIPPED: numpy not installed"); return
    default_ir_dir = (os.path.join(os.environ.get("APPDATA", ""), "REAPER", "Data", "sepulchre_irs")
                      if sys.platform == "win32" else os.path.expanduser("~/.config/REAPER/Data/sepulchre_irs"))
    ir_dir = os.environ.get("SEPULCHRE_IR_DIR") or default_ir_dir
    ir_path = os.path.join(ir_dir, "01_BlackWizard_Center.wav")
    di_path = os.path.join(ROOT, "tests", "render", "di_input.wav")
    if not (os.path.exists(ir_path) and os.path.exists(di_path)):
        print(f"  - SKIPPED: {ir_path if not os.path.exists(ir_path) else di_path} not found"); return
    ir_src = raw_files["sepulchre_dsp_ir.jsfx-inc"]
    amp = raw_files["sepulchre_dsp_amp_cab.jsfx-inc"]
    e48 = float(re.search(r"^IR_E48 = ([0-9.]+);", ir_src, flags=re.MULTILINE).group(1))
    m = re.search(r"dist_ped == 0 \? ([-0-9.]+) : dist_ped == 1 \? ([-0-9.]+) : dist_ped == 3 \? ([-0-9.]+) : ([-0-9.]+)\)", amp)
    ped_db = {0: float(m.group(1)), 1: float(m.group(2)), 3: float(m.group(3)), 2: float(m.group(4))}
    sr = 48000.0
    raw, isr = _read_wav_mono(ir_path)
    raw = raw[:8192]
    isc = isr / sr
    fl = int(min(8192, min(math.floor(2048 * sr / 48000), math.floor(len(raw) / isc))))
    i = np.arange(fl); ipos = np.floor(i * isc).astype(int); fr = i * isc - ipos
    ir = raw[ipos] * (1 - fr) + raw[np.minimum(len(raw) - 1, ipos + 1)] * fr
    fade_n = int(min(math.floor(0.0025 * sr), math.floor(fl * 0.1)))
    if fade_n > 1 and math.floor(len(raw) / isc) > fl:
        for fi in range(fade_n):
            ir[fl - fade_n + fi] *= 0.5 * (1.0 + math.cos(math.pi * (fi + 1) / fade_n))
    buf = list(ir) + [0.0] * 2048
    for b in (bq_hp_coeffs(85.0, 0.7071, sr), bq_hp_coeffs(180.0, 0.7071, sr), bq_lp_coeffs(4200.0, 0.7071, sr),
              bq_peak_coeffs(900.0, 0.8, 3.0, sr)):
        buf = _bq_run(b, buf)
    ir = ir * math.sqrt(e48 / sum(v * v for v in buf))
    di = list(_read_wav_mono(di_path)[0])
    presets = parse_global_presets(presets_src)
    results = []
    for idx in sorted(presets):
        p = dict(presets[idx])
        master = p.get(51, 0.0)
        p[49], p[51] = 0.0, -12.0                     # cab applied below; -12 dB keeps the limiter out of the mirror
        y = np.array(simulate_chain(p, di, sr)) * 10.0 ** (12.0 / 20.0)
        y = np.convolve(y, ir)[:len(y)]               # Air (in simulate_chain) is linear, so it commutes with the cab
        if p.get(10, 1) > 0.5:
            y = y * 10.0 ** (ped_db[int(p[11] + 0.5)] / 20.0)
        y = np.array(_bq_run(bq_hp_coeffs(85.0, 0.7071, sr), y)) * 10.0 ** (master / 20.0)
        y = [limit_sample(v, 0.89125) for v in y]
        lu = _lufs_ungated(y)
        dry = p.get(20, 0) < 0.5 and (p.get(40, 0) < 0.5 or p.get(45, 0) <= 15)
        results.append((idx, lu, dry))
    target = -18.25   # Round 71 (Task 4): fixed loudness anchor (prevents silent bank-level drift)
    fails = []
    for idx, lu, dry in results:
        tag = "checked" if dry else "info only (chorus / long reverb not mirrored)"
        print(f"  - Preset {idx + 1:02d}: {lu:+.2f} LUFS ({lu - target:+.2f} vs {target:.2f}) [{tag}]")
        if dry and abs(lu - target) > 1.0:
            fails.append(f"{idx + 1:02d} {lu:+.2f} LUFS")
    if fails:
        raise AssertionError(f"presets off the {target:.2f} LUFS anchor by > 1 dB through the real IR: " + ", ".join(fails))


if __name__ == "__main__":
    try:
        raw_files = check_syntax_and_r2_fixes()
        check_presets_dc_and_levels(raw_files["sepulchre_presets.jsfx-inc"])
        check_pre_cab_aliasing_all_bins(raw_files["sepulchre_presets.jsfx-inc"])
        check_no_resonant_filters()
        check_ir_loudness_constant()
        check_distortion_gain_curve(raw_files["sepulchre_presets.jsfx-inc"])
        check_defaults_match_preset_1(raw_files["sepulchre_presets.jsfx-inc"])
        check_tone_readouts_match_dsp(raw_files)
        check_real_ir_loudness(raw_files["sepulchre_presets.jsfx-inc"], raw_files)
        print("\nALL VERIFICATION & OFFLINE DSP CHECKS PASSED.")
    except Exception as exc:
        print(f"\nVERIFICATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
