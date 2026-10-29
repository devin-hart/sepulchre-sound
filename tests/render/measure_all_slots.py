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
base = dict(presets[0]) # Preset 0: Tight Rhythm (RAT, Amp on, Cab on)
# Disable delay and reverb bleed
base[20] = 0; base[30] = 0; base[40] = 0

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
# Slot 0..10 in our test: Track 0 = IIR Cab Profile 0, Tracks 1..10 = WAV IR Slots 0..9
track_names = ["IIR_Cab0"] + [f"WAV_IR_Slot{i}" for i in range(10)]

p_iir = dict(base)
p_iir[49] = 1; p_iir[50] = 0; p_iir[52] = 0
tracks_xml.append(make_track("IIR_Cab0", p_iir, 0.0))

for slot in range(10):
    p_wav = dict(base)
    p_wav[49] = 1; p_wav[52] = 1; p_wav[53] = slot
    tracks_xml.append(make_track(f"WAV_IR_Slot{slot}", p_wav, round((slot + 1) * 0.5, 2)))

total_len = round(11 * 0.5 + 0.5, 2)
out_p = f"{RENDER_DIR}/out_slots.wav"
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
with open(f"{RENDER_DIR}/test_slots.rpp", "w") as f:
    f.write(rpp)

if os.path.exists(out_p):
    os.remove(out_p)

print("Rendering all 10 IR slots + IIR cab reference in REAPER...")
subprocess.run(["D:/Reaper/reaper.exe", "-newinst", "-nosplash", "-renderproject", f"{RENDER_DIR}/test_slots.rpp"], check=True)

# Read rendered 24-bit audio
with wave.open(out_p, "rb") as wf:
    raw = wf.readframes(wf.getnframes())
    n = wf.getnframes()
    samples_l = np.array([int.from_bytes(raw[i*6:i*6+3], "little", signed=True) / 8388608.0 for i in range(n)])
    samples_r = np.array([int.from_bytes(raw[i*6+3:i*6+6], "little", signed=True) / 8388608.0 for i in range(n)])

# ITU-R BS.1770 K-weighting filters for 48 kHz
def bs1770_kweight(x):
    # Stage 1: High shelf (+4 dB @ 1682 Hz)
    # Exact ITU-R BS.1770-4 coefficients for 48 kHz:
    b_hs = [1.53512485958697, -2.69169618940638, 1.19839281085285]
    a_hs = [1.0, -1.69065929318241, 0.73248077421585]
    # Stage 2: High pass (38 Hz RLB)
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

def calc_lufs(l, r):
    kl = bs1770_kweight(l)
    kr = bs1770_kweight(r)
    ms = (np.mean(kl ** 2) + np.mean(kr ** 2)) / 2.0
    return -0.691 + 10.0 * math.log10(max(1e-12, ms))

# 1/3-octave band center frequencies
bands = [100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000]

def calc_octave_bands(sig, sr=48000):
    n = len(sig)
    fft_mag = np.abs(np.fft.rfft(sig * np.hanning(n))) ** 2
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    band_db = []
    ratio = 2.0 ** (1.0 / 6.0)
    for fc in bands:
        f_lo = fc / ratio
        f_hi = fc * ratio
        mask = (freqs >= f_lo) & (freqs < f_hi)
        pwr = np.sum(fft_mag[mask]) if np.any(mask) else 1e-12
        band_db.append(10.0 * math.log10(max(1e-12, pwr)))
    return np.array(band_db)

seg_len = int(0.40 * sr)
slot_lufs = []
slot_bands = []

slot_names = [
    "01 BlackWizard Center",
    "02 BlackWizard Edge",
    "03 Destroyer Center",
    "04 Destroyer Edge",
    "05 LordOfGoats Center",
    "06 LordOfGoats Edge",
    "07 MysteriousSatan Center",
    "08 Swordman Center",
    "09 HeadKrush Center",
    "10 PlagueBearer Center"
]

# IIR Cab ref
st0 = int((0.0 * 0.5 + 0.03) * sr)
ref_lufs = calc_lufs(samples_l[st0:st0+seg_len], samples_r[st0:st0+seg_len])
ref_bands = calc_octave_bands(samples_l[st0:st0+seg_len])
print(f"Reference IIR Cab 0 -> Integrated LUFS: {ref_lufs:.2f} LUFS")

print("\n--- PER-SLOT MEASUREMENTS (vs IIR Cab 0) ---")
for slot in range(10):
    st = int(((slot + 1) * 0.5 + 0.03) * sr)
    seg_l = samples_l[st : st + seg_len]
    seg_r = samples_r[st : st + seg_len]
    lufs = calc_lufs(seg_l, seg_r)
    b_db = calc_octave_bands(seg_l)
    diff_lufs = lufs - ref_lufs
    slot_lufs.append(lufs)
    slot_bands.append(b_db)
    print(f"Slot {slot:2d} ({slot_names[slot]}): {lufs:.2f} LUFS | delta vs IIR: {diff_lufs:+.2f} dB")

# Pairwise max band difference matrix
print("\n--- PAIRWISE MAX 1/3-OCTAVE BAND DIFFERENCE (100 Hz - 8 kHz) ---")
pairwise_min_diff = 999.0
pairwise_max_diff = 0.0
for i in range(10):
    for j in range(i + 1, 10):
        diff = np.max(np.abs(slot_bands[i] - slot_bands[j]))
        pairwise_min_diff = min(pairwise_min_diff, diff)
        pairwise_max_diff = max(pairwise_max_diff, diff)

print(f"Min pairwise max band difference between any two slots: {pairwise_min_diff:.2f} dB")
print(f"Max pairwise max band difference between any two slots: {pairwise_max_diff:.2f} dB")

# Also print slot-by-slot table against slot 0
print("\n--- SPECTRAL DIFFERENCE VS SLOT 0 (BlackWizard C) ---")
for slot in range(1, 10):
    max_d = np.max(np.abs(slot_bands[slot] - slot_bands[0]))
    mean_d = np.mean(np.abs(slot_bands[slot] - slot_bands[0]))
    print(f"Slot {slot} ({slot_names[slot]}): Max Band Diff = {max_d:.2f} dB | Mean Band Diff = {mean_d:.2f} dB")
