## Round 50 — Claude: Round 49 accepted; TS-808 boost added

### Round 49
Accepted. The stale-slider fixes and the slider-id guard are what Round 48 asked for, and the numbers match R40.

### New: TS-808 boost in front of the pedal
Devin asked for the Tube Screamer trick: Drive 0, Tone 5, Level 10 into the distortion for a tighter attack.

**Chain:** Gate → [GE-7 Pre] → **TS-808** → Pedal → [GE-7 Post] → Amp → …

**Sliders** (all default to the trick setting; every global preset turns the TS off and resets these knobs):

| Slider | Control | Range | Default |
|---|---|---|---|
| `slider79` | Enable | Off / On | 0 |
| `slider80` | Drive | 0..10 | 0 |
| `slider81` | Tone | 0..10 | 5 |
| `slider82` | Level | 0..10 | 10 |

**DSP** (`sepulchre_dsp_dist.jsfx-inc`: `update_ts_coeffs`, `ts_os`, `ts_tone`, `reset_ts_state`, `proc_ts`). It runs at 4x with its own 8th-order Butterworth up/down filters, `bq_ts_up1..4` and `bq_ts_dn1..4`, allocated in core.
- **IC1 stage:** `x + dclip(LP51pF(G * HP720(x)), 0.6, 2.5)`, then `sclip(·, 4)`.
  - `G = (51k + 500k * a_taper(Drive)) / 4.7k`, so G = 11.9 at Drive 0.
  - The 51 pF pole sits at 1 / (2π · Rf · 51 pF).
- **Tone:** a 723 Hz one-pole LPF (`lt`), output `lt + hg * (x - lt)`, with `hg` from −14 dB (Tone 0) through −2 dB (5) to +10 dB (10).
- **Level:** `a_taper(Level)`, unity at 10.
- **Bypass:** a 20 ms crossfade (`ts_mix_s`); state is cleared once fully off.
- **Transport start:** `reset_ts_state()` runs and `ts_mix_s` snaps to its target.
- `c1r(fc, rate)` is now the shared one-pole helper; `c1x` and `c1b` call it.

**UI:** I INPUT gains a `TS-808 ON/OFF` toggle and a `DRV / TONE / LVL` readout below the meter, using `lay_begin(190, 7)`. Drive, Tone and Level are host parameters only (REAPER's parameter list / automation). `auto_slider` now covers ids up to 82.

**Python mirror:** `TubeScreamer` class, applied in `simulate_chain` when `slider79` is on.
- Check [3/7] now also runs every pedal with the TS in front:
  - RAT: −43.6 dB
  - DS-1: −42.3 dB
  - MT-2: −55.0 dB
  - HM-2: −48.4 dB
- New check [7/7] (trick voicing, small signal): 82 Hz +4.5 dB, 1 kHz +18.5 dB, so the mid push is 14.0 dB. Aliasing at Drive 10 is −43.8 dB.
- `verify_jsfx.py` passes. Preset levels are unchanged because the TS is off in every preset.

**Mirror, IIR cab, TS off → on** (peak / RMS, dB):

| Preset | Peak off | Peak on | RMS off | RMS on |
|---|---|---|---|---|
| 0 | −8.92 | −8.43 | −22.39 | −21.13 |
| 1 | −9.26 | −7.83 | −20.76 | −19.56 |
| 2 | −9.48 | −7.80 | −16.95 | −16.47 |
| 3 | −8.62 | −8.37 | −23.38 | −22.14 |
| 4 | −9.54 | −9.23 | −18.37 | −18.54 |
| 5 (clean) | −18.04 | −11.54 | −28.80 | −21.15 |
| 6 | −8.74 | −6.72 | −18.55 | −17.30 |

With a pedal on, the TS adds 0–1.3 dB RMS; that is real behaviour and needs no make-up. Into the clean amp (preset 5) it is a +7.6 dB overdrive, which is expected.

### Line counts
| File | Lines |
|---|---|
| `sepulchre_sound.jsfx` | 172 |
| `sepulchre_dsp_core.jsfx-inc` | 224 |
| `sepulchre_dsp_dist.jsfx-inc` | 249 |
| `sepulchre_dsp_fx.jsfx-inc` | 195 |
| `sepulchre_dsp_amp_cab.jsfx-inc` | 256 |
| `sepulchre_presets.jsfx-inc` | 112 |
| `sepulchre_ui.jsfx-inc` | 260 |
| `sepulchre_ui_panels.jsfx-inc` | 227 |

Total: 1,695.

### For Antigravity (Round 51)
1. Deploy, then recompile in REAPER and confirm there are no compile errors.
2. Add sliders 79..82 to the `render_common` slider-id guard.
3. `test_mirror_null`: add a TS-on case for all four pedals (79 = 1, other TS knobs at defaults). Report the null in dB; expect around −130 dB like the pedal-only nulls.
4. TS toggle click test: toggle `slider79` mid-note and report the max sample jump, the same way as the GE-7 toggle test.
5. Loudness: run TS off/on per pedal at default knobs on the WAV IR path and report the LUFS delta. Expect about +0..1.5 dB. Do not recalibrate anything.
6. CPU: REAPER performance meter with pedal only vs pedal + TS, at 64 samples.
7. UI: only claim it is verified with a real REAPER FX-window capture. Otherwise write "UI not visually verified".
