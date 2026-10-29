import os
import sys
import wave
import subprocess
import math

RENDER_DIR = "D:/VSTs/sepulchre_sound/tests/render"
sr = 48000

def make_track_xml(name, s_dict, wav_file, pos=0.0):
    s_line = " ".join(str(s_dict.get(i, "-")) for i in range(1, 65))
    return f"""  <TRACK
    NAME "{name}"
    VOLPAN 1 0 -1 -1 1
    MUTESOLO 0 0 0
    NCHAN 2
    FX 1
    MAINSEND 1 0
    <FXCHAIN
      BYPASS 0 0 0
      <JS sepulchre_sound/sepulchre_sound.jsfx ""
        {s_line}
      >
      WAK 0 0
    >
    <ITEM
      POSITION {pos}
      LENGTH 0.25
      <SOURCE WAVE
        FILE "{wav_file}"
      >
    >
  >"""

def read_wav24(path):
    with wave.open(path, "rb") as wf:
        raw = wf.readframes(wf.getnframes())
        return [int.from_bytes(raw[i*6:i*6+3], "little", signed=True) / 8388608.0 for i in range(wf.getnframes())]

# 1. Impulse test
base_clean = {
    1: 0.0, 2: 40.0, 4: 0, 10: 0, 16: 0, 20: 0, 30: 0, 40: 0,
    49: 1, 51: 0.0, 52: 1, 53: 0, 54: 0, 58: 50.0
}
impulse_track = make_track_xml("Impulse_Slot0", base_clean, f"{RENDER_DIR}/impulse.wav")
rpp_imp = f"""<REAPER_PROJECT 0.1 "7.0" 1700000000
  SAMPLERATE 48000 0 0
  RENDER_FILE "{RENDER_DIR}/out_impulse.wav"
  RENDER_FMT 0 2 48000
  RENDER_1X 0
  RENDER_RANGE 1 0.0 0.25 0 1000
{impulse_track}
>"""

with open(f"{RENDER_DIR}/test_impulse.rpp", "w") as f:
    f.write(rpp_imp)

if os.path.exists(f"{RENDER_DIR}/out_impulse.wav"):
    os.remove(f"{RENDER_DIR}/out_impulse.wav")

subprocess.run(["D:/Reaper/reaper.exe", "-newinst", "-nosplash", "-renderproject", f"{RENDER_DIR}/test_impulse.rpp"], check=True)

samples = read_wav24(f"{RENDER_DIR}/out_impulse.wav")
pre_128_max = max(abs(s) for s in samples[:128])
post_128_peak = max(abs(s) for s in samples[128:1024])
print(f"Impulse test -> Max pre-128 samples: {pre_128_max:.3e}")
print(f"Impulse test -> Peak post-128 samples: {post_128_peak:.4f}")
print(f"Sample 126: {samples[126]:.6e} | Sample 127: {samples[127]:.6e}")
print(f"Sample 128: {samples[128]:.6f} | Sample 129: {samples[129]:.6f} | Sample 130: {samples[130]:.6f}")

# 2. Continuity tests (100 Hz and 2578 Hz)
for f_hz in [100, 2578]:
    sine_tr = make_track_xml(f"Sine_{f_hz}", base_clean, f"{RENDER_DIR}/sine_{f_hz}.wav")
    rpp_sine = f"""<REAPER_PROJECT 0.1 "7.0" 1700000000
  SAMPLERATE 48000 0 0
  RENDER_FILE "{RENDER_DIR}/out_sine_{f_hz}.wav"
  RENDER_FMT 0 2 48000
  RENDER_1X 0
  RENDER_RANGE 1 0.0 0.25 0 1000
{sine_tr}
>"""
    with open(f"{RENDER_DIR}/test_sine.rpp", "w") as f:
        f.write(rpp_sine)
    if os.path.exists(f"{RENDER_DIR}/out_sine_{f_hz}.wav"):
        os.remove(f"{RENDER_DIR}/out_sine_{f_hz}.wav")
    subprocess.run(["D:/Reaper/reaper.exe", "-newinst", "-nosplash", "-renderproject", f"{RENDER_DIR}/test_sine.rpp"], check=True)
    sine_s = read_wav24(f"{RENDER_DIR}/out_sine_{f_hz}.wav")
    # Check 128-sample block boundaries (e.g. sample 127->128, 255->256, 383->384, etc.)
    boundary_jumps = []
    normal_jumps = []
    for i in range(512, len(sine_s) - 1):
        diff = abs(sine_s[i+1] - sine_s[i])
        if (i + 1) % 128 == 0:
            boundary_jumps.append(diff)
        else:
            normal_jumps.append(diff)
    max_b = max(boundary_jumps)
    max_n = max(normal_jumps)
    print(f"Continuity {f_hz} Hz -> Max jump at 128-spl boundary: {max_b:.6f} vs Max normal jump: {max_n:.6f}")
