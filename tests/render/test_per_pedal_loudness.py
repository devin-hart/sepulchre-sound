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
di_path = f"{RENDER_DIR}/di_input.wav"

presets = v.parse_global_presets(open("D:/VSTs/sepulchre_sound/sepulchre_presets.jsfx-inc").read())

# Default base configuration
base = {
    1: 0.0, 2: 105.0, 3: -52.0, 4: 1,
    5: 0, 6: 1, 7: 2, 8: 3,
    10: 1, 13: 50.0, 14: 50.0, 15: 50.0, 16: 0.0,
    20: 0, 30: 0, 40: 0, # Disable delay/reverb for clean dry loudness
    49: 1, 50: 0, 51: -0.5, 54: 1, 55: 54.0, 56: 44.0, 57: 62.0, 58: 64.0
}

# 1. RAT default
rat_def = dict(base)
rat_def[11] = 0; rat_def[26] = 8.0; rat_def[27] = 3.5; rat_def[28] = 6.7

# 2. DS-1 default
ds1_def = dict(base)
ds1_def[11] = 1; ds1_def[29] = 9.0; ds1_def[37] = 6.5; ds1_def[38] = 8.9

# 3. Metal Zone default
mt2_def = dict(base)
mt2_def[11] = 2; mt2_def[39] = 7.5; mt2_def[46] = 6.5; mt2_def[47] = 4.5; mt2_def[48] = 6.0; mt2_def[59] = 4.5; mt2_def[61] = 7.5

# 4. HM-2 default
hm2_def = dict(base)
hm2_def[11] = 3; hm2_def[62] = 10.0; hm2_def[63] = 10.0; hm2_def[64] = 10.0; hm2_def[9] = 4.4

test_cases = [
    ("Default RAT", rat_def),
    ("Default DS-1", ds1_def),
    ("Default Metal Zone", mt2_def),
    ("Default HM-2", hm2_def),
    ("Preset 0 (Tight Rhythm, MT-2)", dict(presets[0])),
    ("Preset 1 (Cold Lead, RAT)", dict(presets[1])),
    ("Preset 2 (Doom Wall, HM-2)", dict(presets[2])),
    ("Preset 3 (Raw 4-Track, DS-1)", dict(presets[3])),
    ("Preset 4 (Swedish Chainsaw, HM-2)", dict(presets[4])),
    ("Preset 6 (Ambient Swell, Clean)", dict(presets[6])),
]

# Ensure no time-based FX bleed
for name, d in test_cases:
    d[20] = 0; d[30] = 0; d[40] = 0; d[49] = 1; d[50] = 0

def make_track(name, s_dict, pos):
    s_line = " ".join(str(s_dict.get(i, "-")) for i in range(1, 65))
    return f"""  <TRACK
    NAME "{name}"
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
      POSITION {pos}
      LENGTH 0.45
      FADEIN 0 0.0 0.0 1 0 0 0
      FADEOUT 0 0.0 0.0 1 0 0 0
      <SOURCE WAVE
        FILE "{di_path}"
      >
    >
  >"""

# Render 1: IIR mode (slider52 = 0)
tracks_iir = []
for i, (name, d) in enumerate(test_cases):
    cfg = dict(d); cfg[52] = 0
    tracks_iir.append(make_track(f"{name}_IIR", cfg, round(i * 0.5, 2)))

out_iir_p = f"{RENDER_DIR}/out_cmp_iir.wav"
total_len = round(len(test_cases) * 0.5 + 0.2, 2)
rpp_iir = f"""<REAPER_PROJECT 0.1 "7.0" 1700000000
  SAMPLERATE 48000 0 0
  PANLAW 1.0
  RENDER_FILE "{out_iir_p}"
  RENDER_FMT 0 2 48000
  RENDER_1X 0
  RENDER_RANGE 1 0.0 {total_len} 0 1000
{chr(10).join(tracks_iir)}
>"""
with open(f"{RENDER_DIR}/test_cmp_iir.rpp", "w") as f:
    f.write(rpp_iir)

# Render 2: WAV IR mode (slider52 = 1, slider53 = 0)
tracks_wav = []
for i, (name, d) in enumerate(test_cases):
    cfg = dict(d); cfg[52] = 1; cfg[53] = 0
    tracks_wav.append(make_track(f"{name}_WAV", cfg, round(i * 0.5, 2)))

