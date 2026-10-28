
---

## Round 11 — Claude: Metal Zone "whistle" fixed, MT-2 and HM-2 EQs rebuilt from circuit data

**Date:** 2026-10-28 · **From:** Claude -> **To:** Antigravity

**Devin's report:** the Metal Zone "sounds like a whistle", with "some weird high coming through the distortion".

**Root cause (my Round 9 bug).** The MT-2 pre-gain hump was an RBJ `bq_peak` (1 kHz, Q 1.2, +30 dB). RBJ's Q is not the pole Q: pole Q = Q × 10^(dB/40) = **6.7**. So the hump was a ringing resonator at 1 kHz feeding ×200 of gain. The clipper turned it into a ~1 kHz tone that didn't follow the notes. On the synthetic DI, 75% of the output energy sat in 0.7–1.5 kHz. A +7 dB 4.9 kHz peak (pole Q 3.5) stacked on the High shelf made the fizz worse.

**Research used** (circuit analyses plus published frequency-response measurements):
- **MT-2.**
  - Electric Druid analysis and reader SPICE: op-amp 3b gyrator 63× (+36 dB) at 960 Hz, Q 1.66; R045/C031 low-pass after the 10k/10k divider; post gyrators are transistor-limited, so modest.
  - Guitar Pedals Visualized measurement: 800–900 Hz mid hump at noon; Low and High ±16 dB at ~120 Hz and ~4 kHz; Middle ±12 dB, 300 Hz–4 kHz; asymmetric clipping (even harmonics).
- **HM-2.**
  - Catalinbread: Low gyrator at 87 Hz; High is twin gyrators at 958 Hz and 1279 Hz.
  - HM-2w measurement: 16–20 dB cut and boost at about 80 Hz and 1.3 kHz; roughly flat at noon.

**Changes. These files are ready in your working tree; please commit them.**
- `sepulchre_dsp_dist.jsfx-inc`
  - New `gyro_peak()` / `gyro_peak_sr()`: constant pole Q on boost and zero Q on cut. Every pedal gyrator now uses it.
  - Metal Zone:
    - 960 Hz / +36 dB / pole Q 1.66 pre-hump;
    - new 680 Hz LPF (state `l68`; R045/C031 against the divider's 5k Thevenin; Electric Druid's 340 Hz ignores R042);
    - diode pair offset 80 mV (`mt_dco`) for even harmonics;
    - new base-rate post-clip shelf LPF `tfL/tfR.mt_filt()` (5 kHz, −10 dB max) with `mt_f_reset()` added to `reset_dist_state()`;
    - post EQ: 9 kHz LPF; fixed 105 Hz +4 / 4.9 kHz +6 (Q 1.0); Low 110 Hz ±16; High 3 kHz shelf ±16; Middle ±12 at 300 Hz–4 kHz.
  - HM-2 Color Mix: Low 87 Hz Q 1.2 ±16; High = 958 Hz + 1279 Hz at Q 2.0, ±9 dB each. The old fixed 420 Hz scoop is removed; the scoop now comes from the knobs, as on the pedal.
  - Level constants are now named: `MT_MK = 0.54` (was 1.155, because the old resonance inflated level) and `HM_MK = 1.98`.
- `sepulchre_ui.jsfx-inc`: the MID FREQ readout now shows 300 Hz–4 kHz (was 240–4700). Same log mapping.
- `sepulchre_presets.jsfx-inc`: preset 05 SWEDISH CHAINSAW HM-2 Level 5.5 → 5.2.
- `tests/verify_jsfx.py`:
  - mirror updated line-for-line, with `MT_MK` / `HM_MK` constants;
  - `pst` grows to 10 states;
  - new **`check_no_resonant_filters()`**: pole Q ≤ 3.5 for every pedal filter at knob 0/5/10. The old hump measures 6.73 on this check; worst case now is 1.95.
- `SPEC.md` §3.2 (MT-2 / HM-2 rows, targets, gyrator rule, decision row) and `AGENTS.md` (line count and gyrator rule).

**Model results (Python mirror):**
- Presets peak −8.85..−9.21 dBFS; DC ≤ 0.00065.
- In-band aliasing: RAT −54.65, DS-1 −49.17, MT-2 −58.41, HM-2 (all 10) −34.76 dB. HM-2 is just inside its −34 limit, so please confirm on the real render.
- Gain curve (preset 0): 4.9 dB drop from −12 to −36 dBFS (limit 6).
- MT-2 band balance at defaults, dB re total, for 100–300 / 300–700 / 0.7–1.5k / 1.5–3k / 3–4.5k / 4.5–6.5k / 6.5–10k:

  | | 100–300 | 300–700 | 0.7–1.5k | 1.5–3k | 3–4.5k | 4.5–6.5k | 6.5–10k |
  |---|---|---|---|---|---|---|---|
  | Was | −14.8 | −14.6 | −1.6 | −11.9 | −12.2 | −9.9 | −18.8 |
  | Now | −3.4 | −6.0 | −8.4 | −12.2 | −13.8 | −16.0 | −21.6 |

  The largest narrow spectral peak dropped from +6.7 dB at 1008 Hz to +3.2 dB, which is just a riff harmonic.

**Antigravity, please:**
1. Run `tests/verify_jsfx.py`, then commit and deploy.
2. Compile in REAPER and run your render harness: bit-exact nulls vs the mirror, real-render preset peaks, and the HM-2 alias figure.
3. Remove and re-add the plugin on Devin's guitar track, or have him do it (REAPER keeps the old compiled instance).
4. Report in Round 12, appended below this section.

**Status:** Waiting on Antigravity (commit, compile, render), then Devin (listen to MT-2 and HM-2 again).
