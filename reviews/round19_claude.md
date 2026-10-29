
---

## Round 19 — Claude: WAV IR is the new default and is loudness-matched to the IIR cab; IR checks requested

**Date:** 2026-10-28 · **From:** Claude -> **To:** Antigravity

**Devin's A/B result:**
- "the WAV IR sounds WAY better… there's some natural sound in there that i was missing".
- Two problems: (1) the volume doesn't match the IIR cab; (2) he's "not sure if the different wavs are actually making a difference".

**Cause of (1).** `prepare_ir_fft()` normalised each IR to raw energy 0.18. Raw energy ignores spectral shape: a bass-heavy IR and a bright IR with equal energy differ a lot in loudness. Nothing related it to the IIR cab's level, which is what the presets and pedal Levels are calibrated on.

**Changes. These files are in your working tree; please commit them.**
- `sepulchre_dsp_amp_cab.jsfx-inc` (245 lines). Built on your current version, grit resets kept.
  - New `bq_buf()`: filters a scratch buffer in place with its own state.
  - New weighting biquads `bq_irw1..3` (3 × `alloc_buf(9)` before the 64K alignment; verify sees 65 buffers, 0 overlaps).
  - `prepare_ir_fft()` copies the resampled IR (plus 2048 zeros) into the `ir_blk_last` scratch. It runs that through the cab HPF, a 90 Hz HP, a 500 Hz +12 dB low shelf and a 6 kHz LP (≈ the average distorted-guitar spectrum × K-weighting), then sets the gain so the weighted energy equals `IR_E48 × 48000 / srate`.
  - `IR_E48 = 0.283543` is the same measure for IIR profile 0. Fit over 4 pedals × 11 test IRs: 1.6 dB rms error; the 4.9 dB worst case is on extreme synthetic IRs.
- `sepulchre_sound.jsfx`: `slider52` (Cabinet Source) now defaults to **1, WAV IR**. With no IR files, `ir_filter_len = 0` and the IIR cab runs automatically.
- `sepulchre_presets.jsfx-inc`: `recall_global_preset()` no longer forces `slider52 = 0`, and neither does preset 05 Freezing Clean. A preset now keeps the user's cab choice.
- `sepulchre_ui_panels.jsfx-inc`: the header said "4x OVERSAMPLED"; it is 8x since Round 9.
- `tests/verify_jsfx.py`: new `check_ir_loudness_constant()` recomputes `IR_E48` from the IIR profile 0 coefficients. Whole suite passes.
- `SPEC.md` §3.6 and decision row.

**Please (Antigravity):**
1. Run verify, then commit, deploy and compile.
2. **IR inventory.** List every file in `%APPDATA%\REAPER\Data\sepulchre_irs\`: name, sample rate, channels, length.
   - **Provenance:** where did these 10 IRs come from (download, which pack, which license), or were they generated?
   - If they're third-party, check the license allows redistribution with a free plugin before any release.
3. **Do the slots really differ?** For each slot, render the default chain (WAV IR, slot N) on the same DI and report:
   - integrated LUFS vs the IIR cab (target within ±1 dB);
   - 1/3-octave band levels 100 Hz–8 kHz;
   - pairwise max band difference between slots.
   - If two slots null to within about 0.5 dB in every band, they are near-identical files. Also confirm that clicking the slot arrows actually reloads, i.e. the render changes.
4. **Latency.** With WAV IR on, the header reports the overlap-add block latency: `ir_chunk_size` ≈ 2048 samples ≈ 43 ms at 48 kHz. Please report the exact figure from the live header. 43 ms is too much for live monitoring. If Devin plays through it live, Round 20 should be a low-latency partitioned convolution.
5. Report in Round 20.

**Status:** Waiting on Antigravity (commit, IR inventory, per-slot render, latency figure), then Devin (cab volume check, live-monitoring question).
