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

    # --- PART 1: FOUR PEDALS DEFAULT LOUDNESS BALANCE (WAV IR Slot 0, Tube Amp) ---
    base = {
        1: 0.0, 2: 105.0, 3: -52.0, 4: 1,
        10: 1,
        20: 0, 40: 0,
        49: 1, 51: -0.5, 53: "01_BlackWizard_Center.wav", 54: 1, 55: 54.0, 56: 44.0, 57: 62.0, 58: 64.0,
        65: 0, 76: 1
    }

    pedals = [
        ("Default RAT", "RAT", {**base, **rc.PEDAL_DEFAULTS["RAT"]}),
        ("Default DS-1", "DS-1", {**base, **rc.PEDAL_DEFAULTS["DS-1"]}),
        ("Default Metal Zone", "Metal Zone", {**base, **rc.PEDAL_DEFAULTS["Metal Zone"]}),
        ("Default HM-2", "HM-2", {**base, **rc.PEDAL_DEFAULTS["HM-2"]}),
    ]

    p_gap = 0.50
    p_len = 0.45
    p_tracks = []
    for i, (name, model, cfg) in enumerate(pedals):
        p_tracks.append(rc.make_track(f"{name}_{model}", cfg, di_path, round(i * p_gap, 2), p_len))

    p_wav = os.path.join(RENDER_DIR, "out_pedals_balance.wav")
    p_rpp = os.path.join(RENDER_DIR, "test_pedals_balance.rpp")
    p_total_len = round(len(pedals) * p_gap + 0.2, 2)

    with open(p_rpp, "w", encoding="utf-8") as f:
        f.write(rc.build_rpp(p_tracks, p_wav, p_total_len, sr=sr))

    rc.run_reaper(p_rpp)
    p_samples = rc.read_wav24(p_wav, channel=0)
    seg_spl = int(0.40 * sr)

    p_results = []
    for i, (name, model, _) in enumerate(pedals):
        st = int((i * p_gap + 0.03) * sr)
        seg = p_samples[st : st + seg_spl]
        lufs = rc.calc_lufs(seg)
        pk = rc.calc_peak_db(seg)
        p_results.append((name, model, lufs, pk))

    mt2_lufs = p_results[2][2] # Metal Zone baseline

    print("\n" + "=" * 96)
    print("--- 1. FOUR PEDALS DEFAULT LOUDNESS BALANCE (WAV IR Slot 0, Tube Amp) ---")
    print(f"{'Pedal':<22} | {'Voicing':<12} | {'WAV LUFS':<10} | {'Delta vs MT-2':<14} | {'WAV Peak':<10} | Limiter Status")
    print("=" * 96)

    for name, model, lufs, pk in p_results:
        delta = lufs - mt2_lufs
        headroom = KNEE_DBFS - pk
        status = f"Clean ({headroom:.2f} dB below knee)" if pk < KNEE_DBFS else f"**EXCEEDED** (+{-headroom:.2f} dB)"
        print(f"{name:<22} | {model:<12} | {lufs:6.2f} LUFS| {delta:+6.2f} dB      | {pk:6.2f} dBFS | {status}")
        assert pk < KNEE_DBFS, f"{name} exceeded limiter knee: {pk:.2f} dBFS >= {KNEE_DBFS:.2f} dBFS"

    print("=" * 96)

    if os.path.exists(p_wav): os.remove(p_wav)
    if os.path.exists(p_rpp): os.remove(p_rpp)

    # --- PART 2: GLOBAL PRESETS LOUDNESS GATE (WAV IR Slot 0, Isolated Tracks) ---
    # Round 59 / Round 76 (R4): derived from rc.GLOBAL_PRESET_NAMES; every preset within +/-1.5 dB from median, peak < -3.10 dBFS.
    preset_entries = rc.GLOBAL_PRESET_NAMES
    n_presets = len(preset_entries)

    gap = 10.0
    item_len = 0.45
    tracks = []
    for idx, _, _ in preset_entries:
        cfg = dict(presets[idx])
        cfg[49] = 1
        cfg[52] = 1
        cfg[53] = "01_BlackWizard_Center.wav" # WAV IR slot 0
        t_pos = idx * gap
        tracks.append(rc.make_track(f"Track_{idx}", cfg, di_path, pos=t_pos, length=item_len))

    out_wav = os.path.join(RENDER_DIR, "out_presets_gate.wav")
    rpp_path = os.path.join(RENDER_DIR, "test_presets_gate.rpp")
    total_len = n_presets * gap + 2.0

    with open(rpp_path, "w", encoding="utf-8") as f:
        f.write(rc.build_rpp(tracks, out_wav, total_len, sr=sr))

    print(f"\nRendering {n_presets} Global Presets in live REAPER (WAV IR Slot 0, Active FX, Isolated Tracks)...")
    rc.run_reaper(rpp_path)

    samples = rc.read_wav24(out_wav, channel=0)
    lufs_list = []
    pk_list = []
    for idx, _, _ in preset_entries:
        seg = samples[int(idx * gap * sr) : int((idx * gap + item_len) * sr)]
        lufs = rc.calc_lufs(seg)
        pk = rc.calc_peak_db(seg)
        lufs_list.append(lufs)
        pk_list.append(pk)

    med_lufs = np.median(lufs_list)

    print("\n" + "=" * 105)
    print(f"--- 2. GLOBAL PRESETS LOUDNESS GATE (WAV IR Slot 0, Active FX, Median: {med_lufs:.2f} LUFS) ---")
    print(f"{'Preset':<28} | {'Mono LUFS':<10} | {'Delta vs Med':<14} | {'True Peak':<10} | Limiter Status (Knee: -3.10 dBFS)")
    print("=" * 105)

    fails = []
    for idx, name, _ in preset_entries:
        lufs = lufs_list[idx]
        pk = pk_list[idx]
        delta = lufs - med_lufs
        headroom = KNEE_DBFS - pk
        p_cfg = presets[idx]
        is_dry = p_cfg.get(20, 0) < 0.5 and (p_cfg.get(40, 0) < 0.5 or p_cfg.get(45, 0) <= 15)
        status = f"Clean ({headroom:.2f} dB below knee)" if pk < KNEE_DBFS else f"**EXCEEDED** (+{-headroom:.2f} dB)"
        tag = "" if is_dry else " [FX info]"
        print(f"{name:<28} | {lufs:6.2f} LUFS| {delta:+6.2f} dB      | {pk:6.2f} dBFS | {status}{tag}")
        if is_dry and abs(delta) > 1.5:
            fails.append(f"{name} loudness delta {delta:+.2f} dB exceeds +/-1.5 dB from median ({med_lufs:.2f} LUFS)")
        if pk >= KNEE_DBFS:
            fails.append(f"{name} exceeded limiter knee: {pk:.2f} dBFS >= {KNEE_DBFS:.2f} dBFS")
    assert not fails, "\n".join(fails)

    print("=" * 105)
    print(f"LOUDNESS GATE PASSED: All {n_presets} presets within +/-{max(abs(l - med_lufs) for l in lufs_list):.2f} dB of median ({med_lufs:.2f} LUFS), 0 knee exceedances.")

    if os.path.exists(out_wav): os.remove(out_wav)
    if os.path.exists(rpp_path): os.remove(rpp_path)

    return p_results, lufs_list, pk_list

if __name__ == "__main__":
    run_per_pedal_loudness_comparison()
