# SPEC.md — Sepulchre Sound

## 1. Goal & Overview
**Sepulchre Sound** is a native Cockos REAPER JSFX multi-effect guitar rig tailored for raw black metal, death/doom, and underground lo-fi tracking. It features four 8x-oversampled circuit-modelled distortion pedals (RAT, DS-1, Metal Zone, HM-2; `16.5 kHz` 8th-order Butterworth resampling), an integrated Tube / Solid-State Amp stage, a 128-sample (2.7 ms) partitioned-convolution WAV Impulse Response (IR) loader (plus 3 built-in IIR cabinet curves), swappable effect block ordering, calibrated `-10.0 dBFS` to `-8.0 dBFS` tracking headroom, and a resolution-independent **necro-monochrome** UI (`1204×500` design space, Retina-aware) with numbered signal-flow stages (`I–VIII`), 30% alpha bypass dimming, bipolar `±dB` EQ sliders, scaled dB meters with gate-threshold marker, and a 7-preset dropdown menu.

---

## 2. System Architecture & Signal Flow

### 2.1 File Modularization (<300 Lines per File)
REAPER's JSFX engine compiles `sepulchre_sound.jsfx`, which imports seven modular `.jsfx-inc` headers (each beginning with `@init` and strictly under 300 lines):
1. `sepulchre_sound.jsfx` (144 lines) — Slider declarations (`slider1`..`slider60`, including `slider52` Cabinet Source Mode), `filename:0,sepulchre_bg.jpg` and `filename:1,sepulchre_titles.png` asset declarations, `@init`/`@slider`/`@block`/`@sample`/`@gfx 1204 500` lifecycle sections, PDC convolution latency reporting (`pdc_delay = ir_chunk_size`), `ir_reload_req` handler, transport-start state clearing, thread-safe `@block` coefficient updates, and dynamic slot routing.
2. `sepulchre_dsp_core.jsfx-inc` (222 lines) — RBJ Audio EQ Cookbook biquad filters, C1 Hermite ceiling limiter (`limit_sample`), core buffer allocation, and Module 0 (Input & Hysteresis/Hold Gate). Module 1 (Distortion) lives in `sepulchre_dsp_dist.jsfx-inc` (198 lines, imported directly after core).
3. `sepulchre_dsp_fx.jsfx-inc` (195 lines) — Fractional linear-interpolated ring buffers (`buf_read_interp`), RT60-calibrated damped comb filters (`comb_proc`), Schroeder allpass diffusers (`allpass_proc`), Module 2 (Chorus), Module 3 (Delay with bypassed self-oscillation decay clamp `!en ? fb = min(fb, 0.75)`), and Module 4 (Reverb) with continuous bypass spillover.
4. `sepulchre_dsp_amp.jsfx-inc` (82 lines) — Module 5: Tube / Solid-State Amp stage + 10 Hz post-amp DC blocker + 4-band tone stack (Bass, Mid, Treble, Presence/Air), 128-sample UPOLS WAV IR convolution (`slider52` mode, `slider53` slot 0..9), 3-profile IIR Cabinet mode, and master output stage.
5. `sepulchre_presets.jsfx-inc` (96 lines) — Bitmask routing validator (`validate_routing`), WAV IR name lookup table (`get_ir_slot_name`), and parameter tables for 7 global presets (calibrated strictly to `[-10.0, -8.0] dBFS`).
6. `sepulchre_ui.jsfx-inc` (256 lines) — "Crypt" necro-monochrome theme (`#090909` void, `#E8E3D7` bone values, `#A39E94` labels, `#841216` blood engaged toggles, `#B01C22` ember LEDs), resolution-independent scaling (`ui_begin` / `ui_S`, `gfx_ext_retina = 1`), 2x Retina background/title sprite loaders (`ui_load_images`, `ui_draw_background`, `ui_title`), `auto_slider(id, end_touch)` helper, and widgets (`ui_seg`, `ui_toggle`, `ui_power_led`, bipolar dB `ui_hslider`, `ui_meter` with `-48/-24/-12/-6/0` ticks, gate threshold marker, and `-10..-8 dBFS` target band, `ui_led`, and preset dropdown).
7. `sepulchre_ui_panels.jsfx-inc` (211 lines) — Crypt 8-stage stone-slab layout (`I INPUT` → `II..V` swappable slots with hover `<`/`>` move arrows → `VI AMP` → `VII CABINET` → `VIII OUTPUT`) with 28% alpha bypass dimming, vertical column distributor (`lay_begin` / `lay`), and header with live `8x OVERSAMPLED / IR LATENCY` readout (`ui_header`).
8. `sepulchre_bg.jpg` & `sepulchre_titles.png` — `2408×1000` (2x Retina) Crypt stone-slab + black-metal logo background and 2x Cinzel stage title / Roman numeral (`I..VIII`) sprite sheet.

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

