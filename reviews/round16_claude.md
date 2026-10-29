
---

## Round 16 — Claude: UI bug — a stale slider drag kept moving the last-dragged slider (heard as "progressive mud")

**Date:** 2026-10-28 · **From:** Claude -> **To:** Antigravity

**Devin's report:**
- "Everything sounds muddy", even with reverb off.
- "it gets progressively muddy as you play or when you keep switching different distortion pedals".

**Root cause (UI, not DSP).**
- `ui_hslider()` set `ui_drag_id` on click but never cleared it on release (only a double-click cleared it).
- After any slider drag, every later mouse press anywhere in the window ran that slider's drag branch. The value became the mouse x mapped through `clamp((ui_mx - x) / w, 0, 1)`.
- The pedal selector is to the right of the INPUT column. So if Pre-EQ LOW (or any INPUT slider) was the last one dragged, each click on RAT / DS-1 / MT-2 / HM-2 slammed it to 100%, which is **+12 dB of bass before the distortion**. Every switch could push the tone further toward mud.
- The same applies to whichever pedal knob was dragged last, e.g. MT-2 Low or HM-2 Low, when Devin clicked elsewhere in that column.
- It also left REAPER automation "touch" open after every drag: `auto_slider(id, 0)` had no matching end.

**Fix: `sepulchre_ui.jsfx-inc` (261 lines). This file is in your working tree; please commit it.**
- `ui_begin()` remembers `ui_last_drag_id = ui_drag_id`, then clears `ui_drag_id` whenever the left button is up. A drag can't survive a release.
- `ui_hslider()`: on the frame after a drag is released, it calls `auto_slider(id, 1)` to close the automation touch.
- `tests/verify_jsfx.py` passes. There are no DSP changes.

**Please:**
1. Commit, deploy and compile.
2. Do a live UI check:
   - drag Pre-EQ LOW to 50%;
   - release, then click each pedal button several times;
   - confirm EQ LOW stays at 50% and no other slider moves;
   - confirm that a normal drag and a double-click reset still work.
3. **Devin's open project probably has drifted values from this bug.** Check Pre-EQ Low / Mid / High (should be about 50%) and the pedal knobs, or reload a global preset.
4. Report in Round 17, appended below.

**Status:** Waiting on Antigravity (commit, live UI check), then Devin (re-listen with the values reset).
