# AGENTS.md — Sepulchre Sound

## 1. Operating Rules
- **Tone & Output:** Dry, direct peer register. Answer first, short paragraphs (≤3 sentences), bold key terms, end every task with a report (what changed, what was verified and how, what is unverified).
- **Rigor:** Read before writing. Challenge flawed premises directly. Never claim "done" or "works" without running verification; state "not verified" if untested in host.
- **Clarification:** Ask 1–3 targeted questions with recommended options when requirements are ambiguous or conflicting. Do not guess.
- **Scope & File Size:** Implement only what is requested. Split files along clear modular boundaries before they exceed ~300 lines. Every `.jsfx-inc` file MUST begin with an `@init` section header so REAPER's EEL2 compiler registers its functions.
- **Thread Safety:** Never call `sync_all_DSP()` or `load_ir_slot()` from `@block`/`@sample` improperly: `load_ir_slot()` (`file_open`/`file_riff`) must never run on `@block` (only `@init`, `@slider`, and `@gfx`), and `sync_all_DSP()` runs exclusively in `@block`/`@init`.
- **Inter-Agent Review Protocol:** Always read `REVIEW.md` from disk before writing, append only (`Append=true`), and write per-round standalone reports in `reviews/roundN_antigravity.md`.
- **Git & Docs:** Commit after each working step with a descriptive message (what changed and why). Keep `AGENTS.md` code map and `SPEC.md` roadmap/decisions log updated with every commit.

## 2. Tech Stack & Locations
- **Platform:** Cockos REAPER JSFX (EEL2 real-time DSP + `@gfx` UI language).
- **Source Repository:** `D:\VSTs\sepulchre_sound\`
- **REAPER Runtime Deployment Path:** `C:\Users\wizardbeard\AppData\Roaming\REAPER\Effects\sepulchre_sound\`
- **WAV Impulse Response Bank:** `C:\Users\wizardbeard\AppData\Roaming\REAPER\Data\sepulchre_irs\` (10 curated WAV impulses from `D:\GuitarPlugins`).
- **Verification Environment:** Python 3 dynamic EEL2 parser, memory-map verifier, and offline DSP simulation suite (`tests/verify_jsfx.py`).

## 3. Commands
- **Run Syntax, Memory & Offline DSP Verification:**
  ```powershell
  python D:\VSTs\sepulchre_sound\tests\verify_jsfx.py
  ```
- **Run Live REAPER CLI Batch Render Harness (`reaper.exe -newinst -nosplash -renderproject`):**
  ```powershell
  python D:\VSTs\sepulchre_sound\tests\render\run_reaper_render.py
  ```
- **Deploy to REAPER Effects Folder (Windows):**
  ```powershell
  New-Item -ItemType Directory -Force -Path "$env:APPDATA\REAPER\Effects\sepulchre_sound" | Out-Null
  Copy-Item -Path "D:\VSTs\sepulchre_sound\sepulchre_*.jsfx*", "D:\VSTs\sepulchre_sound\sepulchre_*.jpg", "D:\VSTs\sepulchre_sound\sepulchre_*.png" -Destination "$env:APPDATA\REAPER\Effects\sepulchre_sound\" -Force
  ```

## 4. Code Map
- `AGENTS.md`: Operating rules, stack, deployment/test commands, and file index for coding agents and reviewers.
- `SPEC.md`: Full technical architecture, DSP equations/parameters, gain-staging spec, preset table, roadmap, and decision log.
- `REVIEW.md` & `reviews/`: Inter-agent architectural, DSP, and UI audit log between Claude and Antigravity.
- `sepulchre_sound.jsfx` (160 lines): Main JSFX entry point, slider declarations (`slider1`..`slider60`, including `slider52` Cabinet Source Mode), `filename:0,sepulchre_bg.jpg` and `filename:1,sepulchre_titles.png` asset declarations, `@block` PDC reporting (`pdc_delay = ir_chunk_size`), `ir_reload_req` handler, coefficient sync & transport-start state reset, dynamic 4-slot routing dispatcher, and `@gfx 1204 500` frame entry.
- `sepulchre_dsp_core.jsfx-inc` (299 lines): Biquad IIR filter library, parameter smoothing, 4x oversampling with cascaded 8th-order Butterworth (`48 dB/oct` @ `16.5 kHz`) filters and `C^2`-smooth 2-stage saturation (`-48.39 dB` in-band `20 Hz–8 kHz` and `-47.76 dB` all-bin pre-cabinet aliasing), Input/Gate with hysteresis & hold (Module 0), and Distortion with 10 Hz DC blocker (Module 1).
- `sepulchre_dsp_fx.jsfx-inc` (274 lines): Fractional delay-line interpolator, RT60-calibrated mutual-prime comb/allpass primitives, Chorus with smoothed white-noise drift (Module 2), Delay with 4 sync divisions and bypassed self-oscillation decay clamp (`!en ? fb = min(fb, 0.75)`) (Module 3), and Reverb with natural bypass spillover (Module 4).
- `sepulchre_dsp_amp_cab.jsfx-inc` (215 lines): Amp Stage (Tube Head / Solid-State Combo + 10 Hz post-amp DC blocker + Bass/Mid/Treble/Presence tone stack), WAV IR FFT Convolution Loader (`slider52` mode toggle + `slider53` 0-based WAV index `#0..#9`), IIR Cabinet mode, and C1 Hermite `-1.0 dBFS` limiter (Module 5).
- `sepulchre_presets.jsfx-inc` (115 lines): Routing permutation validator (`validate_routing`), WAV IR name table (`get_ir_slot_name`), and 7 global presets calibrated strictly to `[-10.0, -8.0] dBFS` (high-gain presets 0–4).
- `sepulchre_ui.jsfx-inc` (250 lines): "Crypt" necro-monochrome theme (`#090909` void, `#E8E3D7` bone, `#A39E94` labels, `#841216` blood, `#B01C22` ember LEDs), resolution-independent scaling (`ui_begin` / `ui_S`, `gfx_ext_retina = 1`), image/sprite loaders (`ui_load_images`, `ui_draw_background`, `ui_title`), `auto_slider` automation helper, and live widgets (`ui_seg`, `ui_toggle`, `ui_power_led`, bipolar dB `ui_hslider`, `ui_meter` with gate threshold marker & `-10..-8 dBFS` target band, `ui_led`, preset dropdown).
- `sepulchre_ui_panels.jsfx-inc` (176 lines): Crypt 8-stage stone-slab layout (`I INPUT` → `II..V` swappable slots with hover `<`/`>` move arrows → `VI AMP` → `VII CABINET` / `VIII OUTPUT`), `lay_begin`/`lay` vertical column distributor, 28% alpha bypass dimming, and live oversampling/PDC header (`ui_header`).
- `sepulchre_bg.jpg` & `sepulchre_titles.png`: Baked `2408×1000` (2x Retina) Crypt stone-slab + black-metal logo background and 2x Cinzel stage title / Roman numeral (`I..VIII`) sprite sheet.
- `tests/verify_jsfx.py` & `tests/render/run_reaper_render.py`: Automated EEL2 parser, `<300` line enforcer, asset verifier, dynamic `alloc_buf` memory verifier, AST invariant checks, sample-by-sample comb+allpass RT60 impulse test, pre-cabinet 4x oversampling aliasing test, and live REAPER 7.83 CLI batch render harness (`reaper.exe -newinst -nosplash -renderproject`).
