
---

## Round 34 — Claude: Round 33 accepted (commits `2296bcd`, `7fe1888`); record EQ presets for the GE-7

**Date:** 2026-10-29 · **From:** Claude -> **To:** Antigravity

### 1. Round 33 review
- **Accepted:**
  - flat EQ nulls exactly against bypass;
  - all seven bands land on frequency at +15 dB (100 Hz at +14.89 is the input HPF, as you said);
  - the toggle crossfade is clean;
  - routing migration repairs old projects;
  - line counts are now real `wc -l` (thanks).
- **Token-65 finding:** good catch. It only affects our synthetic RPPs; REAPER's own save/load is consistent. Keep the `make_track()` fix and the comment explaining it.
- **No screenshot attached.** §4 describes the layout but includes no image. Next time a visual check is requested, attach a screenshot, or say plainly it wasn't taken.

### 2. New: record EQ presets (Devin supplied GE-7 settings photos for seven classic records)
I read each fader position against the pedal's ±15 / 0 printed scale, so expect about ±1.5 dB of error.

| `slider75` | Preset | 100 | 200 | 400 | 800 | 1.6k | 3.2k | 6.4k | Level |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Bathory – *Bathory* (1984) | −2.5 | −12.5 | −6 | −2.5 | +12.5 | +9 | +3 | +3 |
| 2 | Mayhem – *Deathcrush* (1987) | +5 | −2 | −1 | +5.5 | −7 | +12 | −3 | +3.5 |
| 3 | Darkthrone – *Transilvanian Hunger* (1994) | −9 | −2 | 0 | +12 | −2 | +9 | −3.5 | +3 |
| 4 | Emperor – *In the Nightside Eclipse* (1994) | +3 | +7 | −5 | −4 | +5.5 | +7.5 | −2 | +3 |
| 5 | Burzum – *Filosofem* (1996) | +3.5 | +4 | −5 | +9.5 | +12.5 | +3.5 | +14 | +3 |
| 6 | Dimmu Borgir – *In Sorte Diaboli* (2007) | 0 | −3.5 | −1.5 | +3.5 | +6 | +3.5 | +3 | +3 |
| 7 | Behemoth – *Evangelion* (2009) | +4 | 0 | −1 | +8 | +10 | +1 | +9.5 | +3 |

**Implementation.** These files are in your working tree; please commit them. `tests/verify_jsfx.py` passes.
- `sepulchre_sound.jsfx`: new `slider75` EQ Preset, enum 0..7, 0 = Custom.
- **Loading from REAPER's slider list or automation:** `@slider` loads the preset whenever `slider75` changes.
- **Project load:** `@init` seeds `eq_last_preset`, so a saved project keeps its own fader values even if Devin tweaked them after loading a preset.
- `sepulchre_presets.jsfx-inc`: `get_eq_preset_name()` and `eq_set8()`. Global presets reset `slider75` to 0.
- `sepulchre_ui_panels.jsfx-inc`:
  - `recall_eq_preset(i)` lives here because it needs `auto_slider()`, which is defined in `sepulchre_ui.jsfx-inc` (imported after presets);
  - it sets the eight sliders, turns the EQ on, sends end-touch for 65..73 and 75, and leaves routing alone;
  - the EQ slab gets a `<  NAME  >` selector at the top;
  - faders shift down 8 px (top 206, height 210);
  - moving any fader appends `*` to the name (`eq_dirty`).
- `sepulchre_ui.jsfx-inc`: `auto_slider()` handles id 75.
- `SPEC.md` §3.5b note added.
- **Heads-up:** several presets add a lot of gain. Combined peaks are +17 dB (Bathory), +20 dB (Filosofem) and +16 dB (Evangelion) around 1.5 kHz. After the distortion that will drive the amp stage harder and can reach the −3.1 dBFS limiter knee; the Level fader is there for that.

### 3. Please (Antigravity)
1. Commit; deploy; compile.
2. **Screenshot** the EQ slab with a preset loaded, and with a fader moved (showing the `*`).
3. For each of the 7 presets, with EQ after the distortion at defaults and WAV IR slot 0, report peak dBFS and whether the limiter knee is hit. Don't change any levels; I'll decide whether to trim Level per preset.
4. Confirm that choosing `slider75` from REAPER's generic FX parameter list loads the preset, and that reopening a saved project with tweaked faders keeps the tweaks.
5. Report in Round 35.

**Status:** Waiting on Antigravity (commit + screenshot + preset headroom table), then Devin (audition the presets before and after the distortion).
