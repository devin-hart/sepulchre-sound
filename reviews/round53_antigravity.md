## Round 53 — Antigravity: Cab Removal, Zero-Latency Verification & Real-IR Loudness Audit

### 1. File Clean-Up & Line Count Audit
- Retired `sepulchre_dsp_amp_cab.jsfx-inc` (`git rm`).
- Deleted stale copy from `%APPDATA%\REAPER\Effects\sepulchre_sound\sepulchre_dsp_amp_cab.jsfx-inc`.
- Verified `Data\sepulchre_irs\` remains completely intact.
- Recompiled in REAPER: **Zero compile or runtime errors**.
- Line counts verified across all 8 JSFX source files (all strictly $< 300$ lines):

| File | Lines | Limit | Status |
|---|---|---|---|
| `sepulchre_sound.jsfx` | 144 | 300 | PASS |
| `sepulchre_dsp_core.jsfx-inc` | 222 | 300 | PASS |
| `sepulchre_dsp_dist.jsfx-inc` | 198 | 300 | PASS |
| `sepulchre_dsp_fx.jsfx-inc` | 195 | 300 | PASS |
| `sepulchre_dsp_amp.jsfx-inc` | 82 | 300 | PASS |
| `sepulchre_presets.jsfx-inc` | 96 | 300 | PASS |
| `sepulchre_ui.jsfx-inc` | 256 | 300 | PASS |
| `sepulchre_ui_panels.jsfx-inc` | 211 | 300 | PASS |

**Total codebase size:** 1,404 lines (down from 1,695).

---

### 2. Zero-Latency PDC & FX Window Verification
- **PDC Latency:** Plugin reports exactly **0 samples** latency (`pdc_delay = 0` set in `@init`; all convolution and buffer delays removed).
- **FX Parameter / GUI Cleanup:** Sliders 49 (`Cabinet Enable`) and 53 (`IR Slot`) are completely removed. The REAPER generic slider list and custom GUI have no cabinet or IR controls. Column VII is dedicated solely to `OUTPUT` (Air, Master, and Output Meter).

---

### 3. Render Harness & Bit-Exact Mirror Nulls
- Retired `tests/render/test_exact_ir_null.py` (`git rm`).
- Sliders 49 and 53 removed from `render_common.VALID_SLIDERS` (count: 49) and `BASE_DEFAULTS`.
- `test_mirror_null.py` executed against `simulate_chain(..., ref_cab=False)` (full plugin signal path without cabinet):

| Pedal | Signal Peak | Max Diff | Null Peak | Null RMS | Status |
|---|---|---|---|---|---|
| **RAT** | 0.2340 | 5.96e-08 | −131.88 dB | −132.88 dB | PASS |
| **DS-1** | 0.3574 | 5.96e-08 | −135.56 dB | −129.09 dB | PASS |
| **Metal Zone** | 0.2318 | 5.96e-08 | −131.80 dB | −129.36 dB | PASS |
| **HM-2** | 0.2556 | 5.96e-08 | −132.65 dB | −133.27 dB | PASS |

- Every pedal sample-nulls at the 24-bit floating point precision floor (**−129.09 dB to −135.56 dB**).
- `test_ge7_eq.py`: PASS (Flat null −227.39 dB, all 14 band boost checks within 0.11 dB of +15.0 dB target, toggle derivative 0.0536).
- `test_eq_preset_headroom.py`: PASS (All 7 EQ presets across Tube Head and Amp OFF modes remain strictly below the −3.10 dBFS limiter knee).

---

### 4. Per-Pedal Loudness Audit Through Real IR (`01_BlackWizard_Center.wav`)
Rendered each pedal at factory default knobs with Tube Amp mode (`slider54=1`) directly in live REAPER JSFX, then convolved offline in Python with `01_BlackWizard_Center.wav` (no trims applied, report only):

| Pedal | Voicing | Raw Peak | Raw LUFS | IR LUFS | Delta vs MT-2 | Knee Margin | Limiter Status |
|---|---|---|---|---|---|---|---|
| **RAT** | Cold Lead | −8.79 dBFS | −18.71 LUFS | **+0.09 LUFS** | +2.88 dB | 5.70 dB | Clean |
| **DS-1** | Raw 4-Track | −6.01 dBFS | −20.27 LUFS | **−4.08 LUFS** | −1.30 dB | 2.91 dB | Clean |
| **Metal Zone** | Tight Rhythm | −8.75 dBFS | −21.13 LUFS | **−2.79 LUFS** | 0.00 dB | 5.65 dB | Clean |
| **HM-2** | Chainsaw | −11.86 dBFS | −18.70 LUFS | **−0.59 LUFS** | +2.20 dB | 8.76 dB | Clean |

#### Findings for Devin:
1. **DS-1 Relative Level:** Without the removed `ir_ped_g` trim (+3.1 dB on DS-1), the DS-1 sits at **−4.08 LUFS** through the BlackWizard IR. It is **4.17 dB quieter than the RAT** (+0.09 LUFS) and **3.49 dB quieter than the HM-2** (−0.59 LUFS).
2. **Headroom:** All raw pedal peaks remain well below the −3.10 dBFS safety limiter knee (highest raw peak is DS-1 at −6.01 dBFS, leaving 2.91 dB margin). The safety limiter never engages.
3. **Action:** Per instructions, **nothing was changed or recalibrated**. The findings are reported for Devin to decide whether to adjust pedal default Level knobs or let the external IR loader (Ugritone TRVE Cab) handle level balancing.

---

### 5. UI Status
- **UI not visually verified** (no fresh REAPER FX-window capture taken in this session).
