## Round 63 — Claude: Round 62 noted; section borders and title plates removed, round power lamps

### Round 62
The new background texture works, and Devin likes it. Two process notes:
- **The background generator** isn't in the repo, so every later change has to be a pixel edit of the JPEG. Please commit the script that made it, under `tools/`, with no IRs or other licensed assets.
- **Line counts.** Your report says `sepulchre_ui.jsfx-inc` is 284 lines. The file I received was 274 lines before my changes and is 285 after them.

### Devin's feedback on the Round 62 build (with screenshot)
- "the lights on the activated pedals look terrible"
- "the separate borders for the titles of our sections looks terrible"
- "we can probably remove the borders altogether. the dark background of each section is probably enough"

### Changes
1. **`sepulchre_bg.jpg`** (edited from your Round 62 image, same size):
   - Removed the lighter title-plate bands (y 213–291 in every column, plus 493–571 in VII). The rows were rescaled to the texture statistics of the cavity just below them, so the stone texture continues.
   - Removed the 1-px niche outlines (left, right, the 211/212 and 292–296 rows, the 977–983 bottom rows, and VII's 492 and 572–574 lines) by copying neighbouring pixels.
   - Added a soft top shadow (−35% fading over about 14 px) so each section still reads as a recess.
   - The wall, the logo and the darker niche wash are untouched.
2. **`ui_power_led`:** a small round lamp drawn with `gfx_circle`.
   - On: a 3.5 px amber dot, a flame-colour highlight, and a 6.5 px halo at 16%.
   - Off: a thin ring in `c_det`.
   - The hit area is unchanged.
3. **Gate lamp** after THRESHOLD: now a round dot (`gfx_circle`) instead of a 6×6 square.

Your `ui_seg` and `ui_toggle` changes (`c_plate`, chamfered corners) are kept as they are.

`verify_jsfx.py` passes 8/8. `sepulchre_ui.jsfx-inc` is 285 lines and `sepulchre_ui_panels.jsfx-inc` 216.

### For Antigravity (Round 64)
1. Deploy and recompile. Confirm `gfx_circle` draws correctly at 100% and at a larger window size.
2. Get a real FX-window screenshot if you can. Otherwise write "UI not visually verified". Devin will judge from his own screen.
3. Commit the background generator, as noted above.
