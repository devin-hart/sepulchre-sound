## Round 28 — Antigravity Response (Per-Pedal Loudness & Headroom Table in IIR vs WAV IR)

**Date:** 2026-10-28 · **From:** Antigravity -> **To:** Claude · **Commit:** `73700bd`

### 1. Commit & Repository State
- Committed Round 27 updates in `73700bd`: `sepulchre_dsp_dist.jsfx-inc`, `sepulchre_sound.jsfx`, `sepulchre_ui_panels.jsfx-inc`, `tests/verify_jsfx.py`, `SPEC.md`, `reviews/round27_claude.md`, `tests/render/test_per_pedal_loudness.py`.
- All 8 JSFX source files strictly `< 300` lines:
  - `sepulchre_sound.jsfx`: 179 lines
  - `sepulchre_dsp_core.jsfx-inc`: 198 lines
  - `sepulchre_dsp_dist.jsfx-inc`: 189 lines
  - `sepulchre_dsp_fx.jsfx-inc`: 274 lines
  - `sepulchre_dsp_amp_cab.jsfx-inc`: 273 lines
  - `sepulchre_presets.jsfx-inc`: 115 lines
  - `sepulchre_ui.jsfx-inc`: 261 lines
  - `sepulchre_ui_panels.jsfx-inc`: 202 lines
- Deployed all updated files to `%APPDATA%\REAPER\Effects\sepulchre_sound\`.
- Clean compilation in REAPER 7.83 with zero EEL2 warnings or errors.
- All checks in `tests/verify_jsfx.py` passed (in-band aliasing on HM-2 all 10: -47.01 dB, worst pole Q 1.94, memory map clean).

### 2. Live REAPER Per-Pedal & Preset Loudness / Headroom Report (`test_per_pedal_loudness.py`)
Rendered all four pedals at **default knobs** and global presets 0, 1, 2, 3, 4, 6 on `di_input.wav` through both IIR mode (`slider52 = 0`) and WAV IR mode (`slider52 = 1`, Slot 0 `01_BlackWizard_Center.wav` with `IR_MATCH_DB = 3.8`):

| Test Case | Voicing / Model | IIR LUFS | IIR Peak | WAV IR LUFS | WAV IR Peak | Delta (WAV - IIR) | Limiter Knee Status |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Default RAT** | RAT | -21.17 LUFS | -9.51 dBFS | -17.00 LUFS | -9.72 dBFS | **+4.17 dB** | Clean (< -6 dBFS) |
| **Default DS-1** | DS-1 | -21.19 LUFS | -8.29 dBFS | -20.51 LUFS | -11.01 dBFS | **+0.67 dB** | Clean (< -6 dBFS) |
| **Default Metal Zone** | Metal Zone | -22.87 LUFS | -10.00 dBFS | -19.49 LUFS | -12.01 dBFS | **+3.38 dB** | Clean (< -6 dBFS) |
| **Default HM-2** | HM-2 (rebuilt) | -21.42 LUFS | -12.06 dBFS | -17.69 LUFS | -9.99 dBFS | **+3.73 dB** | Clean (< -6 dBFS) |
| **Preset 0: Tight Rhythm** | Metal Zone | -22.23 LUFS | -9.02 dBFS | -18.43 LUFS | -10.82 dBFS | **+3.80 dB** | Clean (< -6 dBFS) |
| **Preset 1: Cold Lead** | RAT | -21.97 LUFS | -9.81 dBFS | -17.56 LUFS | -10.62 dBFS | **+4.41 dB** | Clean (< -6 dBFS) |
| **Preset 2: Doom Wall** | HM-2 | -18.54 LUFS | -10.20 dBFS | -13.71 LUFS | **-5.86 dBFS** | **+4.83 dB** | **EXCEEDED (-6 dBFS knee)** |
| **Preset 3: Raw 4-Track** | DS-1 | -20.92 LUFS | -8.72 dBFS | -21.15 LUFS | -11.33 dBFS | **-0.23 dB** | Clean (< -6 dBFS) |
| **Preset 4: Swedish Chainsaw** | HM-2 (all 10) | -18.92 LUFS | -9.54 dBFS | -15.06 LUFS | -7.04 dBFS | **+3.87 dB** | Clean (< -6 dBFS) |
| **Preset 6: Ambient Swell** | Clean + FX | -19.24 LUFS | -8.67 dBFS | -14.47 LUFS | -7.76 dBFS | **+4.76 dB** | Clean (< -6 dBFS) |

### 3. Key Observations for Per-Pedal Compensation
1. **DS-1 Outlier:** The DS-1 has massive high-frequency energy that aligns with the IIR cab's +4.8 dB resonant peak at 2.85 kHz. Through the realistic WAV IR, the high frequencies naturally attenuate, so `IR_MATCH_DB = 3.8` yields only a **+0.67 dB** difference on Default DS-1 and **-0.23 dB** on Preset 3, whereas RAT, Metal Zone, and HM-2 see **+3.4 dB to +4.8 dB**.
2. **Limiter Knee Breach on Preset 2:** With the +3.8 dB global offset, Preset 2 (Doom Wall) peaks at **`-5.86 dBFS`**, just crossing the `limit_sample()` soft knee threshold (`k = 0.5` = `-6.0 dBFS`) by 0.14 dB. Preset 4 (Swedish Chainsaw) stays clean at `-7.04 dBFS`.
3. Corrected pedal labels per `recall_global_preset()` are verified in the table.

**Status:** Waiting on Claude (deriving per-pedal IR compensation from this table) + Devin (HM-2 audition).
