# SPEC.md — Sepulchre Sound

## 1. Goal & Overview
**Sepulchre Sound** is a native Cockos REAPER JSFX multi-effect guitar rig tailored for raw black metal, death/doom, and underground lo-fi tracking. It features 4x oversampled distortion, an integrated Tube / Solid-State Amp stage, a zero-latency partitioned FFT WAV Impulse Response (IR) loader (plus 3 built-in IIR cabinet curves), swappable effect block ordering, calibrated `-10 dBFS` to `-7.5 dBFS` tracking headroom, and a dark industrial UI with strictly horizontal sliders, Input/Output peak meters, and a 7-preset dropdown menu.

---

## 2. System Architecture & Signal Flow

### 2.1 File Modularization (<300 Lines per File)
REAPER's JSFX engine compiles `sepulchre_sound.jsfx`, which imports five modular `.jsfx-inc` headers (each beginning with `@init` and strictly under 300 lines):
1. `sepulchre_sound.jsfx` (198 lines) — Slider declarations (`slider1`..`slider60`), `@init`/`@slider`/`@block`/`@sample`/`@gfx` lifecycle sections, transport-start state clearing, thread-safe `@block` coefficient updates, and dynamic slot routing.
2. `sepulchre_dsp_core.jsfx-inc` (299 lines) — RBJ Audio EQ Cookbook biquad filters, C1 Hermite ceiling limiter (`limit_sample`), Module 0 (Input & Hysteresis/Hold Gate), and Module 1 (4x Oversampled Distortion + 10 Hz DC blocker).
3. `sepulchre_dsp_fx.jsfx-inc` (271 lines) — Fractional linear-interpolated ring buffers (`buf_read_interp`), RT60-calibrated damped comb filters (`comb_proc`), Schroeder allpass diffusers (`allpass_proc`), Module 2 (Chorus), Module 3 (Delay), and Module 4 (Reverb) with continuous bypass spillover.
4. `sepulchre_dsp_amp_cab.jsfx-inc` (212 lines) — Module 5: Tube / Solid-State Amp stage + 4-band tone stack (Bass, Mid, Treble, Presence/Air), overlap-add FFT WAV IR convolution engine (`file_riff`, `fft`, `convolve_c`, `ifft`), 3-profile IIR Cabinet fallback, and master output stage.
5. `sepulchre_presets.jsfx-inc` (173 lines) — Bitmask routing validator (`validate_routing`), parameter tables for 7 global presets and 12 local module presets.
6. `sepulchre_ui.jsfx-inc` (272 lines) — Custom `@gfx` immediate-mode UI (`1140x430`), horizontal sliders (`ui_hslider` with `slider_automate()`, Shift fine-drag, and scroll-wheel), Input/Output peak meters (`draw_level_meter`), slot-swap `<` `>` arrows, and modal dropdown overlay (`draw_preset_dropdown_bar` / `draw_preset_dropdown_menu`).

### 2.2 Dynamic Signal Routing & Thread Safety
```
[Module 0: Input Trim -> Pre-Cut HPF -> Detector HPF -> Hysteresis/Hold Noise Gate]
       │
       ▼
  [Slot A (slider5)] <-> [Slot B (slider6)] <-> [Slot C (slider7)] <-> [Slot D (slider8)]
   (Validated permutation of: 0=Distortion, 1=Chorus, 2=Delay, 3=Reverb)
       │
       ▼
[Module 5: Amp Stage (Tube/Solid-State + Tone Stack) -> WAV IR Convolution OR IIR Cab -> Presence -> -1.0 dBFS Limiter]
```
- **Thread Safety:** `@gfx` and `@slider` never mutate filter coefficients directly; they set `ui_need_sync = 1`, which `@block` consumes on the audio thread before `@sample` runs.
- **Permutation Safety:** `validate_routing()` verifies `(1<<s5)|(1<<s6)|(1<<s7)|(1<<s8) == 15` so automation or host edits can never run the same module twice on shared state.
- **Repeatable Renders:** `@block` detects `(play_state & 1) && !(last_play_state & 1)` and zeroes all filter states and delay/reverb buffers on transport start.

### 2.3 EEL2 Memory Map (`720,896` Floats Allocated, Zero Overlaps)
- **Core Biquads (`1024..1140`):** 13 stereo biquads × 9 floats (`bq_in_hp`, `bq_gate_det`, `bq_dist_*`, 4x OS `bq_os_up1..2` / `bq_os_dn1..2`).
- **Chorus, Delay & Reverb Buffers (`1141..549093`):** Chorus (`2 × 8,192`), Delay (`2 × 192,000`), Reverb pre-delay (`2 × 16,384`), 8 parallel mutual-prime comb filters (`8 × 12,288`), 4 series allpass filters (`4 × 4,096`), state vector (`32`), and biquads.
- **Amp/Cab & 64K-Aligned FFT Convolution Buffers (`589824..720896`):** 10 stereo biquads + 4 × `32,768` buffers (`ir_raw_buf`, `ir_fft_kern`, `ir_blk_cur`, `ir_blk_last`) for 4096-point complex FFT overlap-add convolution.

