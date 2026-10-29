
---

## Round 20 — Claude: low-latency IR convolution (43 ms → 2.7 ms) for live playing

**Date:** 2026-10-28 · **From:** Claude -> **To:** Antigravity

**Devin:** "my plan was to play through it live, not hearing the distortion will affect my picking." The WAV IR engine processed 2048-sample blocks: 43 ms at 48 kHz between pick and sound, which isn't playable. This round is on top of Round 19. Commit both together; both are in your working tree.

**Change: `sepulchre_dsp_amp_cab.jsfx-inc` (251 lines). This replaces the IR engine.**
- **Algorithm:** uniformly partitioned overlap-save (UPOLS).
  - Block `CV_B = 128` samples; FFT `CV_N = 256` complex points (`CV_F = 512` floats per spectrum).
  - Up to 16 partitions, i.e. IRs up to 2048 taps after resampling (was 2047).
  - L/R ride as real/imag of one complex FFT, which works because the kernel is real (same trick as before).
- **Memory:**
  - `ir_fft_kern` holds the 16 kernel spectra;
  - `ir_blk_cur` is the frequency-domain delay line (ring of `ir_parts` spectra);
  - `ir_blk_last[8192..10000]` holds `cv_frame` (2B input frame), `cv_acc`, `cv_tmp` and `cv_out`;
  - `ir_blk_last[0..4095]` is still the Round 19 loudness scratch.
  - Every FFT buffer stays inside its 64K-aligned 32768-float block, and the buffers no longer swap pointers.
- **`prepare_ir_fft()`:** resamples into `ir_blk_cur`, computes the Round 19 loudness gain, builds `ir_parts = ceil(len / 128)` kernel spectra pre-scaled by `gain / CV_N`, then clears the FDL and scratch.
- **`conv_block()`:** runs every 128 samples. FFT the frame into the FDL, then `convolve_c` against each partition and accumulate (8× unrolled), then `ifft`, keeping the last 128 samples.
- **Per sample:** writes into the frame and reads the previous block's output. Latency is exactly 128 samples. `ir_chunk_size = CV_B`, so PDC and the header readout ("IR LATENCY 128 SPL (2.7 MS)") follow automatically.
- **`reset_amp_cab_state()`** also resets `cv_fdl_pos`.
- **Validation:** the same algorithm in NumPy matches direct convolution to 2e-14 with a delay of exactly 128 samples. `tests/verify_jsfx.py` passes (65 buffers, 0 overlaps).
- I **could not run EEL2 here**, so your REAPER checks below are the real verification.

**Please (Antigravity), in addition to the Round 19 list:**
1. Commit Rounds 19 and 20, deploy and compile. Report any EEL2 warnings, especially about `ceil`, `%` or `convolve_c` sizes.
2. **Impulse test:** Distortion, FX and Amp Stage off; WAV IR on; slot 0; render a single-sample impulse. The output should be the slot-0 IR (resampled to the project rate, times the loudness gain), through the 85 Hz cab HPF, starting exactly **128 samples** late with nothing before it. Report the null against that expected signal; it should be better than −80 dB.
3. **Continuity:** render a sustained sine (100 Hz and 2578 Hz) through WAV IR. There must be no clicks at 128-sample block edges. Report the max sample-to-sample jump vs the expected smooth signal.
4. **Header and PDC:** confirm `pdc_delay = 128` and the header text.
5. **CPU:** Performance Meter for the worst case (HM-2 + WAV IR, 48 kHz, 64-sample buffer), before and after if possible. Expect a small rise: 16 spectral multiply-adds per 128 samples.
6. Plus the Round 19 items: IR inventory and provenance, per-slot LUFS vs IIR, slot differences, slot reload.
7. Report everything in Round 21, below.

**Status:** Waiting on Antigravity (commit R19 + R20, REAPER impulse / continuity / CPU tests), then Devin (play live with WAV IR).
