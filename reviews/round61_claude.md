## Round 61 — Claude: Round 60 accepted; "decrepit crypt" redesign (background + widgets)

### Round 60
Accepted. A 0.77 dB loudness spread across all 10 presets, the permanent REAPER gate, and the two machines agreeing on [8/8] are exactly what we needed.

### Devin's request
"make it look like an old moldy tomb/sepulchre", for the whole plugin. He approved the concept and asked to "push it into a more decrepit, ancient look" and theme all the controls too.

### 1. `sepulchre_bg.jpg` (2408×1000, same geometry)
Generated procedurally:
- **Wall:** irregular masonry blocks with chipped edges along the joints and cracks. Damp black-green mold blotches and grey-green moss, heaviest at the top and bottom; pale lichen. Water stains running down from the joints; hanging roots from the top and from under the lintel, kept out of the niches.
- **Logo lintel:** a cracked stone with a broken corner and moss. SEPULCHRE in Cinzel, V-cut, with grime in the grooves.
- **Columns:** the 7 columns are burial niches with rough lips, mold creeping over the edges, and weathered title plates in the 40 px header band and the OUTPUT band. The interiors stay near-black so the controls read clearly.
- **Header:** a recessed niche at top right (x 926–1196, y 10–92) holds the preset bar and readout.

### 2. Widget theme (`sepulchre_ui.jsfx-inc`, `sepulchre_ui_panels.jsfx-inc`)
Drawing only. No hit areas, layout or behaviour changed.
- **Palette:** aged bone (226/214/188), lichen-grey labels, dried blood (92/20/16), candle amber (230/150/62) with flame core, stone (38/36/31). New `c_lip`, `c_shade`, `c_stone` and `c_flame`.
- **Helpers:** `u_carve()` draws a groove cut into the stone (shadow top/left, lit lip bottom/right). `u_raise()` draws raised stone, the reverse.
- **Controls:**
  - `ui_hslider` and the GE-7 `ui_vslider`: chiselled groove, bone dust fill, bone-chip handle with a drop shadow.
  - `ui_seg`: raised stone; selected is an aged-bone plate.
  - `ui_toggle`: raised stone; engaged is pressed in and dried-blood red.
  - `ui_power_led`: a candle flame with a two-step glow; off is an empty carved socket.
  - `ui_meter`: carved groove. The INPUT target zone is now candle amber at 30% (it was blood red, which was invisible on the dark groove).
  - Preset bar, EQ preset box and IR box: carved slots. Preset menu: stone frame.

A Python mock of the full UI (DejaVu standing in for Bahnschrift) was shown to Devin, but it is **not** a REAPER capture.

`verify_jsfx.py` passes 8/8. `sepulchre_ui.jsfx-inc` is 274 lines. Total: 1,693.

### For Antigravity (Round 62)
1. Deploy, including `sepulchre_bg.jpg`, then recompile.
2. **The priority is a real REAPER FX-window screenshot**, at 100% and at a larger window size. We need it to check:
   - text contrast on the title plates and in the preset niche;
   - the moss and roots don't make any label or value hard to read;
   - the candle LEDs and the dried-blood toggles read clearly as on and off;
   - the bypass dimming (28%) still reads.
   If you can't capture the real window, say so plainly: no composites or mock-ups.
3. Run the full test suite to confirm nothing functional moved.
