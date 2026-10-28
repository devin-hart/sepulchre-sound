# SPEC.md — Sepulchre Sound

## 1. Goal
Build **Sepulchre Sound**, a native Cockos REAPER JSFX multi-effect pedalboard plugin tailored for raw black metal guitar tracking, featuring authentic underground analog/lo-fi character, high pick articulation, dynamic block routing, and a dark industrial UI with strictly horizontal sliders and click toggles.

## 2. Technical Specifications
- **Format:** Native REAPER JSFX (`sepulchre_sound.jsfx` + modular `.jsfx-inc` includes, each kept under ~300 lines).
- **Signal Flow:** Stereo/mono processing with swappable middle blocks (`[Block A] <-> [Block B] <-> [Block C] <-> [Block D]`):
  `Input/Gate -> [Slot 1] -> [Slot 2] -> [Slot 3] -> [Slot 4] -> Cab Sim -> Master Output`
- **DSP Modules:**
  - **Module 0 (Input & Gate):** Input Trim (-12 to +18 dB), Pre-Cut 12 dB/oct HPF (40–180 Hz, default 105 Hz), Noise Gate (-80 to -30 dB, hard clamp, smooth exponential release).
  - **Module 1 (Dirt - Distortion):** Drive, Pre-EQ (Low, Mid, High), Grit (slew + bit/sample-hold degrader), Output Level. Modes: *Rodent* (RAT-style hard symmetrical clip + slew LPF), *Fang* (asymmetrical clip, tight sub, scooped low-mid, bright attack), *Chainsaw* (HM-2 dual-gyrator resonant mid boost ~1 kHz).
  - **Module 2 (Frost - Chorus):** Rate (0.1–4.0 Hz), Depth, Tone (post high-dampening), Mix. Modes: *Analog BBD* (drifting modulated delay), *Dimension* (multi-tap spatial quadrature widening).
  - **Module 3 (Echo - Delay):** Time (20–800 ms + tempo sync toggle), Feedback (0–105% with soft-clipped self-oscillation), Tone (damping), Mix. Modes: *Tape / BBD* (darkened, subtly drifting feedback loop), *Digital 80s* (crisp repeats).
  - **Module 4 (Cavern - Reverb):** Decay (0.5–10 s), Pre-Delay (0–60 ms), Dampening (high-cut shelf), Mix. Modes: *Crypt Hall* (4 prime comb filters + 2 series allpass diffusers with dark absorption), *Cold Plate* (dense metallic early diffusion), *Abyss* (long-swell ambient wash).
  - **Module 5 (Cabinet Shaper & Master):** Fixed 90 Hz HPF + steep 5.5 kHz LPF + switchable multi-biquad Cabinet IIR profile (*Raw 4x12*, *Cold 2x12*, *Dark Crypt*) + Master Output (-24 to +6 dB).
- **Presets:**
  - Global recalls: *Human Worms*, *Transylvanian Frost*, *Crypt Drone*.
  - Local 3-preset quick toggles per middle module (Dirt, Frost, Echo, Cavern).
- **UI:** Charcoal/obsidian background (`#111113`), dark chassis (`#1A1A1E`), steel borders (`#2E2E36`), crimson (`#A82028`) and bone-silver (`#D0CEC8`) highlights. Strictly horizontal sliders and click toggles; zero rotary knobs.

## 3. Roadmap
- [x] Initialize Git repository, `AGENTS.md`, and `SPEC.md`.
- [ ] Implement core DSP & filter library (`sepulchre_dsp_core.jsfx-inc`).
- [ ] Implement modulation & time-based DSP modules (`sepulchre_dsp_fx.jsfx-inc`).
- [ ] Implement global & local module preset definitions (`sepulchre_presets.jsfx-inc`).
- [ ] Implement custom `@gfx` horizontal-slider pedalboard interface (`sepulchre_ui.jsfx-inc`).
- [ ] Implement main plugin entry and dynamic routing (`sepulchre_sound.jsfx`).
- [ ] Write and run static syntax + numerical DSP verification suite (`tests/verify_jsfx.py`).

## 4. Decisions Log
| Date | Decision | Why |
| :--- | :--- | :--- |
| 2026-10-28 | Split implementation into `sepulchre_sound.jsfx` and 4 `.jsfx-inc` files | Keeps every file well under the ~300-line limit along clear DSP, preset, and UI boundaries. |
| 2026-10-28 | Hide default REAPER sliders (`-` prefix) and drive parameters from custom `@gfx` + `slider_automate()` | Ensures full DAW automation and state recall while strictly enforcing the custom dark industrial horizontal-slider UI. |
| 2026-10-28 | Build `tests/verify_jsfx.py` linter and DSP math verifier | REAPER binary is not in system PATH; automated syntax/paren/memory check and filter stability tests verify code logic deterministically. |
