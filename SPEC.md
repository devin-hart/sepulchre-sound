# SPEC.md — Sepulchre Sound

## 1. Goal & Overview
**Sepulchre Sound** is a native Cockos REAPER JSFX multi-effect guitar rig tailored for raw black metal, death/doom, and underground lo-fi tracking. It features 4x oversampled distortion, an integrated Tube / Solid-State Amp stage, a zero-latency partitioned FFT WAV Impulse Response (IR) loader (plus 3 built-in IIR cabinet curves), swappable effect block ordering, calibrated `-10 dBFS` to `-7.5 dBFS` tracking headroom, and a dark industrial UI with strictly horizontal sliders, Input/Output peak meters, and a 7-preset dropdown menu.

---

## 2. System Architecture & Signal Flow

### 2.1 File Modularization (<300 Lines per File)
REAPER's JSFX engine compiles `sepulchre_sound.jsfx`, which imports five modular `.jsfx-inc` headers (each beginning with `@init` and strictly under 300 lines):
1. `sepulchre_sound.jsfx` (222 lines) — Slider declarations (`slider1`..`slider60`, including `slider52` Cabinet Source Mode), `@init`/`@slider`/`@block`/`@sample`/`@gfx` lifecycle sections, PDC convolution latency reporting (`pdc_delay = ir_chunk_size`), transport-start state clearing, thread-safe `@block` coefficient updates, and dynamic slot routing.
2. `sepulchre_dsp_core.jsfx-inc` (299 lines) — RBJ Audio EQ Cookbook biquad filters, C1 Hermite ceiling limiter (`limit_sample`), Module 0 (Input & Hysteresis/Hold Gate), and Module 1 (4x Oversampled Distortion with 8th-order Butterworth filters @ 8.5 kHz, `C^2` 2-stage saturation, and 10 Hz DC blocker).
3. `sepulchre_dsp_fx.jsfx-inc` (272 lines) — Fractional linear-interpolated ring buffers (`buf_read_interp`), RT60-calibrated damped comb filters (`comb_proc`), Schroeder allpass diffusers (`allpass_proc`), Module 2 (Chorus), Module 3 (Delay with bypassed self-oscillation decay clamp `!en ? fb = min(fb, 0.75)`), and Module 4 (Reverb) with continuous bypass spillover.
4. `sepulchre_dsp_amp_cab.jsfx-inc` (215 lines) — Module 5: Tube / Solid-State Amp stage + 10 Hz post-amp DC blocker + 4-band tone stack (Bass, Mid, Treble, Presence/Air), overlap-add FFT WAV IR convolution engine (`slider52` mode toggle + `slider53` 0-based WAV index `#0..#9`), 3-profile IIR Cabinet mode, and master output stage.
5. `sepulchre_presets.jsfx-inc` (175 lines) — Bitmask routing validator (`validate_routing`), parameter tables for 7 global presets (calibrated strictly to `[-10.0, -8.0] dBFS`) and 12 local module presets.
6. `sepulchre_ui.jsfx-inc` (287 lines) — Custom `@gfx` immediate-mode UI (`1140x430`), horizontal sliders (`ui_hslider` with bitmask `auto_slider(id, end_touch)`, double-click-to-default reset, Shift fine-drag, and scroll-wheel), 4 Delay sync division buttons (`1/8`, `1/4T`, `1/8.`, `1/4`), distinct Input / Post-Dist / Master peak meters, slot-swap `<` `>` arrows, and modal dropdown overlay.

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
- **4x Oversampling:** Zero-stuffing 4x upsampler filtered by cascaded **8th-order Butterworth (`48 dB/oct` @ `8.5 kHz`, `Q = 0.5098, 0.6013, 0.9000, 2.5629`)** low-pass (`bq_os_up1..4`) → 1-pole OP07 bandwidth/slew filter + `C^2`-smooth 2-stage rational saturation (`soft_tanh` clamped at `±3.0` where $f'(\pm 3) = f''(\pm 3) = 0$) + (in HM-2 mode) dual-gyrator resonators at `4 * srate` → 8th-order Butterworth anti-aliasing filter (`bq_os_dn1..4`) and 4:1 decimation (**`-48.2 dB` total integrated alias power across all non-harmonic bins pre-cabinet**).
- **DC Blocker:** 10 Hz 1-pole high-pass (`dc_r = exp(-2*pi*10/srate)`) immediately after decimation eliminates asymmetric clipping DC offset (`< 0.0003`).
- **Modes (`slider11`):** `0 = RAT` (symmetric 2-stage clip + slew LPF `2.4`–`6.4 kHz`), `1 = MODERN HG` (tight `155 Hz` HPF, `420 Hz` scoop, `2.2 kHz` bite, asymmetric 2-stage clip), `2 = HM-2` (`115 Hz` + `1020 Hz` dual gyrators between saturation stages).

### 3.3 Module 2 — Chorus
- **Bypass Spillover:** Buffer and LFO run continuously; bypass smoothly crossfades `chorus_mix_s` to `0.0`.
- **Modes (`slider21`):** `0 = ANALOG BBD` (quadrature sine LFO modulated by 150 ms low-pass filtered white noise `chorus_rng` for hitch-free organic drift), `1 = DIMENSION` (4-tap cross-phase spatial widening).

### 3.4 Module 3 — Delay
- **Bypass Spillover, Self-Oscillation Decay Clamp & Instant Lock:** Delay buffer runs continuously with `0.0` input when bypassed so repeats decay naturally; when bypassed (`!en`), feedback is clamped via `!en ? fb = min(fb, 0.75)` so self-oscillating (`100–105%`) settings decay to silence rather than ringing forever. `delay_smooth_init` snaps to `target_del` on first sample to prevent startup pitch glides.
- **Tempo Sync (`slider36`):** Supports 4 divisions (`1/8`, `1/4T`, `1/8.`, `1/4`) via dedicated UI selector buttons and displays both the division name and computed milliseconds directly on the slider (`1/8. (375 ms)`).

### 3.5 Module 4 — Reverb
- **Calibrated RT60 Formula:** Mutual-prime comb lengths (`1559, 1619, 1493, 1423` samples @ 44.1 kHz, +stereo spread offsets) use exact per-comb RT60 feedback:
  `fb_i = clamp(exp(-6.907755 * L_i / (srate * T_decay)), 0.15, 0.9992)`
  Sample-by-sample impulse response decays to `-58.73 dB` at `t = 1.5 s` (`T_decay = 1.5 s`) and `-59.36 dB` at `t = 3.0 s` (`T_decay = 3.0 s`).
- **Modes (`slider41`):** `0 = HALL` (1.0x scale), `1 = PLATE` (0.68x scale, `0.68` allpass density), `2 = AMBIENT` (1.32x scale, 1.25x decay, symmetric `78%/22%` stereo cross-wash).

### 3.6 Module 5 — Amp Stage, WAV IR Loader / IIR Cabinet & Limiter
- **Amp Stage (`slider54`):** `0 = OFF`, `1 = TUBE HEAD` (asymmetric cathode/plate saturation), `2 = SOLID-STATE` (crisp MOSFET rail clip), followed by a **10 Hz 1-pole DC blocker** (`amp_dc_x1`/`amp_dc_y1`), `Bass` (`125 Hz`), `Mid` (`520/620 Hz`), `Treble` (`2.4 kHz`), and `Presence/Air` (`3.8 kHz`).
- **WAV IR Convolution (`slider52` Mode + `slider53` File Index):** `slider52` selects `0 = IIR Cabinet` or `1 = WAV IR Convolution`. `slider53` strictly indexes WAV files `#0..#9` (`01_BlackWizard_Center.wav` .. `10_PlagueBearer_Center.wav`) from `%APPDATA%\REAPER\Data\sepulchre_irs\` via `file_riff()`. File I/O (`load_ir_slot()`) runs strictly off the audio thread (`@init`, `@slider`, `@gfx`), while `@block` runs `prepare_ir_fft()` and reports `pdc_delay = ir_chunk_size` (`2048` samples) when WAV IR convolution is active.
- **Master Ceiling Limiter:** `limit_sample(x, 0.89125)` is **100% linear below `-6.0 dBFS` (`0.50`)** and uses a $C^1$ cubic Hermite knee above `-6 dBFS` to clamp peaks at exactly **`-1.0 dBFS` (`0.89125`)** with zero low-level harmonic coloration.

---

## 4. Global Preset Catalog (`slider60`)

| # | Preset Name | Distortion | Amp Stage | Chorus | Delay | Reverb | Cab / Peak |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | **01: TIGHT RHYTHM** | Modern HG (82%) | Tube Head | Bypass | Bypass | Hall (15%) | 4x12 (`-9.76 dBFS`) |
| 1 | **02: COLD LEAD** | RAT (76%) | Tube Head | Analog BBD (36%) | Tape 390ms (28%) | Plate (24%) | 2x12 (`-9.20 dBFS`) |
| 2 | **03: DOOM WALL** | HM-2 (84%) | Tube Head | Dimension (28%) | Tape 520ms (28%) | Ambient (34%) | Damped (`-9.24 dBFS`) |
| 3 | **04: RAW 4-TRACK** | RAT (80%, 48% Grit) | Solid-State | Bypass | Tape 140ms (18%) | Bypass | 2x12 (`-9.38 dBFS`) |
| 4 | **05: SWEDISH CHAINSAW** | HM-2 (88%) | Solid-State | Bypass | Bypass | Plate (14%) | 4x12 (`-9.53 dBFS`) |
| 5 | **06: FREEZING CLEAN** | Bypass (+3.5 dB In) | Tube Head | Analog BBD (48%) | Digital 440ms (32%) | Hall (34%) | 2x12 |
| 6 | **07: AMBIENT SWELL** | RAT (68%) | Tube Head | Dimension (40%) | Tape 580ms (38%) | Ambient (46%) | Damped |

---

## 5. Roadmap
- [x] Initialize Git repository, `AGENTS.md`, and `SPEC.md`.
- [x] Implement core DSP, FX, Presets, UI, and main JSFX entry.
- [x] Replace proprietary labels with direct hardware/effect names and add 7-preset dropdown menu.
- [x] Resolve Round 1 items (`REVIEW.md` items 1–11).
- [x] Resolve Round 2 items (`REVIEW.md` R2-1 through R2-6 + Round 3 audit asks):
  - [x] **R2-1:** Remove `recall_global_preset(slider60)` from `@init` and `@slider` so REAPER project reloads preserve user parameter edits.
  - [x] **R2-2:** Clamp delay feedback (`!en ? fb = min(fb, 0.75)`) when bypassed so `100–105%` self-oscillation decays to silence.
  - [x] **R2-3:** Report `pdc_delay = ir_chunk_size` (`pdc_bot_ch = 0; pdc_top_ch = 2`) in `@block` when WAV IR convolution is active.
  - [x] **R2-4:** Separate Cabinet Source Mode (`slider52`: IIR vs WAV IR) from WAV file index (`slider53`: `#0..#9`) so file `#0` (`01_BlackWizard_Center.wav`) is reachable.
  - [x] **R2-5:** Fix `slider_automate(2 ^ (id - 1), end_touch)` bitmask call after value assignment and send `end_touch = 1` on mouse release.
  - [x] **R2-6:** Remove `load_ir_slot()` (`file_open`/`file_riff`) from `@block` audio thread; only `prepare_ir_fft()` runs in `@block`.
  - [x] Upgrade 4x oversampler to 8th-order Butterworth (`48 dB/oct` @ `8.5 kHz`) + `C^2` 2-stage saturation (`-48.2 dB` pre-cabinet aliasing across all non-harmonic bins).
  - [x] Calibrate all 5 high-gain presets strictly inside `[-10.0, -8.0] dBFS`, add post-amp 10 Hz DC blocker, distinct `POST-DIST LEVEL` meter, 4 tempo-sync division buttons, and double-click slider reset.

---

## 6. Decisions Log
| Date | Decision | Why |
| :--- | :--- | :--- |
| 2026-10-28 | Split implementation into `sepulchre_sound.jsfx` and 5 `.jsfx-inc` files | Keeps every file under the 300-line limit along clear DSP, Amp/IR, Preset, and UI boundaries. |
| 2026-10-28 | Deploy runtime JSFX to `%APPDATA%\REAPER\Effects\sepulchre_sound\` and curated WAV IRs to `%APPDATA%\REAPER\Data\sepulchre_irs\` | Matches REAPER's native JSFX and `/sepulchre_irs` WAV file-slider discovery paths. |
| 2026-10-28 | Defer UI coefficient recalculation to `@block` (`ui_need_sync`) and call `slider_automate(2^(id-1), end_touch)` on user edits | Prevents audio-thread/UI-thread race conditions on biquad coefficients and records touch/latch DAW automation with proper bitmask and end-touch release. |
| 2026-10-28 | Upgrade 4x oversampler to 8th-order Butterworth (`8.5 kHz`) + `C^2` 2-stage saturation (`soft_tanh` clamped at `±3.0`) | Eliminates derivative discontinuities at saturation knees and achieves `-48.2 dB` total integrated non-harmonic aliasing pre-cabinet across all FFT bins. |
| 2026-10-28 | Separate `slider52` (Cabinet Source Mode) from `slider53` (0-based WAV IR slot) and move `load_ir_slot()` off `@block` | Makes WAV IR slot `#0` (`01_BlackWizard_Center.wav`) reachable and prevents blocking disk I/O on the real-time audio thread. |
