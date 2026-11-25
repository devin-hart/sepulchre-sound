import os
import sys
import wave
import math
import re
import subprocess
import numpy as np

# Repository and Path Resolution
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RENDER_DIR = os.path.join(REPO_DIR, "tests", "render")
REAPER_EXE = os.environ.get("REAPER_EXE", "D:/Reaper/reaper.exe" if sys.platform == "win32" else "/usr/bin/reaper")
APPDATA_DIR = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming") if sys.platform == "win32" else os.path.expanduser("~/.config"))
IR_DIR = os.environ.get("SEPULCHRE_IR_DIR", os.path.join(APPDATA_DIR, "REAPER", "Data", "sepulchre_irs"))
DI_DIR = os.environ.get("SEPULCHRE_DI_DIR", "")

def get_declared_sliders(jsfx_path=None):
    if jsfx_path is None:
        jsfx_path = os.path.join(REPO_DIR, "sepulchre_sound.jsfx")
    with open(jsfx_path, "r", encoding="utf-8") as f:
        src = f.read()
    return set(int(m) for m in re.findall(r"^slider([0-9]+):", src, re.MULTILINE))

VALID_SLIDERS = get_declared_sliders()

def load_slider_defaults(jsfx_path=None):
    if jsfx_path is None:
        jsfx_path = os.path.join(REPO_DIR, "sepulchre_sound.jsfx")
    with open(jsfx_path, "r", encoding="utf-8") as f:
        src = f.read()
    out = {}
    for m in re.finditer(r"^slider(\d+):([^<\r\n]+)", src, re.MULTILINE):
        sid = int(m.group(1))
        val = m.group(2).strip()
        if val.startswith("/"):
            parts = val.split(":")
            out[sid] = parts[1] if len(parts) > 1 else "none"
        else:
            fval = float(val)
            out[sid] = int(fval) if fval.is_integer() and "." not in val else fval
    return out


def load_global_preset_names(presets_path=None):
    if presets_path is None:
        presets_path = os.path.join(REPO_DIR, "sepulchre_presets.jsfx-inc")
    with open(presets_path, "r", encoding="utf-8") as f:
        src = f.read()
    m_fn = re.search(r"function get_global_preset_name\([^)]*\)\s*\((.*?)\n\);", src, re.S)
    names = re.findall(r'"([^"]+)"', m_fn.group(1)) if m_fn else []
    ped_map = {0: "RAT", 1: "DS-1", 2: "MT-2", 3: "HM-2"}
    out = []
    chunks = re.split(r"idx == (\d+) \? \(", src)
    ped_by_idx = {}
    for k in range(1, len(chunks), 2):
        idx = int(chunks[k]); body = chunks[k + 1]
        m10 = re.search(r"slider10\s*=\s*([0-9.]+)", body)
        m11 = re.search(r"slider11\s*=\s*([0-9.]+)", body)
        if m10 and float(m10.group(1)) < 0.5:
            ped_by_idx[idx] = "Clean"
        elif m11:
            ped_by_idx[idx] = ped_map.get(int(float(m11.group(1)) + 0.5), "?")
    for i, nm in enumerate(names):
        out.append((i, nm.title(), ped_by_idx.get(i, "?")))
    return out


# Round 76 (R4): derived directly from sepulchre_sound.jsfx and sepulchre_presets.jsfx-inc
FRESH_INSERT_DEFAULTS = load_slider_defaults()

# Base slider defaults for clean/bypass conditions
BASE_DEFAULTS = {
    1: 0.0, 2: 40.0, 3: -52.0, 4: 0,
    10: 1,
    20: 0, 40: 0,
    49: 0, 51: 0.0, 53: "01_BlackWizard_Center.wav", 54: 0, 58: 50.0,
    60: 0,
    65: 0, 66: 0.0, 67: 0.0, 68: 0.0, 69: 0.0, 70: 0.0, 71: 0.0, 72: 0.0, 73: 0.0, 75: 0,
    76: 1
}

GLOBAL_PRESET_NAMES = load_global_preset_names()

# Pedal slider definitions at factory defaults
PEDAL_DEFAULTS = {
    "RAT": {11: 0, 26: 8.0, 27: 3.5, 28: 6.7},
    "DS-1": {11: 1, 29: 9.0, 37: 6.5, 38: 8.9},
    "Metal Zone": {11: 2, 39: 7.5, 46: 6.5, 47: 4.5, 48: 6.0, 59: 4.5, 61: 7.5},
    "HM-2": {11: 3, 62: 10.0, 63: 10.0, 64: 10.0, 9: 4.4},
}

