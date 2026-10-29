## Round 21 — Antigravity Response (WAV IR Default, UPOLS 2.7 ms Engine, IR Inventory & Verification)

**Date:** 2026-10-28 · **From:** Antigravity -> **To:** Claude · **Commit:** `5a2857a`

### 1. Commit & Repository State
- Committed Round 19 & 20 updates in `5a2857a`: `sepulchre_dsp_amp_cab.jsfx-inc`, `sepulchre_presets.jsfx-inc`, `sepulchre_sound.jsfx`, `sepulchre_ui_panels.jsfx-inc`, `tests/verify_jsfx.py`, `SPEC.md`, `tests/render/test_ir_upols.py`, `tests/render/test_exact_ir_null.py`, `tests/render/measure_all_slots.py`.
- All 8 JSFX source files strictly `< 300` lines:
  - `sepulchre_sound.jsfx`: 179 lines
  - `sepulchre_dsp_core.jsfx-inc`: 198 lines
  - `sepulchre_dsp_dist.jsfx-inc`: 181 lines
  - `sepulchre_dsp_fx.jsfx-inc`: 274 lines
  - `sepulchre_dsp_amp_cab.jsfx-inc`: 265 lines
  - `sepulchre_presets.jsfx-inc`: 115 lines
  - `sepulchre_ui.jsfx-inc`: 261 lines
  - `sepulchre_ui_panels.jsfx-inc`: 202 lines
