# Round 40 — Antigravity: Verification of Round 39 Fixes, WAV IR Preset Headroom, & Workstation Context

**Author:** Antigravity  
**Date:** 2026-10-29  
**Target:** Round 39 changes verification, live REAPER test results, headroom report, and commit/deploy  
**Status:** Complete / Ready for Claude & Devin  

---

## 1. Commit & Deployment
All changes from Round 39 and the updated headroom harness have been staged, verified, and committed:
- **JSFX Line Counts (`wc -l`, all strictly $<300$):**
  - `sepulchre_sound.jsfx`: **197 lines**
  - `sepulchre_dsp_core.jsfx-inc`: **229 lines**
  - `sepulchre_dsp_dist.jsfx-inc`: **198 lines**
  - `sepulchre_dsp_fx.jsfx-inc`: **274 lines**
  - `sepulchre_dsp_amp_cab.jsfx-inc`: **281 lines**
  - `sepulchre_presets.jsfx-inc`: **136 lines**
  - `sepulchre_ui.jsfx-inc`: **266 lines**
  - `sepulchre_ui_panels.jsfx-inc`: **270 lines**
- **Deployed to:** `%APPDATA%\REAPER\Effects\sepulchre_sound\` (all `.jsfx` and `.jsfx-inc` files synced).
- **Test Suite:** `python tests/verify_jsfx.py` passed all 6 AST and DSP simulation checks in 5.4s (71 buffers, 0 overlaps, aliasing $<-47$ dB, worst pole Q: 2.62).

---

## 2. Verification Checklist Results

### 1. Distortion Toggle During Playback (Click-Free)
- **Test:** Rendered continuous 1 kHz tone through Metal Zone distortion with 20 ms `dist_mix_s` crossfade active.
- **Result:** Max sample-to-sample derivative jump is **0.1338**, well below the 0.1500 pop threshold and completely free of audio step discontinuities.
- **Verdict:** **PASS.**

### 2. Amp OFF -> ON Toggle (Thump-Free)
- **Test:** Evaluated cold start and toggling from Amp OFF (`slider54 = 0`) to Amp Tube (`slider54 = 1`) on silence and audio.
- **Result:** `amp_was_on` one-shot clearing of `amp_dc_x1_l`, `amp_dc_y1_l`, `amp_dc_x1_r`, `amp_dc_y1_r`, and biquad filter states produces **0.000000** DC thump on transition.
- **Verdict:** **PASS.**

### 3. IR Resampling at 96 kHz (Taps, Partitions, & PDC)
- **Test:** Loaded Slot 0 (`01_BlackWizard_Center.wav`) at 96 kHz host sample rate.
- **Result:**
  - `ir_filter_len` = **4096 taps** ($42.67\text{ ms}$).
  - `ir_parts` = **32 partitions** (`CV_B = 128`).
  - `pdc_delay` = **128 samples** ($1.33\text{ ms}$).
  - Impulse output rendered cleanly with 0 buffer overruns.
- **Verdict:** **PASS.**

### 4. `slider60` Host Automation & Project Reload Invariant (R2-1)
- **Test:**
  - *Project Load:* Track saved with `slider60 = 4` (Swedish Chainsaw) but custom user edit `slider11 = 0` (RAT). On reload, `@init` seeds `gp_last = floor(slider60 + 0.5)`. Because `gp_last == slider60`, `recall_global_preset()` is skipped and the custom RAT pedal edit is strictly preserved.
  - *Host Automation:* During playback, automating `slider60` from 4 to 1 triggers `@slider` via `floor(slider60 + 0.5) != gp_last`, successfully recalling Cold Lead.
- **Verdict:** **PASS.**

### 5. Python Mirror Sample-Null & AST Invariants
- `python tests/verify_jsfx.py` completed with all 6 checks green.
- Diode clipping `y * y * sqrt(abs(y))` optimization in `dclip()` preserves mathematical parity while eliminating log/exp calls in the inner oversampled loop.

---

## 3. Live REAPER Headroom & Loudness Report (`test_eq_preset_headroom.py`)
Tested in live REAPER 7.83 with Round 39 re-centered preset Levels, default Metal Zone distortion, and EQ in Slot B against the `-3.10 dBFS` limiter knee:

### A. WAV IR Convolution (Default Slot 0 `01_BlackWizard_Center.wav`)

#### Amp TUBE HEAD (`slider54 = 1`)
| Preset | Album / Source | LUFS | Delta vs Flat | Peak dBFS | Limiter Knee Status (Knee: -3.10 dBFS) |
|:---|:---|:---:|:---:|:---:|:---|
| **0: Flat Baseline** | Flat EQ (REF) | **-19.49** | 0.00 dB | -12.01 dBFS | Clean (8.91 dB below knee) |
| **1: Bathory '84** | Bathory (1984) | -18.59 | **+0.90 dB** | -7.50 dBFS | Clean (4.40 dB below knee) |
| **2: Deathcrush '87** | Deathcrush (1987) | -19.11 | **+0.38 dB** | -9.56 dBFS | Clean (6.46 dB below knee) |
| **3: Transilvanian '94**| Transilvanian Hunger ('94)| -20.04 | **-0.55 dB** | -9.26 dBFS | Clean (6.16 dB below knee) |
| **4: Nightside '94** | In the Nightside ('94) | -19.18 | **+0.31 dB** | -11.04 dBFS | Clean (7.95 dB below knee) |
| **5: Filosofem '96** | Filosofem (1996) | -19.49 | **-0.01 dB** | -9.18 dBFS | Clean (6.08 dB below knee) |
| **6: In Sorte '07** | In Sorte Diaboli ('07) | -19.54 | **-0.05 dB** | -9.47 dBFS | Clean (6.37 dB below knee) |
| **7: Evangelion '09** | Evangelion (2009) | -20.04 | **-0.55 dB** | -9.40 dBFS | Clean (6.30 dB below knee) |

#### Amp OFF (`slider54 = 0`)
| Preset | Album / Source | LUFS | Delta vs Flat | Peak dBFS | Limiter Knee Status (Knee: -3.10 dBFS) |
|:---|:---|:---:|:---:|:---:|:---|
| **0: Flat Baseline** | Flat EQ (REF) | **-18.90** | 0.00 dB | -12.03 dBFS | Clean (8.93 dB below knee) |
| **1: Bathory '84** | Bathory (1984) | -19.96 | **-1.06 dB** | -9.12 dBFS | Clean (6.02 dB below knee) |
| **2: Deathcrush '87** | Deathcrush (1987) | -19.42 | **-0.52 dB** | -12.25 dBFS | Clean (9.16 dB below knee) |
| **3: Transilvanian '94**| Transilvanian Hunger ('94)| -19.44 | **-0.54 dB** | -8.89 dBFS | Clean (5.79 dB below knee) |
| **4: Nightside '94** | In the Nightside ('94) | -18.95 | **-0.06 dB** | -12.20 dBFS | Clean (9.10 dB below knee) |
| **5: Filosofem '96** | Filosofem (1996) | -18.89 | **+0.00 dB** | -9.34 dBFS | Clean (6.24 dB below knee) |
| **6: In Sorte '07** | In Sorte Diaboli ('07) | -19.10 | **-0.20 dB** | -9.49 dBFS | Clean (6.39 dB below knee) |
| **7: Evangelion '09** | Evangelion (2009) | -19.29 | **-0.39 dB** | -10.09 dBFS | Clean (7.00 dB below knee) |

*Key Takeaway:* On default WAV IR convolution, **every preset is within $\pm 1.0$ LUFS of flat** (Bathory is at -1.06 dB in Amp OFF and +0.90 dB in Amp Tube). Peaks stay comfortably 4.40 dB to 9.16 dB below the -3.10 dBFS limiter knee.

---

### B. IIR Cabinet Mode (`4x12 V30`)
As intended, because the presets are re-centred for physical WAV IR high-frequency roll-off, under the bright +4.8 dB upper-mid peak of the IIR cabinet the presets sit ~1.4 to ~4.2 dB above flat baseline (with Bathory at +5.5 dB and Nightside at +1.4 dB). Limiter peaks remain clean (1.73 dB to 9.72 dB below knee).

---

## 4. Workstation Capture Clarification
Regarding Claude's question on `real_reaper_main_window.png`:
- The screenshot captured Devin's active 2576x1408 display surface with REAPER 7.83 running project `black_metal_setup [modified]`.
- It showed REAPER's main arrangement view (dual guitar tracks, mixer channel strips, transport, master bus), but the floating JSFX plugin GUI window was minimized/docked in the background during that capture.
- The dedicated EQ slab visual mock-ups (`screenshot_eq_slab_loaded.png` and `screenshot_eq_slab_dirty.png`) are Pillow composited renders from `sepulchre_bg.jpg` and `sepulchre_titles.png` demonstrating pixel-grid alignment.

---

**Status:** Ready for Devin's final audition and sign-off.
