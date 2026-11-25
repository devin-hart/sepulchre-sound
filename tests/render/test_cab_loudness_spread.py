#!/usr/bin/env python3
"""
Round 90 Task 13: Reproducible live REAPER loudness spread check for Built-in 4x12 vs 01_BlackWizard_Center.wav
across all 4 pedals at defaults, on both a deterministic 2.0 s broadband multi-note black-metal riff and the
synthetic three-sine chord `tests/render/di_input.wav`.

Run:
  REAPER_EXE=/usr/bin/reaper APPDATA=~/.config python3 tests/render/test_cab_loudness_spread.py
Optional: pass --compare-old <git_ref> to also render an older commit (e.g. 84019a9) in the same run.
"""

import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_common as rc

SR = 48000
JSFX_FILES = [
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
ASSET_FILES = ["sepulchre_bg.jpg", "sepulchre_titles.png"]
EFFECTS_DIR = os.path.join(rc.APPDATA_DIR, "REAPER", "Effects")


def generate_bm_riff(sr=SR, dur=2.0):
    """Deterministic 2.0 s broadband multi-note tremolo/chord guitar-spectrum riff (harmonics 82 Hz..6.5 kHz, -12 dBFS peak)."""
    n = int(dur * sr)
    riff = np.zeros(n, dtype=np.float64)
    chords = [
        (82.41, 123.47, 164.81, 246.94),
        (87.31, 130.81, 174.61, 261.63),
        (98.00, 146.83, 196.00, 293.66),
        (116.54, 174.61, 233.08, 349.23),
        (123.47, 185.00, 246.94, 369.99),
        (146.83, 220.00, 293.66, 440.00),
        (164.81, 246.94, 329.63, 493.88),
        (82.41, 123.47, 164.81, 196.00),
    ]
    step = n // len(chords)
    for idx, chord in enumerate(chords):
        st = idx * step
        en = min(n, st + step)
        tl = np.arange(en - st) / sr
        env = np.exp(-(tl % 0.125) * 14.0) * (1.0 - np.exp(-(tl % 0.125) * 400.0))
        sig = np.zeros(en - st, dtype=np.float64)
        for f0 in chord:
            for h in range(1, 20):
                if f0 * h < 6500.0:
                    sig += (1.0 / (h ** 1.15)) * np.sin(2.0 * math.pi * f0 * h * tl + 0.3 * h)
        riff[st:en] = sig * env
    return riff / np.max(np.abs(riff)) * (10.0 ** (-12.0 / 20.0))


def install_clean(commit, folder):
    dst = os.path.join(EFFECTS_DIR, folder)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst, exist_ok=True)
    for f in JSFX_FILES + ASSET_FILES:
        if commit is None:
            shutil.copy2(os.path.join(rc.REPO_DIR, f), os.path.join(dst, f))
        else:
            data = subprocess.check_output(["git", "show", f"{commit}:{f}"], cwd=rc.REPO_DIR)
            with open(os.path.join(dst, f), "wb") as out:
                out.write(data)
    return dst


