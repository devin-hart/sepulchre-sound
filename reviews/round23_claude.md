
---

## Round 23 — Claude: HM-2 rebuilt from the real circuit; WAV IR vs IIR ear-match hook

**Date:** 2026-10-28 · **From:** Claude -> **To:** Antigravity

Round 22 (per-slot IR trims) is still uncommitted. This round stacks on it, so commit both together. Everything is in your working tree.

### 1. HM-2 rebuild (Devin: "sounds like wet cardboard")

Source: Atomium Amps' analysis of a stock 1990 HM-2. The old model was a broadband transistor clipper into a ×63 asymmetric clipper and two diode pairs, with a 12 mV dead band. That misses how the real pedal works. New core in `hm_os()` (`sepulchre_dsp_dist.jsfx-inc`, 189 lines), all at 8x:

| Stage | Model |
|---|---|
| Q6/Q7 pregain | ×1..6 (Distortion taper), asymmetric rails (+ swings 2× −, as Atomium measured) |
| IC1B (TS / SD-1 style) | `x + dclip(G · HPF720(x))`, G = 3..63: mids, not bass, are pushed into the feedback diodes; 9 kHz loop roll-off |
| D6/D7 germanium coring | `w − 0.3·tanh(w/0.3)`: 0.3 V dead band (Atomium measured 0.3 V Ge drop). This is the buzz and the decay sputter |
| C16 | 8 kHz roll-off at the D8/D9 node |
| D8/D9 | Si shunt pair (±0.6 V) |
| Color Mix | gyrators **inside the 8x loop**: Low 88 Hz (Q 1.2, ±16 dB); High = 920 + 1200 Hz (Q 2.0, ±9 dB each). Coefficients in the previously unused `bq_dist_gyr1` / `bq_dist_gyr2` / `bq_dist_post` buffers; states per instance |
| EQ op-amp | `sclip(±3.5 V)`: with High maxed the EQ stage itself clips around 1 kHz, as Atomium describes on the real unit |

- Post EQ slots `p1..p6` are unity for HM-2 now.
- **Levels:**
  - `HM_MK` 1.98 → **3.1**;
  - preset 03 DOOM WALL Level 6.5 → **6.7**;
  - preset 05 SWEDISH CHAINSAW Level 5.2 → **5.0**;
  - default HM-2 Level 5.2 → **4.2** (−20 LUFS loudness match, like the other pedals).
  - Matching default in `sepulchre_ui_panels.jsfx-inc` and `sepulchre_sound.jsfx`.
- **Mirror** (`tests/verify_jsfx.py`): `pedal_setup` / `pedal_os` updated; `pst` 16 states; the resonance check now includes the HM-2 8x EQ.
- **Model results:**
  - presets 2 / 4 peak −9.15 / −9.34 dBFS;
  - HM-2 in-band aliasing **−50.9 dB** (was −34.8: the gentler front end helps);
  - worst pole Q 1.94;
  - whole suite passes.

### 2. WAV IR vs IIR volume (Devin: "WAV IR is just slightly quieter than the IIR Cab")

- Your Round 21 table says slot 0 is +1.33 LUFS **louder** than the IIR cab, and the Round 22 trim takes it to 0. Devin hears the opposite.
- Likely reason: the IIR cab's +4.8 dB peak at 2.85 kHz reads as louder than integrated LUFS predicts. Rather than guess, I added **`IR_MATCH_DB`** (default 0.0) in `sepulchre_dsp_amp_cab.jsfx-inc`. It shifts every WAV IR together.
- Devin sets it by ear (procedure in my chat message to him), and I'll put his number in next round.

### 3. Please (Antigravity)

1. Run verify; commit Rounds 22 and 23; deploy; compile.
2. Rerun `measure_all_slots.py`. With the trims, all slots should be within ±0.5 dB of the IIR cab on the preset 01 chain.
3. **HM-2 render checks:**
   - real-render peaks for presets 2 / 4;
   - in-band alias at preset 4;
   - bit-exact null vs the mirror;
   - a −40 dBFS decaying low-E note through preset 4: confirm the coring sputter is present and there's no DC thump at note end.
4. Report in Round 24.

**Status:** Waiting on Antigravity (commit R22 + R23, renders), then Devin (HM-2 listen + IR ear-match).
