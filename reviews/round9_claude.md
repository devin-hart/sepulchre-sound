## Round 9 — Claude: Four Pedal Models (base commit `bbb2283`)

**Date:** 2026-10-28 · **From:** Claude -> **To:** Antigravity · **Requested by:** Devin

### Why
Devin couldn't hear a difference between RAT and MODERN. At 60+ dB of gain both voicings saturate into nearly the same wave, so they differed by only 1–2 dB per band. Devin asked for the distortion to be **four real pedals, each acting like the pedal it's modelled after, with only that pedal's knobs shown**: RAT, DS-1, Metal Zone, HM-2. MODERN is dropped (the VI AMP stage covers amp-style tone). Pre-EQ moves to the INPUT column and GRIT moves to OUTPUT. The release will be free; names stay as-is for now.

### What I changed (written to `D:\VSTs\sepulchre_sound\`, all files < 300 lines)
| File | Change |
| --- | --- |
| `sepulchre_sound.jsfx` | `slider11` is now `{RAT,DS-1,Metal Zone,HM-2}`. New per-pedal sliders (0..10): RAT 26/27/28, DS-1 29/37/38, Metal Zone 39/46/47/48/59/61, HM-2 62/63/64/9. `slider12` (Drive) and `slider17` (Output) removed. 13–15 renamed Pre-EQ Low/Mid/High; 16 renamed Lo-Fi Grit. All slider numbers stay ≤ 64, so the render harness's `range(1, 65)` still covers them. |
| `sepulchre_dsp_dist.jsfx-inc` | **Rewritten.** Four circuit-topology models, nonlinear parts at **8x** (was 4x) via per-channel `instance()` functions (`pdL.rat_os()`, `pdR.ds_os()`, …), base-rate tone stacks, DC blocker, pedal Level, post-gate. Details in SPEC.md §3.2. |
| `sepulchre_dsp_core.jsfx-inc` | Allocates `bq_dist_p1..p6`. Pre-EQ coefficients in `update_core_coeffs()`; Pre-EQ applied at the end of `proc_input_gate()`. |
| `sepulchre_dsp_amp_cab.jsfx-inc` | Lo-Fi Grit (`slider16`) after the cab, before Air/Master. |
| `sepulchre_ui.jsfx-inc` | `auto_slider()` covers the new ids above 30. `ui_hslider` bipolar mode is now centred on (min+max)/2; `bip_k == -1` shows Metal Zone MID FREQ in Hz. |
| `sepulchre_ui_panels.jsfx-inc` | Distortion column: RAT / DS-1 / MT-2 / HM-2 selector, a one-line circuit caption, then only that pedal's knobs. INPUT: TRIM, LOW CUT, EQ LOW/MID/HIGH, gate toggle, THRESHOLD with gate-state LED, INPUT meter (POST-DRIVE meter dropped for space). OUTPUT: AIR, LO-FI GRIT, MASTER, meter. |
| `sepulchre_presets.jsfx-inc` | Presets remapped: Tight Rhythm → Metal Zone, Cold Lead → RAT, Doom Wall → HM-2, Raw 4-Track → DS-1 + 40% grit, Swedish Chainsaw → HM-2 all on 10, Ambient Swell → RAT. Pedal Level knobs calibrated with the model (−8.8 to −9.2 dBFS). |
| `tests/verify_jsfx.py` | `simulate_chain()` now mirrors the four pedal models line for line (`pedal_setup()`, `pedal_os()`), plus Pre-EQ and Grit. Level check covers presets 0–4 **and 6**. Aliasing check runs **each pedal**: ≤ −40 dB in-band, except HM-2 with every knob on 10 (≤ −34 dB). Gain-curve guard kept. Passes: RAT −54.7, DS-1 −49.2, Metal Zone −64.0, HM-2 −36.2 dB. |
| `AGENTS.md`, `SPEC.md` | Code map, §3.2 rewritten (per-pedal topology table + sources), §4 preset table, §6 decision row. |

The models are behavioural (component values from ElectroSmash, Electric Druid and HM-2 write-ups, linked in SPEC.md), not SPICE-accurate.

### Asks for Antigravity
- [ ] **Commit** all files above plus `REVIEW.md` and `reviews/round9_claude.md`. Suggested message: `DSP+UI: four pedal models (RAT, DS-1, Metal Zone, HM-2) with real knobs, 8x OS, Pre-EQ to INPUT, Grit to OUTPUT, presets remapped (Claude Round 9)`.
- [ ] **Deploy + compile in REAPER.** New EEL2 features in use: `instance()` functions called through namespaces (`pdL.` / `pdR.` / `tfL.` / `tfR.`). If anything doesn't compile, fix it, keeping the maths identical, and list exactly what changed.
- [ ] **Run** `verify_jsfx.py` and the render harness; report the real-render preset peaks (presets 0–4, and 6 if you extend the harness), DC, and aliasing. Audio won't null against `bbb2283` (expected).
- [ ] **CPU:** report the plugin's CPU % from REAPER's Performance Meter with each pedal selected (8x oversampling costs more).
- [ ] **Only if** a real-render preset peak falls outside −10..−8 dBFS: adjust that preset's pedal **Level** knob only, and report old → new.

### Then
I'll check the new distortion column in REAPER, and Devin will audition the four pedals on a real DI.

**Status:** Waiting on Antigravity (commit, deploy, compile, render, CPU report).
