## Round 56 — Claude: Round 55 accepted; headstone logo, black metal preset bank, UX fixes

### Round 55
Accepted: the restore is clean and matches Round 49. I merged your `ref_cab` change to `simulate_chain` into my version of `verify_jsfx.py`.

### Devin's requests
A new logo ("lettering carved into a headstone") and a usability audit: "a simple plug in and start ripping black metal… we need some really good presets". He picked logo A and approved the preset bank and the fixes below.

### Changes
1. **Logo.** `sepulchre_bg.jpg` was regenerated: "SEPULCHRE" in Cinzel 700, V-cut carved into the stone texture.
   - Method: a height field from the distance transform, lit from the top left, with frosted grooves like cut granite.
   - The slab geometry is unchanged, including the OUTPUT band in VII. The old blackletter logo is gone.
2. **New 10-preset bank** (`sepulchre_presets.jsfx-inc`, SPEC §4):
   - Frostbitten (DS-1), Tremolo Rhythm (MT-2), Raw 4-Track (DS-1), Buzzsaw (HM-2), Atmospheric Wall (RAT);
   - Depressive (RAT), Modern Black (MT-2), Cold Lead, Freezing Clean, Ambient Swell.
   - Doom Wall and Swedish Chainsaw were removed.
   - `slider60` is now 0..9. `GP_COUNT = 10`.
3. **Record curves in global presets.** The GE-7 record table moved to `eq_preset_vals(i)` in presets. `gp_eq(n)` loads a curve with EQ on, after the pedal.
   - Frostbitten uses Transilvanian, Buzzsaw uses Bathory, Atmospheric Wall uses Filosofem, Modern Black uses Evangelion.
   - `recall_eq_preset` in panels now calls `eq_preset_vals`.
   - `recall_global_preset` sets `eq_last_preset`, so `@slider` doesn't re-trigger an EQ recall.
4. **Loudness matching instead of peak matching.** Check [2/7] now requires every preset (including Clean) to have K-weighted RMS of −21 ± 1 dB and peak ≤ −6 dBFS through the reference cab. Masters were set by the mirror.
   - The old peak window let presets differ by about 6 dB in loudness.
   - Freezing Clean needed Trim +5 and Master +6 (the Master ceiling).
5. **Fresh insert = preset 01.** All 36 sliders preset 01 sets now have it as their default. New check [7/7] fails on any mismatch.
6. **< > preset buttons** left of the preset bar (`draw_preset_dropdown_bar`). The bar is now x 998, w 188, and the menu shows `GP_COUNT` rows.
7. **INPUT meter target zone, −18..−6 dBFS.**
   - `ui_meter`'s `target` argument now means: `< 0` draws a band from target to target + 12 dB. The old `-10..-8` mode was unused.
   - The presets are tuned for input peaks around −12 dBFS, and the pedals respond to input level because they're modelled in volts.
8. **`@serialize`** saves `preset_dirty` and `eq_dirty`, so the "edited" asterisks survive a project reload.

`verify_jsfx.py`: all 7 checks pass.
- Loudness −21.04..−20.96 dB.
- Aliasing: RAT −52.0, DS-1 −51.8, MT-2 −56.9, HM-2 all-10 −60.9 dB.
- Pole Q 2.62.

### Line counts
| File | Lines |
|---|---|
| `sepulchre_sound.jsfx` | 169 |
| `sepulchre_dsp_core.jsfx-inc` | 222 |
| `sepulchre_dsp_dist.jsfx-inc` | 198 |
| `sepulchre_dsp_fx.jsfx-inc` | 195 |
| `sepulchre_dsp_amp_cab.jsfx-inc` | 256 |
| `sepulchre_presets.jsfx-inc` | 155 |
| `sepulchre_ui.jsfx-inc` | 263 |
| `sepulchre_ui_panels.jsfx-inc` | 216 |

Total: 1,674.

### For Antigravity (Round 57)
1. Deploy, including the new `sepulchre_bg.jpg`. Then recompile and confirm there are no compile errors.
2. **Real loudness per preset.** Render all 10 presets on `di_input.wav` through the WAV IR path (slot 0), with chorus and reverb active as in each preset.
   - Report integrated LUFS and true peak per preset, and the spread.
   - The mirror doesn't model chorus or reverb, so 05, 06, 09 and 10 may come out louder. Flag any preset more than 1.5 dB from the median.
   - Flag any preset that touches the −3.1 dBFS limiter knee.
   - Change nothing.
3. Fresh insert: add the plugin to a new track and confirm the header reads "01: FROSTBITTEN" with no asterisk. Confirm < and > step through all 10 and wrap around.
4. `@serialize`: tweak a knob, save, reload, and confirm the asterisk is still there.
5. Render tests: update `render_common` for `slider60` 0..9 and the new slider defaults. Update the headroom test's preset list.
6. UI: capture the real REAPER FX window if you can (logo, < > buttons, INPUT zone). Otherwise write "UI not visually verified".
