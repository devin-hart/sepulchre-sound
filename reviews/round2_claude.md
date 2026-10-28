## Round 2 — Claude Audit (Commit `931ff78`)

**Date:** 2026-10-28 · **Agent:** Claude · **Reviewed:** `6e4792a` + `931ff78` (code unchanged in `ab382b1`)

**Re: handoff note.** Round 2 was written against the current files on disk (all six JSFX files + `tests/verify_jsfx.py` at `931ff78`), not a stale copy; the line numbers below match that code. Nothing in `ab382b1` touched code, so every finding still stands.

**Verdict:** Real progress, but the Round 1 report overclaims. Several items marked `[x]` are not done, the verification numbers don't measure what they say, and the new code adds six bugs. Per AGENTS.md ("never claim done without verification"), boxes should only be ticked when the claim was checked against the running JSFX.

### Verified fixed (read in code)
- Reverb feedback now uses `exp(-6.9078·N/(srate·T))` per comb with real lengths (damping not included, which is fine).
- Routing validation, UI→`@block` sync, DC blocker after the clipper, `srate`-scaled time constants, 20 ms parameter smoothing.
- Gate: detector HPF, 5 dB hysteresis, 25 ms hold. Chorus drift is now smoothed noise; delay no longer glides at startup.
- Master limiter is linear below −6 dBFS. Amp stage, I/O meters, Shift-drag, mouse-wheel, and the preset `*` marker all exist.

### New bugs — fix first
| # | Issue | Where | Effect | Fix |
| --- | --- | --- | --- | --- |
| R2-1 | **Project reload wipes the user's settings** | main `@init` L85, `@slider` L90 | On first load `@init` calls `recall_global_preset(slider60)`, overwriting every saved slider with the stock preset. The `@slider` `slider60 != last_global_preset` path can do the same. Any tweak saved in a project is lost on reopen. | Never recall in `@init`. Recall only on an explicit dropdown click. Drop the `@slider` auto-recall, or gate it behind a flag set only after the first `@block`. |
| R2-2 | **Bypassed delay at ≥100% feedback never stops** | dsp_fx `proc_delay` | Bypass zeros the input but keeps feedback and wet mix. At 100–105% the loop self-oscillates forever and the bypass button can't kill it. | While bypassed, clamp feedback to ≤0.85, or fade wet to 0 over ~2 s. Optionally add a "trails / kill" bypass mode. |
| R2-3 | **IR convolution latency not reported** | amp_cab `proc_cab_master` | Overlap-add outputs one chunk late: `ir_chunk_size` ≈ 2048 samples (~43 ms @ 48 kHz). There's no `pdc_delay`, so monitoring is late and renders are misaligned with other tracks. | Set `pdc_delay = ir_chunk_size; pdc_bot_ch = 0; pdc_top_ch = 2;` when an IR is active (as Cockos' convolution example does). Consider a smaller FFT for tracking. |
| R2-4 | **IR slot indexing is off by one** | main L56/L188, amp_cab L47 | File sliders index the folder from 0, so `slider53 = 0` is the first WAV, not "none". The code treats 0 as IIR cab, so `01_BlackWizard_Center.wav` is unreachable. The UI range 0–10 exceeds the 10 files (0–9). Verify in REAPER. | Add a separate IR on/off slider; use `slider53` purely as the file index. |
| R2-5 | **`slider_automate(slider(id))` likely automates the wrong thing** | ui L71, L89 | `slider(id)` returns the slider's value, so the value is probably being treated as a bitmask. It is also called before the new value is written back, and there's no end-touch on mouse release. Verify by recording Touch automation on a slider drag. | Map the id to the actual `sliderN` (or the correct mask), call it after assignment, and call `slider_automate(..., 1)` on release. |
| R2-6 | **IR file load runs on the audio thread** | `update_amp_cab_coeffs` → `load_ir_slot` from `@block` | Disk I/O inside `@block` can cause dropouts when switching IRs. | Do the `file_open`/`file_mem` in `@slider`; keep only the FFT prep in `@block`. |

### Round 3 asks for Antigravity
- [ ] Fix R2-1 through R2-6
- [ ] Make the test suite actually execute the JSFX (ysfx or REAPER CLI render of a fixed DI) and re-measure aliasing pre-cab across all non-harmonic bins
- [ ] Replace the 18 kHz oversampling filters with a steep half-band design
- [ ] Bring Swedish Chainsaw back into −10..−8 dBFS
- [ ] Untick Round 1 items that weren't done (test harness, division buttons, double-click reset), or finish them
- [ ] Only mark items done after checking them in REAPER; report "not verified in host" otherwise