def measure_build(fx_folder, wav_path, dur, cab_src, workdir):
    """Render all 4 pedals at defaults in one RPP (sequential slots) and return {pedal_name: LUFS}."""
    slot_len = dur + 0.30
    peds = list(rc.PEDAL_DEFAULTS.items())
    tracks = []
    for idx, (ped_name, ped_cfg) in enumerate(peds):
        s = dict(rc.FRESH_INSERT_DEFAULTS)
        s.update({20: 0, 40: 0, 65: 0, 49: 1, 52: cab_src, 53: "01_BlackWizard_Center.wav", 54: 1, 51: 0.0})
        s.update(ped_cfg)
        tracks.append(rc.make_track(
            f"{ped_name}_{cab_src}", s, wav_path, pos=idx * slot_len, length=dur,
            fx_path=f"{fx_folder}/sepulchre_sound.jsfx",
        ))
    stem = os.path.splitext(os.path.basename(wav_path))[0]
    rpp = os.path.join(workdir, f"{fx_folder}_{cab_src}_{stem}.rpp")
    out_wav = os.path.join(workdir, f"{fx_folder}_{cab_src}_{stem}.wav")
    with open(rpp, "w", encoding="utf-8") as f:
        f.write(rc.build_rpp(tracks, out_wav, len(peds) * slot_len))
    rc.run_reaper(rpp)
    y = rc.read_wav24(out_wav, 0)
    res = {}
    n_eval = int(dur * SR)
    for idx, (ped_name, _) in enumerate(peds):
        st = int(idx * slot_len * SR)
        res[ped_name] = rc.calc_lufs(y[st : st + n_eval])
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare-old", default=None, help="Optional git ref for old Built-in baseline (e.g. 84019a9)")
    ap.add_argument("--compare-untrimmed", default=None, help="Optional git ref for untrimmed Cand A (e.g. 927ac5f)")
    ap.add_argument("--assert-target", action="store_true", help="Fail if mean |Built-in - IR01| on riff > 0.5 dB")
    args = ap.parse_args()

    workdir = tempfile.mkdtemp(prefix="sep_cab_spread_")
    installed = []
    try:
        riff = generate_bm_riff()
        riff_wav = os.path.join(workdir, "bm_riff_2s.wav")
        rc.write_wav24(riff_wav, riff, sr=SR, nchannels=2)

        di_mono = rc.read_wav24(os.path.join(rc.RENDER_DIR, "di_input.wav"), 0)
        di_loop = np.tile(di_mono, 4)
        di_wav = os.path.join(workdir, "di_input_4x.wav")
        rc.write_wav24(di_wav, di_loop, sr=SR, nchannels=2)

        cur_fld = "sepulchre_spread_cur"
        installed.append(install_clean(None, cur_fld))
        old_fld = unt_fld = None
        if args.compare_old:
            old_fld = "sepulchre_spread_old"
            installed.append(install_clean(args.compare_old, old_fld))
        if args.compare_untrimmed:
            unt_fld = "sepulchre_spread_unt"
            installed.append(install_clean(args.compare_untrimmed, unt_fld))

        for label, wpath, dur in [
            ("2.0 s broadband multi-note riff", riff_wav, 2.0),
            ("di_input.wav x4 (synthetic 3-sine chord)", di_wav, len(di_loop) / float(SR)),
        ]:
            ir01 = measure_build(cur_fld, wpath, dur, 1, workdir)
            cur_bi = measure_build(cur_fld, wpath, dur, 0, workdir)
            old_bi = measure_build(old_fld, wpath, dur, 0, workdir) if old_fld else None
            unt_bi = measure_build(unt_fld, wpath, dur, 0, workdir) if unt_fld else None

            print(f"\n=== {label} (Built-in vs 01_BlackWizard_Center.wav) ===")
            hdr = f"{'Pedal':<12} | {'IR01':>7}"
            if old_bi: hdr += f" | {'Old Δ':>8}"
            if unt_bi: hdr += f" | {'CandA Δ':>8}"
            hdr += f" | {'Worktree Δ':>10}"
            print(hdr)
            print("-" * len(hdr))
            deltas_cur = []
            for p in rc.PEDAL_DEFAULTS:
                row = f"{p:<12} | {ir01[p]:+6.2f}"
                if old_bi: row += f" | {old_bi[p] - ir01[p]:+7.2f}"
                if unt_bi: row += f" | {unt_bi[p] - ir01[p]:+7.2f}"
                d = cur_bi[p] - ir01[p]
                deltas_cur.append(d)
                row += f" | {d:+9.2f}"
                print(row)
            mean_d = float(np.mean(deltas_cur))
            max_d = float(np.max(np.abs(deltas_cur)))
            print(f"  Worktree Built-in vs IR01: mean={mean_d:+.2f} dB | max|Δ|={max_d:.2f} dB")
            if args.assert_target and "broadband" in label:
                assert max_d <= 0.5, f"Built-in vs IR01 max|Δ|={max_d:.2f} dB exceeds 0.5 dB target!"
    finally:
        for d in installed + [workdir]:
            if os.path.exists(d):
                shutil.rmtree(d)


if __name__ == "__main__":
    main()
