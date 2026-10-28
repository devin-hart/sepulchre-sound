# AGENTS.md — Sepulchre Sound

## 1. Operating Rules
- **Tone & Output:** Dry, direct peer register. Answer first, short paragraphs (≤3 sentences), bold key terms, end every task with a report (what changed, what was verified and how, what is unverified).
- **Rigor:** Read before writing. Challenge flawed premises directly. Never claim "done" or "works" without running verification; state "not verified" if untested in host.
- **Clarification:** Ask 1–3 targeted questions with recommended options when requirements are ambiguous or conflicting. Do not guess.
- **Scope & File Size:** Implement only what is requested. Split files along clear modular boundaries before they exceed ~300 lines. Every `.jsfx-inc` file MUST begin with an `@init` section header so REAPER's EEL2 compiler registers its functions.
- **Thread Safety:** Never call `sync_all_DSP()` from `@gfx`. Set `ui_need_sync = 1` in `@gfx`/`@slider` and consume it exclusively in `@block`.
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
- **Deploy to REAPER Effects Folder (Windows):**
  ```powershell
  New-Item -ItemType Directory -Force -Path "$env:APPDATA\REAPER\Effects\sepulchre_sound" | Out-Null
  Copy-Item -Path "D:\VSTs\sepulchre_sound\sepulchre_*.jsfx*" -Destination "$env:APPDATA\REAPER\Effects\sepulchre_sound\" -Force
  ```

## 4. Code Map
- `AGENTS.md`: Operating rules, stack, deployment/test commands, and file index for coding agents and reviewers.
- `SPEC.md`: Full technical architecture, DSP equations/parameters, gain-staging spec, preset table, roadmap, and decision log.
- `REVIEW.md`: External architectural and DSP audit checklist (all 11 items resolved and verified).
- `sepulchre_sound.jsfx`: Main JSFX entry point, slider declarations (`slider1`..`slider60`), `@block` thread-safe coefficient sync & transport-start state reset, dynamic 4-slot routing dispatcher, and `@gfx` frame layout.
- `sepulchre_dsp_core.jsfx-inc`: Biquad IIR filter library, parameter smoothing, 4x oversampling (`bq_os_up`/`bq_os_dn`), Input/Gate with hysteresis & hold (Module 0), and Distortion with 10 Hz DC blocker (Module 1).
- `sepulchre_dsp_fx.jsfx-inc`: Fractional delay-line interpolator, RT60-calibrated mutual-prime comb/allpass primitives, Chorus with smoothed white-noise drift (Module 2), Delay with 4 sync divisions (Module 3), and Reverb with natural bypass spillover (Module 4).
- `sepulchre_dsp_amp_cab.jsfx-inc`: Amp Stage (Tube Head / Solid-State Combo + Bass/Mid/Treble/Presence tone stack), WAV IR FFT Convolution Loader (`file_riff` + `convolve_c`), IIR Cabinet fallback, and C1 Hermite `-1.0 dBFS` limiter (Module 5).
- `sepulchre_presets.jsfx-inc`: Routing permutation validator (`validate_routing`), 7 global presets calibrated to `-10`..`-7.5 dBFS`, and 4x3 per-module quick presets.
- `sepulchre_ui.jsfx-inc`: Dark industrial `@gfx` pedalboard UI, horizontal sliders (`ui_hslider` with `slider_automate()`, Shift-drag, mouse-wheel), Input/Output peak meters (`draw_level_meter`), and preset dropdown overlay with dirty `*` indicator.
- `tests/verify_jsfx.py`: Automated EEL2 parser, dynamic `alloc_buf` memory verifier, RT60 verifier, 4x oversampling aliasing test, DC offset test, preset peak calibration check, and routing fuzz suite.
