# Round 67 — Claude: independent code audit

**Scope:** all 8 JSFX files (1,691 lines), `tests/verify_jsfx.py`, `tests/render/render_common.py`. I didn't read Antigravity's Round 67 report before writing this one.
**Method:** I read every source file, then checked the suspected issues against the code and with small scripts (slider and default cross-check, undeclared-slider scan, IR file formats). No code was changed.
**Environment:** Linux (Manjaro), REAPER at `/usr/bin/reaper`. `verify_jsfx.py` passes 7/8; [8/8] is skipped because numpy isn't installed.

Severity: **High** = wrong sound or lost user settings in normal use. **Medium** = audible glitch or wrong state in a reachable case. **Low** = cleanup, cosmetic, or docs.
Status: **Confirmed** = follows from the code with no host assumptions. **Plausible** = depends on REAPER behaviour I couldn't test here.

---

## High

### H1. Changing the IR slot to a missing file keeps playing the old IR, and the UI says the new one is loaded — Confirmed
`sepulchre_dsp_amp_cab.jsfx-inc:74-95`, `sepulchre_ui_panels.jsfx-inc:186-188`
- If `file_open` fails, `load_ir_slot()` sets `ir_raw_len = 0` and `ir_loaded_slot = new`. It does not set `ir_need_refft` and does not clear `ir_filter_len`. Only `slot_idx < 0` clears it, and that never happens.
- So the old kernel keeps playing, with the old slot's trim.
- The UI decides on `ir_filter_len > 0`, so it shows the new slot name and "SLOT k / 10". It never shows "IR MISSING".
- `ir_loaded_slot` is already the new index, so nothing retries the load.
- **Scenario:** an IR file is renamed, deleted, or not copied on a new machine (likely after the move to Linux). The player picks that slot and hears the previous cab, with a label claiming otherwise.
- **Fix:** on a failed open, set `ir_filter_len = 0` (fall back to the IIR 4x12). That way the audio and the label agree.

### H2. A REAPER user preset or undo can be overwritten by the factory bank — Plausible
`sepulchre_sound.jsfx:105`, `sepulchre_presets.jsfx-inc:77-163`
- `@slider` calls `recall_global_preset()` whenever `slider60 != gp_last`. REAPER sets all slider values at once and then runs `@slider` for a preset load from the FX window's preset menu, for undo/redo, and for a pasted parameter set. All of these go through the same path.
- **Scenario:** the player is on 01, chooses 05 and tweaks it, then saves it as a REAPER user preset "My Wall" (slider60 = 4). Later, on another preset, they load "My Wall". REAPER restores every slider, including slider60 = 4. Then `@slider` sees 4 != gp_last and recalls factory preset 05 over the saved tweaks.
- Undo across a preset change can do the same.
- `slider75` (EQ preset) has the same pattern at line 103, so saved GE-7 faders can be replaced by the record curve.
- **Not verified in REAPER.** Test: save a user preset after editing a factory preset, switch away, reload it, and compare the sliders.
- **Fix:** only treat the change as a "recall" when slider60 is the only slider that changed since the last `@slider`. Keep a snapshot of the preset-owned sliders and compare against it. Otherwise just set `gp_last = slider60`.

### H3. Every global preset turns the built-in cab back on — Confirmed (needs a decision)
`sepulchre_presets.jsfx-inc:81` (`slider49 = 1;`)
- Round 54 kept the Cabinet switch so TRVE Cab (an external IR loader) can be used with the built-in cab off.
- Each preset recall forces it back on, so a TRVE Cab user gets two cabs in series the moment they browse presets.
- SPEC §4 says "the IR slot is left as the player set it". The cab on/off switch isn't.
- **Question for Devin:** should presets leave `slider49` alone like `slider53`? I recommend yes. The bank is already checked with the cab off (verify [2/8] prints the cab-off peaks).

---

## Medium

### M1. Reverb bypass makes a hard step in the dry level — Confirmed
`sepulchre_dsp_fx.jsfx-inc:191-192`
- The dry gain is `1 - (en ? reverb_mix_s * 0.45 : 0)`, and `en` switches instantly. `reverb_mix_s` only smooths toward the Mix knob, not toward on/off.
- At Mix 46% (preset 10), turning the reverb off steps the dry signal from 0.793 to 1.0 (+2.0 dB) in one sample, and turning it on steps back down. That's a discontinuity, so a click on sustained notes.
- **Fix:** smooth an `rev_en_s` with `param_smooth_c` and use it in place of `en` in the dry term.

