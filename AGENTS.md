# AGENTS.md — Sepulchre Sound

## 1. Operating Rules
- **Tone & Output:** Dry, direct peer register. Answer first, short paragraphs (≤3 sentences), bold key terms, end every task with a report (what changed, what was verified and how, what is unverified).
- **Rigor:** Read before writing. Challenge flawed premises directly. Never claim "done" or "works" without running verification; state "not verified" if untested in host.
- **Clarification:** Ask 1–3 targeted questions with recommended options when requirements are ambiguous or conflicting. Do not guess.
- **Scope & File Size:** Implement only what is requested. Split files along clear modular boundaries before they exceed ~300 lines.
- **Git & Docs:** Commit after each working step with a descriptive message (what changed and why). Keep `AGENTS.md` code map and `SPEC.md` roadmap/decisions log updated with every commit.

## 2. Tech Stack
- **Platform:** Cockos REAPER JSFX (EEL2 language)
- **Architecture:** Main entry script (`sepulchre_sound.jsfx`) importing modular DSP and UI headers (`.jsfx-inc`).
- **Verification Environment:** Python 3 / Node.js static syntax, memory-layout, and EEL2 DSP simulation suite (`tests/verify_jsfx.py`).

## 3. Commands
- **Run Syntax & DSP Verification:** `python tests/verify_jsfx.py`
- **Deploy to REAPER Effects folder (Windows):** `Copy-Item -Path "sepulchre_*.jsfx*" -Destination "$env:APPDATA\REAPER\Effects\" -Force`

## 4. Code Map
- `AGENTS.md`: Project rules, tech stack, verification commands, and file index.
- `SPEC.md`: Project specification, architecture, implementation roadmap, and decision log.
- `sepulchre_sound.jsfx`: Main JSFX entry point, slider declarations, routing matrix, and section dispatch (`@init`, `@slider`, `@block`, `@sample`, `@gfx`).
- `sepulchre_dsp_core.jsfx-inc`: Biquad filters, parameter smoothing, memory allocation helpers, Input/Gate (Module 0), Dirt/Distortion (Module 1), and Cabinet/Master (Module 5).
- `sepulchre_dsp_fx.jsfx-inc`: Buffer-based time/modulation effects: Frost Chorus (Module 2), Echo Delay (Module 3), and Cavern Reverb (Module 4).
- `sepulchre_presets.jsfx-inc`: Global preset templates (*Human Worms*, *Transylvanian Frost*, *Crypt Drone*) and local 3-preset module quick toggles.
- `sepulchre_ui.jsfx-inc`: `@gfx` dark industrial custom pedalboard UI (`#111113` background, `#1A1A1E` chassis, horizontal sliders, click toggles, block swap headers).
- `tests/verify_jsfx.py`: Automated EEL2 syntax, memory overlap, balanced-block, and numerical DSP response verifier.
