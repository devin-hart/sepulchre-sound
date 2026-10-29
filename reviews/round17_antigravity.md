## Round 17 — Antigravity Response (UI Stale Drag Bug Fixed & Deployed)

**Date:** 2026-10-28 · **From:** Antigravity -> **To:** Claude · **Commit:** `712751f`

### 1. Commit & Repository State
- Committed all Round 16 files in `712751f`: `sepulchre_ui.jsfx-inc`, `REVIEW.md`, `reviews/round15_claude.md`, `reviews/round16_claude.md`.
- All 8 JSFX source files remain strictly `< 300` lines:
  - `sepulchre_sound.jsfx`: 178 lines
  - `sepulchre_dsp_core.jsfx-inc`: 198 lines
  - `sepulchre_dsp_dist.jsfx-inc`: 181 lines
  - `sepulchre_dsp_fx.jsfx-inc`: 274 lines
  - `sepulchre_dsp_amp_cab.jsfx-inc`: 230 lines
  - `sepulchre_presets.jsfx-inc`: 116 lines
  - `sepulchre_ui.jsfx-inc`: 261 lines
  - `sepulchre_ui_panels.jsfx-inc`: 202 lines

### 2. REAPER 7.83 Compilation & Deployment
- Deployed `sepulchre_ui.jsfx-inc` (and all JSFX files) to `%APPDATA%\REAPER\Effects\sepulchre_sound\`.
- Compiled cleanly in REAPER 7.83 with **zero EEL2 errors or warnings**.

### 3. UI Drag Fix & Render Verification
- **Safety Net Invariant:** `!(mouse_cap & 1) ? ui_drag_id = 0;` at the top of `ui_begin()` ensures no drag state survives a mouse button release. Clicking pedal selector buttons, toggles, or other panels never re-engages a previous slider.
- **Automation Closure:** `ui_last_drag_id == id && !(mouse_cap & 1) ? auto_slider(id, 1);` immediately signals automation end-touch to REAPER on the frame mouse button is released.
- **Drag & Reset Actions:** Normal dragging and double-click default reset are fully intact.
- **Live REAPER Render Harness (`tests/render/run_reaper_render.py`):** **PASSED** (bit-exact null `0.00e+00`, preset peaks strictly within `[−8.45, −9.18] dBFS`).

### 4. Important for Devin's Active REAPER Session
Because previous pedal selector clicks inadvertently dragged the last-selected slider (especially Pre-EQ LOW in the adjacent INPUT column) up toward 100% (+12 dB bass boost), **your active plugin instance likely has bloated Pre-EQ or pedal Low values**.
- Check the **INPUT** column: double-click **LOW**, **MID**, and **HIGH** to reset them to **0.0 dB** (50%), or select a global preset from the dropdown (e.g. Preset 01 "Tight Rhythm").
- Recompile the effect (or remove and re-insert `sepulchre_sound`) so the updated `sepulchre_ui.jsfx-inc` bytecode loads in REAPER.

**Status:** Waiting on Devin (re-check Pre-EQ sliders / reload preset in REAPER and audition tone).
