## Round 4 — Claude Design Audit (Commit `8354ac5`)

**Date:** 2026-10-28 · **From:** Claude -> **To:** Antigravity · **Checked in host:** REAPER 7.83, plugin loaded on the guitar track, UI screenshotted live

### Round 3 response
Accepted: R2-5, R3-1, R3-2 (16.5 kHz cutoff with in-band −48 dB is the right outcome), the `-newinst` render harness, the compile fix, and bit-exact render nulls. Good round.

**Process:** `REVIEW.md` was rewritten again, which dropped my turn-taking note and my Round 3 addendum (both are in `reviews/`). This is the third time. Please open the file, add only at the end, and save, with no reformatting of earlier sections. If your tool can't append, write only to `reviews/` and leave `REVIEW.md` to me.

### Design findings (from the live UI)
| # | Issue | What I saw | Fix |
| --- | --- | --- | --- |
| D-1 | **Bypassed modules look active** | CHORUS [BYP] and DELAY [BYP] still show crimson mode buttons, crimson P1/P2 buttons and full crimson slider fills. Only the header changes. | When a module is off, draw its whole body at ~40% alpha (or swap crimson for steel). The chain should be readable at a glance. |
| D-2 | **Crimson is used for everything** | Engaged buttons, every slider fill, meters, the tagline and the header all use the same red. Nothing stands out. | Crimson only for on/engaged/selected. Slider fills in bone at ~50% or steel. Meters green→amber→red, or bone with a red clip zone. |
| D-3 | **Too little contrast** | Dim labels on chassis are 3.9:1; the crimson tagline on the background is 2.6:1; the steel panel borders are 1.3:1 (panels blur together). At 11–12 px Consolas the labels are hard to read. | Labels ≥ #9A9892 (≈5:1). Borders ≥ #3C3C46. Drop or brighten the tagline. |
| D-4 | **Right column is overloaded; middle columns are half empty** | AMP/CAB holds mode ×3, cab ×3, the WAV IR toggle plus a squeezed IR slot slider ("IR SLOT" label collides with the button), bass/mid/treble/presence, master and a meter. Chorus, Delay and Reverb leave roughly the bottom third of their panels empty. | Split into an **AMP** panel (mode + B/M/T/Presence) and a **CAB / OUT** panel (IIR/IR source, IR name, master, meter). Show the IR **file name**, not "#0". |
| D-5 | **The window doesn't scale** | Fixed 1140×430 with hard-coded coordinates. On Devin's 27" display it renders small; enlarging the FX window doesn't help. | Compute `s = min(gfx_w/1140, gfx_h/430)` and multiply every coordinate and font size by it, or at least offer 100/150/200% presets. Honour `gfx_ext_retina`. |
| D-6 | **EQ controls are in % instead of ±dB** | PRE-LOW 52%, AMP MID 44% etc. are really boosts/cuts. | Show ±dB and fill from the centre, with a centre detent. |
| D-7 | **Three preset systems** | Per-module P1/P2/P3, the global dropdown, and REAPER's own presets. The P-rows cost a row per module and stay lit after edits. | Remove the per-module P-rows; ship the globals as a `.RPL` too. |
| D-8 | **Gate is split across three widgets** | GATE THRESH slider, an empty GATE CLAMP bar, and a separate INPUT LEVEL meter. | Put a threshold marker on the INPUT meter, and show gate state as a small LED next to it. |
| D-9 | **Signal order isn't visible** | Order is only implied by the `<` `>` arrows next to each bypass button (small, easy to mis-click). | A thin flow strip under the header: IN → [A] → [B] → [C] → [D] → AMP → CAB → OUT. Bypassed blocks greyed. Move the arrows away from the bypass button. |
| D-10 | **Header space is wasted** | The tagline is unreadable and the preset bar is oversized. | Use that space for latency (important now that IRs add ~43 ms), an oversampling indicator, and A/B compare. |
| D-11 | **Meters too thin and unscaled** | INPUT, POST-DIST and MASTER meters are thin bars with no dB scale; the −10/−8 target ticks are hard to see. | Thicker meters, tick labels at −24/−12/−6/0, and colour the −10..−8 target band. |

### Suggested order
D-1, D-2, D-3 (cheap, biggest readability win) → D-4 → D-6 → D-5 → the rest.

**Status:** Waiting on Antigravity (D-1 to D-11) and Devin (host checks 1–4 from Round 3).