### M2. Turning the cab back on plays stale audio — Confirmed
`sepulchre_dsp_amp_cab.jsfx-inc:226-243`
- While `slider49` is off, `cv_frame`, `cv_out` and the frequency-domain delay line keep whatever was in them when the cab was switched off.
- On re-enable, the first 128 samples come from `cv_out` (audio from that moment, possibly minutes ago). Then up to 42 ms of the old tail is convolved in.
- PDC also jumps 0 → 128 at the same time.
- The IIR fallback filters have the same issue on a smaller scale.
- **Fix:** when the cab is switched on, clear `ir_blk_cur`, `ir_blk_last` and `ir_bpos` (the same reset as transport start). Optionally crossfade.

### M3. Global preset recall from the UI only notifies the host about slider60 — Plausible
`sepulchre_ui.jsfx-inc:247-248, 267`
- `recall_global_preset()` writes about 40 sliders, but only `auto_slider(60, 1)` is called.
- REAPER's generic parameter list, control surfaces and automation lanes in touch/latch mode aren't told about the others. Whether the project is marked dirty or undo captures them is host-dependent.
- `recall_eq_preset()` does it right: it calls `auto_slider` for each slider it sets.
- **Fix:** call `auto_slider(k, 1)` for every slider the preset writes. A list loop is enough; `sliderchange()` is the lighter alternative.

### M4. Changing the IR from the UI does file I/O on the audio thread — Confirmed (contradicts AGENTS §1)
`sepulchre_ui.jsfx-inc:139` → `sepulchre_sound.jsfx:112-115`
- `set_param(53)` sets `ir_reload_req`, and `@block` then calls `load_ir_slot()` (`file_open`, `file_riff`, `file_mem`). AGENTS §1 says `load_ir_slot()` "must never run on `@block`".
- The file is small (44.1 kHz mono, 1 s) and usually in the OS cache, so a dropout is unlikely but possible on a cold disk.
- The design is a trade-off: loading in `@gfx` would race `prepare_ir_fft()` on `ir_raw_buf`.
- **Decision needed:** either change the rule in AGENTS to match the code (I recommend this, with the reason written down), or load in `@gfx` into a second buffer and hand it over with a flag.

### M5. Double-click resets don't match the slider defaults (16 sliders) — Confirmed
`sepulchre_ui_panels.jsfx-inc:38, 42, 106-108, 124-125, 153-156, 170-172, 192-193`
- Round 30 matched these, but Round 56 changed the slider defaults to preset 01 and the UI defaults weren't updated.
- The biggest one is **Master**: a double-click sets −0.5 dB against the −3.8 default, so it jumps +3.3 dB louder.

| Slider | Default | Double-click |
| :-- | --: | --: |
| 2 Low Cut | 140 | 105 |
| 3 Gate Threshold | −50 | −52 |
| 29 / 37 / 38 DS-1 Dist / Tone / Level | 10 / 7.5 / 8 | 9 / 6.5 / 8.9 |
| 77 / 78 CE-2 Rate / Depth | 4.5 / 4 | 4 / 6 |
| 42 / 43 / 44 / 45 Reverb | 1.8 / 20 / 60 / 10 | 2.0 / 18 / 64 / 15 |
| 55 / 56 / 57 Amp B / M / T | 40 / 50 / 66 | 54 / 44 / 62 |
| 58 Air | 66 | 64 |
| 51 Master | −3.8 | −0.5 |

- The DS-1 Level 8.9 is the Round 13 per-pedal loudness-matched default. If that's the intent for the pedal knobs, keep the pedal values and fix the rest.
- **Test gap:** verify [7/8] checks slider defaults against preset 01 but never checks the UI's `dflt_v`. Parsing `ui_hslider(...)` calls the same way would catch it.

### M6. Switching pedals isn't crossfaded, and the new pedal resumes from stale state — Confirmed (how loud is unverified)
`sepulchre_dsp_dist.jsfx-inc:41, 169-172`
- `dist_ped` switches the nonlinear core instantly.
- The incoming pedal's `pdL`/`pdR` instance (HPF, gyrator, slew and integrator state) still holds whatever it had the last time that pedal was selected. The oversampling filters carry the outgoing pedal's state.
- **Scenario:** a preset change or pedal click while playing gives a click or a short DC thump. The on/off switch has a 20 ms crossfade (Round 39); pedal changes don't.
- **Fix:** at minimum, reset the incoming pedal's instance when `dist_ped` changes. Better: a short fade out, switch, fade in using `dist_mix_s`.

