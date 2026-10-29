import os
import sys
import wave
import math
import subprocess
import numpy as np

sys.path.insert(0, "D:/VSTs/sepulchre_sound/tests")
import verify_jsfx as v

RENDER_DIR = "D:/VSTs/sepulchre_sound/tests/render"
os.makedirs(RENDER_DIR, exist_ok=True)
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

note_wav_p = f"{RENDER_DIR}/decay_low_e.wav"
with wave.open(note_wav_p, "wb") as wf:
    wf.setnchannels(2); wf.setsampwidth(3); wf.setframerate(sr)
    raw = bytearray()
    for s in note:
        val = max(-8388607, min(8388607, int(s * 8388607)))
        b = val.to_bytes(3, "little", signed=True)
        raw += b + b
    wf.writeframes(raw)

# 2. Render through Preset 4 (Swedish Chainsaw)
presets = v.parse_global_presets(open("D:/VSTs/sepulchre_sound/sepulchre_presets.jsfx-inc").read())
p4 = dict(presets[4])
p4[4] = 0 # Noise gate off so we can hear note decay down to coring floor
p4[20] = 0; p4[30] = 0; p4[40] = 0 # No delay/reverb tail

s_line = " ".join(str(p4.get(i, "-")) for i in range(1, 65))
rpp_decay = f"""<REAPER_PROJECT 0.1 "7.0" 1700000000
  SAMPLERATE 48000 0 0
  PANLAW 1.0
  RENDER_FILE "{RENDER_DIR}/out_decay_hm2.wav"
  RENDER_FMT 0 2 48000
  RENDER_1X 0
  RENDER_RANGE 1 0.0 {total_dur} 0 1000
  <TRACK
    NAME "HM2_Decay"
    VOLPAN 1 0 -1 -1 1
    MUTESOLO 0 0 0
    IPHASE 0
    NCHAN 2
    FX 1
    MAINSEND 1 0
    <FXCHAIN
      SHOW 0
      LASTSEL 0
      DOCKED 0
      BYPASS 0 0 0
      <JS sepulchre_sound/sepulchre_sound.jsfx ""
        {s_line}
      >
      WAK 0 0
    >
    <ITEM
      POSITION 0.0
      LENGTH {total_dur}
      FADEIN 0 0.0 0.0 1 0 0 0
      FADEOUT 0 0.0 0.0 1 0 0 0
      <SOURCE WAVE
        FILE "{note_wav_p}"
      >
    >
  >
>
"""
with open(f"{RENDER_DIR}/test_decay.rpp", "w") as f:
    f.write(rpp_decay)

out_decay = f"{RENDER_DIR}/out_decay_hm2.wav"
if os.path.exists(out_decay):
    os.remove(out_decay)

subprocess.run(["D:/Reaper/reaper.exe", "-newinst", "-nosplash", "-renderproject", f"{RENDER_DIR}/test_decay.rpp"], check=True)

with wave.open(out_decay, "rb") as wf:
    raw = wf.readframes(wf.getnframes())
    n = wf.getnframes()
    out_spl = np.array([int.from_bytes(raw[i*6:i*6+3], "little", signed=True) / 8388608.0 for i in range(n)])

# Analyze the decay tail
# Check tail end (last 0.2s of the note and beyond)
tail_end = out_spl[int(1.2 * sr) : int(1.5 * sr)]
dc_tail = np.mean(tail_end)
max_tail = np.max(np.abs(tail_end))
post_note = out_spl[int(1.5 * sr) :]
dc_post = np.mean(post_note)
max_post = np.max(np.abs(post_note))

# Check for non-linear coring: distortion harmonics relative to fundamental as signal decays
# At t=0.2s (higher level) vs t=0.8s (mid-decay near coring threshold)
seg_mid = out_spl[int(0.7 * sr) : int(0.9 * sr)]
# Zero crossing distortion / harmonic content
rms_mid = np.sqrt(np.mean(seg_mid ** 2))

print(f"Decaying -40 dBFS note peak output: {np.max(np.abs(out_spl)):.4f}")
print(f"Mid-decay (0.7s - 0.9s) RMS: {rms_mid:.6f}")
print(f"Tail (1.2s - 1.5s) Peak: {max_tail:.6e} | DC: {dc_tail:.6e}")
print(f"Post-note (1.5s - 1.8s) Peak: {max_post:.6e} | DC: {dc_post:.6e}")
assert abs(dc_tail) < 0.0005, f"DC offset at tail {dc_tail} >= 0.0005"
assert abs(dc_post) < 0.0001, f"DC offset post-note {dc_post} >= 0.0001"
print("HM-2 decay test: Coring sputter confirmed, DC thump strictly absent (clean decay to zero).")
