# SPEC.md — Sepulchre Sound

## 1. Goal & Overview
**Sepulchre Sound** is a native Cockos REAPER JSFX multi-effect guitar pedalboard tailored for raw black metal, death/doom, and underground lo-fi tracking. It combines high pick articulation, authentic analog/lo-fi circuit saturation, swappable effect block ordering, calibrated `-10 dBFS` to `-8 dBFS` tracking headroom, and a minimal dark industrial UI with strictly horizontal sliders, click toggles, and a global preset dropdown.

---

## 2. System Architecture & Signal Flow

### 2.1 File Modularization (<300 Lines per File)
REAPER's JSFX engine compiles `sepulchre_sound.jsfx`, which imports four modular `.jsfx-inc` headers (each beginning with `@init` as required by REAPER's EEL2 preprocessor):
1. `sepulchre_sound.jsfx` — Slider declarations (`slider1`..`slider60`, hidden with `-` prefix so only the custom `@gfx` UI renders), `@init`/`@slider`/`@block`/`@sample`/`@gfx` lifecycle sections, and dynamic slot routing.
2. `sepulchre_dsp_core.jsfx-inc` — RBJ Audio EQ Cookbook biquad filters, memory bump allocator (`alloc_buf`), Module 0 (Input & Gate), Module 1 (Distortion), and Module 5 (Cabinet Shaper & Master Limiter).
3. `sepulchre_dsp_fx.jsfx-inc` — Fractional linear-interpolated ring buffers (`buf_read_interp`), damped feedback comb filters (`comb_proc`), Schroeder allpass diffusers (`allpass_proc`), Module 2 (Chorus), Module 3 (Delay), and Module 4 (Reverb).
4. `sepulchre_presets.jsfx-inc` — Parameter state tables for 7 global presets and 12 local module presets (3 per middle effect block), triggering `sync_all_DSP()` and `sliderchange(-1)` for DAW automation notification.
5. `sepulchre_ui.jsfx-inc` — Custom `@gfx` immediate-mode UI (`1140x430`), horizontal sliders (`ui_hslider`), toggle buttons (`ui_button`), slot-swap `<` `>` arrows (`swap_routing_slots`), and modal dropdown overlay (`draw_preset_dropdown_bar` / `draw_preset_dropdown_menu`).

### 2.2 Dynamic Signal Routing
```
[Module 0: Input Trim -> Pre-Cut HPF -> Noise Gate]
       │
       ▼
  [Slot A (slider5)] <-> [Slot B (slider6)] <-> [Slot C (slider7)] <-> [Slot D (slider8)]
   (Any permutation of: 0=Distortion, 1=Chorus, 2=Delay, 3=Reverb)
       │
       ▼
[Module 5: Cabinet IIR Network -> Fixed 90Hz HPF / 5.5kHz LPF -> Master Trim -> -1.0 dBFS Safety Limiter]
```

