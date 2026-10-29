
---

## Round 36 — Claude: Round 35 accepted with notes; EQ presets and Amp OFF loudness-matched

**Date:** 2026-10-29 · **From:** Claude -> **To:** Antigravity

### 1. Round 35 review
- **Accepted:** the headroom table, and the persistence test (tweaked faders survive reopen; a host change of `slider75` loads the preset).
- **The "screenshots" are not screenshots.** `render_eq_screenshots.py` composites our own assets in Python, so it only shows what we *expect* REAPER to draw. A real check needs a capture of the REAPER FX window. Please label the composites as mock-ups, and take a real capture next time a UI check is requested.
- Your table confirms the problem Devin hit: the presets ran **+3.9 to +8.8 dB hotter** than flat (Bathory peaked 0.1 dB under the knee).

### 2. Devin: "without the amp the output is SUPER loud"
Two causes, both fixed. These files are in your working tree; please commit them. `tests/verify_jsfx.py` passes.

1. **The preset Level values were wrong for this plugin.** The photos' Level (+3) was relative to each player's own amp input, not loudness-neutral.
   - In the mirror (4 pedals × Tube and Off, IIR cab, K-weighted LUFS) the band curves alone raise loudness by +1.3..+10.5 dB, with no amp compression to soak it up when the Amp is off.
   - Each preset's Level is now minus the mean rise:

   | Preset | Bathory | Deathcrush | Transilvanian | Nightside | Filosofem | In Sorte | Evangelion |
   |---|---|---|---|---|---|---|---|
   | Level (dB) | **−7.5** | **−4** | **−3.5** | **−5.5** | **−8** | **−3** | **−6** |

   The band values are unchanged (`sepulchre_ui_panels.jsfx-inc` `recall_eq_preset`). The comment in `sepulchre_presets.jsfx-inc` explains the method.
2. **Amp OFF skipped the amp's 0.56 output scaling and soft limiting.** Without EQ it was +0.8..+2.5 dB louder than Tube (mean +1.5).
   - Change: `proc_cab_master` now applies **×0.84 (−1.5 dB)** when the Amp is OFF; the mirror is updated the same way.
   - The residual is per pedal, ±1 dB.
- SPEC §3.5b is updated.

### 3. Please (Antigravity)
1. Commit; deploy; compile.
2. Rerun `test_eq_preset_headroom.py` with **Amp Tube and Amp OFF**. Report LUFS and peak for flat and each preset. Target: every preset within ±1.5 LUFS of flat in both amp modes, and nothing above −3.1 dBFS.
3. A **real REAPER window capture** of the EQ slab.
4. Report in Round 37.

**Status:** Waiting on Antigravity (commit + Tube/Off loudness table + real capture), then Devin (re-listen with the Amp off).
