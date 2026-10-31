## Round 52 — Claude: Round 51 noted; cab sim removed, TS-808 dropped (supersedes Round 50)

Devin: "let's get rid of the cab sim and the TS-808". He owns Ugritone TRVE Cab: 8 IR slots, with level, pan, HP/LP and phase on each slot. Playing one IR at a time could not match it. The Ugritone IRs could not ship anyway, and removing the cab removes the plugin's only latency.

### Round 51 (Antigravity) and the TS-808 (Round 50)
Thanks for the TS verification; the nulls and the click test were clean. Devin then decided the TS was overkill, so it is reverted completely. The code is back to the Round 49 state: sliders 79..82, `proc_ts` and the `TubeScreamer` mirror are gone. Antigravity: skip every Round 50 task.

### Cab removal
**Gone:**
- the UPOLS convolution engine, IR file loading, `prepare_ir_fft`, `conv_block`;
- the IR name and file tables, per-slot trims, `IR_E48`, `IR_MATCH_DB`, per-pedal `ir_ped_g`;
- the IIR 4x12 fallback, `slider49` (Cabinet Enable), `slider53` (IR Slot);
- the `ir_reload_req` path and PDC. `pdc_delay = 0` is set in `@init`.

**New layout:**
- `sepulchre_dsp_amp_cab.jsfx-inc` is renamed to **`sepulchre_dsp_amp.jsfx-inc`** (82 lines).
- Functions: `init_amp_dsp`, `reset_amp_state`, `update_amp_coeffs`, `proc_amp` (unchanged) and `proc_output` (Air → Master → limiter → meter).
- Chain: Input/Gate → [GE-7 Pre] → Pedal → [GE-7 Post] → Amp → Chorus → Reverb → Air → Master → −1 dBFS safety limiter. The IR loader goes after the plugin.
- No level constants changed.

**UI:**
- Column VII is now OUTPUT only: header "VII OUTPUT", then Air, Master, the meter, and a tiny "NO CAB: USE AN IR LOADER" note.
- The header readout always shows "ZERO LATENCY".
- `sepulchre_bg.jpg` was regenerated from the same generator without the OUTPUT band in slab VII.

**Mirror (`tests/verify_jsfx.py`):**
- The IIR 4x12 survives only as a reference cab (`ref_cab=True`), so preset calibration stays at −10..−8 dBFS through it. Those numbers are unchanged.
- The IR_E48 check is replaced by **[5/6] raw output headroom**. Every preset with no cab must peak below the −3.1 dBFS limiter knee. Measured:
  - presets 0..6 raw peaks: −7.92, −8.35, −9.13, −5.29, −8.81, −13.78, −8.22 dBFS;
  - so the limiter never touches the signal going into TRVE Cab.
- Source invariants:
  - zero PDC;
  - `load_ir_slot`, `prepare_ir_fft`, `conv_block`, `slider49`, `slider53` and `proc_cab_out` must not come back.
- Memory map: 52 buffers, top 165,211 floats.

### Line counts
| File | Lines |
|---|---|
| `sepulchre_sound.jsfx` | 144 |
| `sepulchre_dsp_core.jsfx-inc` | 222 |
| `sepulchre_dsp_dist.jsfx-inc` | 198 |
| `sepulchre_dsp_fx.jsfx-inc` | 195 |
| `sepulchre_dsp_amp.jsfx-inc` | 82 |
| `sepulchre_presets.jsfx-inc` | 96 |
| `sepulchre_ui.jsfx-inc` | 256 |
| `sepulchre_ui_panels.jsfx-inc` | 211 |

Total: 1,404 (was 1,625).

### For Antigravity (Round 53)
1. `git rm sepulchre_dsp_amp_cab.jsfx-inc` (Claude can't delete files from here).
   - Also delete the stale copy in REAPER's Effects folder so an old include can't load.
   - Leave `Data\sepulchre_irs\` alone; they are Devin's files.
2. Deploy, recompile, and confirm:
   - no compile errors;
   - the plugin reports 0 PDC samples;
   - the FX window has no IR selector.
3. Render tests:
   - remove sliders 49 and 53 from every test and from the `render_common` slider-id guard;
   - retire `test_exact_ir_null`;
   - `test_mirror_null` should null against `simulate_chain(..., ref_cab=False)`.
4. **Report only, change nothing.** Measure per-pedal loudness through the real IRs. Render each pedal at its default knobs (amp Tube), convolve offline in Python with `01_BlackWizard_Center.wav`, and report LUFS per pedal.
   - The removed `ir_ped_g` trims (RAT −0.8, DS-1 +3.1, MT-2 0, HM-2 −0.6 dB) evened this out. Without them, the DS-1 may sit about 3 dB under the others in TRVE Cab.
   - If so, Devin decides whether to move those trims into the pedal Levels.
5. UI: write "UI not visually verified" unless you have a real REAPER FX-window capture.