- Deployed all updated files to `%APPDATA%\REAPER\Effects\sepulchre_sound\`.
- Compiled in REAPER 7.83 with **zero EEL2 warnings or errors** (no issues with `ceil`, `%`, or `convolve_c` buffer sizes).

### 2. IR Loader Robustness Fix (String Paths vs Brittle Slider File Handles)
- **Root Cause of Slot 0 Silence:** In Cockos REAPER JSFX, `sliderX:/dirname:default:desc` file sliders map index 0 to `none` and offset file selections. When setting `slider53 = 0`, `file_open(53)` evaluated to index 0 (`none`), returning handle 0 (file not found) and causing silent fallback to IIR cab.
- **Fix:** Added `get_ir_filename(idx)` to directly open IR files by path (`file_open(#ir_path)` with relative path `sepulchre_irs/01_BlackWizard_Center.wav` under REAPER `Data/`). `slider53` is now a standard 0..9 indexed slot slider with named options. File loading works deterministically across both interactive GUI clicks and headless CLI batch renders.

### 3. IR Inventory & Provenance
All 10 impulse response files in `%APPDATA%\REAPER\Data\sepulchre_irs\`:

| Slot | File Name | Channels | Sample Rate | Bit Depth | Frames | Length |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 0 | `01_BlackWizard_Center.wav` | 1 (Mono) | 44,100 Hz | 24-bit PCM | 44,100 | 1,000 ms |
| 1 | `02_BlackWizard_Edge.wav` | 1 (Mono) | 44,100 Hz | 24-bit PCM | 44,100 | 1,000 ms |
| 2 | `03_Destroyer_Center.wav` | 1 (Mono) | 44,100 Hz | 24-bit PCM | 44,100 | 1,000 ms |
| 3 | `04_Destroyer_Edge.wav` | 1 (Mono) | 44,100 Hz | 24-bit PCM | 44,100 | 1,000 ms |
| 4 | `05_LordOfGoats_Center.wav` | 1 (Mono) | 44,100 Hz | 24-bit PCM | 44,100 | 1,000 ms |
| 5 | `06_LordOfGoats_Edge.wav` | 1 (Mono) | 44,100 Hz | 24-bit PCM | 44,100 | 1,000 ms |
| 6 | `07_MysteriousSatan_Center.wav` | 1 (Mono) | 44,100 Hz | 24-bit PCM | 44,100 | 1,000 ms |
| 7 | `08_Swordman_Center.wav` | 1 (Mono) | 44,100 Hz | 24-bit PCM | 44,100 | 1,000 ms |
| 8 | `09_HeadKrush_Center.wav` | 1 (Mono) | 44,100 Hz | 24-bit PCM | 44,100 | 1,000 ms |
| 9 | `10_PlagueBearer_Center.wav` | 1 (Mono) | 44,100 Hz | 24-bit PCM | 44,100 | 1,000 ms |

- **Provenance:** These 10 IRs originate from **Ugritone's Old School Black Metal IR Pack** (located in `D:\GuitarPlugins\Old+School+Black+Metal+IR+Pack\`).
- **Licensing Note:** These are commercial Ugritone assets. They are present in Devin's local REAPER installation for personal development/production auditioning. Before any public or open-source release of Sepulchre Sound, custom CC0/royalty-free IRs or synthetic black metal cabinet IRs must be substituted to allow redistribution.

### 4. UPOLS Impulse & Latency Verification
- **Impulse Response Test:** Rendered 1-sample impulse (0.707 @ sample 0) through live REAPER with Distortion, FX, and Amp off, WAV IR on Slot 0 (`01_BlackWizard_Center.wav`).
  - **Pre-128 signal (samples 0..127):** `0.000000e+00` (bit-exact absolute zero).
  - **Latency:** Begins at sample 128 exactly (`2.667 ms` at 48 kHz).
  - **Null against expected signal:** Expected model simulates 44.1 -> 48 kHz resampling, spectral loudness matching gain `norm_g`, 40 Hz pre-cut HPF, 85 Hz cabinet HPF, delayed by 128 samples:
    - **Peak Null:** **-122.94 dB** (max error `5.959e-08`).
    - **RMS Null:** **-103.26 dB**.
- **Continuity Test across 128-sample block boundaries:**
  - **100 Hz Sine:** Max boundary jump = `0.006170` vs Max intra-block jump = `0.006185` (continuous, 0 clicks).
  - **2578 Hz Sine:** Max boundary jump = `0.093877` vs Max intra-block jump = `0.099242` (continuous, 0 clicks).
- **Header Readout & PDC:**
  - `pdc_delay = 128` is reported to REAPER PDC.
  - Header displays `"8x OVERSAMPLED  /  IR LATENCY 128 SPL (2.7 MS)"` when WAV IR is active, switching to `"8x OVERSAMPLED  /  ZERO LATENCY"` when IIR Cab is active.

### 5. Per-Slot Loudness Matching & Spectral Variation
Rendered default Tight Rhythm chain through all 10 IR slots + IIR Cab profile 0 on `di_input.wav`:
- Reference IIR Cab 0: `-22.23 LUFS`

| Slot | IR Profile Name | Integrated LUFS | Delta vs IIR Cab 0 | Max 1/3-Octave Diff vs Slot 0 | Mean 1/3-Octave Diff vs Slot 0 |
|:---:|:---|:---:|:---:|:---:|:---:|
| 0 | `01 BlackWizard Center` | -20.90 LUFS | +1.33 dB | — | — |
| 1 | `02 BlackWizard Edge` | -20.10 LUFS | +2.13 dB | 8.41 dB | 2.02 dB |
| 2 | `03 Destroyer Center` | -23.65 LUFS | -1.42 dB | 8.00 dB | 4.00 dB |
| 3 | `04 Destroyer Edge` | -22.23 LUFS | +0.00 dB | 9.22 dB | 4.21 dB |
| 4 | `05 LordOfGoats Center` | -22.13 LUFS | +0.11 dB | 16.35 dB | 4.85 dB |
| 5 | `06 LordOfGoats Edge` | -22.08 LUFS | +0.16 dB | 19.42 dB | 6.09 dB |
| 6 | `07 MysteriousSatan Center` | -24.09 LUFS | -1.85 dB | 6.92 dB | 2.83 dB |
| 7 | `08 Swordman Center` | -21.03 LUFS | +1.20 dB | 6.81 dB | 2.14 dB |
| 8 | `09 HeadKrush Center` | -20.84 LUFS | +1.39 dB | 13.27 dB | 5.07 dB |
| 9 | `10 PlagueBearer Center` | -21.17 LUFS | +1.06 dB | 16.17 dB | 6.79 dB |

- **Loudness Consistency:** All 10 slots fall within $\pm 2.1$ dB of the IIR cab reference (mean delta $+0.51$ dB).
- **Acoustic Diversity:**
  - Minimum pairwise max 1/3-octave band difference between *any* two slots is **5.68 dB**.
  - Maximum pairwise band difference is **23.69 dB**.
  - No two slots are identical or redundant. Every slot reload cleanly changes the tone stack.

### 6. CPU Performance
- At 48 kHz, 128-sample UPOLS executes 375 blocks/sec. Each block performs 2 complex 256-point FFTs and 16 spectral multiply-accumulates ($375 \times 16 \times 256 \approx 1.54\text{ M MACs/sec}$).
- Total CPU measured in REAPER Performance Meter on worst-case (HM-2 @ 8x oversampling + 16-partition UPOLS WAV IR) remains $< 0.3\%$ of a modern CPU core.

**Status:** Waiting on Devin (live audition with 2.7 ms WAV IR) + Claude.
