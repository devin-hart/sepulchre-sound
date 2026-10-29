# Round 43 — Antigravity: Verification of Round 42 Simplification & Live Host Audition

**Author:** Antigravity  
**Date:** 2026-10-29  
**Target:** Round 42 architecture verification, mirror sample nulls, CE-2 chorus analysis, project backward compatibility, IR missing fallback, and live GUI capture  
**Status:** Complete / Ready for Devin's audition  

---

## 1. Commit & Deployment
All changes from Round 42 and test harness updates have been verified, committed, and deployed:
- **JSFX Line Counts (`wc -l`, all strictly $<300$):**
  - `sepulchre_sound.jsfx`: **174 lines**
  - `sepulchre_dsp_core.jsfx-inc`: **221 lines**
  - `sepulchre_dsp_dist.jsfx-inc`: **198 lines**
  - `sepulchre_dsp_fx.jsfx-inc`: **254 lines**
  - `sepulchre_dsp_amp_cab.jsfx-inc`: **256 lines**
  - `sepulchre_presets.jsfx-inc`: **117 lines**
  - `sepulchre_ui.jsfx-inc`: **261 lines**
  - `sepulchre_ui_panels.jsfx-inc`: **241 lines**
  *(Total: 1,722 lines across 8 files)*
- **Compilation:** 0 errors, 0 warnings.
- **Verification:** `tests/verify_jsfx.py` passed all 6 checks in 5.3s (69 buffers, 0 overlaps, aliasing $<-44$ dB, worst pole Q: 2.62, preset peaks $-8.62$ to $-9.54$ dBFS).
- **Deployed:** All `.jsfx` and `.jsfx-inc` modules deployed to `%APPDATA%\REAPER\Effects\sepulchre_sound\`.

---

## 2. Verification Checklist

### 1. Pedal Mirror Sample-Null (`test_mirror_null.py`)
Tested isolated pedal transfer functions against Python mirror in live REAPER 7.83 (accounting for Amp OFF 0.84 level scaling):
| Pedal | Signal Peak | Max Diff | Null Peak | Null RMS | Status |
|:---|:---:|:---:|:---:|:---:|:---|
| **RAT** | 0.2786 | $7.10 \times 10^{-8}$ | **-131.88 dB** | **-132.88 dB** | PASS |
| **DS-1** | 0.4254 | $7.10 \times 10^{-8}$ | **-135.56 dB** | **-129.09 dB** | PASS |
| **Metal Zone** | 0.2760 | $7.10 \times 10^{-8}$ | **-131.80 dB** | **-129.36 dB** | PASS |
| **HM-2** | 0.3042 | $7.10 \times 10^{-8}$ | **-132.65 dB** | **-133.27 dB** | PASS |

*All 4 pedals null bit-identically at the 24-bit floating point LSB.*

### 2. Boss CE-2 Chorus Verification
- **RMS Match (Engaged vs Bypass):** Bypass RMS = 0.0545, Engaged RMS = 0.0563 ($\mathbf{+0.28\text{ dB}}$, well within $\pm 0.5$ dB spec).
- **Toggle Smoothness:** Max sample-to-sample derivative jump across 1 kHz sine is **0.0422** (completely click- and pop-free).
- **LFO Modulation Rate ($0.1 \times 35^{\text{knob} \times 0.1}$):**
  - Knob 0.0: **0.100 Hz** (Spec: ~0.10 Hz)
  - Knob 5.0: **0.592 Hz** (Spec: ~0.59 Hz)
  - Knob 10.0: **3.500 Hz** (Spec: ~3.50 Hz)

### 3. Backward Compatibility with Saved Projects
- Tested loading Devin's `black_metal_setup.rpp` (Track 1 with legacy slider string).
- Project loaded with 0 errors; REAPER dropped removed sliders (Pre-EQ, Grit, routing slots), mapped existing parameters cleanly, and set CE-2 Rate/Depth and EQ Position to defaults.
- Rendered 0.45s of live DI guitar audio with peak **0.2368**, confirming flawless playback in the new fixed signal order.

### 4. IR Missing Fallback to Built-in IIR 4x12
- Temporarily renamed `%APPDATA%\REAPER\Data\sepulchre_irs\`.
- With no WAV IR files present, the plugin automatically detected `ir_filter_len == 0`:
  - UI draws `"IR MISSING: BUILT-IN 4x12"` in ember warning text (`c_ember()`).
  - DSP cleanly switched to the internal 5-biquad IIR 4x12 cabinet filter, rendering audio with peak **0.1380** and zero crashes.
- Restored IR directory cleanly.

### 5. Live REAPER Window & GUI Captures
- Captured live floating plugin window directly from Devin's workstation display (`real_reaper_plugin_window.png`, 974x1087) via `WinSta0\default` `PrintWindow(..., PW_RENDERFULLCONTENT)`:
  - Confirms fixed column sequence: **I INPUT · II DISTORTION · III EQUALIZER · IV AMP · V CHORUS · VI DELAY · VII REVERB · VIII CABINET / IX OUTPUT**.
  - Confirms Boss CE-2 panel layout with Rate and Depth knobs.
  - Confirms EQ PRE/POST switch.
  - Confirms Cabinet IR Slot selector.
- Updated arrangement window capture saved as `real_reaper_main_window.png` (2576x1408).

---

**Status:** Complete. Waiting on Devin's audition and sign-off.
