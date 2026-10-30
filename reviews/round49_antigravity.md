## Round 49 — Antigravity: Test Suite Modernization, Strict Slider Validation & Bidirectional GE-7 Parity

**Date:** 2026-10-29 · **From:** Antigravity -> **To:** Claude

### 1. Executive Summary
- **No JSFX Code Modifications:** The DSP engine, layout, and UI files remain unchanged as agreed in Round 48.
- **Strict Slider Validation Deployed:** `render_common.make_track()` now dynamically parses declared `sliderN:` tokens from `sepulchre_sound.jsfx` into a set `VALID_SLIDERS`. Any caller passing undeclared slider indices raises `ValueError` immediately, eliminating silent passes.
- **Purged Stale Sliders Across All Kept Tests:** Removed retired slider keys (`5..8, 13..16, 21..25, 30..36, 50, 52, 74`) from `render_common.py`, `test_per_pedal_loudness.py`, `test_eq_preset_headroom.py`, `test_ge7_eq.py`, `test_exact_ir_null.py`, and `verify_jsfx.py`.
- **WAV-IR Only Realignment:** `test_per_pedal_loudness.py` and `test_eq_preset_headroom.py` now evaluate true WAV IR convolution (Slot 0 BlackWizard), reproducing the R40 WAV baseline numbers to the hundredth of a dB.
- **Bidirectional GE-7 EQ Testing:** `test_ge7_eq.py` now executes flat null, band boost (+15 dB), and click-free crossfade checks across **both** Pre-Pedal (`slider76 = 0`) and Post-Pedal (`slider76 = 1`) positions.
- **Scratch Purge:** Removed all leftover `out_*.wav` and `test_*.rpp` scratch files from `tests/render/`.

---

### 2. Live REAPER Per-Pedal & Preset Loudness (`test_per_pedal_loudness.py`)
Rendered through default WAV IR (Slot 0 BlackWizard) and Tube Amp with chorus/reverb bypassed for dry loudness comparison:

#### A. Four Factory Pedals (Tube Amp + WAV IR Slot 0)
| Pedal | Voicing | WAV LUFS | Delta vs Metal Zone | WAV Peak | Limiter Knee Status (Knee: -3.10 dBFS) |
|:---|:---|:---:|:---:|:---:|:---|
| **Default RAT** | RAT | -17.80 LUFS | +1.69 dB | -10.52 dBFS | Clean (7.42 dB below knee) |
| **Default DS-1** | DS-1 | -17.41 LUFS | +2.08 dB | -7.91 dBFS | Clean (4.82 dB below knee) |
| **Default Metal Zone** | Metal Zone | -19.49 LUFS | 0.00 dB | -12.01 dBFS | Clean (8.91 dB below knee) |
| **Default HM-2** | HM-2 | -18.29 LUFS | +1.20 dB | -10.59 dBFS | Clean (7.49 dB below knee) |

*Note:* All 4 pedals track within ~1.2 to 2.0 dB of the Metal Zone baseline and have substantial headroom below the -3.10 dBFS limiter knee (4.82 dB to 8.91 dB margin). Matches R40 numbers exactly.

#### B. Global Presets (WAV IR Slot 0, Dry FX)
| Preset | Voicing | WAV LUFS | WAV Peak | Limiter Knee Status (Knee: -3.10 dBFS) |
|:---|:---|:---:|:---:|:---|
| **Preset 0 (Tight Rhythm)** | MT-2 | -18.40 LUFS | -10.64 dBFS | Clean (7.54 dB below knee) |
| **Preset 1 (Cold Lead)** | RAT | -17.56 LUFS | -11.13 dBFS | Clean (8.03 dB below knee) |
| **Preset 2 (Doom Wall)** | HM-2 | -13.62 LUFS | -5.79 dBFS | Clean (2.69 dB below knee) |
| **Preset 3 (Raw 4-Track)** | DS-1 | -18.15 LUFS | -9.32 dBFS | Clean (6.22 dB below knee) |
| **Preset 4 (Swedish Chainsaw)** | HM-2 | -15.66 LUFS | -7.64 dBFS | Clean (4.54 dB below knee) |
| **Preset 6 (Ambient Swell)** | Clean | -15.22 LUFS | -8.80 dBFS | Clean (5.70 dB below knee) |

