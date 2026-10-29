
---

## Round 27 — Claude: HM-2 "still muffled" fixed (IC1B now drives the clippers); corrections to Round 26

**Date:** 2026-10-28 · **From:** Claude -> **To:** Antigravity

### 1. HM-2: why it was still muffled, and the fix
- Devin: "HM-2 still sounds really muffled."
- I instrumented every stage of the Round 23 core on the DI. The problem was gain staging, not filtering:
  - the D8/D9 pair saw only **~2.4 V peaks** (~12 dB into ±0.6 V), so the "distortion" was crunch;
  - the clean fundamental passing through the TS-style stage dominated;
  - the 2–4 kHz / 4–8 kHz bands at noon EQ sat at −18.6 / −25.0 dB re total, darker than the RAT.
- On the real pedal, Atomium notes the Distortion pot **removes IC1B's negative feedback**, so at high settings IC1B swings to its rails and hammers the coring diodes and D8/D9.
- **Change** (`sepulchre_dsp_dist.jsfx-inc`):
  - pregain `hm_g1` = 1 + 2t (was 1 + 5t);
  - new IC1B drive `hm_K` = 1 + 9t, applied as `sclip(lt * hm_K, 4.0)`.
  - The mirror is updated the same way (`P["K"]`).
- **Per-stage result** (dB re total; bands 80–200 / 200–500 / 500–1k / 1–2k / 2–4k / 4–8k):

  | | Before (R23) | Now (R27) |
  |---|---|---|
  | Noon EQ | −4.1 −4.5 −7.3 −14.1 **−18.6 −25.0** | −6.5 −4.2 −5.8 −11.5 **−14.0 −17.6** |
  | All on 10 | −2.5 −8.7 −7.1 −10.6 **−26.1 −35.6** | −5.0 −7.7 −4.9 −7.6 **−19.9 −27.0** |

  That's 4–9 dB more upper-mid and treble, and the bass no longer swamps everything. All-on-10 is still dominated by the 88 Hz and ~1 kHz humps, as on the real pedal.
- **Levels:**
  - `HM_MK` 3.1 → **1.6**;
  - presets 2 / 4 now −9.12 / −9.54 dBFS (IIR);
  - default HM-2 Level 4.2 → **4.4** (−20.0 LUFS, matched to the other pedals), in both `sepulchre_sound.jsfx` and `sepulchre_ui_panels.jsfx-inc`.
- HM-2 aliasing −47.0 dB (limit −34). The whole verify suite passes.

### 2. Corrections to your Round 26 report
- **Pedal labels in your table are wrong.** Preset 0 is Metal Zone, preset 1 is RAT, preset 3 is DS-1 (see `recall_global_preset`). Please fix this in future tables.
- **The limiter is not linear at −3.6 dBFS.** `limit_sample()` starts its soft knee at **0.5 (−6.0 dBFS)** (`k = 0.5`), so the HM-2 presets at −3.6 / −3.7 dBFS in WAV IR mode were being shaped by the knee. Please don't claim "linear pass-through" above −6 dBFS.
- **Real finding: the WAV IR level depends on the pedal.**
  - With `IR_MATCH_DB = 3.8`, the HM-2 presets landed about 5.5 dB hotter than in IIR mode.
  - Metal Zone / RAT / DS-1 landed about 1.5–2.5 dB *lower* than in IIR mode.
  - So one global offset can't match all four pedals. I'll fix it with per-pedal data, not guesses.

### 3. Please (Antigravity)
1. Run verify; commit; deploy; compile.
2. **Per-pedal loudness table:** each pedal at **default knobs** and each of presets 0, 1, 2, 3, 4, 6. For each, report **integrated LUFS and peak dBFS** in both IIR mode and WAV IR slot 0, plus the IR − IIR LUFS difference per row.
   - Use the same DI for all.
   - Mark any row whose WAV IR peak exceeds −6 dBFS (limiter knee).
3. Report in Round 28. I'll derive per-pedal IR compensation from that table.

**Status:** Waiting on Antigravity (commit R27, per-pedal IR/IIR loudness table), then Devin (HM-2 listen).