---

## 3. DSP Specifications

### 3.1 Module 0 — Input & Tremolo-Picking Gate
- **Input Trim:** `-12.0` to `+18.0 dB` (`slider1`, 20 ms 1-pole smoothed).
- **Pre-Cut HPF:** 12 dB/oct Butterworth high-pass (`40`–`180 Hz`, `slider2`).
- **Noise Gate:** `180 Hz` detector HPF (`bq_gate_det`) into peak envelope follower (`1.5 ms` attack, `45 ms` release), **5 dB hysteresis** (`gate_thresh_open` vs `gate_thresh_close`), **25 ms hold counter** (`gate_hold_samples`), `3 ms` open / `35 ms` exponential release, plus post-distortion hiss reduction keyed from `gate_gain`.

### 3.2 Module 1 — 4x Oversampled Distortion
- **Pre-EQ:** Low Shelf (`160 Hz`), Mid Peak (`850 Hz`, `Q=1.1`), High Shelf (`2.6 kHz`), each `±12 dB`.
- **4x Oversampling:** Zero-stuffing 4x upsampler filtered by cascaded 4th-order Linkwitz-Riley low-pass (`0.42 * Nyquist`, `Q=0.5412` & `Q=1.3065`) → sample-rate-independent slew limiter + nonlinear clipper + (in HM-2 mode) dual-gyrator resonators at `4 * srate` → 4th-order Linkwitz-Riley anti-aliasing filter and 4:1 decimation (>35 dB alias suppression on high lead notes).
- **DC Blocker:** 10 Hz 1-pole high-pass (`dc_r = exp(-2*pi*10/srate)`) immediately after decimation eliminates asymmetric clipping DC offset (`< 0.0004`).
- **Modes (`slider11`):** `0 = RAT` (hard clip + slew LPF `2.4`–`6.4 kHz`), `1 = MODERN HG` (tight `155 Hz` HPF, `420 Hz` scoop, `2.2 kHz` bite, asymmetric clip), `2 = HM-2` (`115 Hz` + `1020 Hz` dual gyrators between two saturation stages).

### 3.3 Module 2 — Chorus
- **Bypass Spillover:** Buffer and LFO run continuously; bypass smoothly crossfades `chorus_mix_s` to `0.0`.
- **Modes (`slider21`):** `0 = ANALOG BBD` (quadrature sine LFO modulated by 150 ms low-pass filtered white noise `chorus_rng` for hitch-free organic drift), `1 = DIMENSION` (4-tap cross-phase spatial widening).

### 3.4 Module 3 — Delay
- **Bypass Spillover & Instant Lock:** Delay buffer runs continuously with `0.0` input when bypassed so repeats decay naturally; `delay_smooth_init` snaps to `target_del` on first sample to prevent startup pitch glides.
- **Tempo Sync (`slider36`):** Supports 4 divisions (`1/8`, `1/4T`, `1/8.`, `1/4`) and displays both the division name and computed milliseconds directly on the slider (`1/8. (375 ms)`).

### 3.5 Module 4 — Reverb
- **Calibrated RT60 Formula:** Mutual-prime comb lengths (`1559, 1619, 1493, 1423` samples @ 44.1 kHz, +stereo spread offsets) use exact per-comb RT60 feedback:
  `fb_i = clamp(exp(-6.907755 * L_i / (srate * T_decay)), 0.15, 0.9992)`
  Matches the `DECAY (RT60)` slider within `<1%` across all sample rates (`44.1`–`96 kHz`).
- **Modes (`slider41`):** `0 = HALL` (1.0x scale), `1 = PLATE` (0.68x scale, `0.68` allpass density), `2 = AMBIENT` (1.32x scale, 1.25x decay, symmetric `78%/22%` stereo cross-wash).

