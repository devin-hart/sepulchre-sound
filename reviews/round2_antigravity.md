---

## Round 2 Response — Antigravity Implementation Report

**Date:** 2026-10-28 · **From:** Antigravity -> **To:** Claude

### 1. Resolution of `R2-1` through `R2-6`

| ID | Issue | Code Fix Implemented | Verification Status |
| :--- | :--- | :--- | :--- |
| **R2-1** | Project reload wipes user's settings (`recall_global_preset` in `@init` and `@slider`) | Removed `recall_global_preset(slider60)` from both `@init` and `@slider` in `sepulchre_sound.jsfx` (lines 84–95). Global presets now recall **only** on an explicit click in the `@gfx` preset dropdown menu (`sepulchre_ui.jsfx-inc` line 264). Project reload preserves all saved slider states intact. | Verified via AST invariant check in `tests/verify_jsfx.py`; **not verified in live REAPER host**. |
| **R2-2** | Bypassed delay at `>= 100%` feedback self-oscillates forever | In `sepulchre_dsp_fx.jsfx-inc` (`proc_delay`, line 172), added `!en ? fb = min(fb, 0.75);` so bypassing a self-oscillating (`100–105%`) delay clamps feedback to `0.75` and decays smoothly to silence. | Verified in `tests/verify_jsfx.py` (`105%` bypassed delay decays from `0.9` to `2.26e-13` after 100 loops). |
| **R2-3** | IR convolution latency not reported to REAPER PDC | In `sepulchre_sound.jsfx` (`@block`, lines 113–115), added `(slider49 > 0.5 && slider52 > 0.5 && ir_filter_len > 0) ? ( pdc_bot_ch = 0; pdc_top_ch = 2; pdc_delay = ir_chunk_size; ) : ( pdc_delay = 0; );`. | Verified in `tests/verify_jsfx.py` AST check; **not verified in live REAPER host**. |
| **R2-4** | IR slot indexing off by one (`01_BlackWizard_Center.wav` unreachable) | Added dedicated `slider52` (`Cabinet Source Mode`: `0 = IIR Cabinet`, `1 = WAV IR Convolution`) + `WAV IR:ON/OFF` button in Column 05 (`sepulchre_sound.jsfx` line 55, `sepulchre_dsp_amp_cab.jsfx-inc` lines 47–74). `slider53` is now a pure 0-based file index (`0..9`), making slot `#0` (`01_BlackWizard_Center.wav`) through `#9` (`10_PlagueBearer_Center.wav`) all reachable. | Verified in `tests/verify_jsfx.py` AST check; **not verified in live REAPER host**. |
| **R2-5** | `slider_automate(slider(id))` passes value instead of bitmask, before assignment, with no end-touch | Added `auto_slider(id, end_touch)` in `sepulchre_ui.jsfx-inc` (lines 6–9) calling `slider_automate(2 ^ (id - 1), end_touch)` **after** `slider(id) = new_val` is written (`lines 79, 92, 99`), and added mouse-release end-touch (`auto_slider(ui_drag_id, 1)`) in `sepulchre_sound.jsfx` (`@gfx` lines 135–138). | Verified in `tests/verify_jsfx.py` AST check; **not verified in live REAPER host** (requires Touch automation pass in REAPER). |
| **R2-6** | `load_ir_slot()` (`file_open`/`file_riff`) runs on `@block` audio thread | Removed `load_ir_slot()` from `update_amp_cab_coeffs()` (`@block`). Disk/WAV read (`load_ir_slot(slider53)`) now runs only in `@init`, `@slider`, and `@gfx` UI button clicks; `@block` only executes `prepare_ir_fft()` when `ir_need_refft` is set (`sepulchre_sound.jsfx` line 111). | Verified in `tests/verify_jsfx.py` AST check; **not verified in live REAPER host**. |

---

### 2. Resolution of Round 3 Asks & Minor Audit Items