## Round 42 architecture (supersedes the routing / Pre-EQ / Grit / IIR-cab notes below)
- **Fixed chain (amp FX loop):** Input & Gate → [GE-7 if *Pre Pedal*] → Pedal → [GE-7 if *Post Pedal*, default] → Amp → **CE-2 Chorus → Reverb** → Cab (WAV IR) → Air → Master → −1 dBFS limiter. The 5 routing slots (`slider5..8, 74`) are gone. EQ position is `slider76` {Before Pedal, After Pedal}.
- **Removed:** Input Pre-EQ (`slider13..15`; presets that used it now carry an equivalent GE-7 *Pre Pedal* curve), Lo-Fi Grit (`slider16`), cab source switch (`slider52`) and IIR profiles 2x12 / Damped (`slider50`). The IIR 4x12 survives only as the silent fallback when no IR file loads. The UI then says "IR MISSING: BUILT-IN 4x12". It is also the loudness reference behind `IR_E48`.
- **Chorus = Boss CE-2** (`slider20` on, `slider77` Rate 0..10 → 0.1..3.5 Hz log, `slider78` Depth 0..10 → BBD sweep 3 ms + 0.3..5 ms). Per ElectroSmash: triangle LFO; wet path 48 Hz HPF → 3rd-order 6.6 / 6.9 kHz anti-alias LPF → BBD → same reconstruction LPF; dry + wet 50/50 (×0.78 for unity RMS). Mono like the pedal (same LFO on L/R). Old chorus sliders 21..25 removed.
- **UI columns (Round 43):** I INPUT · II DISTORTION · III EQUALIZER (preset selector, PRE / POST PEDAL switch, 8 faders) · IV AMP · V CHORUS · VI REVERB · VII CABINET (IR slot only) / VIII OUTPUT (Air, Master, meter). Design space back to 1204×500 with the original 7-slab background (2408×1000).
- **Round 52 — cab sim removed, TS-808 dropped.** No cabinet in the plugin: WAV IR engine (UPOLS), IR slots (`slider53`), Cabinet enable (`slider49`), IIR 4x12 fallback, per-slot / per-pedal IR trims and PDC are gone; the plugin reports zero latency. Follow it with an IR loader (Devin: Ugritone TRVE Cab with the same Old School Black Metal IRs). Output = amp / FX loop → Air → Master → −1 dBFS safety limiter; raw preset peaks −13.8..−5.3 dBFS, below the −3.1 dBFS knee (verify check [5/6]). The old IIR 4x12 lives on only in the Python mirror as a reference cab so the presets stay level-matched (−10..−8 dBFS through it). `sepulchre_dsp_amp_cab.jsfx-inc` renamed `sepulchre_dsp_amp.jsfx-inc` (`init_amp_dsp`, `reset_amp_state`, `update_amp_coeffs`, `proc_amp`, `proc_output`). UI: column VII is OUTPUT only (Air, Master, meter); background regenerated without the OUTPUT band. The Round 50 TS-808 boost was removed before it shipped.
- **Delay removed (Round 43):** sliders 30..36, `proc_delay`, its 2×192000-float buffers and filters (memory top now 327,680).

## 3. DSP Specifications