def make_track(name, s_dict, wav_file, pos=0.0, length=0.45, pan=0.0, fx_path="sepulchre_sound/sepulchre_sound.jsfx"):
    invalid = [k for k in s_dict.keys() if k not in VALID_SLIDERS]
    if invalid:
        raise ValueError(f"Stale/undeclared slider ID(s) passed to make_track: {invalid}")
    # Support up to slider 78 (Round 42 additions: 76 EQ Pos, 77 CE-2 Rate, 78 CE-2 Depth)
    max_slider = max(78, max(s_dict.keys()) if s_dict else 78)
    tokens = [str(s_dict.get(i, "-")) for i in range(1, 65)]
    if max_slider >= 65:
        tokens.append("-")  # Token 65: REAPER internal preset/state placeholder
        for i in range(65, max_slider + 1):
            tokens.append(str(s_dict.get(i, "-")))
    s_line = " ".join(tokens)
    clean_wav = wav_file.replace("\\", "/")
    return f"""  <TRACK
    NAME "{name}"
    VOLPAN 1 {pan} -1 -1 1
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
      <JS {fx_path} ""
        {s_line}
      >
      WAK 0 0
    >
    <ITEM
      POSITION {pos}
      LENGTH {length}
      FADEIN 0 0.0 0.0 1 0 0 0
      FADEOUT 0 0.0 0.0 1 0 0 0
      <SOURCE WAVE
        FILE "{clean_wav}"
      >
    >
  >"""

def build_rpp(tracks_xml, render_file, total_len, sr=48000, panlaw=1.0):
    clean_render = render_file.replace("\\", "/")
    if isinstance(tracks_xml, (list, tuple)):
        tracks_block = "\n".join(tracks_xml)
    else:
        tracks_block = tracks_xml
    return f"""<REAPER_PROJECT 0.1 "7.0" 1700000000
  SAMPLERATE {sr} 0 0
  PANLAW {panlaw}
  RENDER_FILE "{clean_render}"
  RENDER_FMT 0 2 {sr}
  RENDER_1X 0
  RENDER_RANGE 1 0.0 {total_len} 0 1000
{tracks_block}
>
"""

def run_reaper(rpp_path, reaper_exe=None):
    exe = reaper_exe or REAPER_EXE
    if not os.path.exists(exe):
        raise FileNotFoundError(f"REAPER executable not found at {exe}")
    subprocess.run([exe, "-newinst", "-nosplash", "-renderproject", rpp_path], check=True)

def read_wav24(path, channel=0):
    with wave.open(path, "rb") as wf:
        n_ch = wf.getnchannels()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
        step = n_ch * 3
        offset = min(channel, n_ch - 1) * 3
        return np.array([
            int.from_bytes(raw[i * step + offset : i * step + offset + 3], "little", signed=True) / 8388608.0
            for i in range(n_frames)
        ], dtype=np.float64)

def write_wav24(path, data, sr=48000, nchannels=2):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(nchannels)
        wf.setsampwidth(3)
        wf.setframerate(sr)
        frames = bytearray()
        for s in data:
            val = max(-8388607, min(8388607, int(s * 8388607.0)))
            b = val.to_bytes(3, "little", signed=True)
            for _ in range(nchannels):
                frames += b
        wf.writeframes(frames)

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

def calc_peak_db(sig):
    pk = np.max(np.abs(sig))
    return 20.0 * math.log10(max(1e-12, pk))


def wav_duration(path):
    with wave.open(path, "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def find_external_di_pairs(di_dir=None):
    """Discover optional user/third-party DI take pairs in SEPULCHRE_DI_DIR (*_L/*_R or *_1/*_2.wav).
    Returns a list of (stem, path_l, path_r); returns [] cleanly if the env var / directory is unset."""
    d = di_dir if di_dir is not None else os.environ.get("SEPULCHRE_DI_DIR", DI_DIR)
    if not d or not os.path.isdir(d):
        return []
    wavs = sorted(f for f in os.listdir(d) if f.lower().endswith(".wav"))
    wav_set = set(wavs)
    pairs = []
    for f in wavs:
        for suf_l, suf_r in (("_L.wav", "_R.wav"), ("_l.wav", "_r.wav"), ("_1.wav", "_2.wav")):
            if f.endswith(suf_l):
                partner = f[:-len(suf_l)] + suf_r
                if partner in wav_set:
                    pairs.append((f[:-len(suf_l)], os.path.join(d, f), os.path.join(d, partner)))
    return pairs


def render_double_tracked_pair(name, s_dict, wav_l, wav_r, out_wav, length=None, sr=48000,
                               fx_path="sepulchre_sound/sepulchre_sound.jsfx", rpp_path=None):
    """Render two guitar takes through identical settings (or a (s_left, s_right) tuple) panned hard L/R."""
    s_l, s_r = s_dict if isinstance(s_dict, tuple) else (s_dict, s_dict)
    dur = length if length is not None else min(wav_duration(wav_l), wav_duration(wav_r))
    trk_l = make_track(f"{name}_L", s_l, wav_l, pos=0.0, length=dur, pan=-1.0, fx_path=fx_path)
    trk_r = make_track(f"{name}_R", s_r, wav_r, pos=0.0, length=dur, pan=1.0, fx_path=fx_path)
    rpp = rpp_path or (out_wav + ".rpp")
    with open(rpp, "w", encoding="utf-8") as f:
        f.write(build_rpp([trk_l, trk_r], out_wav, dur + 0.15, sr=sr))
    run_reaper(rpp)
    return read_wav24(out_wav, 0), read_wav24(out_wav, 1)