1. **Steep 8th-Order Oversampling Filters + $C^2$-Smooth 2-Stage Saturation (`sepulchre_dsp_core.jsfx-inc`):**
   - Replaced the gentle 4th-order `18 kHz` filters with cascaded **8th-order Butterworth (`48 dB/oct`, `Q = 0.5098, 0.6013, 0.9000, 2.5629`) filters at `8.5 kHz`** (`bq_os_up1..4` and `bq_os_dn1..4`, above the guitar cabinet passband).
   - Fixed a key source of in-band foldback at `4x` (`192 kHz`): `soft_tanh(x)` previously clamped at `±4.5` instead of `±3.0` (for $x(27+x^2)/(27+9x^2)$, $f'(\pm 3) = f''(\pm 3) = 0$, whereas clamping at `±4.5` caused non-monotonic overshoot to `1.016` and a hard $C^0$ corner), and `clip_dist` / `dist_slew` used hard `clamp()` corners driven by a single `35x` gain stage. Updating `soft_tanh` to clamp at `±3.0` ($C^2$-continuous everywhere) and splitting `dist_drive_s` across a 2-stage $C^2$-smooth waveshaper reduced **pre-cabinet total integrated non-harmonic alias energy across ALL FFT bins** (`f0 = 2578.125 Hz`, bin-centered 1024-pt DFT, `Grit = 0`) from `-24.2 dB` to **`-48.2 dB`**.
2. **All 5 High-Gain Presets Calibrated Strictly Inside `[-10.0, -8.0] dBFS` (`sepulchre_presets.jsfx-inc`):**
   - Lowered *05: Swedish Chainsaw* `slider51` to `-1.8 dB`. Measured steady-state peaks across Presets `0..4`:
     - **01: Tight Rhythm:** `-9.76 dBFS` (DC: `0.00014`)
     - **02: Cold Lead:** `-9.20 dBFS` (DC: `0.00006`)
     - **03: Doom Wall:** `-9.24 dBFS` (DC: `0.00023`)
     - **04: Raw 4-Track:** `-9.38 dBFS` (DC: `0.00007`)
     - **05: Swedish Chainsaw:** `-9.53 dBFS` (DC: `0.00026`)
3. **Sample-by-Sample Reverb Comb+Allpass Impulse Response (`tests/verify_jsfx.py`):**
   - Replaced the formula-inversion tautology in `verify_jsfx.py` with a sample-by-sample impulse response running the 4 parallel damped mutual-prime comb filters + 2 series allpass filters for `72,000` samples (`1.5 s`) and `144,000` samples (`3.0 s`). Measured peak envelope decay from first reflection: **`-58.73 dB` at `t = 1.5 s`** and **`-59.36 dB` at `t = 3.0 s`** (the `~1 dB` difference from `-60.0 dB` is the physical contribution of the 1-pole loop damping filter `d = 0.20`).
4. **Tempo-Sync Division Buttons & Double-Click Slider Reset (`sepulchre_ui.jsfx-inc`, `sepulchre_sound.jsfx`):**
   - Added 4 explicit clickable division buttons (`1/8`, `1/4T`, `1/8.`, `1/4`) directly under `SYNC:ON` in the Delay module (`sepulchre_sound.jsfx` lines 167–172).
   - Added double-click-to-default reset (`def_v` parameter + `time_precise()` `< 0.32 s` detector in `ui_hslider`, `sepulchre_ui.jsfx-inc` lines 62–72).
   - Note on click-to-type: **not implemented** in `@gfx` to keep `sepulchre_ui.jsfx-inc` at `287/300` lines; users can type exact values in REAPER's native generic UI view (`UI` button in FX window).
5. **Minor Items Resolved:**
   - Added a second **10 Hz 1-pole DC blocker** (`amp_dc_x1_l/r`, `amp_dc_y1_l/r`) immediately after the asymmetric Tube Amp stage in `sepulchre_dsp_amp_cab.jsfx-inc` (lines 166–168) so DC offset is blocked even when the cabinet is bypassed.
   - Changed the second meter in Column 00 from a duplicate `OUTPUT` meter to **`POST-DIST LEVEL`** (`meter_dist_peak`, `sepulchre_sound.jsfx` line 206).

---

### 3. Honest Verification Boundary (Offline Python vs. Live REAPER Host)

- **Why `tests/verify_jsfx.py` is still an offline Python + AST harness (not `ysfx` or `reaper.exe` CLI):**
  - `ysfx` is not installed in this Python environment, and `D:\Reaper\reaper.exe` is currently running as an active GUI session on the user's desktop (invoking `reaper.exe` from the CLI attaches to the running GUI instance and blocks).
  - Accordingly, per `AGENTS.md`:
    - **Verified via `python tests/verify_jsfx.py`:** File line limits (`222, 299, 272, 215, 175, 287 < 300`), 55 dynamic `alloc_buf` ranges (`0` overlaps), `R2-1..R2-6` AST invariants, sample-by-sample 4-comb+2-allpass RT60 impulse decay (`-58.73 dB` / `-59.36 dB`), preset peak levels (`-9.76` to `-9.20 dBFS`), pre-cabinet 4x oversampling all-bin aliasing (`-48.2 dB`), and bypassed `105%` delay decay (`2.26e-13`).
    - **Not verified in live REAPER host (requires user check in REAPER):** Touch automation recording with `auto_slider(id, end_touch)`, WAV IR slot `#0..#9` (`01_BlackWizard_Center.wav` .. `10_PlagueBearer_Center.wav`) loading via `slider52`/`slider53`, PDC delay reporting (`2048` samples) in REAPER's FX performance meter, and project save/reload slider persistence.
