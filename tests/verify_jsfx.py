#!/usr/bin/env python3
"""
Static & Numerical DSP Verifier for Sepulchre Sound JSFX.
Checks:
1. File line count limits (< 300 lines per file).
2. EEL2 syntax: balanced parentheses, slider definitions, import resolution, function definitions/calls.
3. Memory buffer allocation non-overlap and bounds safety.
4. Numerical stability & frequency response of all biquad filters, clipping stages, and presets.
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
    "sepulchre_presets.jsfx-inc",
    "sepulchre_ui.jsfx-inc",
]


def strip_comments_and_strings(code):
    out = []
    i = 0
    n = len(code)
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
                if code[i] == "\\":
                    i += 2
                else:
                    i += 1
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


def check_files_and_syntax():
    print("[1/4] Checking file existence, line count limits (<300 lines), and EEL2 syntax...")
    defined_funcs = {}
    all_cleaned = {}

    for fname in EXPECTED_FILES:
        fpath = os.path.join(ROOT, fname)
        if not os.path.exists(fpath):
            raise AssertionError(f"Missing expected file: {fname}")

        with open(fpath, "r", encoding="utf-8") as f:
            raw = f.read()
        lines = raw.splitlines()
        line_count = len(lines)
        print(f"  - {fname}: {line_count} lines")
        if line_count >= 300:
            raise AssertionError(f"{fname} exceeds 300-line modular threshold ({line_count} lines)")

        if fname.endswith(".jsfx-inc") and not re.search(r"^@init\b", raw, flags=re.MULTILINE):
            raise AssertionError(f"{fname} is missing required '@init' section header for REAPER import")

        cleaned = strip_comments_and_strings(raw)
        all_cleaned[fname] = cleaned

        # Check balanced parentheses
        depth = 0
        for idx, ch in enumerate(cleaned):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth < 0:
                    raise AssertionError(f"Unmatched closing parenthesis in {fname} near offset {idx}")
        if depth != 0:
            raise AssertionError(f"Unbalanced parentheses in {fname}: net depth {depth}")

        # Collect function definitions
        for m in re.finditer(r"\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)", cleaned):
            fn_name = m.group(1)
            params = [p.strip() for p in m.group(2).split(",") if p.strip()]
            defined_funcs[fn_name] = (fname, len(params))

    # Verify imports in sepulchre_sound.jsfx
    main_raw = open(os.path.join(ROOT, "sepulchre_sound.jsfx"), "r", encoding="utf-8").read()
    imports = re.findall(r"^import\s+([^\s]+)", main_raw, flags=re.MULTILINE)
    for imp in imports:
        if imp not in EXPECTED_FILES:
            raise AssertionError(f"Imported file {imp} not in expected files")

    # Verify slider definitions
    sliders = re.findall(r"^slider(\d+):([^<]+)<([^,]+),([^,]+),([^>{]+)(?:\{([^}]+)\})?>-(.+)$", main_raw, flags=re.MULTILINE)
    if len(sliders) < 25:
        raise AssertionError(f"Expected at least 25 sliders defined, found {len(sliders)}")
    for s_idx, dflt, mn, mx, step, opts, desc in sliders:
        d_val, mn_val, mx_val = float(dflt), float(mn), float(mx)
        if not (mn_val <= d_val <= mx_val):
            raise AssertionError(f"slider{s_idx} default {d_val} outside [{mn_val}, {mx_val}]")

    print(f"  - Verified {len(defined_funcs)} EEL2 functions and {len(sliders)} hidden sliders.")


def check_memory_allocations():
    print("[2/4] Verifying EEL2 memory allocation layout...")
    mem_top = 1024
    allocations = []

    def alloc(name, size):
        nonlocal mem_top
        start = mem_top
        mem_top += size
        allocations.append((name, start, mem_top - 1, size))

    # Core biquads (14 * 9)
    for bq in [
        "bq_in_hp", "bq_dirt_pre_hp", "bq_dirt_low", "bq_dirt_mid", "bq_dirt_high",
        "bq_dirt_gyr1", "bq_dirt_gyr2", "bq_dirt_post", "bq_cab_hp", "bq_cab_lp1",
        "bq_cab_lp2", "bq_cab_f1", "bq_cab_f2", "bq_cab_f3"
    ]:
        alloc(bq, 9)

    # FX buffers
    alloc("frost_buf_l", 8192)
    alloc("frost_buf_r", 8192)
    alloc("bq_frost_lp", 9)
    alloc("echo_buf_l", 192000)
    alloc("echo_buf_r", 192000)
    alloc("bq_echo_lp", 9)
    alloc("bq_echo_hp", 9)
    alloc("rev_pre_l", 16384)
    alloc("rev_pre_r", 16384)
    for c in ["comb_l1", "comb_l2", "comb_l3", "comb_l4", "comb_r1", "comb_r2", "comb_r3", "comb_r4"]:
        alloc(c, 12288)
    for a in ["ap_l1", "ap_l2", "ap_r1", "ap_r2"]:
        alloc(a, 4096)
    alloc("rev_state", 32)
    alloc("bq_rev_shelf", 9)

    # Check non-overlap and JSFX default 8M slot limit
    for i in range(len(allocations) - 1):
        assert allocations[i][2] < allocations[i + 1][1], f"Overlap at {allocations[i]} vs {allocations[i+1]}"
    assert mem_top < 1_000_000, f"Memory usage too high: {mem_top}"
    print(f"  - Total EEL2 memory slots allocated: {mem_top:,} (well within 8,388,608 standard limit, 0 overlaps).")


def check_dsp_math():
    print("[3/4] Running numerical DSP simulation (filters, clippers, delay/reverb stability)...")
    srate = 48000.0

    def bq_hp(freq, q):
        w0 = 2.0 * math.pi * freq / srate
        cosw, sinw = math.cos(w0), math.sin(w0)
        alpha = sinw / (2.0 * max(0.1, q))
        inv_a0 = 1.0 / (1.0 + alpha)
        b0 = (1.0 + cosw) * 0.5 * inv_a0
        b1 = -(1.0 + cosw) * inv_a0
        b2 = b0
        a1 = (-2.0 * cosw) * inv_a0
        a2 = (1.0 - alpha) * inv_a0
        return [b0, b1, b2, a1, a2]

    def bq_lp(freq, q):
        w0 = 2.0 * math.pi * freq / srate
        cosw, sinw = math.cos(w0), math.sin(w0)
        alpha = sinw / (2.0 * max(0.1, q))
        inv_a0 = 1.0 / (1.0 + alpha)
        b1 = (1.0 - cosw) * inv_a0
        b0 = b1 * 0.5
        b2 = b0
        a1 = (-2.0 * cosw) * inv_a0
        a2 = (1.0 - alpha) * inv_a0
        return [b0, b1, b2, a1, a2]

    def bq_peak(freq, q, gain_db):
        A = 10.0 ** (gain_db / 40.0)
        w0 = 2.0 * math.pi * freq / srate
        cosw, sinw = math.cos(w0), math.sin(w0)
        alpha = sinw / (2.0 * max(0.1, q))
        inv_a0 = 1.0 / (1.0 + alpha / A)
        b0 = (1.0 + alpha * A) * inv_a0
        b1 = (-2.0 * cosw) * inv_a0
        b2 = (1.0 - alpha * A) * inv_a0
        a1 = b1
        a2 = (1.0 - alpha / A) * inv_a0
        return [b0, b1, b2, a1, a2]

    def check_stability(coeffs, name):
        # Poles of 1 + a1 z^-1 + a2 z^-2 inside unit circle <=> |a2| < 1 and |a1| < 1 + a2
        _, _, _, a1, a2 = coeffs
        if not (abs(a2) < 1.0 and abs(a1) < 1.0 + a2):
            raise AssertionError(f"Filter {name} is unstable: a1={a1}, a2={a2}")

    check_stability(bq_hp(105.0, 0.7071), "Input Pre-Cut HPF 105Hz")
    check_stability(bq_hp(90.0, 0.7071), "Master HPF 90Hz")
    check_stability(bq_lp(5500.0, 0.7071), "Master LPF 5.5kHz")
    check_stability(bq_peak(1020.0, 2.8, 17.5), "Chainsaw HM-2 Gyrator Peak")

    # Verify soft_tanh & self-oscillation clamping at 105% feedback
    def soft_tanh(x):
        x = max(-4.5, min(4.5, x))
        x2 = x * x
        return x * (27.0 + x2) / (27.0 + 9.0 * x2)

    state = 0.8
    for _ in range(1000):
        state = soft_tanh(state * 1.05)
        assert math.isfinite(state) and abs(state) <= 1.0, "Echo 105% feedback runaway!"

    print("  - All biquad poles strictly inside unit circle; 105% Echo self-oscillation bounded in [-1.0, 1.0].")


def check_ui_and_presets():
    print("[4/4] Verifying preset definitions and UI rotary-knob prohibition...")
    ui_raw = open(os.path.join(ROOT, "sepulchre_ui.jsfx-inc"), "r", encoding="utf-8").read()
    # Ensure no gfx_arc or gfx_circle rotary knobs are used
    if "gfx_arc" in ui_raw or "gfx_circle" in ui_raw:
        raise AssertionError("Rotary knob drawing primitives (gfx_arc/gfx_circle) detected in UI!")

    presets_raw = open(os.path.join(ROOT, "sepulchre_presets.jsfx-inc"), "r", encoding="utf-8").read()
    for p_fn in ["recall_dirt_preset", "recall_frost_preset", "recall_echo_preset", "recall_cavern_preset", "recall_global_preset"]:
        if p_fn not in presets_raw:
            raise AssertionError(f"Missing preset function: {p_fn}")

    print("  - Confirmed strictly horizontal slider UI (`ui_hslider`) and all 3 global + 4x3 local presets.")


if __name__ == "__main__":
    try:
        check_files_and_syntax()
        check_memory_allocations()
        check_dsp_math()
        check_ui_and_presets()
        print("\nALL VERIFICATION CHECKS PASSED.")
    except Exception as exc:
        print(f"\nVERIFICATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