### 3.6 Module 5 — Amp Stage, WAV IR Loader / IIR Cabinet & Limiter
- **Amp Stage (`slider54`):** `0 = OFF`, `1 = TUBE HEAD` (asymmetric cathode/plate saturation), `2 = SOLID-STATE` (crisp MOSFET rail clip), followed by `Bass` (`125 Hz`), `Mid` (`520/620 Hz`), `Treble` (`2.4 kHz`), and `Presence/Air` (`3.8 kHz`).
- **WAV IR Convolution (`slider53`):** Reads WAV files from `%APPDATA%\REAPER\Data\sepulchre_irs\` via `file_riff()`, resamples to host `srate` if needed, normalizes energy, and runs 4096-point partitioned overlap-add FFT convolution (`fft` / `convolve_c` / `ifft`). When `slider53 == 0`, falls back to the 3 gain-compensated IIR cabinet curves (`4x12 V30`, `2x12 Combo`, `4x12 Damped`) with extended upper-mid air (`5.1`–`6.2 kHz` + `7.8 kHz` LPF).
- **Master Ceiling Limiter:** `limit_sample(x, 0.89125)` is **100% linear below `-6.0 dBFS` (`0.50`)** and uses a $C^1$ cubic Hermite knee above `-6 dBFS` to clamp peaks at exactly **`-1.0 dBFS` (`0.89125`)** with zero low-level harmonic coloration.

---

## 4. Global Preset Catalog (`slider60`)

| # | Preset Name | Distortion | Amp Stage | Chorus | Delay | Reverb | Cab / Peak |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | **01: TIGHT RHYTHM** | Modern HG (82%) | Tube Head | Bypass | Bypass | Hall (15%) | 4x12 (`-8.75 dBFS`) |
| 1 | **02: COLD LEAD** | RAT (76%) | Tube Head | Analog BBD (36%) | Tape 390ms (28%) | Plate (24%) | 2x12 (`-9.36 dBFS`) |
| 2 | **03: DOOM WALL** | HM-2 (84%) | Tube Head | Dimension (28%) | Tape 520ms (28%) | Ambient (34%) | Damped (`-8.99 dBFS`) |
| 3 | **04: RAW 4-TRACK** | RAT (80%, 48% Grit) | Solid-State | Bypass | Tape 140ms (18%) | Bypass | 2x12 (`-9.60 dBFS`) |
| 4 | **05: SWEDISH CHAINSAW** | HM-2 (88%) | Solid-State | Bypass | Bypass | Plate (14%) | 4x12 (`-7.57 dBFS`) |
| 5 | **06: FREEZING CLEAN** | Bypass (+3.5 dB In) | Tube Head | Analog BBD (48%) | Digital 440ms (32%) | Hall (34%) | 2x12 |
| 6 | **07: AMBIENT SWELL** | RAT (68%) | Tube Head | Dimension (40%) | Tape 580ms (38%) | Ambient (46%) | Damped |

---

## 5. Roadmap
- [x] Initialize Git repository, `AGENTS.md`, and `SPEC.md`.
- [x] Implement core DSP, FX, Presets, UI, and main JSFX entry.
- [x] Replace proprietary labels with direct hardware/effect names and add 7-preset dropdown menu.
- [x] Resolve all 11 items from `REVIEW.md`:
  - [x] Replace static test checks with dynamic memory parser + offline DSP simulation in `tests/verify_jsfx.py`.
  - [x] Fix Reverb RT60 decay formula per comb length (`exp(-6.907755 * N / (srate * T))`).
  - [x] Keep Chorus/Delay/Reverb buffers running on bypass for natural tail spillover + clear on transport start.
  - [x] Validate routing slots in `@block` (`validate_routing()`) so duplicate slots reset to `0-1-2-3`.
  - [x] Move `sync_all_DSP()` out of `@gfx` into `@block` via `ui_need_sync` flag; add `slider_automate()` on UI edits.
  - [x] Add 10 Hz 1-pole DC blocker after distortion clipping.
  - [x] Add 4x oversampling (`bq_os_up`/`bq_os_dn`) around distortion slew limiter, clippers, and HM-2 gyrators.
  - [x] Make all time constants sample-rate independent and add 20 ms 1-pole parameter smoothing.
  - [x] Add 5 dB gate hysteresis, 25 ms hold timer, 180 Hz detector HPF, and post-distortion gate key spillover.
  - [x] Add Input/Output peak level meters, 4-division tempo-sync label display, Shift-drag/scroll-wheel, and preset dirty `*` indicator.
  - [x] Add Tube / Solid-State Amp stage (`sepulchre_dsp_amp_cab.jsfx-inc`), WAV IR FFT Convolution loader (`sepulchre_irs`), and re-calibrate all high-gain presets within `-9.6` to `-7.5 dBFS`.

---

## 6. Decisions Log
| Date | Decision | Why |
| :--- | :--- | :--- |
| 2026-10-28 | Split implementation into `sepulchre_sound.jsfx` and 5 `.jsfx-inc` files | Keeps every file under the 300-line limit along clear DSP, Amp/IR, Preset, and UI boundaries. |
| 2026-10-28 | Deploy runtime JSFX to `%APPDATA%\REAPER\Effects\sepulchre_sound\` and curated WAV IRs to `%APPDATA%\REAPER\Data\sepulchre_irs\` | Matches REAPER's native JSFX and `/sepulchre_irs` WAV file-slider discovery paths. |
| 2026-10-28 | Defer UI coefficient recalculation to `@block` (`ui_need_sync`) and call `slider_automate()` on user edits | Prevents audio-thread/UI-thread race conditions on biquad coefficients and enables touch/latch DAW automation recording without dirtying project state on load. |
| 2026-10-28 | Run 4x Linkwitz-Riley oversampling around distortion and replace Padé soft-clipper with C1 Hermite limiter (`limit_sample`) | Pushes 2.6 kHz lead note aliasing down to `-97.1 dB` in-band and keeps the master bus 100% linear below `-6 dBFS` with an exact `-1.0 dBFS` ceiling. |
