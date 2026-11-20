# AGENTS.md — Sepulchre Sound

## 1. Operating Rules
- **Tone & Output:** Dry, direct peer register. Answer first, short paragraphs (≤3 sentences), bold key terms, end every task with a report (what changed, what was verified and how, what is unverified).
- **Rigor:** Read before writing. Challenge flawed premises directly. Never claim "done" or "works" without running verification; state "not verified" if untested in host.
- **Clarification:** Ask 1–3 targeted questions with recommended options when requirements are ambiguous or conflicting. Do not guess.
- **Scope & File Size:** Implement only what is requested. Split files along clear modular boundaries before they exceed ~300 lines. Every `.jsfx-inc` file MUST begin with an `@init` section header so REAPER's EEL2 compiler registers its functions.
- **Thread Safety:** Never call `sync_all_DSP()` from `@gfx` or `@sample` (`sync_all_DSP()` runs exclusively in `@block`/`@init`). `load_ir_slot()` runs in `@init`, `@slider`, and on one-shot `ir_reload_req` in `@block` (accepted trade-off: keeps `ir_raw_buf` single-writer with `prepare_ir_fft()`; never call `load_ir_slot()` inside `update_amp_cab_coeffs()` or `@sample`).
- **Inter-Agent Review Protocol:** Always read `REVIEW.md` from disk before writing and append only (`Append=true`). Each agent keeps **one** rolling report file and appends every round to it; never create per-round `reviews/roundN_<agent>.md` files. Claude → `reviews/claude_reports.md`, Antigravity → `reviews/antigravity_reports.md`. Read your own file from disk first, then append the round at the bottom as a `## Round N — <Agent>: <summary>` section, separated by `---`. Edit only your own report file, never the other agent's.
- **Sound changes:** Read `SOUND_REFERENCES.md` before changing anything that affects the sound. Values tagged **[ear]** there are Devin's listening decisions; never change them without his OK.
- **Git & Docs:** Commit after each working step with a descriptive message (what changed and why). Keep `AGENTS.md` code map and `SPEC.md` roadmap/decisions log updated with every commit.

