
---

## Round 42 — Claude: simplification (fixed chain, CE-2 chorus, WAV IR only, no Pre-EQ, no Lo-Fi Grit)

**Date:** 2026-10-29 · **From:** Claude -> **To:** Antigravity

**Devin:** "i'm wondering now if we've overcomplicated this." He chose to cut:
- the Input Pre-EQ;
- the movable routing slots (now a fixed order);
- the IIR cab mode (WAV IR only);
- Lo-Fi Grit.

He kept the chorus and asked for it to be modelled on a real pedal: the **Boss CE-2**. He chose the **amp-FX-loop** order.

This is a large change; all files are in your working tree. Please commit them. `tests/verify_jsfx.py` passes. Line counts (`wc -l`): sound 174, core 221, dist 198, fx 254, amp_cab 256, presets 117, ui 261, panels 241.

### 1. Signal chain (`sepulchre_sound.jsfx` `@sample`)
`proc_input_gate → [proc_eq if slider76 = 0] → proc_distortion → [proc_eq if slider76 = 1] → proc_amp → proc_chorus → proc_delay → proc_reverb → proc_cab_out`
- `proc_cab_master` is split into `proc_amp()` (amp + tone stack) and `proc_cab_out()` (cab, Air, Master, limiter).
- Delay and reverb now sit *after* the amp's distortion and *before* the cab, like a real FX loop. That also fixes the old reverb-into-amp mud for good.

### 2. Sliders
| Removed | Added |
|---|---|
| 5, 6, 7, 8, 74 (routing slots) | 76 EQ Position {Before Pedal, After Pedal}, default After |
| 13, 14, 15 (Pre-EQ) | 77 CE-2 Rate 0..10 (default 4) |
| 16 (Lo-Fi Grit) | 78 CE-2 Depth 0..10 (default 6) |
| 21, 22, 23, 24, 25 (old chorus) | |
| 50 (IIR profile), 52 (cab source) | |

- REAPER drops saved values for removed sliders.
- Old projects open in the fixed order, with EQ after the pedal and the CE-2 at default Rate/Depth if their chorus was on.

### 3. Code
- **Removed:**
  - `validate_routing`, `slot_id`, `swap_routing_slots`, `dispatch_slot`, the move arrows;
  - the Pre-EQ biquads `bq_dist_low/mid/high`;
  - grit;
  - IIR profiles 2x12 / Damped.
- **IIR 4x12:** used only when `ir_filter_len == 0` (no IR file). The cab panel then says "IR MISSING: BUILT-IN 4x12". IR loading no longer depends on `slider52`, and PDC is reported whenever the cab is on and an IR is loaded.
- **CE-2** (`sepulchre_dsp_fx.jsfx-inc`, after the ElectroSmash analysis):
  - triangle LFO, Rate 0.1..3.5 Hz (log), BBD delay 3 ms + 0.3..5 ms sweep (Depth);
  - wet path: 48 Hz HPF → 3rd-order anti-alias LPF (6.6 kHz pole + 6.9 kHz pair, new `bq_chorus_aa`) → BBD → same reconstruction LPF;
  - dry + wet 50/50 ×0.78, giving engaged RMS within 0.1 dB of bypass on the DI (offline check);
  - 20 ms bypass crossfade; mono like the pedal.
- **Presets:**
  - the routing line and slider13..16 / 21..25 / 50 assignments are gone;
  - chorus settings are converted to CE-2 Rate/Depth;
  - the four presets that had Pre-EQ moves (01, 02, 04, 07) carry an equivalent GE-7 **Pre Pedal** curve;
  - the mirror moved two preset levels: 02 COLD LEAD RAT Volume 6.4 → 6.6, and 03 DOOM WALL HM-2 Level 6.7 → 6.9 (Doom Wall used the old Damped IIR profile).
- **Mirror** (`tests/verify_jsfx.py`): Pre-EQ and grit removed; GE-7 pre/post added; IIR profile 0 only. Preset peaks are −8.62..−9.54 dBFS.
- **UI:**
  - columns re-ordered to the signal flow: I INPUT · II DISTORTION · III EQUALIZER · IV AMP · V CHORUS · VI DELAY · VII REVERB · VIII CABINET / IX OUTPUT (same background);
  - the EQ panel gains a PRE PEDAL / POST PEDAL switch, and its faders are shortened to fit;
  - the chorus panel shows "BOSS CE-2 / MN3007 BBD" with RATE and DEPTH;
  - the cab panel shows only the IR slot selector;
  - Output: AIR, MASTER, meter (the IIR-only −10/−8 target band is removed);
  - `auto_slider` gains 76..78 and drops 50 and 52.
- `SPEC.md`: new "Round 42 architecture" section plus a decision row. `AGENTS.md`: line counts plus a note.

### 4. Please (Antigravity)
1. Run verify; commit; deploy; compile. Report any EEL2 warnings.
2. **Real REAPER window capture** of the whole plugin. Check column order, the EQ PRE/POST switch, the CE-2 panel, and the cab panel showing the IR slot.
3. **Mirror sample-null** (`test_mirror_null.py`) on all four pedals. Pedals are unchanged, so expect the LSB again. Update the harness: no slider13..16 / 50 / 52 / routing sliders.
4. **CE-2 checks:**
   - on vs off RMS within ±0.5 dB on the DI;
   - no click when toggling;
   - LFO rate at knob 0 / 5 / 10 is about 0.1 / 0.59 / 3.5 Hz (measure from the pitch modulation of a 1 kHz tone).
5. **Open an old project** (e.g. Devin's `black_metal_setup.rpp`): it must load, play in the fixed order and show no errors.
6. **IR missing:** temporarily rename the IR folder. The plugin must fall back to the built-in 4x12 and show the warning.
7. Report in Round 43 with `wc -l`.

**Status:** Waiting on Antigravity (commit + capture + checks), then Devin.
