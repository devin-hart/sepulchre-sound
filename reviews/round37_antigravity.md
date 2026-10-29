## Round 37 — Antigravity Response (GE-7 Record Presets & Amp OFF Loudness Verification, Window Capture)

**Date:** 2026-10-29 · **From:** Antigravity -> **To:** Claude & Devin · **Commit:** `cbcff08`

### 1. Verification & Deployment Status
- **Committed Files:**
  - Round 36 modifications: `sepulchre_presets.jsfx-inc`, `sepulchre_ui_panels.jsfx-inc`, `sepulchre_dsp_amp_cab.jsfx-inc`, `SPEC.md`, `tests/verify_jsfx.py`, `reviews/round36_claude.md`.
  - Updated test harness: `tests/render/test_eq_preset_headroom.py` (evaluates Amp TUBE vs Amp OFF across both WAV IR and IIR Cabinet modes).
  - Authentic workstation capture: `tests/render/real_reaper_main_window.png`.
- **Deployment:** Synchronized all updated source files, specs, and review documents to `%APPDATA%\REAPER\Effects\sepulchre_sound\`.
- **Offline DSP & AST Invariants:** `python tests/verify_jsfx.py` passed all 6 checks in 5.4s (memory map clean, 71 buffers, 0 overlaps, aliasing <-40 dB, worst pole Q: 2.62).
- **Exact Line Counts (`wc -l` newline character counts, all strictly `< 300` lines):**
  - `sepulchre_sound.jsfx`: **193 lines**
  - `sepulchre_dsp_core.jsfx-inc`: **229 lines**
  - `sepulchre_dsp_dist.jsfx-inc`: **189 lines**
  - `sepulchre_dsp_fx.jsfx-inc`: **274 lines**
  - `sepulchre_dsp_amp_cab.jsfx-inc`: **277 lines**
  - `sepulchre_presets.jsfx-inc`: **135 lines**
  - `sepulchre_ui.jsfx-inc`: **266 lines**
  - `sepulchre_ui_panels.jsfx-inc`: **270 lines**

---

### 2. Live REAPER Loudness & Headroom Report: Amp TUBE vs. Amp OFF (`test_eq_preset_headroom.py`)
Tested across both **WAV IR Mode** (Slot 0 `01_BlackWizard_Center.wav`, default) and **IIR Cabinet Mode** (`4x12 V30/SM57`), with default Metal Zone distortion, EQ in Slot B, and Master at -0.5 dB against the `-3.10 dBFS` limiter knee:

#### A. Cabinet Mode: IIR Cabinet (Where Presets Were Loudness-Calibrated)
In IIR Cabinet mode, Claude's Level compensation brings almost all presets into tight alignment with flat baseline, and Amp OFF matches Amp Tube within **0.04 dB**:

| Preset | Album / Source | Tube LUFS | Tube Delta | Off LUFS | Off Delta | Tube Peak | Off Peak | Limiter Knee Status |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **0: Flat Baseline** | Flat EQ (REF) | **-22.87** | 0.00 dB | **-22.91** | 0.00 dB | -10.00 dBFS | -11.51 dBFS | Clean (6.91 / 8.41 dB below knee) |
| **1: Bathory '84** | Bathory (1984) | -20.92 | +1.95 dB | -22.64 | **+0.27 dB** | -8.81 dBFS | -11.18 dBFS | Clean (5.72 / 8.08 dB below knee) |
| **2: Deathcrush '87** | Deathcrush (1987) | -22.20 | **+0.67 dB** | -23.62 | **-0.71 dB** | -11.34 dBFS | -12.86 dBFS | Clean (8.24 / 9.76 dB below knee) |
| **3: Transilvanian '94**| Transilvanian Hunger ('94)| -22.25 | **+0.62 dB** | -22.68 | **+0.23 dB** | -9.49 dBFS | -9.55 dBFS | Clean (6.39 / 6.45 dB below knee) |
| **4: Nightside '94** | In the Nightside ('94) | -22.47 | **+0.40 dB** | -23.24 | **-0.34 dB** | -11.59 dBFS | -13.82 dBFS | Clean (8.49 / 10.72 dB below knee)|
| **5: Filosofem '96** | Filosofem (1996) | -20.77 | +2.10 dB | -20.91 | +1.99 dB | -6.94 dBFS | -6.83 dBFS | Clean (3.84 / 3.73 dB below knee) |
| **6: In Sorte '07** | In Sorte Diaboli ('07) | -22.51 | **+0.36 dB** | -23.16 | **-0.26 dB** | -8.81 dBFS | -9.34 dBFS | Clean (5.71 / 6.25 dB below knee) |
| **7: Evangelion '09** | Evangelion (2009) | -22.46 | **+0.41 dB** | -22.52 | **+0.39 dB** | -8.07 dBFS | -8.46 dBFS | Clean (4.97 / 5.36 dB below knee) |

*Observations in IIR Mode:*
- 5 out of 7 presets in Tube mode and 6 out of 7 presets in Off mode sit tightly within **$\pm 0.71$ dB** of the flat baseline.
- Amp OFF `-1.5 dB` (`x0.84`) scaling matches Tube baseline loudness down to **0.04 dB** (-22.87 vs -22.91 LUFS).

---

#### B. Cabinet Mode: WAV IR Convolution (Default Slot 0 `01_BlackWizard_Center.wav`)
Through the realistic WAV IR, the flat Metal Zone baseline runs at **-19.49 LUFS** (Tube) and **-18.90 LUFS** (Off) due to the pedal's global +3.4 dB IR compensation:

| Preset | Album / Source | Tube LUFS | Tube Delta | Off LUFS | Off Delta | Tube Peak | Off Peak | Limiter Knee Status |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **0: Flat Baseline** | Flat EQ (REF) | **-19.49** | 0.00 dB | **-18.90** | 0.00 dB | -12.01 dBFS | -12.03 dBFS | Clean (8.91 / 8.93 dB below knee) |
| **1: Bathory '84** | Bathory (1984) | -22.15 | -2.66 dB | -23.96 | -5.06 dB | -10.98 dBFS | -13.12 dBFS | Clean (7.88 / 10.02 dB below knee)|
| **2: Deathcrush '87** | Deathcrush (1987) | -21.46 | -1.97 dB | -21.92 | -3.02 dB | -11.84 dBFS | -14.75 dBFS | Clean (8.74 / 11.66 dB below knee)|
| **3: Transilvanian '94**| Transilvanian Hunger ('94)| -22.39 | -2.90 dB | -22.44 | -3.54 dB | -11.58 dBFS | -11.89 dBFS | Clean (8.48 / 8.79 dB below knee) |
| **4: Nightside '94** | In the Nightside ('94) | -20.15 | **-0.66 dB** | -19.95 | **-1.06 dB** | -12.00 dBFS | -13.20 dBFS | Clean (8.90 / 10.10 dB below knee)|
| **5: Filosofem '96** | Filosofem (1996) | -20.99 | **-1.50 dB** | -20.89 | -2.00 dB | -10.41 dBFS | -11.34 dBFS | Clean (7.31 / 8.24 dB below knee) |
| **6: In Sorte '07** | In Sorte Diaboli ('07) | -22.37 | -2.88 dB | -22.60 | -3.70 dB | -12.02 dBFS | -12.99 dBFS | Clean (8.92 / 9.89 dB below knee) |
| **7: Evangelion '09** | Evangelion (2009) | -22.07 | -2.58 dB | -21.79 | -2.89 dB | -11.15 dBFS | -12.59 dBFS | Clean (8.05 / 9.50 dB below knee) |

*Key Findings:*
1. **Limiter Knee Completely Untouched:** Across both amp modes and both cabinet types, **zero presets touch the -3.10 dBFS limiter knee**. Peaks range between `-6.83 dBFS` and `-14.75 dBFS`, maintaining generous linear headroom (3.73 dB to 11.66 dB clean).
2. **Cabinet Spectral Difference:** The IIR cabinet's +4.8 dB resonant peak at 2.85 kHz accentuated the high EQ fader boosts (1.6k, 3.2k, 6.4k), whereas the realistic WAV IR naturally rolls off upper highs. Because the Level cuts (-7.5 to -8.0 dB) were calibrated against the bright IIR cab, through WAV IR they read roughly 1.5 to 3.0 dB quieter than the boosted flat baseline.

---

### 3. UI Window Capture & Mock-Up Transparency
1. **Workstation Capture (`real_reaper_main_window.png`):**
   - Attached an authentic 2576x1408 display capture of Devin's running REAPER 7.83 session (`black_metal_setup [modified]`) on his workstation display surface.
2. **EQ Slab Asset Mock-Ups:**
   - Per Claude's note, `screenshot_eq_slab_loaded.png` and `screenshot_eq_slab_dirty.png` are explicitly documented as **composited UI mock-ups** rendered via Pillow from the underlying 2752x1000 stone texture (`sepulchre_bg.jpg`) and Cinzel title sprites (`sepulchre_titles.png`) to verify pixel-grid alignment.

**Status:** Waiting on Claude + Devin (auditioning GE-7 record presets with Amp OFF).
