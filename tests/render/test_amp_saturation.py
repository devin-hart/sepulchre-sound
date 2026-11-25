#!/usr/bin/env python3
"""
Round 85 Task 11a: Measure how much Sepulchre Sound's Amp Stage (TUBE / SOLID) saturates on its own
(pedal off, GE-7/chorus/reverb/cab off, Master = -12 dB so output stays strictly below the -3.1 dBFS limiter knee),
compared against the Metal Zone (Preset 01 settings, Amp OFF) as a distortion reference.

Run:
  REAPER_EXE=/usr/bin/reaper APPDATA=~/.config python3 tests/render/test_amp_saturation.py
"""

import math
import os
import shutil
import sys
import tempfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_common as rc

SR = 48000
MASTER_DB = -12.0
LIMITER_KNEE = 0.7  # -3.10 dBFS
SINE_LEVELS_DB = [-36, -30, -24, -18, -12, -6, 0]
DI_TRIMS_DB = [0, 6, 12, 18]


def base_sliders(mode):
    """Common setup: gate/EQ/chorus/reverb/cab off, amp tone at defaults, AIR=50, Pre-Cut=40 Hz, Master=-12 dB."""
    s = dict(rc.FRESH_INSERT_DEFAULTS)
    s.update({
        1: 0.0, 2: 40.0, 4: 0,
        10: 0, 20: 0, 40: 0, 49: 0, 65: 0,
        51: MASTER_DB,
        55: 46, 56: 52, 57: 58, 58: 50,
    })
    if mode == "TUBE":
        s[54] = 1
    elif mode == "SOLID":
        s[54] = 2
    elif mode == "MT-2":
        s[10] = 1
        s[11] = 2
        s[54] = 0
    else:
        raise ValueError(mode)
    return s


def calc_thd_h2_10(sig, sr=SR, f0=100.0):
    """Harmonics 2..10 RMS / fundamental RMS (as percentage) over an exact integer-cycle steady-state window."""
    # Drop first 0.25 s (transients / DC blocker settle), take 0.50 s = 50 exact cycles of 100 Hz
    start = int(0.25 * sr)
    n = int(0.50 * sr)
    seg = sig[start:start + n]
    spec = np.fft.rfft(seg)
    bin_f0 = int(round(f0 * n / sr))  # bin 50
    h1 = abs(spec[bin_f0])
    if h1 < 1e-12:
        return 0.0
    h_sq = sum(abs(spec[bin_f0 * k]) ** 2 for k in range(2, 11))
    return 100.0 * math.sqrt(h_sq) / h1


def crest_db(sig):
    pk = float(np.max(np.abs(sig)))
    rms = float(np.sqrt(np.mean(sig ** 2)))
    return 20.0 * math.log10(max(1e-12, pk) / max(1e-12, rms))


def interp_crossing(levels, thds, target):
    for i in range(len(levels) - 1):
        if thds[i] < target <= thds[i + 1]:
            frac = (target - thds[i]) / max(1e-12, thds[i + 1] - thds[i])
            return f"{levels[i] + frac * (levels[i + 1] - levels[i]):+.1f} dBFS"
    if thds[0] >= target:
        return f"<{levels[0]} dBFS"
    return f">{levels[-1]} dBFS"