### 3.1 Module 0 — Input & Tremolo-Picking Gate
- **Input Trim:** `-12.0` to `+18.0 dB` (`slider1`, 20 ms 1-pole smoothed).
- **Pre-Cut HPF:** 12 dB/oct Butterworth high-pass (`40`–`180 Hz`, `slider2`).
- **Noise Gate:** `180 Hz` detector HPF (`bq_gate_det`) into peak envelope follower (`1.5 ms` attack, `45 ms` release), **5 dB hysteresis** (`gate_thresh_open` vs `gate_thresh_close`), **25 ms hold counter** (`gate_hold_samples`), `3 ms` open / `35 ms` exponential release, plus post-distortion hiss reduction keyed from `gate_gain`.

### 3.2 Module 1 — Four Pedal Models (8x Oversampled) — `sepulchre_dsp_dist.jsfx-inc`
- **Principle:** each pedal follows its real circuit's topology and exposes only its real knobs (0..10, dedicated automatable sliders; the distortion column shows only the selected pedal's controls). Signal units are volts (1.0 = 1 V). Nonlinear stages run at 8x (8th-order Butterworth up/down @ 16.5 kHz); passive tone stacks run at 1x. Circuit sources: ElectroSmash (RAT, DS-1), Electric Druid (MT-2), mirosol / Premier Guitar / BOSS (HM-2). These are behavioural models, not SPICE-accurate.
- **Pedal select (`slider11`):** `0 RAT`, `1 DS-1`, `2 Metal Zone`, `3 HM-2`.