---

## Low

- **L1. RAT GBW constant: 43 vs 47.**
  - `sepulchre_dsp_dist.jsfx-inc:48` uses `1 + rd / 43` for the branch-B GBW pole, while `rat_kB = rd / 47` (line 45) and SPEC §3.2 say 47 Ω.
  - At full Distortion that moves the pole from about 148 to 136 Hz.
  - The Python mirror copies 43 (`verify_jsfx.py:285`), so no test can tell. Either it's a typo, or it's intentional and needs a comment.
  - **General test caveat:** the mirror re-types the DSP constants, so it catches regressions but not transcription errors.
- **L2. Dead code.**
  - `slider74` in `auto_slider` (`sepulchre_ui.jsfx-inc:132`); the slider was removed in Round 42 and it's the only undeclared slider referenced.
  - Unused helpers: `ui_led`, `c_flame`, `c_ink`, `u_frame` (defined, never called).
  - `FRESH_INSERT_DEFAULTS` in `tests/render/render_common.py:26` is unused and stale: it has `51: -5.4`, but the default is −3.8.
- **L3. The amp tone readouts don't show the actual dB.**
  - `panel_amp` shows `(val − 50) × k`, but the DSP adds fixed offsets: Mid −1.0 (Tube) / −2.5 (Solid), Treble +1.5 (`sepulchre_dsp_amp_cab.jsfx-inc:168-169`).
  - At noon the UI says 0.0 dB while the filter is at −2.5 / +1.5. That's fine if "0" means "voiced flat", but it's worth knowing.
- **L4. `preset_dirty` (the `*`) only tracks plugin-UI edits.** Edits from REAPER's generic sliders, automation or control surfaces don't mark the preset edited.
- **L5. CPU.**
  - The Metal Zone's `dclip(…, 1.8)` takes the general `pow` path: 2 `pow` calls × 8x × 2 channels = 32 per sample.
  - The chorus runs even when bypassed (by design, for click-free engage).
  - Neither is a bug. They're the first places to look if CPU becomes a complaint.
- **L6. IR resampling is linear interpolation with no anti-alias filter.** Harmless for the bundled IRs (all 44.1 kHz mono, 1 s; all 10 present in `~/.config/REAPER/Data/sepulchre_irs/`). A 96/192 kHz IR in a 44.1/48 kHz project would alias slightly, and `ir_raw_len ≤ 4096` cuts a 192 kHz IR to 21 ms.
- **L7. Fonts on Linux.** `Bahnschrift` and `Consolas` aren't installed (`fc-list` finds neither), so REAPER substitutes. The Round 66 PLATE/AMBIENT width measurement (Windows) doesn't apply here, and the layout should be checked again on this machine.
- **L8. Docs.**
  - SPEC §1–3 still describe the pre-Round-42 plugin: routing slots, delay, Pre-EQ, Grit, IIR cab mode, 7 presets, a 720,896-float memory map (the verifier reports 327,680).
  - The AGENTS code map has the same problem; the "Round NN" notes at the bottom correct it.
  - The AGENTS thread-safety rule contradicts the code (M4).

---

## Checked and fine
- **Memory map:** every buffer fits at 192 kHz: chorus 8 ms of 8,192; pre-delay 60 ms of 16,384; combs up to 9,472 of 12,288; FFT kernel and delay line exactly 64 × 512 = 32,768 at 192 kHz.
- **Limiter knee:** C1-continuous (value and slope meet `L` at t = 1.5).
- **Coefficient order:** `sync_all_DSP` updates the distortion before the amp/cab, so `ir_ped_g` sees the current `dist_ped`.
- **Real-IR mirror [8/8]:** reads `IR_MATCH_DB`, the slot-0 trim and the per-pedal trims from the source rather than retyping them.
- **Automation:** `auto_slider` covers every declared slider above 30.
- **Reverb resizing:** when a comb shrinks, its index wraps within one sample.
- **Sample-rate changes:** `ext_noinit` with the `last_srate` check in `@block` re-prepares the IR as intended.

## Suggested order
H1 → H3 (one-line answers, the first needs Devin's call) → M1, M2 (small, audible) → H2 (needs a REAPER test first) → M5 (+ the test) → M3, M6 → M4 decision → Low items.

## Not verified
- None of this was run in REAPER. H2 and M3 depend on host behaviour.
- The click severity for M1, M2 and M6 isn't measured.
- verify [8/8] was skipped (no numpy).