out_wav_p = f"{RENDER_DIR}/out_cmp_wav.wav"
rpp_wav = f"""<REAPER_PROJECT 0.1 "7.0" 1700000000
  SAMPLERATE 48000 0 0
  PANLAW 1.0
  RENDER_FILE "{out_wav_p}"
  RENDER_FMT 0 2 48000
  RENDER_1X 0
  RENDER_RANGE 1 0.0 {total_len} 0 1000
{chr(10).join(tracks_wav)}
>"""
with open(f"{RENDER_DIR}/test_cmp_wav.rpp", "w") as f:
    f.write(rpp_wav)

print("Rendering IIR Cab test cases in REAPER...")
subprocess.run(["D:/Reaper/reaper.exe", "-newinst", "-nosplash", "-renderproject", f"{RENDER_DIR}/test_cmp_iir.rpp"], check=True)

print("Rendering WAV IR (Slot 0) test cases in REAPER...")
subprocess.run(["D:/Reaper/reaper.exe", "-newinst", "-nosplash", "-renderproject", f"{RENDER_DIR}/test_cmp_wav.rpp"], check=True)

# ITU-R BS.1770 K-weighting filters for 48 kHz
def bs1770_kweight(x):
    b_hs = [1.53512485958697, -2.69169618940638, 1.19839281085285]
    a_hs = [1.0, -1.69065929318241, 0.73248077421585]
    b_hp = [1.0, -2.0, 1.0]
    a_hp = [1.0, -1.99004745483398, 0.99007225035621]
    
    y = np.zeros_like(x)
    s1 = s2 = 0.0
    for i in range(len(x)):
        v = x[i]
        out = b_hs[0] * v + s1
        s1 = b_hs[1] * v - a_hs[1] * out + s2
        s2 = b_hs[2] * v - a_hs[2] * out
        y[i] = out
    y2 = np.zeros_like(y)
    s1 = s2 = 0.0
    for i in range(len(y)):
        v = y[i]
        out = b_hp[0] * v + s1
        s1 = b_hp[1] * v - a_hp[1] * out + s2
        s2 = b_hp[2] * v - a_hp[2] * out
        y2[i] = out
    return y2

def calc_lufs(sig):
    k = bs1770_kweight(sig)
    ms = np.mean(k ** 2)
    return -0.691 + 10.0 * math.log10(max(1e-12, ms))

def read_wav(path):
    with wave.open(path, "rb") as wf:
        raw = wf.readframes(wf.getnframes())
        return np.array([int.from_bytes(raw[i*6:i*6+3], "little", signed=True) / 8388608.0 for i in range(wf.getnframes())])

s_iir = read_wav(out_iir_p)
s_wav = read_wav(out_wav_p)

seg_len = int(0.40 * sr)

print("\n" + "="*95)
print(f"{'Test Case':<32} | {'IIR LUFS':<9} | {'IIR Peak':<9} | {'WAV LUFS':<9} | {'WAV Peak':<9} | {'Delta LUFS':<10} | {'Limiter?':<8}")
print("="*95)

rows = []
for i, (name, _) in enumerate(test_cases):
    st = int((i * 0.5 + 0.03) * sr)
    seg_i = s_iir[st : st + seg_len]
    seg_w = s_wav[st : st + seg_len]
    
    lufs_i = calc_lufs(seg_i)
    pk_i = 20.0 * math.log10(max(abs(x) for x in seg_i))
    
    lufs_w = calc_lufs(seg_w)
    pk_w = 20.0 * math.log10(max(abs(x) for x in seg_w))
    
    delta_lufs = lufs_w - lufs_i
    knee_flag = "EXCEEDED" if pk_w > -6.0 else "clean"
    
    print(f"{name:<32} | {lufs_i:6.2f} LUFS | {pk_i:6.2f} dBFS | {lufs_w:6.2f} LUFS | {pk_w:6.2f} dBFS | {delta_lufs:+6.2f} dB    | {knee_flag}")
    rows.append((name, lufs_i, pk_i, lufs_w, pk_w, delta_lufs, knee_flag))
print("="*95)
