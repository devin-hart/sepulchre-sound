## Round 55 — Antigravity: Cab Sim Restored, PDC 128/0 Verified & Fast Batched Regression Parity

### 1. Codebase Restoration & Line Count Audit
- Reverted code back to Round 49 baseline per Claude / Devin instructions:
  - `sepulchre_dsp_amp.jsfx-inc` removed (`git rm`).
  - Restored `sepulchre_dsp_amp_cab.jsfx-inc` (256 lines).
  - Restored `tests/render/test_exact_ir_null.py`.
  - Restored sliders 49 (`Cabinet Enable`) and 53 (`IR Slot`) in `render_common.py`.
- Deployed files to `C:\Users\wizardbeard\AppData\Roaming\REAPER\Effects\sepulchre_sound\`.
- Recompiled in REAPER: **Zero compile or runtime errors**.
- Line counts verified across all 8 JSFX source files (all strictly $< 300$ lines):

| File | Lines | Limit | Status |
|---|---|---|---|
| `sepulchre_sound.jsfx` | 164 | 300 | PASS |
| `sepulchre_dsp_core.jsfx-inc` | 222 | 300 | PASS |
| `sepulchre_dsp_dist.jsfx-inc` | 198 | 300 | PASS |
| `sepulchre_dsp_fx.jsfx-inc` | 195 | 300 | PASS |
| `sepulchre_dsp_amp_cab.jsfx-inc` | 256 | 300 | PASS |
| `sepulchre_presets.jsfx-inc` | 110 | 300 | PASS |
| `sepulchre_ui.jsfx-inc` | 258 | 300 | PASS |
| `sepulchre_ui_panels.jsfx-inc` | 222 | 300 | PASS |

**Total codebase size:** 1,625 lines (identical to Round 49).

---

### 2. PDC Latency & FX Window Verification
- **PDC Latency:**
  - With Cabinet ON (`slider49=1`): reports **128 samples** (`pdc_delay = ir_chunk_size`).
  - With Cabinet OFF / Bypassed (`slider49=0`): reports **0 samples** (`pdc_delay = 0`).
- **FX Parameter / GUI Status:**
  - `slider49` (Cabinet Enable) and `slider53` (IR Slot 0..9) are restored and functional.
  - Column VII displays `VII CABINET` with IR slot selection, IR file name readout, and `WAV IR:ON/OFF` switch.

---

### 3. Full Regression Suite Results (Matching Round 49 Baselines)

1. **AST & Offline Checks ([verify_jsfx.py](file:///D:/VSTs/sepulchre_sound/tests/verify_jsfx.py)):**
   - 65 EEL2 buffers parsed; top=327,680 (0 overlaps).
   - All 6 distorted presets peak between −9.54 and −8.62 dBFS (DC $< 0.0003$).
   - Pre-cabinet aliasing: RAT −52.0 dB, DS-1 −44.5 dB, MT-2 −56.9 dB, HM-2 −47.0 dB.
   - Filter pole Q: worst pole Q = 2.62 (limit 3.5).
   - `IR_E48` file value matches computed: 0.283543.
   - High-gain saturation curve verified (−12 dBFS $\rightarrow$ −16.7 dB RMS, −36 dBFS $\rightarrow$ −21.4 dB RMS).
   - **Status: PASS (6/6 checks clean)**.

2. **Bit-Exact Python Mirror Nulls ([test_mirror_null.py](file:///D:/VSTs/sepulchre_sound/tests/render/test_mirror_null.py)):**
   - RAT: Signal Peak 0.2786 | Max Diff 7.10e-08 | Null Peak −131.88 dB | Null RMS −132.88 dB | **PASS**
   - DS-1: Signal Peak 0.4254 | Max Diff 7.10e-08 | Null Peak −135.56 dB | Null RMS −129.09 dB | **PASS**
   - Metal Zone: Signal Peak 0.2760 | Max Diff 7.10e-08 | Null Peak −131.80 dB | Null RMS −129.36 dB | **PASS**
   - HM-2: Signal Peak 0.3042 | Max Diff 7.10e-08 | Null Peak −132.65 dB | Null RMS −133.27 dB | **PASS**

3. **UPOLS Convolution Engine Null ([test_exact_ir_null.py](file:///D:/VSTs/sepulchre_sound/tests/render/test_exact_ir_null.py)):**
   - Peak Null: **−123.91 dB**, RMS Null: **−104.26 dB** vs Python FFT convolution.
   - Block boundary continuity (128-sample boundaries): Clean at 100 Hz (0.000275) and 2578 Hz (0.104795).
   - **Status: PASS**.

4. **GE-7 Graphic EQ Suite ([test_ge7_eq.py](file:///D:/VSTs/sepulchre_sound/tests/render/test_ge7_eq.py)):**
   - **Batch Optimization:** Batch-rendered all 14 band sweeps into a single REAPER render pass; test runtime slashed from ~55s to ~15s.
   - Flat Null: **−227.39 dB** peak null in both Pre-Pedal and Post-Pedal positions.
   - 14 Band Frequency & Gain Checks: All 7 bands hit within 0.11 dB of +15.0 dB target at exact center frequencies in both Pre and Post positions.
   - Toggle smoothness: Max sample jump = **0.0536** (clean, click-free).
   - **Status: PASS**.

5. **GE-7 Record EQ Presets Headroom ([test_eq_preset_headroom.py](file:///D:/VSTs/sepulchre_sound/tests/render/test_eq_preset_headroom.py)):**
   - All 7 presets (Bathory '84 through Evangelion '09) in both Amp Tube Head and Amp OFF modes remain within **$\pm 1.06$ dB** of baseline (within $\pm 1.1$ dB limit).
   - All peaks remain safely below −3.10 dBFS limiter knee (closest is Bathory '84 at −7.50 dBFS, 4.40 dB headroom).
   - **Status: PASS**.

6. **Per-Pedal Loudness & Headroom ([test_per_pedal_loudness.py](file:///D:/VSTs/sepulchre_sound/tests/render/test_per_pedal_loudness.py)):**
   - RAT: −17.80 LUFS | Peak −10.52 dBFS (Clean, 7.42 dB below knee)
   - DS-1: −17.41 LUFS | Peak −7.91 dBFS (Clean, 4.82 dB below knee)
   - Metal Zone: −19.49 LUFS | Peak −12.01 dBFS (Clean, 8.91 dB below knee)
   - HM-2: −18.29 LUFS | Peak −10.59 dBFS (Clean, 7.49 dB below knee)
   - Presets 0..6 peak from −11.13 to −5.79 dBFS (all clean).
   - **Status: PASS**.

---

### 4. UI Status
- **UI not visually verified** (no fresh REAPER FX-window capture taken in this session). Code inspection confirms `sepulchre_ui_panels.jsfx-inc` renders Column VII with `VII CABINET` header, IR Slot slider, IR name, and WAV IR toggle button.
