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

KNEE_DBFS = 20.0 * math.log10(0.70) # -3.10 dBFS

def run_per_pedal_loudness_comparison():
    sr = 48000
    di_path = os.path.join(RENDER_DIR, "di_input.wav")
    if not os.path.exists(di_path):
        raise FileNotFoundError(f"DI input missing at {di_path}")

    presets_path = os.path.join(REPO_DIR, "sepulchre_presets.jsfx-inc")
    with open(presets_path, "r", encoding="utf-8") as f:
        presets = v.parse_global_presets(f.read())

    # Default base configuration (Tube Amp, valid sliders only)
    base = {
        1: 0.0, 2: 105.0, 3: -52.0, 4: 1,
        10: 1,
        20: 0, 40: 0, # Disable chorus/reverb for clean dry loudness
        51: -0.5, 54: 1, 55: 54.0, 56: 44.0, 57: 62.0, 58: 64.0,
        65: 0, 76: 1
    }

    # 4 pedals at factory defaults
    rat_def = {**base, **rc.PEDAL_DEFAULTS["RAT"]}
    ds1_def = {**base, **rc.PEDAL_DEFAULTS["DS-1"]}
    mt2_def = {**base, **rc.PEDAL_DEFAULTS["Metal Zone"]}
    hm2_def = {**base, **rc.PEDAL_DEFAULTS["HM-2"]}

    pedal_cases = [
        ("Default RAT", "RAT", rat_def),
        ("Default DS-1", "DS-1", ds1_def),
        ("Default Metal Zone", "Metal Zone", mt2_def),
        ("Default HM-2", "HM-2", hm2_def),
    ]

    preset_cases = [
        ("Preset 0 (Tight Rhythm)", "MT-2", dict(presets[0])),
        ("Preset 1 (Cold Lead)", "RAT", dict(presets[1])),
        ("Preset 2 (Doom Wall)", "HM-2", dict(presets[2])),
        ("Preset 3 (Raw 4-Track)", "DS-1", dict(presets[3])),
        ("Preset 4 (Swedish Chainsaw)", "HM-2", dict(presets[4])),
        ("Preset 6 (Ambient Swell)", "Clean", dict(presets[6])),
    ]

    # Ensure dry loudness check for presets (no chorus/reverb bleed)
    for name, model, d in preset_cases:
        d[20] = 0; d[40] = 0

    all_cases = pedal_cases + preset_cases

    item_len = 0.45
    item_gap = 0.50
    total_len = round(len(all_cases) * item_gap + 0.2, 2)

    tracks = []
    for i, (name, model, cfg) in enumerate(all_cases):
        t_pos = round(i * item_gap, 2)
        tracks.append(rc.make_track(f"{name}_{model}", cfg, di_path, t_pos, item_len))

    out_wav = os.path.join(RENDER_DIR, "out_per_pedal_loudness.wav")
    rpp_path = os.path.join(RENDER_DIR, "test_per_pedal_loudness.rpp")

    with open(rpp_path, "w", encoding="utf-8") as f:
        f.write(rc.build_rpp(tracks, out_wav, total_len, sr=sr))

    if os.path.exists(out_wav):
        os.remove(out_wav)

    print("Rendering raw (no cab) per-pedal and preset test cases in REAPER...")
    rc.run_reaper(rpp_path)

    samples = rc.read_wav24(out_wav, channel=0)
    seg_spl = int(0.40 * sr)

    ir_path = os.path.join(rc.IR_DIR, "01_BlackWizard_Center.wav")
    ir = rc.read_wav24(ir_path)

    results = []
    for i, (name, model, _) in enumerate(all_cases):
        st = int((i * item_gap + 0.03) * sr)
        seg = samples[st : st + seg_spl]
        raw_lufs = rc.calc_lufs(seg)
        raw_pk = rc.calc_peak_db(seg)

        # Offline convolution with 01_BlackWizard_Center.wav (Round 53 verification)
        N = len(seg) + len(ir) - 1
        conv = np.fft.irfft(np.fft.rfft(seg, n=N) * np.fft.rfft(ir, n=N))[:len(seg)]
        ir_lufs = rc.calc_lufs(conv)
        ir_pk = rc.calc_peak_db(conv)

        results.append((name, model, raw_lufs, raw_pk, ir_lufs, ir_pk))

    # Baseline: Metal Zone default loudness
    mt2_ir_lufs = results[2][4] # Index 2 is Default Metal Zone (IR convolved)

    print("\n" + "=" * 105)
    print("--- 1. FOUR PEDALS DEFAULT LOUDNESS BALANCE (Amp Tube Head, Offline Convolved with 01_BlackWizard_Center) ---")
    print(f"{'Pedal':<22} | {'Voicing':<12} | {'Raw Peak':<10} | {'Raw LUFS':<10} | {'IR LUFS':<10} | {'Delta vs MT-2':<14} | Headroom")
    print("=" * 105)

    for name, model, raw_lufs, raw_pk, ir_lufs, ir_pk in results[:4]:
        delta = ir_lufs - mt2_ir_lufs
        headroom = KNEE_DBFS - raw_pk
        status = f"Clean ({headroom:.2f} dB below knee)" if raw_pk < KNEE_DBFS else f"**EXCEEDED** (+{-headroom:.2f} dB)"
        print(f"{name:<22} | {model:<12} | {raw_pk:6.2f} dBFS | {raw_lufs:6.2f} LUFS| {ir_lufs:6.2f} LUFS| {delta:+6.2f} dB      | {status}")
        assert raw_pk < KNEE_DBFS, f"{name} exceeded limiter knee: {raw_pk:.2f} dBFS >= {KNEE_DBFS:.2f} dBFS"

    print("=" * 105)

    print("\n" + "=" * 105)
    print("--- 2. GLOBAL PRESETS RAW HEADROOM & OFFLINE IR LOUDNESS (Dry FX) ---")
    print(f"{'Preset':<28} | {'Voicing':<10} | {'Raw Peak':<10} | {'Raw LUFS':<10} | {'IR LUFS':<10} | Limiter Status")
    print("=" * 105)

    for name, model, raw_lufs, raw_pk, ir_lufs, ir_pk in results[4:]:
        headroom = KNEE_DBFS - raw_pk
        status = f"Clean ({headroom:.2f} dB below knee)" if raw_pk < KNEE_DBFS else f"**EXCEEDED** (+{-headroom:.2f} dB)"
        print(f"{name:<28} | {model:<10} | {raw_pk:6.2f} dBFS | {raw_lufs:6.2f} LUFS| {ir_lufs:6.2f} LUFS| {status}")
        assert raw_pk < KNEE_DBFS, f"{name} exceeded limiter knee: {raw_pk:.2f} dBFS >= {KNEE_DBFS:.2f} dBFS"

    print("=" * 105)

    # Clean up test files
    if os.path.exists(out_wav): os.remove(out_wav)
    if os.path.exists(rpp_path): os.remove(rpp_path)

    return results

if __name__ == "__main__":
    run_per_pedal_loudness_comparison()
