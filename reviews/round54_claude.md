## Round 54 — Claude: Round 53 noted; cab sim restored (Round 49 code)

Devin A/B'd Sepulchre's **built-in cab** against a $70 commercial amp sim demo: "it didn't sound any better than what we have going on here". The Round 52 removal is reverted.

### What changed
- Every plugin source file is **byte-identical to Round 49** (the state before the Round 50 TS-808):
  - `sepulchre_sound.jsfx`, `sepulchre_dsp_core.jsfx-inc`, `sepulchre_dsp_dist.jsfx-inc`;
  - `sepulchre_dsp_amp_cab.jsfx-inc` (restored), `sepulchre_presets.jsfx-inc`;
  - `sepulchre_ui.jsfx-inc`, `sepulchre_ui_panels.jsfx-inc`;
  - `sepulchre_bg.jpg` (7-slab with the OUTPUT band), `tests/verify_jsfx.py`.
- `sepulchre_dsp_fx.jsfx-inc` was never touched.
- Back as before:
  - sliders 49 (Cabinet Enable) and 53 (IR Slot);
  - PDC of 128 samples while the cab is on and an IR is loaded;
  - per-slot and per-pedal IR trims (`ir_ped_g`). These answer Round 53's DS-1 finding.
- The TS-808 stays removed.
- Devin can still use TRVE Cab with the Cabinet switch off.
- `verify_jsfx.py` passes with the Round 49 numbers. Total: 1,625 lines.

### Round 53
Clean work.
- The relative pedal levels through BlackWizard Center (DS-1 −1.3 dB vs MT-2, −4.2 dB vs RAT) confirm why `ir_ped_g` existed, and it's back now.
- One nit: the "IR LUFS" column shows positive values (+0.09 LUFS), so the convolved renders weren't normalized. Only the deltas are meaningful. Next time, normalize the IR to unit energy, or report deltas only.

### For Antigravity (Round 55)
1. **Restore from git** what Round 53 removed outside the plugin files:
   - `tests/render/test_exact_ir_null.py`;
   - sliders 49 / 53 in `render_common.VALID_SLIDERS` and `BASE_DEFAULTS`;
   - the `test_mirror_null` setup from Round 49 (the IIR/WAV path, not `ref_cab=False`).
   - The simplest route is to check those files out from the Round 49 commit.
2. `git rm sepulchre_dsp_amp.jsfx-inc`, and delete its copy in REAPER's Effects folder. Then deploy `sepulchre_dsp_amp_cab.jsfx-inc` again.
3. Recompile and confirm:
   - no compile errors;
   - PDC is 128 with the cab on and 0 with it off;
   - the IR selector is back in column VII.
4. Rerun the Round 49 suite and confirm it matches the Round 49 numbers. No new measurements.
5. UI: write "UI not visually verified" unless you have a real FX-window capture.
