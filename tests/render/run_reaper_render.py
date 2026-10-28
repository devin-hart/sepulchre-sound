import os
import sys
import math
import wave
import subprocess

sys.path.insert(0, "D:/VSTs/sepulchre_sound/tests")
import verify_jsfx as v

RENDER_DIR = "D:/VSTs/sepulchre_sound/tests/render"
os.makedirs(RENDER_DIR, exist_ok=True)

presets = v.parse_global_presets(open("D:/VSTs/sepulchre_sound/sepulchre_presets.jsfx-inc").read())
sr = 48000
di_path = f"{RENDER_DIR}/di_input.wav"
sine_path = f"{RENDER_DIR}/sine_2578.wav"
out1_path = f"{RENDER_DIR}/out1.wav"
out2_path = f"{RENDER_DIR}/out2.wav"
rpp_path = f"{RENDER_DIR}/test.rpp"

# Write 0.45s DI input WAV (24-bit PCM)
n_di = int(0.45 * sr)
with wave.open(di_path, "wb") as wf:
    wf.setnchannels(2); wf.setsampwidth(3); wf.setframerate(sr)
    frames = bytearray()
    for i in range(n_di):
        t = i / sr
        env = math.exp(-t * 4.5) * (1.0 - math.exp(-t * 250.0))
        val = 0.25 * env * (
            0.6 * math.sin(2 * math.pi * 82.41 * t)
            + 0.4 * math.sin(2 * math.pi * 164.82 * t)
            + 0.3 * math.sin(2 * math.pi * 247.23 * t)
        )
        s = max(-8388607, min(8388607, int(val * 8388607)))
        b = s.to_bytes(3, "little", signed=True)
        frames += b + b
    wf.writeframes(frames)

# Write 0.45s bin-centered 2578.125 Hz sine WAV for pre-cab aliasing test
f0 = 55.0 * sr / 1024.0
with wave.open(sine_path, "wb") as wf:
    wf.setnchannels(2); wf.setsampwidth(3); wf.setframerate(sr)
    frames = bytearray()
    for i in range(n_di):
        val = 0.25 * math.sin(2.0 * math.pi * f0 * (i / sr))
        s = max(-8388607, min(8388607, int(val * 8388607)))
        b = s.to_bytes(3, "little", signed=True)
        frames += b + b
    wf.writeframes(frames)

