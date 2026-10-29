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

def test_hm2_decay_circuit():
    sr = 48000
    # 1. Synthesize -40 dBFS decaying low-E (82.41 Hz) note
    note_dur = 1.2
    total_dur = 1.6
    n_spl = int(total_dur * sr)
    t = np.arange(int(note_dur * sr)) / sr
    decay_env = 0.01 * np.exp(-t * 3.5)
    f0 = 82.41
    note_sig = (
        0.7 * np.sin(2 * np.pi * f0 * t)
        + 0.2 * np.sin(2 * np.pi * 2 * f0 * t)
        + 0.1 * np.sin(2 * np.pi * 3 * f0 * t)
    ) * decay_env
    note = np.zeros(n_spl)
    note[:len(note_sig)] = note_sig

    note_wav_p = os.path.join(RENDER_DIR, "decay_low_e.wav")
    rc.write_wav24(note_wav_p, note, sr=sr)

    # 2. Render through Preset 4 (Swedish Chainsaw)
    presets_path = os.path.join(REPO_DIR, "sepulchre_presets.jsfx-inc")
    with open(presets_path, "r", encoding="utf-8") as f:
        presets = v.parse_global_presets(f.read())
    p4 = dict(presets[4])
    p4[4] = 0 # Noise gate off so we can hear note decay down to coring floor
    p4[20] = 0; p4[30] = 0; p4[40] = 0 # No delay/reverb tail

    out_decay = os.path.join(RENDER_DIR, "out_decay_hm2.wav")
    rpp_decay_p = os.path.join(RENDER_DIR, "test_decay.rpp")
    rpp_content = rc.build_rpp(rc.make_track("HM2_Decay", p4, note_wav_p, pos=0.0, length=total_dur), out_decay, total_dur, sr=sr)
    with open(rpp_decay_p, "w", encoding="utf-8") as f:
        f.write(rpp_content)

    if os.path.exists(out_decay):
        os.remove(out_decay)

    print("Rendering HM-2 low-E decaying note in REAPER...")
    rc.run_reaper(rpp_decay_p)

    out_spl = rc.read_wav24(out_decay, channel=0)

    # Analyze the decay tail
    tail_end = out_spl[int(1.2 * sr) : int(1.5 * sr)]
    dc_floor = float(np.mean(tail_end))
    peak_tail = float(np.max(np.abs(tail_end)))

    print(f"\nHM-2 Decay Tail Analysis:")
    print(f"Tail End DC offset: {dc_floor:+.6f} (Limit: < 0.0005)")
    print(f"Tail End Peak:      {peak_tail:.6f}")
    assert abs(dc_floor) < 0.0005, f"HM-2 tail DC offset {dc_floor:.6f} exceeded 0.0005!"
    print("HM-2 decay sputtering clean and DC-free.")

    if os.path.exists(rpp_decay_p):
        os.remove(rpp_decay_p)

if __name__ == "__main__":
    test_hm2_decay_circuit()