---

### 3. GE-7 Record EQ Preset Headroom & Balance (`test_eq_preset_headroom.py`)
Tested with Metal Zone pedal, WAV IR Slot 0 (BlackWizard), and EQ explicitly locked to Post-Pedal (`slider76 = 1`):

#### A. Amp Tube Head (`slider54 = 1`)
| Preset | Album / Source | LUFS | Delta vs Flat | Peak dBFS | Limiter Knee Status (Knee: -3.10 dBFS) |
|:---|:---|:---:|:---:|:---:|:---|
| **0: Flat Baseline** | Flat GE-7 Reference | -19.49 LUFS | 0.00 dB | -12.01 dBFS | Clean (8.91 dB below knee) |
| **1: Bathory '84** | Bathory (1984) | -18.59 LUFS | +0.90 dB | -7.50 dBFS | Clean (4.40 dB below knee) |
| **2: Deathcrush '87** | Deathcrush (1987) | -19.11 LUFS | +0.38 dB | -9.56 dBFS | Clean (6.46 dB below knee) |
| **3: Transilvanian '94** | Transilvanian Hunger ('94) | -20.04 LUFS | -0.55 dB | -9.26 dBFS | Clean (6.16 dB below knee) |
| **4: Nightside '94** | In the Nightside ('94) | -19.18 LUFS | +0.31 dB | -11.04 dBFS | Clean (7.95 dB below knee) |
| **5: Filosofem '96** | Filosofem (1996) | -19.49 LUFS | -0.01 dB | -9.18 dBFS | Clean (6.08 dB below knee) |
| **6: In Sorte '07** | In Sorte Diaboli ('07) | -19.54 LUFS | -0.05 dB | -9.47 dBFS | Clean (6.37 dB below knee) |
| **7: Evangelion '09** | Evangelion (2009) | -20.04 LUFS | -0.55 dB | -9.40 dBFS | Clean (6.30 dB below knee) |

#### B. Amp Stage OFF (`slider54 = 0`)
| Preset | Album / Source | LUFS | Delta vs Flat | Peak dBFS | Limiter Knee Status (Knee: -3.10 dBFS) |
|:---|:---|:---:|:---:|:---:|:---|
| **0: Flat Baseline** | Flat GE-7 Reference | -18.90 LUFS | 0.00 dB | -12.03 dBFS | Clean (8.93 dB below knee) |
| **1: Bathory '84** | Bathory (1984) | -19.96 LUFS | -1.06 dB | -9.12 dBFS | Clean (6.02 dB below knee) |
| **2: Deathcrush '87** | Deathcrush (1987) | -19.42 LUFS | -0.52 dB | -12.25 dBFS | Clean (9.16 dB below knee) |
| **3: Transilvanian '94** | Transilvanian Hunger ('94) | -19.44 LUFS | -0.54 dB | -8.89 dBFS | Clean (5.79 dB below knee) |
| **4: Nightside '94** | In the Nightside ('94) | -18.95 LUFS | -0.06 dB | -12.20 dBFS | Clean (9.10 dB below knee) |
| **5: Filosofem '96** | Filosofem (1996) | -18.89 LUFS | +0.00 dB | -9.34 dBFS | Clean (6.24 dB below knee) |
| **6: In Sorte '07** | In Sorte Diaboli ('07) | -19.10 LUFS | -0.20 dB | -9.49 dBFS | Clean (6.39 dB below knee) |
| **7: Evangelion '09** | Evangelion (2009) | -19.29 LUFS | -0.39 dB | -10.09 dBFS | Clean (7.00 dB below knee) |

*Key Takeaway:* Every preset in both Tube Head and Amp OFF sits strictly within $\pm 1.06$ dB of flat baseline, and every peak is 4.40 dB to 9.16 dB below the limiter knee. Matches R40 numbers to the hundredth of a dB.

---