| Pedal | Topology modelled | Knobs (slider) |
| :--- | :--- | :--- |
| RAT | LM308 non-inverting stage: gain branches 1+Rd/560 above 60 Hz and +Rd/47 above 1.54 kHz (Rd 0–100k audio taper, 0–67 dB), GBW 316 kHz and 100 pF feedback limits, ±4 V rails, 0.3 V/µs slew → 1N914 pair (±0.6 V) → passive Filter LPF 32 kHz → 475 Hz | Distortion (26), Filter (27), Volume (28) |
| DS-1 | 33 Hz HPF → Q2 booster ×56 (asymmetric supply clip) → op-amp 1+Rd/4.7k on a 72 Hz shelf (0–26.5 dB, B taper), 100 pF feedback LPF, ±4 V rails → 7.2 kHz LPF → 1N4148 pair (±0.7 V) → Big-Muff tone (234 Hz LP / 1063 Hz HP blend, −12 dB) | Dist (29), Tone (37), Level (38) |
| Metal Zone | 106 Hz HPF → op-amp 3b gyrator, 960 Hz, +36 dB (63×), pole Q 1.66 → 7.2 kHz LPF → ±4 V rails → ½ divider + 680 Hz LPF (R045/C031) → 48 Hz HPF → op-amp ×2..×252 with 47 pF LPF → rails → Si pair (±0.65 V, soft knee, +80 mV offset for the measured even harmonics) → post-clip shelf LPF (5 kHz, −10 dB max) → 9 kHz LPF → fixed transistor-limited gyrators 105 Hz +4 dB / 4.9 kHz +6 dB (pole Q 1.0) → Low (110 Hz, Q 1.5, ±16 dB), High (3 kHz shelf, ±16 dB), Middle (±12 dB, Q 1.2, 300 Hz–4 kHz log) | Dist (39), High (46), Low (47), Middle (48), Mid Freq (59), Level (61) |
| HM-2 | (Round 23, per Atomium Amps' analysis of a 1990 HM-2) 40 Hz HPF → Q6/Q7 pregain ×1..3 (+ swings 2× −) → IC1B TS-style stage: x + diode-clipped (×3..63 above 720 Hz), 9 kHz LPF, then IC1B drive ×1..10 into ±4 V rails (Distortion up removes IC1B feedback; Round 27) → D6/D7 germanium coring (0.3 V dead band: buzz and decay sputter) → C16 8 kHz roll-off → D8/D9 shunt pair → Color Mix at 8x: Low gyrator 88 Hz (Q 1.2, ±16 dB), High = 920 Hz + 1200 Hz gyrators (Q 2.0, ±9 dB each) → EQ op-amp rails ±3.5 V (clip with High maxed) | Distortion (62), Low (63), High (64), Level (9) |

- **Pre-EQ moved to INPUT (sliders 13–15):** Low shelf 160 Hz ±12 dB, Mid 850 Hz ±14 dB, High shelf 2.6 kHz ±12 dB, before every pedal.
- **GRIT moved to OUTPUT (slider 16, "Lo-Fi Grit"):** sample-hold + quantize after the cabinet, before Air/Master.
- **Post-gate:** pedal output × input gate's `gate_gain` (closes fully).
- **Targets:** in-band (20 Hz–8 kHz) aliasing ≤ −40 dB for RAT / DS-1 / Metal Zone at preset settings; HM-2 with every knob on 10 ≤ −34 dB (model: RAT −54.7, DS-1 −49.2, MT-2 −58.4, HM-2 −47.0). Presets peak −10..−8 dBFS (model −8.45..−9.21). Default Level knobs (RAT 6.7, DS-1 8.9, MT-2 7.5, HM-2 4.4) are loudness-matched: each pedal at its defaults through the default amp/cab measures −20 ±0.2 LUFS (K-weighted) on the synthetic DI, so switching pedals doesn't jump in volume. Every pedal filter keeps pole Q ≤ 3.5 at all knob extremes (`check_no_resonant_filters`; worst 1.95).
- **Gyrator EQs:** use `gyro_peak()` (constant pole Q on boost, zero Q on cut). Never put a high-gain RBJ `bq_peak` in a pedal path: its Q is not the pole Q (pole Q = Q × 10^(dB/40)), which is what made the Round 9 MT-2 ring.

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

### 3.5b Module 4 — GE-7 Graphic EQ (Round 31)
- **Model:** Boss GE-7 style 7-band graphic EQ: bands 100 / 200 / 400 / 800 / 1600 / 3200 / 6400 Hz, ±15 dB each (`slider66..72`), Level ±15 dB (`slider73`), Enable `slider65` (default off). Bands are RBJ peaks with fixed Q 1.0. Like the pedal's gyrator bands they are reciprocal boost/cut, and pole Q rises with boost (1.0 flat → ~2.4 at +15 dB), all checked by `check_no_resonant_filters`. Bypass crossfades over ~20 ms; filters clear once fully bypassed.
- **Routing:** fifth swappable slot. Slots A..E = `slider5, 6, 7, 8, 74`, each `0..4 {Distortion, Chorus, Delay, Reverb, EQ}`. New default order Distortion → EQ → Chorus → Delay → Reverb, which presets also recall. `validate_routing()` repairs duplicates and out-of-range values by keeping first occurrences and filling the gaps, so pre-Round-31 projects load with EQ appended last and their custom order intact.
- **UI:** design space widened to 1376×500 (background `sepulchre_bg.jpg` 2752×1000 with 8 slabs; titles sprite adds EQUALIZER (row 16) and IX (row 17)). The EQ slab uses GE-7-style vertical faders (`ui_vslider`): double-click resets to 0 dB, Shift for fine drag, mouse wheel 0.5 dB steps, and the readout shows the hovered band. Stage numerals: I INPUT, II–VI slots, VII AMP, VIII CABINET, IX OUTPUT.
- **Record EQ presets (Round 34):** `slider75` {Custom, Bathory '84, Deathcrush '87, Transilvanian Hunger '94, Nightside Eclipse '94, Filosofem '96, In Sorte Diaboli '07, Evangelion '09}. GE-7 settings read off Devin's reference photos (approximate, about ±1.5 dB). The `<` `>` selector at the top of the EQ slab loads one and turns the EQ on; routing and other modules are untouched. Moving a fader marks the name with `*`. Choosing a preset from REAPER's slider list or automation also loads it (`@slider`); on project load, saved fader values win (`eq_last_preset` is seeded in `@init`). Global presets reset `slider75` to Custom. **Round 35:** each preset's Level is the loudness match (minus the mean LUFS rise of its curve over the 4 pedals, with amp Tube and amp Off), not the photo's +3. Round 39 re-centred them on the default WAV IR cab: Bathory −3.5, Deathcrush −1.5, Transilvanian −0.5, Nightside −4.5, Filosofem −6, In Sorte +0.5, Evangelion −3.5 (about 2–3 dB louder than flat on the IIR cab). Amp OFF now applies −1.5 dB (×0.84) to match Tube loudness.

### 3.6 Module 5 — Amp Stage, WAV IR Loader / IIR Cabinet & Limiter
- **Amp Stage (`slider54`):** `0 = OFF`, `1 = TUBE HEAD` (asymmetric cathode/plate saturation), `2 = SOLID-STATE` (crisp MOSFET rail clip), followed by a **10 Hz 1-pole DC blocker** (`amp_dc_x1`/`amp_dc_y1`), `Bass` (`125 Hz`), `Mid` (`520/620 Hz`), `Treble` (`2.4 kHz`), and `Presence/Air` (`3.8 kHz`).
- **WAV IR Convolution (`slider52` Mode + `slider53` File Index):** `slider52` selects `0 = IIR Cabinet` or `1 = WAV IR Convolution`. `slider53` strictly indexes WAV files `#0..#9` (`01_BlackWizard_Center.wav` .. `10_PlagueBearer_Center.wav`) from `%APPDATA%\REAPER\Data\sepulchre_irs\` via `file_riff()`. File I/O (`load_ir_slot()`) runs strictly off the audio thread (`@init`, `@slider`, `@gfx`), while `@block` runs `prepare_ir_fft()` and reports `pdc_delay = ir_chunk_size` (`2048` samples) when WAV IR convolution is active.
- **WAV IR default & loudness match (Round 19):** `slider52` defaults to `1` (WAV IR); with no IR files the engine falls back to the IIR cab automatically (`ir_filter_len = 0`). Global presets no longer force `slider52`. `prepare_ir_fft()` scales each IR so its weighted energy (cab HPF → 90 Hz HP → 500 Hz +12 dB low shelf → 6 kHz LP) equals `IR_E48 × 48000 / srate`, the same measure of IIR profile 0 (`IR_E48 = 0.283543`, checked by `check_ir_loudness_constant`). Fit error over 4 pedals × 11 test IRs: 1.6 dB rms, 4.9 dB worst (extreme synthetic IRs).
- **Low-latency convolution (Round 20):** uniformly partitioned overlap-save (UPOLS): block `CV_B = 128` samples, `CV_N = 256`-point complex FFT, up to 16 partitions (IRs up to 2048 taps after resampling), L/R packed as real/imag of one complex FFT. Latency = `CV_B` = 128 samples (2.7 ms @ 48 kHz; was 2048 samples / 43 ms), reported via `pdc_delay = ir_chunk_size`. `ir_fft_kern` holds the kernel spectra, `ir_blk_cur` the frequency-domain delay line, `ir_blk_last[8192..]` the frame / accumulator / temp / output blocks. Algorithm validated in NumPy against direct convolution (max error 2e-14, delay exactly 128).
- **Per-slot IR trim (Round 22):** `get_ir_slot_trim_db(idx)` applies −(slot LUFS − IIR cab LUFS) from Antigravity's Round 21 render (−2.13..+1.85 dB) on top of the weighted-energy match, so the 10 bundled IRs land within about ±0.3 dB of the IIR cab. Re-measure if an IR file is replaced.
- **Ear-match offset (Round 23):** `IR_MATCH_DB = 3.8` shifts every WAV IR against the IIR cab. LUFS said they matched; Devin heard WAV IR as quieter and ear-matched it at +3.8 dB (Round 25). Consequence: in WAV IR mode, preset peaks sit about 3–4 dB above the −10..−8 dBFS IIR target (about −6 dBFS), still well under the −1 dBFS limiter.
- **Per-pedal WAV IR trim (Round 29):** `ir_ped_g` applies RAT −0.8, DS-1 +3.1, MT-2 0.0, HM-2 −0.6 dB to the WAV IR output (0 dB with the distortion bypassed). This brings each pedal's WAV IR − IIR LUFS delta to the Metal Zone's ear-matched ~+3.4 dB (Antigravity Round 28 table). Bright pedals lose more to a real IR than to the IIR cab's 2.85 kHz peak.
- **Master Ceiling Limiter:** `limit_sample(x, 0.89125)` is **linear below `-3.1 dBFS` (`0.70`)** (Round 30; was −6 dBFS, which WAV IR mode's −7..−4 dBFS peaks were hitting) and uses a $C^1$ cubic knee above it to clamp peaks at exactly **`-1.0 dBFS` (`0.89125`)**.

---

## 4. Global Preset Catalog (`slider60`)

| # | Preset Name | Distortion | Amp Stage | Chorus | Delay | Reverb | Cab / Peak |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | **01: TIGHT RHYTHM** | Metal Zone (Dist 7, Mid 6.5 @ ~950 Hz) | Tube Head | Bypass | Bypass | Hall (15%) | 4x12 (model `-9.19 dBFS`) |
| 1 | **02: COLD LEAD** | RAT (Dist 7.5, Filter 3) | Tube Head | Analog BBD (36%) | Tape 390ms (28%) | Plate (24%) | 2x12 (model `-9.18 dBFS`) |
| 2 | **03: DOOM WALL** | HM-2 (8.5 / Low 8 / High 7.5) | Tube Head | Dimension (28%) | Tape 520ms (28%) | Ambient (34%) | Damped (model `-8.99 dBFS`) |
| 3 | **04: RAW 4-TRACK** | DS-1 (Dist 8.5, Tone 7) + Grit 40% | Solid-State | Bypass | Tape 140ms (18%) | Bypass | 2x12 (model `-8.85 dBFS`) |
| 4 | **05: SWEDISH CHAINSAW** | HM-2 (all on 10) | Solid-State | Bypass | Bypass | Plate (14%) | 4x12 (model `-8.83 dBFS`) |
| 5 | **06: FREEZING CLEAN** | Bypass (+3.5 dB In) | Tube Head | Analog BBD (48%) | Digital 440ms (32%) | Hall (34%) | 2x12 |
| 6 | **07: AMBIENT SWELL** | RAT (Dist 6.5, Filter 4) | Tube Head | Dimension (40%) | Tape 580ms (38%) | Ambient (46%) | Damped (model `-8.99 dBFS`) |

---

## 5. Roadmap
- [x] Initialize Git repository, `AGENTS.md`, and `SPEC.md`.
- [x] Implement core DSP, FX, Presets, UI, and main JSFX entry.
- [x] Replace proprietary labels with direct hardware/effect names and add 7-preset dropdown menu.
- [x] Resolve Round 1 items (`REVIEW.md` items 1–11).
- [x] Resolve Round 2 & Round 3 items (`REVIEW.md` R2-1 through R2-6, R3-1, R3-2, live REAPER render harness):
  - [x] **R2-1:** Remove `recall_global_preset(slider60)` from `@init` and `@slider` so REAPER project reloads preserve user parameter edits.
  - [x] **R2-2:** Clamp delay feedback (`!en ? fb = min(fb, 0.75)`) when bypassed so `100–105%` self-oscillation decays to silence.
  - [x] **R2-3:** Report `pdc_delay = ir_chunk_size` (`pdc_bot_ch = 0; pdc_top_ch = 2`) in `@block` when WAV IR convolution is active.
  - [x] **R2-4 & R3-1:** Separate Cabinet Source Mode (`slider52`: IIR vs WAV IR) from WAV file index (`slider53`: `#0..#9`), trigger `ir_reload_req` on UI edits, and display IR cabinet names (`get_ir_slot_name`).
  - [x] **R2-5:** Use `slider_automate(2 ^ (id - 1), end_touch)` for `id <= 30` and direct `slider_automate(sliderN, end_touch)` for `id > 30`.
  - [x] **R2-6 & R3-2:** Upgrade 4x oversampler to 8th-order Butterworth (`48 dB/oct` @ `16.5 kHz`) + `C^2` 2-stage saturation (`-48.39 dB` in-band `20 Hz–8 kHz`, `-47.76 dB` all-bin pre-cabinet aliasing).
- [x] Implement Round 5 & Round 6 "Crypt" necro-monochrome UI redesign (`D-1` through `D-11`):
  - [x] Split UI into `sepulchre_ui.jsfx-inc` (theme, scaling, image/sprite loaders, widgets) and `sepulchre_ui_panels.jsfx-inc` (8 numbered stone-slab stages `I–VIII`, `lay_begin`/`lay` column layout, hover `<`/`>` move arrows), add 2x Retina background (`sepulchre_bg.jpg`) and Cinzel title/numeral sprite sheet (`sepulchre_titles.png`), remove redundant per-module `P1/P2/P3` rows, and add bipolar `±dB` EQ sliders and gate threshold meter markers.

---

## 6. Decisions Log
| Date | Decision | Why |
| :--- | :--- | :--- |
| 2026-10-28 | Split implementation into `sepulchre_sound.jsfx` and 6 `.jsfx-inc` files | Keeps every file under the 300-line limit along clear DSP, Amp/IR, Preset, UI primitives, and UI panel boundaries. |
| 2026-10-28 | Deploy runtime JSFX to `%APPDATA%\REAPER\Effects\sepulchre_sound\` and curated WAV IRs to `%APPDATA%\REAPER\Data\sepulchre_irs\` | Matches REAPER's native JSFX and `/sepulchre_irs` WAV file-slider discovery paths. |
| 2026-10-28 | Defer UI coefficient recalculation to `@block` (`ui_need_sync`) and call `auto_slider(id, end_touch)` on user edits | Prevents audio-thread/UI-thread race conditions on biquad coefficients and records touch/latch DAW automation with proper bitmask/symbol and end-touch release. |
| 2026-10-28 | Upgrade 4x oversampler to 8th-order Butterworth (`16.5 kHz`) + `C^2` 2-stage saturation (`soft_tanh` clamped at `±3.0`) | Preserves full `10–16 kHz` passband for WAV IRs and Presence/Air while achieving `-48.39 dB` (`20 Hz–8 kHz`) and `-47.76 dB` (`0–24 kHz`) pre-cabinet aliasing. |
| 2026-10-28 | Adopt Claude's Round 5/6 "Crypt" necro-monochrome UI (`1204×500` scaled via `ui_S`, 2x Retina `sepulchre_bg.jpg` + `sepulchre_titles.png`, numbered stages `I–VIII`, 28% alpha bypass dimming, bipolar `±dB` EQ) | Solves contrast, visual hierarchy, black-metal logo/stone-slab atmosphere, scaling on high-DPI displays, and right-column crowding while removing redundant per-module `P1..P3` preset rows. |
| 2026-10-28 | Replace 2-stage soft distortion with cascaded 3-stage high-gain preamp (DRIVE → `20–75 dB`), remove pre-clip LPF, full-close post-gate; re-level preset LEVEL values (Claude Round 7) | Old stage had ~34 dB gain and a 2.9–5.4 kHz LPF before the clippers, so notes cleaned up as they decayed (blues-overdrive behaviour). New stage stays saturated to ~−36 dBFS input; in-band aliasing −41 to −46 dB. |
| 2026-10-28 | Replace the 3-voicing distortion with four pedal models (RAT, DS-1, Metal Zone, HM-2), each with only its real knobs; move Pre-EQ to INPUT and Grit to OUTPUT; distortion oversampling 4x → 8x (Claude Round 9) | Devin couldn't hear RAT vs MODERN (1–2 dB band difference at 60+ dB gain). Modelling each real topology gives 7.6–23 dB band differences; 8x keeps the harsher pedals' aliasing in budget. |
| 2026-10-28 | Rebuild the Metal Zone and HM-2 EQs from circuit data + published measurements; constant-Q gyrator filters; add 680 Hz pre-gain LPF to MT-2 (Claude Round 11) | Devin heard a 'whistle' on the MT-2: the Round 9 pre-hump was an RBJ peak (Q 1.2, +30 dB) whose real pole Q was 6.7, so it rang at 1 kHz. Measured MT-2: 800–900 Hz mid hump at noon, Low/High ±16 dB @ 120 Hz / 4 kHz, Middle ±12 dB 300 Hz–4 kHz. HM-2: 87 Hz / 958 + 1279 Hz gyrators. |
| 2026-10-28 | Loudness-match the four pedals' default Level knobs (−20 LUFS); DS-1 preset Level 8.1 → 8.2 (Claude Round 13) | Devin: DS-1 slightly quieter. Peak matching hid it: the DS-1's bright, peaky output has a higher crest factor, so equal peaks meant lower loudness. Old defaults spanned −31.2 (DS-1) to −16.7 LUFS (HM-2). |
| 2026-10-28 | WAV IR becomes the default cab; IRs loudness-matched to the IIR cab; presets keep the user's cab source (Claude Round 19) | Devin: WAV IR sounds "WAY better… more natural" but its volume didn't match. Old normalisation set raw IR energy to 0.18, ignoring spectral shape; the new one weights by an average distorted-guitar spectrum × K-weighting. |
| 2026-10-28 | Replace the single-block 4096-pt overlap-add IR convolution (43 ms latency) with 128-sample UPOLS (2.7 ms) (Claude Round 20) | Devin plays live through the plugin; 43 ms between pick and sound wrecks timing. |
| 2026-10-28 | Rebuild the HM-2 from Atomium Amps' circuit analysis: TS-style IC1B stage, 0.3 V Ge coring, D8/D9 + C16, EQ at 8x with op-amp rail clipping (Claude Round 23) | Devin: HM-2 "sounds like wet cardboard". The old model had a broadband 2-stage clipper and a 12 mV dead band; the real pedal pushes mids into its first clipper and its germanium coring makes the buzz. Aliasing improved −34.8 → −50.9 dB. |
| 2026-10-28 | HM-2: drive IC1B into its rails before the coring and D8/D9 (Claude Round 27) | Devin: Round 23 HM-2 "still sounds really muffled". Per-stage analysis showed D8/D9 saw only ~2.4 V peaks (about 12 dB of clipping), so it behaved like crunch: fundamentals dominated and the 2–8 kHz harmonics were 6–9 dB lower than a hard-driven clipper. |
| 2026-10-29 | Code + test audit (Claude Round 30): remove dead state and code, fix stale comments and docs, match double-click defaults to slider defaults, re-prepare the IR on sample-rate change, raise the limiter knee to −3.1 dBFS, drop two tests that never read the plugin source, tighten HM-2 aliasing to −40 dB | Devin asked for an audit for leftovers, bugs and needless tests. |
| 2026-10-29 | Add a Boss GE-7 style 7-band graphic EQ as a fifth swappable slot; widen the UI to 1376 px (Claude Round 31) | Devin wants an EQ pedal in the chain. The GE-7 is the classic metal EQ: before the dirt it tightens and boosts what gets distorted; after it, it carves the distorted tone. |
| 2026-10-29 | Act on the Round 38 audit (Gemini, via Antigravity): fx pointer syntax, distortion on/off crossfade, Amp OFF state clear, time-based IR length (42.7 ms at any rate), host-automatable global preset, dclip p = 2.5 without pow, EQ preset Levels re-centred on WAV IR (Claude Round 39) | Valid findings fixed. Rejected: sliderchange(slider74) is the documented sliderX form; the pre+post gate is deliberate; the mono fast path stays deferred (state hand-off). |
| 2026-10-29 | Simplify (Claude Round 42): fixed chain with chorus / delay / reverb in the amp FX loop; GE-7 Pre/Post switch replaces the routing slots; remove Input Pre-EQ, Lo-Fi Grit and the IIR cab mode (kept as a fallback); chorus rebuilt as a Boss CE-2 | Devin: "i'm wondering now if we've overcomplicated this." Three overlapping EQs, five routing slots and two cab modes were more than a black metal rig needs. Reverb and delay now also skip the amp's distortion. |
| 2026-10-29 | Remove the delay (Claude Round 43); UI back to 7 columns / 1204 px | Devin: "delay is probably overkill we can axe that". |
| 2026-10-30 | TS-808 boost added (Claude Round 50), then removed (Round 52) | Devin asked for the "Drive 0 / Tone 5 / Level 10" trick, then judged it overkill next to the GE-7 Pre position: "let's get rid of the cab sim and the TS-808". |
| 2026-10-30 | Remove the cab sim (Claude Round 52); the plugin ends at Air / Master / limiter, IR loader goes after it | Devin owns TRVE Cab (8 IR slots with level / pan / filters / phase per slot). One IR at a time could not match it, the Ugritone IRs could not ship anyway, and removing it drops the 128-sample latency. |