def make_track(name, sliders_dict, wav_file, pos):
    s_line = " ".join(str(sliders_dict.get(i, "-")) for i in range(1, 65))
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
        FILE "{wav_file}"
      >
    >
  >"""

test_preset_indices = [0, 1, 2, 3, 4, 6]
tracks_xml = []
for slot, idx in enumerate(test_preset_indices):
    p = dict(presets[idx])
    # Disable time-based FX tail bleed across sequential slots while keeping Gate + Dist + Amp + Cab active
    p[20] = 0; p[30] = 0; p[40] = 0
    tracks_xml.append(make_track(f"Preset_{idx}", p, di_path, round(slot * 0.5, 2)))

# Track: Pre-cabinet 8x oversampling sine aliasing test for Metal Zone
p_alias_mt2 = dict(presets[0])
p_alias_mt2[4] = 0; p_alias_mt2[16] = 0; p_alias_mt2[20] = 0; p_alias_mt2[30] = 0; p_alias_mt2[40] = 0
p_alias_mt2[49] = 0; p_alias_mt2[51] = 0.0; p_alias_mt2[52] = 0; p_alias_mt2[54] = 0; p_alias_mt2[58] = 50.0
tracks_xml.append(make_track("PreCab_Alias_MT2", p_alias_mt2, sine_path, 3.0))

# Track: Pre-cabinet 8x oversampling sine aliasing test for HM-2 (all on 10)
p_alias_hm2 = dict(presets[4])
p_alias_hm2[4] = 0; p_alias_hm2[16] = 0; p_alias_hm2[20] = 0; p_alias_hm2[30] = 0; p_alias_hm2[40] = 0
p_alias_hm2[49] = 0; p_alias_hm2[51] = 0.0; p_alias_hm2[52] = 0; p_alias_hm2[54] = 0; p_alias_hm2[58] = 50.0
tracks_xml.append(make_track("PreCab_Alias_HM2", p_alias_hm2, sine_path, 3.5))

for out_p in [out1_path, out2_path]:
    if os.path.exists(out_p):
        os.remove(out_p)
    rpp = f"""<REAPER_PROJECT 0.1 "7.0" 1700000000
  SAMPLERATE 48000 0 0
  PANLAW 1.0
  RENDER_FILE "{out_p}"
  RENDER_FMT 0 2 48000
  RENDER_1X 0
  RENDER_RANGE 1 0.0 4.0 0 1000
{chr(10).join(tracks_xml)}
>
"""
    with open(rpp_path, "w") as f:
        f.write(rpp)
    subprocess.run(["D:/Reaper/reaper.exe", "-newinst", "-nosplash", "-renderproject", rpp_path], check=True)

def read_wav24(path):
    with wave.open(path, "rb") as wf:
        raw = wf.readframes(wf.getnframes())
        return [int.from_bytes(raw[i*6:i*6+3], "little", signed=True) / 8388608.0 for i in range(wf.getnframes())]

w1 = read_wav24(out1_path)
w2 = read_wav24(out2_path)
null_diff = max(abs(a - b) for a, b in zip(w1, w2))
print(f"Render-twice-and-null max difference: {null_diff:.2e}")
assert null_diff == 0.0, f"Render-twice-and-null failed: max_diff={null_diff}"

for slot, idx in enumerate(test_preset_indices):
    seg = w1[int((slot * 0.5 + 0.03) * sr) : int((slot * 0.5 + 0.44) * sr)]
    pk = max(abs(x) for x in seg)
    pk_db = 20 * math.log10(pk)
    dc = abs(sum(seg) / len(seg))
    print(f"LIVE REAPER Preset {idx} -> Peak: {pk_db:+.2f} dBFS | DC: {dc:.5f}")
    assert -10.0 <= pk_db <= -8.0, f"Live REAPER Preset {idx} peak {pk_db:.2f} outside [-10, -8] dBFS"
    assert dc < 0.004, f"Live REAPER Preset {idx} DC {dc:.5f} >= 0.004"

def measure_aliasing(start_time, label):
    start_s = int(start_time * sr) + 4096
    n = 1024
    seg_a = w1[start_s : start_s + n]
    hb = {55 * k for k in range(1, (n // 2) // 55 + 1)}
    bin_8k = int(8000.0 * n / sr)
    harm_all = alias_all = harm_8k = alias_8k = 0.0
    for k in range(1, n // 2):
        re_s = sum(seg_a[i] * math.cos(2.0 * math.pi * k * i / n) for i in range(n))
        im_s = sum(seg_a[i] * math.sin(2.0 * math.pi * k * i / n) for i in range(n))
        pwr = (re_s * re_s + im_s * im_s) / (n * n)
        if k in hb:
            harm_all += pwr
            if k <= bin_8k: harm_8k += pwr
        else:
            alias_all += pwr
            if k <= bin_8k: alias_8k += pwr
    all_db = 10 * math.log10(alias_all / harm_all)
    inband_db = 10 * math.log10(alias_8k / harm_8k)
    print(f"LIVE REAPER Pre-Cab Alias ({label}) -> All bins: {all_db:+.2f} dB | 20Hz-8kHz: {inband_db:+.2f} dB")
    return all_db, inband_db

mt2_all, mt2_in = measure_aliasing(3.0, "Metal Zone")
hm2_all, hm2_in = measure_aliasing(3.5, "HM-2 all 10")
assert mt2_in <= -40.0, f"Metal Zone aliasing {mt2_in:.2f} dB exceeded -40 dB!"
assert hm2_in <= -34.0, f"HM-2 aliasing {hm2_in:.2f} dB exceeded -34 dB!"
print("ALL LIVE REAPER CLI RENDER CHECKS PASSED.")
