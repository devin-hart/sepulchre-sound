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
- `sepulchre_sound.jsfx` (169 lines): Main JSFX entry point, slider declarations (`slider1`..`slider60`, including `slider52` Cabinet Source Mode), `filename:0,sepulchre_bg.jpg` and `filename:1,sepulchre_titles.png` asset declarations, `@block` PDC reporting (`pdc_delay = ir_chunk_size`), `ir_reload_req` handler, coefficient sync & transport-start state reset, dynamic 4-slot routing dispatcher, and `@gfx 1204 500` frame entry.
- `sepulchre_dsp_core.jsfx-inc` (222 lines): Biquad IIR filter library, `soft_tanh` / C1 Hermite limiter, parameter smoothing, all core `alloc_buf` biquads (incl. distortion and 8x oversampling filters), Input/Gate with hysteresis & hold (Module 0), the GE-7 7-band graphic EQ (Module 4, `proc_eq`), and the Pre-EQ (sliders 13–15, Input column) applied before every pedal.
- `sepulchre_dsp_dist.jsfx-inc` (198 lines): Distortion (Module 1) — four pedal models (RAT, DS-1, Metal Zone, HM-2), each with only its real knobs (0..10, dedicated sliders), nonlinear stages at 8x oversampling via per-channel `instance()` functions (`pdL.*` / `pdR.*`), base-rate tone stacks, DC blocker, pedal Level, and full-close post-gate. Signal units 1.0 = 1 V. No lowpass in front of the clippers beyond what the real circuit has. Gyrator EQs use `gyro_peak()` (constant Q); `tests/verify_jsfx.py` fails any pedal filter with pole Q > 3.5.
- `sepulchre_dsp_fx.jsfx-inc` (195 lines): Fractional delay-line interpolator, RT60-calibrated mutual-prime comb/allpass primitives, Chorus with smoothed white-noise drift (Module 2), Delay with 4 sync divisions and bypassed self-oscillation decay clamp (`!en ? fb = min(fb, 0.75)`) (Module 3), and Reverb with natural bypass spillover (Module 4).
- `sepulchre_dsp_amp_cab.jsfx-inc` (256 lines): Lo-Fi Grit (slider 16, Output column: sample-hold + quantize after the cab), Amp Stage (Tube Head / Solid-State Combo + 10 Hz post-amp DC blocker + Bass/Mid/Treble/Presence tone stack), WAV IR loader + 128-sample uniformly partitioned (UPOLS) convolution (`slider52` mode, `slider53` slot 0..9, loudness-matched per slot and per pedal), IIR Cabinet mode, and C1 cubic-knee `-1.0 dBFS` limiter, linear below `-3.1 dBFS` (Module 5).
- `sepulchre_presets.jsfx-inc` (155 lines): Routing permutation validator (`validate_routing`), WAV IR name table (`get_ir_slot_name`), and 7 global presets calibrated strictly to `[-10.0, -8.0] dBFS` (high-gain presets 0–4).
- `sepulchre_ui.jsfx-inc` (263 lines): "Crypt" necro-monochrome theme (`#090909` void, `#E8E3D7` bone, `#A39E94` labels, `#841216` blood, `#B01C22` ember LEDs), resolution-independent scaling (`ui_begin` / `ui_S`, `gfx_ext_retina = 1`), image/sprite loaders (`ui_load_images`, `ui_draw_background`, `ui_title`), `auto_slider` automation helper, and live widgets (`ui_seg`, `ui_toggle`, `ui_power_led`, bipolar dB `ui_hslider`, `ui_meter` with gate threshold marker & `-10..-8 dBFS` target band, `ui_led`, preset dropdown).
- `sepulchre_ui_panels.jsfx-inc` (216 lines): Crypt 8-stage stone-slab layout (`I INPUT` → `II..V` swappable slots with hover `<`/`>` move arrows → `VI AMP` → `VII CABINET` / `VIII OUTPUT`), `lay_begin`/`lay` vertical column distributor, 28% alpha bypass dimming, and live oversampling/PDC header (`ui_header`).
- `sepulchre_bg.jpg` & `sepulchre_titles.png`: Baked `2408×1000` (2x Retina) Crypt stone-slab + black-metal logo background and 2x Cinzel stage title / Roman numeral (`I..VIII`) sprite sheet.
- `tests/verify_jsfx.py` & `tests/render/run_reaper_render.py`: Automated EEL2 parser, high-gain saturation-curve guard (`check_distortion_gain_curve`), `<300` line enforcer, asset verifier, dynamic `alloc_buf` memory verifier, AST invariant checks, Python DSP mirror (preset levels, per-pedal aliasing, filter pole-Q, IR loudness constant), and live REAPER 7.83 CLI batch render harness (`reaper.exe -newinst -nosplash -renderproject`).

> **Round 42 (Claude):** the plugin is now a fixed chain (see SPEC "Round 42 architecture"). Routing slots, Input Pre-EQ, Lo-Fi Grit and the IIR cab mode were removed; chorus is a Boss CE-2 model. Older file descriptions above that mention them are historical.
> **Round 43 (Claude):** delay removed; UI back to 7 columns at 1204×500.
> **Round 56 (Claude):** 10-preset black metal bank (loudness-matched, K-weighted −21 dB via the mirror), `eq_preset_vals` / `gp_eq` in presets, defaults = preset 01 (check [7/7]), preset < > buttons, INPUT target zone, `@serialize` for the edited marks, carved headstone logo baked into `sepulchre_bg.jpg` (generator: Cinzel 700, V-cut height-field shading).
> **Round 54 (Claude):** cab sim restored: code is byte-identical to Round 49 (`sepulchre_dsp_amp_cab.jsfx-inc`, sliders 49 / 53, PDC 128 when the cab is on). The Round 52 note below is historical.
> **Round 52 (Claude, reverted):** cab sim removed (no IRs, no PDC; `sepulchre_dsp_amp.jsfx-inc` replaces `sepulchre_dsp_amp_cab.jsfx-inc`; sliders 49 and 53 gone). The Round 50 TS-808 never shipped. Descriptions above that mention WAV IR / IIR cab / PDC are historical.