def main():
    workdir = tempfile.mkdtemp(prefix="sep_amp_sat_")
    try:
        modes = ["TUBE", "SOLID", "MT-2"]
        # 1. Generate 100 Hz sine files at exact input levels (-36..0 dBFS), 0.85 s
        n_sine = int(0.85 * SR)
        t = np.arange(n_sine) / SR
        sine_unit = np.sin(2.0 * math.pi * 100.0 * t)
        sine_files = {}
        for lvl in SINE_LEVELS_DB:
            p = os.path.join(workdir, f"sine100_{lvl}.wav")
            rc.write_wav24(p, sine_unit * (10.0 ** (lvl / 20.0)), sr=SR, nchannels=2)
            sine_files[lvl] = p

        # Render sine sweep: one RPP per mode with sequential 1.0 s slots
        thd_table = {m: [] for m in modes}
        max_pk_seen = 0.0
        for m in modes:
            tracks = []
            for idx, lvl in enumerate(SINE_LEVELS_DB):
                s = base_sliders(m)
                tracks.append(rc.make_track(f"{m}_{lvl}", s, sine_files[lvl], pos=idx * 1.0, length=0.85))
            rpp = os.path.join(workdir, f"sine_{m}.rpp")
            out_wav = os.path.join(workdir, f"sine_{m}.wav")
            with open(rpp, "w", encoding="utf-8") as f:
                f.write(rc.build_rpp(tracks, out_wav, len(SINE_LEVELS_DB) * 1.0))
            rc.run_reaper(rpp)
            y = rc.read_wav24(out_wav, 0)
            for idx, lvl in enumerate(SINE_LEVELS_DB):
                slot = y[idx * SR : idx * SR + n_sine]
                pk = float(np.max(np.abs(slot)))
                max_pk_seen = max(max_pk_seen, pk)
                assert pk < LIMITER_KNEE, f"{m} sine {lvl} dBFS hit limiter knee: peak={pk:.4f}"
                thd_table[m].append(calc_thd_h2_10(slot))

        print(f"=== 100 Hz Sine THD (harmonics 2..10, Master={MASTER_DB:.1f} dB, max peak={20*math.log10(max_pk_seen):+.2f} dBFS) ===")
        print(f"{'Input':>9} | {'TUBE THD':>10} | {'SOLID THD':>10} | {'MT-2 (ref)':>10}")
        print("-" * 48)
        for i, lvl in enumerate(SINE_LEVELS_DB):
            print(f"{lvl:+4d} dBFS | {thd_table['TUBE'][i]:9.2f}% | {thd_table['SOLID'][i]:9.2f}% | {thd_table['MT-2'][i]:9.2f}%")
        print("\nTHD threshold crossings:")
        for m in modes:
            c1 = interp_crossing(SINE_LEVELS_DB, thd_table[m], 1.0)
            c10 = interp_crossing(SINE_LEVELS_DB, thd_table[m], 10.0)
            c30 = interp_crossing(SINE_LEVELS_DB, thd_table[m], 30.0)
            print(f"  {m:<5}: 1% @ {c1:<10} | 10% @ {c10:<10} | 30% @ {c30:<10}")

        # 2. DI renders: di_input.wav & decay_low_e.wav at Trim 0, +6, +12, +18 dB
        di_files = [
            ("di_input.wav", os.path.join(rc.RENDER_DIR, "di_input.wav"), 0.50),
            ("decay_low_e.wav", os.path.join(rc.RENDER_DIR, "decay_low_e.wav"), 1.60),
        ]
        for fname, fpath, dur in di_files:
            dry = rc.read_wav24(fpath, 0)
            in_cf = crest_db(dry)
            in_lufs = rc.calc_lufs(dry)
            print(f"\n=== {fname} (Input peak={rc.calc_peak_db(dry):+.2f} dBFS, crest={in_cf:.2f} dB, LUFS={in_lufs:+.2f}) ===")
            print(f"{'Mode':<6} | {'Trim':>5} | {'Out Peak':>9} | {'Crest':>8} | {'dCrest':>8} | {'LUFS':>8}")
            print("-" * 60)
            slot_len = dur + 0.25
            for m in modes:
                tracks = []
                for idx, tr in enumerate(DI_TRIMS_DB):
                    s = base_sliders(m)
                    s[1] = float(tr)
                    tracks.append(rc.make_track(f"{m}_{tr}", s, fpath, pos=idx * slot_len, length=dur))
                rpp = os.path.join(workdir, f"{fname}_{m}.rpp")
                out_wav = os.path.join(workdir, f"{fname}_{m}.wav")
                with open(rpp, "w", encoding="utf-8") as f:
                    f.write(rc.build_rpp(tracks, out_wav, len(DI_TRIMS_DB) * slot_len))
                rc.run_reaper(rpp)
                y = rc.read_wav24(out_wav, 0)
                lufs_vals = []
                for idx, tr in enumerate(DI_TRIMS_DB):
                    st = int(idx * slot_len * SR)
                    en = st + int(dur * SR)
                    seg = y[st:en]
                    pk = float(np.max(np.abs(seg)))
                    assert pk < LIMITER_KNEE, f"{fname} {m} Trim +{tr} hit limiter knee: {pk:.4f}"
                    cf = crest_db(seg)
                    lu = rc.calc_lufs(seg)
                    lufs_vals.append(lu)
                    print(f"{m:<6} | {tr:+3d} dB | {rc.calc_peak_db(seg):+6.2f} dB | {cf:5.2f} dB | {cf - in_cf:+5.2f} dB | {lu:+6.2f}")
                print(f"  -> {m} loudness gain from Trim 0 to +18 dB: {lufs_vals[-1] - lufs_vals[0]:+.2f} dB (linear = +18.00 dB)")
    finally:
        if os.path.exists(workdir):
            shutil.rmtree(workdir)


if __name__ == "__main__":
    main()