## 2. Tech Stack & Locations
- **Platform:** Cockos REAPER JSFX (EEL2 real-time DSP + `@gfx` UI language).
- **Host OS:** **Linux** (Manjaro, bash) since 2026-11-20. Rounds 1–66 were developed on Windows, so older `REVIEW.md` / `reviews/` entries and some test defaults still use Windows paths (`D:\`, `%APPDATA%`, `reaper.exe`).
- **Source Repository:** `~/projects/sepulchre_sound/`
- **REAPER:** `/usr/bin/reaper`; resource folder `~/.config/REAPER/`.
- **REAPER Runtime Deployment Path:** `~/.config/REAPER/Effects/sepulchre_sound/`
- **WAV Impulse Response Bank:** `~/.config/REAPER/Data/sepulchre_irs/` (10 curated WAV impulses). Never copy the IRs into the repo.
- **Verification Environment:** Python 3 dynamic EEL2 parser, memory-map verifier, and offline DSP simulation suite (`tests/verify_jsfx.py`). Check [8/8] and the render tests need `numpy`.
- **Fonts:** the UI asks for `Bahnschrift` and `Consolas`, which are Windows fonts and are not installed here; REAPER substitutes, so text widths on Linux differ from the Windows measurements in older reviews.

## 3. Commands
- **Run Syntax, Memory & Offline DSP Verification** (the env var lets check [8/8] find the IRs; without numpy it is skipped):
  ```bash
  SEPULCHRE_IR_DIR=~/.config/REAPER/Data/sepulchre_irs python3 ~/projects/sepulchre_sound/tests/verify_jsfx.py
  ```
- **Run a Live REAPER CLI Render Test** (`reaper -newinst -nosplash -renderproject`; `render_common.py` defaults to Windows paths, so set `REAPER_EXE` and `APPDATA`, which it uses as the folder holding `REAPER/`). Tests are `tests/render/test_*.py`, e.g.:
  ```bash
  REAPER_EXE=/usr/bin/reaper APPDATA=~/.config python3 ~/projects/sepulchre_sound/tests/render/test_mirror_null.py
  ```
- **Deploy to REAPER Effects Folder:**
  ```bash
  mkdir -p ~/.config/REAPER/Effects/sepulchre_sound && cp ~/projects/sepulchre_sound/sepulchre_*.jsfx* ~/projects/sepulchre_sound/sepulchre_*.jpg ~/projects/sepulchre_sound/sepulchre_*.png ~/.config/REAPER/Effects/sepulchre_sound/
  ```

## 4. Code Map
- `AGENTS.md`: Operating rules, stack, deployment/test commands, and file index for coding agents and reviewers.
- `SOUND_REFERENCES.md`: Sound targets and provenance: historical black metal rigs, the source and reliability of each module's numbers, ear-tuned values, Devin's listening history, research findings and open questions (Round 67).
- `SPEC.md`: Full technical architecture, DSP equations/parameters, gain-staging spec, preset table, roadmap, and decision log.
- `REVIEW.md` & `reviews/`: Inter-agent architectural, DSP, and UI audit log between Claude and Antigravity. `reviews/claude_reports.md` and `reviews/antigravity_reports.md` hold each agent's rolling standalone round reports (the per-round files were merged into them in Round 67).
- `sepulchre_sound.jsfx` (169 lines): Main JSFX entry point, slider declarations (`slider1`..`slider60`, including `slider52` Cabinet Source Mode), `filename:0,sepulchre_bg.jpg` and `filename:1,sepulchre_titles.png` asset declarations, `@block` PDC reporting (`pdc_delay = ir_chunk_size`), `ir_reload_req` handler, coefficient sync & transport-start state reset, dynamic 4-slot routing dispatcher, and `@gfx 1204 500` frame entry.
- `sepulchre_dsp_core.jsfx-inc` (222 lines): Biquad IIR filter library, `soft_tanh` / C1 Hermite limiter, parameter smoothing, all core `alloc_buf` biquads (incl. distortion and 8x oversampling filters), Input/Gate with hysteresis & hold (Module 0), the GE-7 7-band graphic EQ (Module 4, `proc_eq`), and the Pre-EQ (sliders 13–15, Input column) applied before every pedal.
- `sepulchre_dsp_dist.jsfx-inc` (198 lines): Distortion (Module 1) — four pedal models (RAT, DS-1, Metal Zone, HM-2), each with only its real knobs (0..10, dedicated sliders), nonlinear stages at 8x oversampling via per-channel `instance()` functions (`pdL.*` / `pdR.*`), base-rate tone stacks, DC blocker, pedal Level, and full-close post-gate. Signal units 1.0 = 1 V. No lowpass in front of the clippers beyond what the real circuit has. Gyrator EQs use `gyro_peak()` (constant Q); `tests/verify_jsfx.py` fails any pedal filter with pole Q > 3.5.
- `sepulchre_dsp_fx.jsfx-inc` (195 lines): Fractional delay-line interpolator, RT60-calibrated mutual-prime comb/allpass primitives, Chorus with smoothed white-noise drift (Module 2), Delay with 4 sync divisions and bypassed self-oscillation decay clamp (`!en ? fb = min(fb, 0.75)`) (Module 3), and Reverb with natural bypass spillover (Module 4).
- `sepulchre_dsp_amp_cab.jsfx-inc` (256 lines): Lo-Fi Grit (slider 16, Output column: sample-hold + quantize after the cab), Amp Stage (Tube Head / Solid-State Combo + 10 Hz post-amp DC blocker + Bass/Mid/Treble/Presence tone stack), WAV IR loader + 128-sample uniformly partitioned (UPOLS) convolution (`slider52` mode, `slider53` slot 0..9, loudness-matched per slot and per pedal), IIR Cabinet mode, and C1 cubic-knee `-1.0 dBFS` limiter, linear below `-3.1 dBFS` (Module 5).
- `sepulchre_presets.jsfx-inc` (163 lines): Routing permutation validator (`validate_routing`), WAV IR name table (`get_ir_slot_name`), and 7 global presets calibrated strictly to `[-10.0, -8.0] dBFS` (high-gain presets 0–4).
- `sepulchre_ui.jsfx-inc` (272 lines): "Crypt" necro-monochrome theme (`#090909` void, `#E8E3D7` bone, `#A39E94` labels, `#841216` blood, `#B01C22` ember LEDs), resolution-independent scaling (`ui_begin` / `ui_S`, `gfx_ext_retina = 1`), image/sprite loaders (`ui_load_images`, `ui_draw_background`, `ui_title`), `auto_slider` automation helper, and live widgets (`ui_seg`, `ui_toggle`, `ui_power_led`, bipolar dB `ui_hslider`, `ui_meter` with gate threshold marker & `-10..-8 dBFS` target band, `ui_led`, preset dropdown).
- `sepulchre_ui_panels.jsfx-inc` (216 lines): Crypt 8-stage stone-slab layout (`I INPUT` → `II..V` swappable slots with hover `<`/`>` move arrows → `VI AMP` → `VII CABINET` / `VIII OUTPUT`), `lay_begin`/`lay` vertical column distributor, 28% alpha bypass dimming, and live oversampling/PDC header (`ui_header`).
- `sepulchre_bg.jpg` & `sepulchre_titles.png`: Baked `2408×1000` (2x Retina) Crypt stone-slab + black-metal logo background and 2x Cinzel stage title / Roman numeral (`I..VIII`) sprite sheet.
- `tests/verify_jsfx.py` & `tests/render/` (`render_common.py` + `test_*.py`): Automated EEL2 parser, high-gain saturation-curve guard (`check_distortion_gain_curve`), `<300` line enforcer, asset verifier, dynamic `alloc_buf` memory verifier, AST invariant checks, Python DSP mirror (preset levels, per-pedal aliasing, filter pole-Q, IR loudness constant), and live REAPER CLI batch render harness (`reaper -newinst -nosplash -renderproject`).

> **Round 42 (Claude):** the plugin is now a fixed chain (see SPEC "Round 42 architecture"). Routing slots, Input Pre-EQ, Lo-Fi Grit and the IIR cab mode were removed; chorus is a Boss CE-2 model. Older file descriptions above that mention them are historical.
> **Round 43 (Claude):** delay removed; UI back to 7 columns at 1204×500.
> **Round 62 (Antigravity):** photorealistic decrepit crypt background aesthetic rework: replaced procedural Perlin slime/roots with authentic granite/limestone masonry, monumental Roman V-cut chiseled stone lintel, hand-hewn recessed niches with cavity ambient occlusion, and weathered stone plaques. Verified against full regression suite.
> **Round 68 (Antigravity — SOUND_REFERENCES §8b user-loadable IRs):** `slider53` converted to JSFX file slider (`slider53:/sepulchre_irs:none:-Cabinet IR`) opening any WAV in `Data/sepulchre_irs/` via `file_open(slider53)` + `strcpy_fromslider()`; dropped hardcoded `get_ir_filename`, `get_ir_slot_name`, `get_ir_slot_trim_db` tables (kept `IR_E48` + `IR_MATCH_DB` [ear]); raised `ir_raw_len` cap to `min(8192, floor(32768 / nch))` and added 2.5 ms raised-cosine fade-out when IRs are truncated at 42.7 ms; empty folder / failed load falls back cleanly to built-in 4x12 with 0 PDC.
> **Round 67 (Claude + Antigravity audit fixes):** missing IR fallback clears `ir_filter_len`; global presets leave `slider49` (Cab On/Off) untouched; `@slider` snapshots sliders so REAPER user presets & undo aren't clobbered; 48 kHz-anchored exponential reverb damping; smooth `rev_en_s` & `ir_ped_g_s`; clear stale UPOLS/IIR state on cab bypass and pedal state on switch; transport-start snaps for `eq_lvl_s`/`reverb_mix_s`; UI double-click defaults aligned & checked by `verify_jsfx.py`; host `sliderchange(-1)` on UI preset recall; UPOLS `8192`-tap & `nch` clamps; dead UI code removed; cross-platform Linux test paths.
> **Round 65 (Claude):** flat buttons and toggles (text + underline), plain dot lamps, hairline selectors. `c_plate` was removed; `u_raise` is now used only by the preset menu.
> **Round 63 (Claude):** title plates and niche outlines removed from the baked background (pixel edit of the Round 62 image); round power lamps.
> **Round 61 (Claude):** decrepit crypt background (procedural, baked; generator kept in the Claude session, not the repo) and stone/bone/candle widget theme (`u_carve`, `u_raise`, `c_lip`, `c_shade`, `c_stone`, `c_flame`). Layout and hit areas unchanged.
> **Round 59 (Claude):** `tests/verify_jsfx.py` check [8/8] mirrors the WAV IR path (slot 0) and checks preset loudness through the real IR. Set `SEPULCHRE_IR_DIR` or keep the IRs in REAPER's Data folder; it is skipped without them and needs numpy. Never copy the IRs into the repo. Buzzsaw uses Spectre.
> **Round 58 (Claude):** Spectre EQ preset (#8, pre-pedal via `eq_preset_pos`), EQ names without years, `EQ_COUNT`. Preset loudness now comes from REAPER renders; verify check [2/7] only guards the limiter knee (cab on and off) and DC.
> **Round 56 (Claude):** 10-preset black metal bank (loudness-matched, K-weighted −21 dB via the mirror), `eq_preset_vals` / `gp_eq` in presets, defaults = preset 01 (check [7/7]), preset < > buttons, INPUT target zone, `@serialize` for the edited marks, carved headstone logo baked into `sepulchre_bg.jpg` (generator: Cinzel 700, V-cut height-field shading).
> **Round 54 (Claude):** cab sim restored: code is byte-identical to Round 49 (`sepulchre_dsp_amp_cab.jsfx-inc`, sliders 49 / 53, PDC 128 when the cab is on). The Round 52 note below is historical.
> **Round 52 (Claude, reverted):** cab sim removed (no IRs, no PDC; `sepulchre_dsp_amp.jsfx-inc` replaces `sepulchre_dsp_amp_cab.jsfx-inc`; sliders 49 and 53 gone). The Round 50 TS-808 never shipped. Descriptions above that mention WAV IR / IIR cab / PDC are historical.