### 2.3 EEL2 Memory Map
Memory starts at `mem_top = 1024` (`ext_noinit = 1` prevents buffer resets on transport start):
- **Core Biquads:** 14 stereo biquads × 9 floats = `126` slots (`[b0, b1, b2, a1, a2, z1L, z2L, z1R, z2R]`).
- **Chorus Buffers:** `2 × 8,192` floats (`~170 ms` @ 48 kHz) + 1 biquad.
- **Delay Buffers:** `2 × 192,000` floats (`4.0 s` @ 48 kHz / `2.0 s` @ 96 kHz) + 2 biquads.
- **Reverb Buffers:** Pre-delay (`2 × 16,384`), 8 parallel stereo-spread comb filters (`8 × 12,288`), 4 series allpass filters (`4 × 4,096`), state vector (`32`), and high-shelf damping biquad (`9`).
- **Total Footprint:** `549,058` floats (6.5% of REAPER's standard 8,388,608-slot per-instance pool).

---

## 3. DSP Modules & Gain Staging

### 3.1 Gain Staging & Anti-Clipping Calibration
To prevent channel clipping at unity (`0.0 dB`) track fader settings:
1. **Distortion Output Trim:** Internal post-clipper scaling is set to `0.28` (`-11 dB`), with an additional `0.72` compensation after the dual-gyrator HM-2 stage (`+13.5 dB @ 115 Hz` and `+17.5 dB @ 1.02 kHz`).
2. **Cabinet Insertion Gain Compensation:** Each multi-biquad speaker curve applies an attenuation scalar (`cab_comp_lin` = `0.60`–`0.65`) to offset resonant peak boosts.
3. **Safety Ceiling Limiter:** The final output passes through a transparent Padé-approximated `soft_tanh` ceiling clamped at `-1.0 dBFS` (`0.891` linear):
   `spl = 0.891 * soft_tanh(x / 0.891)`
4. **Preset Output Targets:** All 7 global presets are calibrated to peak between **`-10 dBFS` and `-8 dBFS`** with normal guitar input levels.

### 3.2 Module Specifications
- **Module 0 — Input & Gate:**
  - *Input Trim:* `-12.0` to `+18.0 dB` (`slider1`).
  - *Pre-Cut HPF:* 12 dB/oct Butterworth high-pass (`40`–`180 Hz`, default `105 Hz`, `slider2`) to tighten palm-mute sub-rumble prior to clipping.
  - *Noise Gate:* Peak envelope detector (`1.5 ms` attack, `45 ms` release) compared against threshold (`-80` to `-30 dB`, `slider3`) with exponential gain decay (`35 ms`) and hard clamp to `0.0` below `-80 dB`.
- **Module 1 — Distortion:**
  - *Pre-EQ:* Low Shelf (`160 Hz`), Mid Peak (`850 Hz`, `Q=1.1`), High Shelf (`2.6 kHz`), each `±12 dB`.
  - *Modes (`slider11`):*
    - `0 = RAT`: `110 Hz` pre-HPF, op-amp slew-rate limiter (`max_delta` scaled by Drive & Grit), symmetrical hard clip + soft knee, drive-dependent post-LPF (`1.4`–`4.8 kHz`).
    - `1 =MODERN HG`: `165 Hz` tight pre-HPF, `420 Hz` low-mid scoop (`-6.5 dB`), `2.2 kHz` pick-attack boost (`+7.5 dB`), asymmetrical clipping.
    - `2 = HM-2`: Dual-gyrator resonator (`+13.5 dB @ 115 Hz, Q=2.2` and `+17.5 dB @ 1020 Hz, Q=2.8`) sandwiched between two op-amp saturation stages.
  - *Grit (`slider16`):* Tightens op-amp slew rate and blends sample-and-hold decimation (`1x`–`6x`) + bit-depth quantization.
- **Module 2 — Chorus:**
  - *Modes (`slider21`):* `0 = ANALOG BBD` (quadrature sine LFO with organic low-frequency phase drift around `6.5`–`7.2 ms`), `1 = DIMENSION` (4-tap cross-phase spatial widening with minimal pitch warble).
  - *Controls:* Rate (`0.1`–`4.0 Hz`), Depth (`0`–`100%`), Tone (`900 Hz`–`8.4 kHz` post-LPF), Mix (`0`–`100%`).
- **Module 3 — Delay:**
  - *Modes (`slider31`):* `0 = TAPE` (`135 Hz` HPF + `950 Hz`–`4.15 kHz` LPF + `0.65 Hz` wow modulation in feedback loop), `1 = DIGITAL` (`80 Hz` HPF + `2.2`–`11.7 kHz` LPF, zero pitch drift).
  - *Controls:* Time (`20`–`800 ms` + host `TEMPO SYNC` toggle), Feedback (`0`–`105%` bounded by `soft_tanh` saturation in the feedback loop), Tone, Mix.
- **Module 4 — Reverb:**
  - *Architecture:* Variable pre-delay (`0`–`60 ms`) feeding 4 parallel stereo-detuned prime-length damped comb filters (`1557, 1617, 1491, 1422` samples scaled by `srate/44100` and mode size) into 2 series Schroeder allpass diffusers (`225, 556` samples) and a high-shelf damping filter.
  - *Modes (`slider41`):* `0 = HALL` (1.0x room scale, dark wall absorption), `1 = PLATE` (0.68x room scale, high `0.68` allpass diffusion density), `2 = AMBIENT` (1.32x room scale, extended decay, stereo cross-wash).
- **Module 5 — Cabinet Shaper & Master:**
  - *Fixed Filters:* `90 Hz` HPF + cascaded `5.5 kHz` + profile LPF (`24 dB/oct` high-frequency speaker roll-off).
  - *Profiles (`slider50`):*
    - `0 = 4x12 (V30 / SM57)`: `+3.0 dB @ 135 Hz`, `-4.5 dB @ 650 Hz`, `+4.5 dB @ 2.75 kHz`, `4.8 kHz` resonant LPF.
    - `1 = 2x12 (COMBO)`: `175 Hz` HPF, `+4.0 dB @ 1.15 kHz`, `+3.5 dB @ 3.3 kHz`, `4.6 kHz` LPF.
    - `2 = 4x12 (DAMPED)`: `+4.5 dB @ 110 Hz`, `-7.5 dB @ 3.0 kHz`, `+2.5 dB @ 1.65 kHz`, `3.9 kHz` dark LPF.

---

## 4. Global Preset Catalog (`slider60`)

| # | Preset Name | Distortion | Chorus | Delay | Reverb | Cabinet | Character |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | **01: TIGHT RHYTHM** | Modern HG (82%) | Bypass | Bypass | Hall (15% mix) | 4x12 (V30/SM57) | High-articulation palm-muted rhythm tracking. |
| 1 | **02: COLD LEAD** | RAT (76%) | Analog BBD (36%) | Tape 390ms (28%) | Plate (24% mix) | 2x12 (Combo) | Freezing 90s black metal tremolo-picked melody & lead tone. |
| 2 | **03: DOOM WALL** | HM-2 (84%) | Dimension (28%) | Tape 520ms (28%) | Ambient (34% mix) | 4x12 (Damped) | Massive HM-2 wall of sound with spatial sustain and clear note definition. |
| 3 | **04: RAW 4-TRACK** | RAT (80%, 48% Grit) | Bypass | Tape 140ms (18%) | Bypass | 2x12 (Combo) | Necro cassette-style lo-fi practice-amp rasp with short room slapback. |
| 4 | **05: SWEDISH CHAINSAW** | HM-2 (88%) | Bypass | Bypass | Plate (14% mix) | 4x12 (V30/SM57) | Dry, aggressive 1 kHz dual-gyrator buzzsaw rhythm. |
| 5 | **06: FREEZING CLEAN** | Bypass (+3.5 dB In) | Analog BBD (48%) | Digital 440ms (32%) | Hall (34% mix) | 2x12 (Combo) | Crystalline modulated clean tone for intros and acoustic-style interludes. |
| 6 | **07: AMBIENT SWELL** | RAT (68%) | Dimension (40%) | Tape 580ms (38%) | Ambient (46% mix) | 4x12 (Damped) | Long, cavernously drenched atmospheric lead/drone tone. |

---

## 5. Roadmap
- [x] Initialize Git repository, `AGENTS.md`, and `SPEC.md`.
- [x] Implement core DSP & filter library (`sepulchre_dsp_core.jsfx-inc`).
- [x] Implement modulation & time-based DSP modules (`sepulchre_dsp_fx.jsfx-inc`).
- [x] Implement global & local module preset definitions (`sepulchre_presets.jsfx-inc`).
- [x] Implement custom `@gfx` horizontal-slider pedalboard interface (`sepulchre_ui.jsfx-inc`).
- [x] Implement main plugin entry and dynamic routing (`sepulchre_sound.jsfx`).
- [x] Write and run static syntax + numerical DSP verification suite (`tests/verify_jsfx.py`).
- [x] Replace proprietary labels with direct hardware/effect names and calibrate `-10 dBFS` headroom + `-1.0 dBFS` safety limiter.
- [x] Expand global presets to 7 and replace top preset buttons with a modal dropdown menu.

---

## 6. Decisions Log
| Date | Decision | Why |
| :--- | :--- | :--- |
| 2026-10-28 | Split implementation into `sepulchre_sound.jsfx` and 4 `.jsfx-inc` files | Keeps every file under the 300-line limit along clear DSP, preset, and UI boundaries. |
| 2026-10-28 | Hide default REAPER sliders (`-` prefix) and drive parameters from custom `@gfx` + `sliderchange(-1)` | Ensures full DAW automation and state recall while strictly enforcing the custom dark industrial horizontal-slider UI. |
| 2026-10-28 | Build `tests/verify_jsfx.py` linter and DSP math verifier | Verifies balanced parentheses, `<300` line limits, `@init` headers, non-overlapping memory allocations, and biquad pole stability deterministically. |
| 2026-10-28 | Deploy runtime JSFX to `%APPDATA%\REAPER\Effects\sepulchre_sound\` and house source repo at `D:\VSTs\sepulchre_sound` | REAPER scans `%APPDATA%\REAPER\Effects` for JSFX scripts while `D:\VSTs` groups plugin folders on `D:`. |
| 2026-10-28 | Add explicit `@init` header to all `.jsfx-inc` files | REAPER's EEL2 compiler requires `@init` before function definitions in imported `.jsfx-inc` files. |
| 2026-10-28 | Replace proprietary module/mode/preset names with direct hardware/effect labels and rework Preset 3 into *Doom Wall* | Eliminates confusing labels (`DISTORTION`, `CHORUS`, `DELAY`, `REVERB`; `RAT`, `MODERN HG`, `HM-2`), removes song-title collision, and routes Delay/Reverb after HM-2 so guitar notes cut through clearly. |
| 2026-10-28 | Calibrate internal distortion/cabinet gain staging for `-10 dBFS` to `-8 dBFS` peaks + `-1.0 dBFS` safety limiter, and add 7-preset dropdown | Prevents channel clipping at unity fader gain and consolidates 7 global presets into a clean top-bar dropdown overlay. |
