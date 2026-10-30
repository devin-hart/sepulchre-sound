#!/usr/bin/env python3
"""
Static checks and offline DSP mirror for Sepulchre Sound (run before every commit).
1. Source checks: every JSFX file < 300 lines, @init headers, balanced parentheses, no unary '~', declared UI assets
   exist, non-overlapping alloc_buf() memory map, and the Round 2 invariants (no preset recall in @init,
   pdc_delay in @block, IR reload handler, no file I/O in coefficient updates, slider
   automation masks).
2. Python mirror of the pedals (8x oversampled), amp, IIR cab and limiter:
   - presets peak in [-10, -8] dBFS with DC < 0.004 (IIR cab path);
   - in-band aliasing per pedal (2578 Hz tone);
   - no pedal filter with pole Q > 3.5 at any knob extreme (no ringing);
   - IR_E48 matches the IIR cab's weighted energy;
   - high-gain saturation curve (Metal Zone preset);
   - Round 50: TS-808 boost (mirror of proc_ts, 4x): trick voicing and aliasing, and every pedal's aliasing with it.
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
    print("[1/7] Checking EEL2 files (<300 lines), dynamic memory map, and Round 2 bug-fix invariants...")
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
    assert "recall_global_preset" not in init_sec, "R2-1 regression: recall_global_preset called in @init!"
    assert "pdc_delay = ir_chunk_size" in block_sec, "R2-3 regression: pdc_delay not set in @block!"
    assert "ir_reload_req ?" in block_sec, "R3-1 regression: ir_reload_req handler missing in @block!"
    assert "load_ir_slot" not in cleaned_by_file["sepulchre_dsp_amp_cab.jsfx-inc"].split("update_amp_cab_coeffs")[1], \
        "R2-6 regression: load_ir_slot called inside update_amp_cab_coeffs!"
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


TS_OS = 4


class TubeScreamer:
    """Round 50: TS-808 boost (Drive/Tone/Level), 4x oversampled. Mirror of ts_os/ts_tone in sepulchre_dsp_dist.jsfx-inc."""

    def __init__(self, s, sr):
        os_sr = sr * TS_OS
        c1 = lambda fc, r: math.exp(-2 * math.pi * min(fc, 0.45 * r) / r)
        rf = 51000 + 500000 * a_taper(s.get(80, 0.0) * 0.1)
        self.G, self.a720, self.aC = rf / 4700, c1(720, os_sr), c1(1 / (2 * math.pi * rf * 51e-12), os_sr)
        self.a723, self.hg = c1(723, sr), 10.0 ** ((2.4 * s.get(81, 5.0) - 14.0) / 20.0)
        self.mk = a_taper(s.get(82, 10.0) * 0.1)
        fc = min(16500.0, sr * 0.36)
        self.up = [bq_lp_coeffs(fc, q, os_sr) for q in (0.5098, 0.6013, 0.9000, 2.5629)]
        self.dn = [bq_lp_coeffs(fc, q, os_sr) for q in (0.5098, 0.6013, 0.9000, 2.5629)]
        self.hx = self.hy = self.lc = self.lt = 0.0

    def step(self, x):
        for k in range(TS_OS):
            v = x * TS_OS if k == 0 else 0.0
            for f in self.up:
                v = bq_step(f, v)
            self.hy = (1 + self.a720) * 0.5 * (v - self.hx) + self.a720 * self.hy; self.hx = v
            f_ = self.G * self.hy; self.lc = f_ + self.aC * (self.lc - f_)
            w = sclip(v + dclip(self.lc, 0.6, 2.5), 4.0)
            for f in self.dn:
                w = bq_step(f, w)
        self.lt = w + self.a723 * (self.lt - w)
        return (self.lt + self.hg * (w - self.lt)) * self.mk


def simulate_chain(sliders_in, signal, sr=48000.0, include_amp_cab=True):
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
    ts = TubeScreamer(sliders, sr) if sliders.get(79, 0) > 0.5 else None
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

    # IIR 4x12 cab (the plugin's fallback / loudness reference; WAV IRs are not in the repo)
    bq_cab_hp = bq_hp_coeffs(85.0, 0.7071, sr)
    bq_cab_lp1 = bq_lp_coeffs(7800.0, 0.7071, sr)
    cf1, cf2, cf3 = bq_peak_coeffs(125.0, 1.6, 3.2, sr), bq_peak_coeffs(650.0, 1.2, -3.8, sr), bq_peak_coeffs(2850.0, 1.4, 4.8, sr)
    clp2, cab_comp = bq_lp_coeffs(6200.0, 0.95, sr), 0.72

    master_lin = 10.0 ** (sliders[51] * 0.05)
    dc_r = math.exp(-2.0 * math.pi * 10.0 / sr)
    dc_x1 = dc_y1 = amp_dc_x1 = amp_dc_y1 = 0.0
    out = []

    for x in signal:
        l = bq_step(bq_in, x * (10.0 ** (sliders[1] * 0.05)))
        if eq_on and eq_pre:
            for b in eq_f:
                l = bq_step(b, l)
            l *= eq_lvl
        if ts:
            l = ts.step(l)
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

        if sliders[49] > 0.5:
            l = bq_step(bq_cab_lp1, bq_step(clp2, bq_step(cf3, bq_step(cf2, bq_step(cf1, bq_step(bq_cab_hp, l)))))) * cab_comp

        l = limit_sample(bq_step(bq_amp_p, l) * master_lin, 0.89125)
        out.append(l)
    return out


def parse_global_presets(presets_src):
    presets = {}
    chunks = re.split(r"idx\s*==\s*(\d+)\s*\?\s*\(", presets_src)
    for k in range(1, len(chunks), 2):
        idx = int(chunks[k])
        body = chunks[k + 1]
        if idx == 5:
            parts = re.split(r"\)\s*:\s*\(\s*//\s*07:", body)
            body5, body6 = parts[0], parts[1].split("ui_need_sync")[0]
            for sub_idx, sub_body in [(5, body5), (6, body6)]:
                s_dict = {}
                for sm in re.finditer(r"slider(\d+)\s*=\s*([-+]?\d+(?:\.\d+)?)", sub_body):
                    s_dict[int(sm.group(1))] = float(sm.group(2))
                presets[sub_idx] = s_dict
        else:
            s_dict = {}
            for sm in re.finditer(r"slider(\d+)\s*=\s*([-+]?\d+(?:\.\d+)?)", body):
                s_dict[int(sm.group(1))] = float(sm.group(2))
            presets[idx] = s_dict
    return presets


def check_presets_dc_and_levels(presets_src):
    print("[2/7] Running offline DSP simulation across the 6 distorted presets (Target: [-10.0, -8.0] dBFS)...")
    presets = parse_global_presets(presets_src)
    sr = 48000.0
    n_samples = int(0.45 * sr)
    signal = []
    for i in range(n_samples):
        t = i / sr
        env = math.exp(-t * 4.5) * (1.0 - math.exp(-t * 250.0))
        val = 0.25 * env * (0.6 * math.sin(2 * math.pi * 82.41 * t) + 0.4 * math.sin(2 * math.pi * 164.82 * t) + 0.3 * math.sin(2 * math.pi * 247.23 * t))
        signal.append(val)

    for idx in (0, 1, 2, 3, 4, 6):
        out = simulate_chain(presets[idx], signal, sr, include_amp_cab=True)
        steady = out[int(0.03 * sr):]
        peak = max(abs(x) for x in steady)
        peak_db = 20.0 * math.log10(peak)
        dc = abs(sum(steady) / len(steady))
        print(f"  - Preset {idx} peak: {peak_db:+.2f} dBFS | DC offset: {dc:.5f}")
        if not (-10.0 <= peak_db <= -8.0):
            raise AssertionError(f"Preset {idx} peak {peak_db:.2f} dBFS outside strict [-10.0, -8.0] dBFS target")
        if dc > 0.004:
            raise AssertionError(f"Preset {idx} DC offset {dc:.5f} exceeds 0.004 threshold")


def check_pre_cab_aliasing_all_bins(presets_src):
    # Round 9: every pedal model, at its preset settings, 8x oversampled. In-band (20 Hz - 8 kHz)
    # limit -40 dB for every pedal (Round 30: HM-2 tightened from -34 dB after its Round 23/27 rebuild measured -47 dB).
    print("[3/7] Measuring PRE-CABINET 8x oversampled aliasing per pedal (2578 Hz tone)...")
    presets = parse_global_presets(presets_src)
    sr = 48000.0
    n = 1024
    bin_f0 = 55  # 55 * 48000 / 1024 = 2578.125 Hz, bin-centred
    f0 = bin_f0 * sr / n
    sig = [0.25 * math.sin(2.0 * math.pi * f0 * (i / sr)) for i in range(n + 4096)]
    harmonic_bins = {bin_f0 * k for k in range(1, (n // 2) // bin_f0 + 1)}
    bin_8k = int(8000.0 * n / sr)
    runs = [(idx, name, ts) for ts in (0, 1) for idx, name in ((1, "RAT"), (3, "DS-1"), (0, "Metal Zone"), (4, "HM-2 (all 10)"))]
    for idx, name, ts in runs:   # Round 50: and again with the TS-808 (Drive 0 / Tone 5 / Level 10) in front
        limit = -40.0
        p = dict(presets[idx])
        p[79] = ts
        name = ("TS > " if ts else "") + name
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
        print(f"  - {name:<19} in-band alias ratio: {ratio:+.2f} dB (limit {limit:+.0f})")
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
    print("[4/7] Checking pedal + GE-7 filter pole Q (no ringing resonances) across knob extremes...")
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
    # Round 19 guard: IR_E48 in sepulchre_dsp_amp_cab.jsfx-inc must equal the weighted energy of IIR cab profile 0
    # (cab HPF + profile 0 + 7.8 kHz LPF, x0.72), measured after the cab HPF and the IR weighting filters.
    print("[5/7] Checking WAV IR loudness-match constant IR_E48 against IIR profile 0...")
    src = open(os.path.join(ROOT, "sepulchre_dsp_amp_cab.jsfx-inc"), "r", encoding="utf-8").read()
    m = re.search(r"^IR_E48 = ([0-9.]+);", src, flags=re.MULTILINE)
    if not m:
        raise AssertionError("IR_E48 constant not found")
    sr = 48000.0
    hp = bq_hp_coeffs(85.0, 0.7071, sr)
    chain = [hp, bq_peak_coeffs(125.0, 1.6, 3.2, sr), bq_peak_coeffs(650.0, 1.2, -3.8, sr), bq_peak_coeffs(2850.0, 1.4, 4.8, sr),
             bq_lp_coeffs(6200.0, 0.95, sr), bq_lp_coeffs(7800.0, 0.7071, sr)]
    weight = [bq_hp_coeffs(85.0, 0.7071, sr), bq_hp_coeffs(90.0, 0.7071, sr), bq_shelf_coeffs(500.0, 12.0, sr, False), bq_lp_coeffs(6000.0, 0.7071, sr)]
    x = [1.0] + [0.0] * 4094
    for b in chain:
        b = list(b); x = [bq_step(b, v) for v in x]
    x = [v * 0.72 for v in x[:2047]] + [0.0] * 2048
    for b in weight:
        b = list(b); x = [bq_step(b, v) for v in x]
    e = sum(v * v for v in x)
    print(f"  - IR_E48 file {float(m.group(1)):.6f} vs computed {e:.6f}")
    if abs(float(m.group(1)) / e - 1.0) > 0.01:
        raise AssertionError("IR_E48 does not match the IIR profile 0 weighted energy")



def check_distortion_gain_curve(presets_src):
    # Round 7 guard: a high-gain stage must stay saturated as notes decay. At preset 0 settings, the
    # distortion-only output RMS for a -36 dBFS low-E note must be within 6 dB of the -12 dBFS output.
    print("[6/7] Verifying high-gain saturation curve (distortion output vs input level)...")
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

def check_ts808_trick():
    # Round 50: the TS-808 at Drive 0 / Tone 5 / Level 10 must act as a mid push that leaves the lows alone
    # (>= 10 dB more gain at 1 kHz than at 82 Hz, small signal), and stay clean of aliasing at Drive 10 (4x).
    print("[7/7] Checking the TS-808 boost (trick voicing at Drive 0, aliasing at Drive 10)...")
    sr = 48000.0

    def gain(f, s, amp=0.01):
        ts = TubeScreamer(s, sr); n = int(0.15 * sr)
        o = [ts.step(amp * math.sin(2 * math.pi * f * i / sr)) for i in range(n)][n // 2:]
        return 20.0 * math.log10(max(abs(v) for v in o) / amp)
    trick = {80: 0.0, 81: 5.0, 82: 10.0}
    g82, g1k = gain(82.41, trick), gain(1000.0, trick)
    print(f"  - Trick setting, small signal: 82 Hz {g82:+.1f} dB, 1 kHz {g1k:+.1f} dB (mid push {g1k - g82:.1f} dB)")
    if g1k - g82 < 10.0:
        raise AssertionError(f"TS-808 mid push only {g1k - g82:.1f} dB (< 10 dB)")
    n, b0 = 1024, 55
    ts = TubeScreamer({80: 10.0, 81: 5.0, 82: 10.0}, sr)
    out = [ts.step(0.25 * math.sin(2.0 * math.pi * b0 * i / n)) for i in range(n + 4096)][4096:]
    harm = alias = 0.0
    for k in range(1, int(8000.0 * n / sr) + 1):
        re_s = sum(out[i] * math.cos(2.0 * math.pi * k * i / n) for i in range(n))
        im_s = sum(out[i] * math.sin(2.0 * math.pi * k * i / n) for i in range(n))
        if k % b0 == 0:
            harm += re_s * re_s + im_s * im_s
        else:
            alias += re_s * re_s + im_s * im_s
    ratio = 10.0 * math.log10(max(1e-18, alias) / max(1e-18, harm))
    print(f"  - Drive 10 in-band alias ratio: {ratio:+.2f} dB (limit -40)")
    if ratio > -40.0:
        raise AssertionError(f"TS-808 aliasing {ratio:+.1f} dB exceeds -40 dB")


if __name__ == "__main__":
    try:
        raw_files = check_syntax_and_r2_fixes()
        check_presets_dc_and_levels(raw_files["sepulchre_presets.jsfx-inc"])
        check_pre_cab_aliasing_all_bins(raw_files["sepulchre_presets.jsfx-inc"])
        check_no_resonant_filters()
        check_ir_loudness_constant()
        check_distortion_gain_curve(raw_files["sepulchre_presets.jsfx-inc"])
        check_ts808_trick()
        print("\nALL VERIFICATION & OFFLINE DSP CHECKS PASSED.")
    except Exception as exc:
        print(f"\nVERIFICATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
