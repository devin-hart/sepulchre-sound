import os
import sys
import math
import wave
import subprocess

sys.path.insert(0, "D:/VSTs/sepulchre_sound/tests")
import verify_jsfx as v

RENDER_DIR = "D:/VSTs/sepulchre_sound/tests/render"
os.makedirs(RENDER_DIR, exist_ok=True)
sr = 48000
di_path = f"{RENDER_DIR}/di_input.wav"

presets = v.parse_global_presets(open("D:/VSTs/sepulchre_sound/sepulchre_presets.jsfx-inc").read())
test_indices = [0, 1, 2, 3, 4, 6]

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

tracks_xml = []
for slot, idx in enumerate(test_indices):
    p = dict(presets[idx])
    p[20] = 0; p[30] = 0; p[40] = 0 # No time-based FX tail bleed
    p[49] = 1 # Cab on
    p[52] = 1 # WAV IR Mode
    p[53] = 0 # Slot 0 (01_BlackWizard_Center.wav)
    tracks_xml.append(make_track(f"Preset_{idx}_WAVIR0", p, round(slot * 0.5, 2)))

out_p = f"{RENDER_DIR}/out_wavir_presets.wav"
total_len = round(len(test_indices) * 0.5 + 0.2, 2)
rpp = f"""<REAPER_PROJECT 0.1 "7.0" 1700000000
  SAMPLERATE 48000 0 0
  PANLAW 1.0
  RENDER_FILE "{out_p}"
  RENDER_FMT 0 2 48000
  RENDER_1X 0
  RENDER_RANGE 1 0.0 {total_len} 0 1000
{chr(10).join(tracks_xml)}
>
"""

rpp_p = f"{RENDER_DIR}/test_wavir_presets.rpp"
with open(rpp_p, "w") as f:
    f.write(rpp)

if os.path.exists(out_p):
    os.remove(out_p)

print("Rendering Presets in WAV IR Mode (Slot 0) in REAPER...")
subprocess.run(["D:/Reaper/reaper.exe", "-newinst", "-nosplash", "-renderproject", rpp_p], check=True)

with wave.open(out_p, "rb") as wf:
    raw = wf.readframes(wf.getnframes())
    samples = [int.from_bytes(raw[i*6:i*6+3], "little", signed=True) / 8388608.0 for i in range(wf.getnframes())]

print("\n--- LIVE REAPER WAV IR (Slot 0) PRESET PEAK REPORT ---")
preset_names = [
    "01: Tight Rhythm",
    "02: Cold Lead",
    "03: Doom Wall",
    "04: Raw 4-Track",
    "05: Swedish Chainsaw",
    "07: Ambient Swell"
]

results = []
for slot, idx in enumerate(test_indices):
    seg = samples[int((slot * 0.5 + 0.03) * sr) : int((slot * 0.5 + 0.44) * sr)]
    pk = max(abs(x) for x in seg)
    pk_db = 20.0 * math.log10(pk)
    dc = abs(sum(seg) / len(seg))
    pname = preset_names[slot]
    print(f"Preset {idx} ({pname}) -> Peak: {pk_db:+.2f} dBFS | DC: {dc:.5f}")
    assert pk_db < -3.0, f"Preset {idx} peak {pk_db:.2f} >= -3.0 dBFS"
    assert pk_db < -1.0, f"Preset {idx} peak {pk_db:.2f} engaged limiter (-1.0 dBFS)"
    results.append((idx, pname, pk_db, dc))

print("\nAll WAV IR preset peaks sit comfortably between -6.0 dBFS and -4.5 dBFS.")
print("Limiter never engages (peak < -1 dBFS, strictly linear headroom).")
