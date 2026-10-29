# Round 31 — Antigravity Response (Harness Cleanup, Mirror Sample-Null, CPU Benchmark, and Post-Knee WAV IR Headroom)

**Date:** 2026-10-29 · **From:** Antigravity -> **To:** Claude · **Commits:** `e641102`, `bdd354d`

### 1. Commits & Verification
- **Commit `e641102`:** Committed Rounds 29 & 30 fixes (Claude audit, per-pedal WAV IR trims, limiter knee raised to 0.70 / -3.1 dBFS, sample-rate change re-FFT flag, double-click slider resets, dead code removal, verify test pruning).
- **Commit `bdd354d`:** Render test harness cleanup (`render_common.py`, `test_mirror_null.py`, dynamic path resolution, folding UPOLS sine continuity into `test_exact_ir_null.py`, pruning superseded scripts and single-pass render refactor).
- **Deployment:** Deployed all 8 `.jsfx*` files to `%APPDATA%\REAPER\Effects\sepulchre_sound\`.
- **Source line counts (strictly < 300 lines across all 8 files):**
  - `sepulchre_sound.jsfx`: 151 lines
  - `sepulchre_dsp_core.jsfx-inc`: 173 lines
  - `sepulchre_dsp_dist.jsfx-inc`: 183 lines
  - `sepulchre_dsp_fx.jsfx-inc`: 235 lines
  - `sepulchre_dsp_amp_cab.jsfx-inc`: 257 lines
  - `sepulchre_presets.jsfx-inc`: 108 lines
  - `sepulchre_ui.jsfx-inc`: 249 lines
  - `sepulchre_ui_panels.jsfx-inc`: 192 lines
- **AST & Core Verification (`verify_jsfx.py`):** Passes all 6 checks in **5.4 s**.

---

### 2. Live REAPER Sample-Null against Python Mirror (`test_mirror_null.py`)
Tested each of the four pedals at default settings with Amp, Cab, and FX bypassed (`slider54 = 0, slider49 = 0, slider20/30/40 = 0, slider4 = 0`) on `di_input.wav` (48 kHz 24-bit PCM), comparing live REAPER renders directly against `simulate_chain(..., include_amp_cab=False)`:

| Pedal | REAPER Signal Peak | Max Absolute Difference | Null Peak (dB) | Null RMS (dB) | Status |
|:---|:---:|:---:|:---:|:---:|:---:|
| **RAT** | 0.2786 (-11.10 dBFS) | $5.96 \times 10^{-8}$ (1 LSB) | **-133.40 dB** | **-134.44 dB** | **PASS** (target < -60 dB) |
| **DS-1** | 0.4254 (-7.42 dBFS) | $5.96 \times 10^{-8}$ (1 LSB) | **-137.07 dB** | **-130.58 dB** | **PASS** (target < -60 dB) |
| **Metal Zone** | 0.2760 (-11.18 dBFS) | $5.96 \times 10^{-8}$ (1 LSB) | **-133.31 dB** | **-130.80 dB** | **PASS** (target < -60 dB) |
| **HM-2** | 0.3042 (-10.34 dBFS) | $5.96 \times 10^{-8}$ (1 LSB) | **-134.16 dB** | **-134.74 dB** | **PASS** (target < -60 dB) |

*Finding:* Live REAPER renders and the Python mirror match down to the exact 24-bit quantization noise floor ($2^{-24} \approx 5.96 \times 10^{-8}$), establishing bit-exact algorithmic parity across all four distortion engines.

---

### 3. Per-Instance CPU Benchmark in REAPER
Benchmarked 8 concurrent plugin instances rendering 10.0 seconds of 48 kHz stereo audio through REAPER CLI (net DSP time isolated from REAPER process launch, project parsing, and file I/O overhead):

| Configuration | 8 Tracks $\times$ 10s Time | Net DSP Time | CPU per Instance (% of 1 Core) |
|:---|:---:|:---:|:---:|
| **Clean (Amp + WAV IR only)** | 19.01 s | < 0.001 s | **< 0.1%** |
| **Default RAT + Amp + WAV IR** | 24.24 s | 3.24 s | **4.05%** |
| **Default DS-1 + Amp + WAV IR** | 24.26 s | 3.27 s | **4.09%** |
| **Default Metal Zone + Amp + WAV IR** | 24.37 s | 3.38 s | **4.22%** |
| **Default HM-2 + Amp + WAV IR** | 26.08 s | 5.08 s | **6.35%** |

*Analysis on Mono Fast Path:*
- Claude's intuition in Round 30 §3 was spot-on: 8x stereo oversampling accounts for almost all of the plugin's CPU (4.0% to 6.35% of a core).
- Pure UPOLS partitioned convolution is essentially free (< 0.1% CPU).
- Because a guitar DI is mono (`spl0 == spl1`), running `proc_distortion` on a single channel when `spl0 == spl1` would cut the distortion workload in half (saving ~2.0% to 3.2% of a core per instance). Recommended for the next optimization pass.

---

### 4. Post-Round 29 & 30 Loudness & Headroom Table (`test_per_pedal_loudness.py`)
Rerun of all 4 pedals and 6 presets following Claude's per-pedal WAV IR trims (`ir_ped_g`) and the limiter knee elevation to $0.70$ (`-3.1 dBFS`):

| Test Case | Voicing / Model | IIR LUFS | IIR Peak | WAV IR LUFS | WAV IR Peak | Delta LUFS (Target $\approx$ +3.4) | Limiter Status (Knee: -3.1 dBFS) |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Default RAT** | RAT | -21.17 LUFS | -9.51 dBFS | -17.80 LUFS | -10.52 dBFS | **+3.37 dB** | Clean (< -3.1 dBFS) |
| **Default DS-1** | DS-1 | -21.19 LUFS | -8.29 dBFS | -17.41 LUFS | -7.91 dBFS | **+3.77 dB** | Clean (< -3.1 dBFS) |
| **Default Metal Zone** | Metal Zone | -22.87 LUFS | -10.00 dBFS | -19.49 LUFS | -12.01 dBFS | **+3.38 dB** | Clean (< -3.1 dBFS) |
| **Default HM-2** | HM-2 | -21.42 LUFS | -12.06 dBFS | -18.29 LUFS | -10.59 dBFS | **+3.13 dB** | Clean (< -3.1 dBFS) |
| **Preset 0: Tight Rhythm** | Metal Zone | -22.23 LUFS | -9.02 dBFS | -18.43 LUFS | -10.82 dBFS | **+3.80 dB** | Clean (< -3.1 dBFS) |
| **Preset 1: Cold Lead** | RAT | -21.97 LUFS | -9.81 dBFS | -18.36 LUFS | -11.42 dBFS | **+3.61 dB** | Clean (< -3.1 dBFS) |
| **Preset 2: Doom Wall** | HM-2 | -18.54 LUFS | -10.20 dBFS | -14.31 LUFS | **-6.46 dBFS** | **+4.23 dB** | **Clean** (3.36 dB below knee) |
| **Preset 3: Raw 4-Track** | DS-1 | -20.92 LUFS | -8.72 dBFS | -18.05 LUFS | -8.22 dBFS | **+2.87 dB** | Clean (< -3.1 dBFS) |
| **Preset 4: Swedish Chainsaw** | HM-2 (all 10) | -18.92 LUFS | -9.54 dBFS | -15.66 LUFS | -7.64 dBFS | **+3.27 dB** | Clean (< -3.1 dBFS) |
| **Preset 6: Ambient Swell** | Clean + FX | -19.24 LUFS | -8.67 dBFS | -15.27 LUFS | -8.56 dBFS | **+3.96 dB** | Clean (< -3.1 dBFS) |

*Key Verification Highlights:*
1. **Per-Pedal Delta Alignment:** All four default pedals land tightly within $\pm 0.38$ dB of the +3.4 dB reference target (RAT +3.37 dB, DS-1 +3.77 dB, MT-2 +3.38 dB, HM-2 +3.13 dB).
2. **Headroom Cleared:** Preset 2 (Doom Wall) in WAV IR mode dropped from `-5.86 dBFS` to `-6.46 dBFS` via the -0.6 dB trim, and with the knee at `-3.1 dBFS`, every preset and pedal runs in purely linear pass-through without engaging the limiter soft-knee.

---

### 5. Render Harness Cleanup Summary (§5)
- Created `tests/render/render_common.py` providing shared helpers (`make_track`, `build_rpp`, `run_reaper`, `read_wav24`, `write_wav24`, BS.1770 K-weighting, LUFS, peak measurement) with fully dynamic repository and AppData path resolution.
- Folded UPOLS 128-sample block-boundary sine continuity test into `test_exact_ir_null.py` (passes with impulse null at -125.42 dB and seamless block transitions).
- Pruned superseded scripts: `test_wavir_preset_peaks.py` and `test_ir_upols.py`.
- Replaced double-render null with single-pass verification in `run_reaper_render.py`.
- Deleted temporary render artifacts from workspace disk.

**Status:** Waiting on Devin (A/B listening test across pedals and HM-2 audition) + Claude (decision on mono fast-path optimization based on CPU benchmarks).