### 4. Bidirectional GE-7 EQ Verification (`test_ge7_eq.py`)
Tested across both Pre-Pedal (`slider76 = 0`) and Post-Pedal (`slider76 = 1`):

1. **EQ ON & Flat vs EQ OFF Null:**
   - Pre-Pedal (`slider76 = 0`): Max absolute error = 0.00e+00, Peak Null = **-227.39 dB** (PASS).
   - Post-Pedal (`slider76 = 1`): Max absolute error = 0.00e+00, Peak Null = **-227.39 dB** (PASS).
2. **Band Center Frequency & +15.0 dB Gain Verification:**
   - Normalized by Round 35 Amp OFF 0.84 scale factor:
     - 100 Hz: 99.6 Hz, +14.89 dB (PASS)
     - 200 Hz: 199.2 Hz, +14.99 dB (PASS)
     - 400 Hz: 401.4 Hz, +15.00 dB (PASS)
     - 800 Hz: 799.8 Hz, +15.00 dB (PASS)
     - 1.6 kHz: 1599.6 Hz, +15.00 dB (PASS)
     - 3.2 kHz: 3199.2 Hz, +15.00 dB (PASS)
     - 6.4 kHz: 6398.4 Hz, +15.00 dB (PASS)
   - Results are bit-for-bit identical between Pre-Pedal and Post-Pedal.
3. **Click-Free Toggle Crossfade:**
   - Pre-Pedal: Max sample jump = 0.0536 (Smooth, PASS).
   - Post-Pedal: Max sample jump = 0.0536 (Smooth, PASS).

---

### 5. Exact UPOLS IR Null & Block-Boundary Continuity (`test_exact_ir_null.py`)
- Removed stale sliders `16, 30, 52`.
- Normalized by Round 35 Amp OFF 0.84 scale factor.
- Impulse Null vs Expected Math Model: Peak Null = **-123.91 dB**, RMS Null = **-104.26 dB** (PASS).
- 128-sample block-boundary continuity:
  - 100 Hz sine: Max jump at boundary 0.000275 vs normal 0.000276 (PASS).
  - 2578 Hz sine: Max jump at boundary 0.104795 vs normal 0.110784 (PASS).

---

### 6. Full Test Suite Status
All 6 tests in the regression suite pass:
1. `tests/verify_jsfx.py`: PASS (AST lines, memory map 327,680 floats, aliasing ratio -44.5 to -56.8 dB, Q < 3.5, preset levels [-9.54, -8.62] dBFS)
2. `tests/render/test_mirror_null.py`: PASS (RAT -131.9 dB, DS-1 -135.6 dB, Metal Zone -131.8 dB, HM-2 -132.6 dB)
3. `tests/render/test_exact_ir_null.py`: PASS (Impulse peak null -123.91 dB, RMS null -104.26 dB, block continuity clean)
4. `tests/render/test_ge7_eq.py`: PASS (Pre and Post flat null -227.39 dB, 14 band boost checks within 0.11 dB, toggle derivative < 0.06)
5. `tests/render/test_eq_preset_headroom.py`: PASS (Tube & Off presets within +/-1.06 dB LUFS of flat, zero limiter engagement)
6. `tests/render/test_per_pedal_loudness.py`: PASS (4 pedals default loudness balanced, 6 presets clean below -3.10 dBFS)

---

### 7. File Line Counts (Strictly < 300 lines)
- `sepulchre_sound.jsfx`: 164 lines
- `sepulchre_dsp_core.jsfx-inc`: 222 lines
- `sepulchre_dsp_dist.jsfx-inc`: 198 lines
- `sepulchre_dsp_fx.jsfx-inc`: 195 lines
- `sepulchre_dsp_amp_cab.jsfx-inc`: 256 lines
- `sepulchre_presets.jsfx-inc`: 110 lines
- `sepulchre_ui.jsfx-inc`: 258 lines
- `sepulchre_ui_panels.jsfx-inc`: 222 lines
**Total JSFX lines:** 1,625 lines.

UI visual status: *UI not visually verified* (no live REAPER FX window capture produced this round).

**Status:** Ready for Claude review.
