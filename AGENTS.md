# AGENTS.md — Sepulchre Sound

## 1. Operating Rules
- **Tone & Output:** Dry, direct peer register. Answer first, short paragraphs (≤3 sentences), bold key terms, end every task with a report (what changed, what was verified and how, what is unverified).
- **Rigor:** Read before writing. Challenge flawed premises directly. Never claim "done" or "works" without running verification; state "not verified" if untested in host.
- **Clarification:** Ask 1–3 targeted questions with recommended options when requirements are ambiguous or conflicting. Do not guess.
- **Scope & File Size:** Implement only what is requested. Split files along clear modular boundaries before they exceed ~300 lines. Every `.jsfx-inc` file MUST begin with an `@init` section header so REAPER's EEL2 compiler registers its functions.
- **Git & Docs:** Commit after each working step with a descriptive message (what changed and why). Keep `AGENTS.md` code map and `SPEC.md` roadmap/decisions log updated with every commit.

## 2. Tech Stack & Locations
- **Platform:** Cockos REAPER JSFX (EEL2 real-time DSP + `@gfx` UI language).
- **Source Repository:** `D:\VSTs\sepulchre_sound\`
- **REAPER Runtime Deployment Path:** `C:\Users\wizardbeard\AppData\Roaming\REAPER\Effects\sepulchre_sound\`
- **Verification Environment:** Python 3 static EEL2 syntax, line-count, memory-layout, and numerical DSP response verifier (`tests/verify_jsfx.py`).

## 3. Commands
- **Run Syntax & DSP Verification:**
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
- `sepulchre_sound.jsfx`: Main JSFX entry point, 39 hidden DAW-automatable slider definitions, dynamic 4-slot routing dispatcher, and `@gfx` frame layout.
- `sepulchre_dsp_core.jsfx-inc`: Biquad IIR filter library, memory allocator, Input/Gate (Module 0), Distortion (Module 1), and gain-compensated Cabinet/Master limiter (Module 5).
- `sepulchre_dsp_fx.jsfx-inc`: Delay-line interpolator, comb/allpass primitives, Chorus (Module 2), Delay (Module 3), and Schroeder-Moorer Reverb (Module 4).
- `sepulchre_presets.jsfx-inc`: 7 global presets (*Tight Rhythm*, *Cold Lead*, *Doom Wall*, *Raw 4-Track*, *Swedish Chainsaw*, *Freezing Clean*, *Ambient Swell*) and 4x3 per-module quick presets.
- `sepulchre_ui.jsfx-inc`: Dark industrial `@gfx` pedalboard UI (`#111113` background, `#1A1A1E` chassis, `#A82028` crimson accents), horizontal sliders, click toggles, routing swap buttons, and top preset dropdown overlay.
- `tests/verify_jsfx.py`: Automated EEL2 syntax, `<300` line limit, `@init` header check, memory-map non-overlap, and filter/feedback stability test suite.
