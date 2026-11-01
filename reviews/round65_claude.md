## Round 65 — Claude: Round 64 accepted; flat buttons and plain dot lamps

### Round 64
Accepted. Thank you for committing `tools/make_background.py`.

### Devin's feedback (screenshots of the Round 63 build)
- "that light looks like shit. that could just be a lot simpler."
- "also these buttons look like shit"

### Changes (`sepulchre_ui.jsfx-inc` 272 lines, `sepulchre_ui_panels.jsfx-inc` 216 lines)
Drawing only. Hit areas, sizes and behaviour are unchanged.
- **`ui_seg`:** text only, no box.
  - Selected: bone text with a 2 px bone underline.
  - Unselected: soft-grey text over a 1 px `c_border` hairline.
  - Hover: label grey.
- **`ui_toggle`** (NOISE GATE): the same style. On = bone text with a 2 px amber underline.
- **`ui_power_led`:** a plain 3 px dot, `c_ember` on and `c_border` off. No halo, highlight or ring.
- **EQ preset strip and IR selector:** the carved box is replaced by a 1 px hairline under the name. The arrows and their hit areas stay where they were.
- **Preset step < >:** these use `ui_seg`, so they get the new style automatically.
- `c_plate` removed (no longer used).

`verify_jsfx.py` passes 8/8.

### For Antigravity (Round 66)
1. Deploy and recompile.
2. Check that "PLATE" and "AMBIENT" don't run together in VI REVERB at 100% window size (the segments are about 44 px wide). If they do, report it; don't fix it.
3. Real FX-window screenshot if you can; otherwise write "UI not visually verified".
