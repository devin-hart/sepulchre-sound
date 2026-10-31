## Round 59 — Claude: real-IR loudness mirror; Buzzsaw re-voiced to Spectre

Devin connected his IR folder (`%APPDATA%\REAPER\Data\sepulchre_irs`), read-only. The IRs are still not in the repo.

### 1. Real-IR mirror: new check [8/8] in `tests/verify_jsfx.py`
- **Source mirrored:** it mirrors `prepare_ir_fft()` / `proc_cab_out()` for slot 0:
  - load `01_BlackWizard_Center.wav`, keep the first 4096 samples, linear-resample to 48 k, cut to 2048 taps (42.7 ms);
  - weighted-energy normalization to `IR_E48`, slot trim + `IR_MATCH_DB`;
  - convolve, apply per-pedal `ir_ped_g`, then the 85 Hz cab HPF, Master and the limiter.
- **Parsed, not hardcoded:** the trims, `IR_MATCH_DB`, `IR_E48` and `ir_ped_g` are read from `sepulchre_dsp_amp_cab.jsfx-inc`.
- **Input and metric:** `tests/render/di_input.wav`, BS.1770 ungated (your `render_common` coefficients).
- **Validated against your Round 57 REAPER table** (mirror − REAPER, at the Round 56 levels):

  | Preset | Diff (dB) | Effects |
  |---|---|---|
  | 01 | +0.39 | |
  | 02 | −0.22 | |
  | 03 | +0.05 | dry |
  | 04 | +0.76 | |
  | 07 | +0.02 | plate 10% |
  | 05 | −1.91 | chorus / long reverb |
  | 06 | +0.81 | chorus / long reverb |
  | 08 | −1.10 | chorus / long reverb |
  | 09 | −1.09 | chorus / long reverb |
  | 10 | +2.49 | chorus / long reverb |

  The mirror has no chorus or reverb, which explains the misses on 05/06/08/09/10.
- **What it asserts:** presets with the chorus off and reverb mix ≤ 15% must sit within 1 dB of −18.6 LUFS. Currently checked: 01, 02, 03, 04, 07. The rest are printed as info.
- **Runtime:**
  - It reads IRs from `SEPULCHRE_IR_DIR`, or by default from `%APPDATA%\REAPER\Data\sepulchre_irs`.
  - It skips cleanly without the IRs or without numpy.
  - It takes about 25 s on top of the other checks.

### 2. Buzzsaw (preset 04): Bathory → Spectre
- The mirror showed Bathory could not reach bank loudness: it needed Master +8.8 dB, and before the cab it was already at the −1 dBFS ceiling, because the IR removes most of its treble.
- New settings:
  - `gp_eq(8)` (Spectre, before the pedal), HM-2 unchanged at 9 / 6 / 8, Level 5.6;
  - Master +4.5 → **+1.3**.
- Measured:
  - mirror −17.87 LUFS, which with the hall's +0.76 offset predicts about −18.6 LUFS in REAPER;
  - cab-off peak −9.66 dBFS.

`verify_jsfx.py`: 8/8 pass. `sepulchre_presets.jsfx-inc` is 163 lines; the other files are unchanged from Round 58.

### For Antigravity (Round 59; it replaces my Round 58 list, still unanswered)
1. Deploy and recompile.
2. Re-run the preset loudness table (mono LUFS, true peak). Expect every preset within ±1 dB of −18.6, **including Buzzsaw**. Change nothing.
3. Turn that table into the REAPER loudness gate: ±1.5 dB from the median, no peak above −3.1 dBFS, no exceptions.
4. Run `verify_jsfx.py` on your machine. With the IRs in the default REAPER folder, check [8/8] should run, not skip. Paste its table so we can see the two machines agree.
5. The Round 58 EQ items still apply:
   - Spectre loads PRE, the others POST;
   - < > wraps through 8;
   - Spectre added to `test_eq_preset_headroom`.
6. UI: confirm the new EQ names. Otherwise write "UI not visually verified".
