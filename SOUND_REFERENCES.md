# SOUND_REFERENCES.md — Sepulchre Sound

What each part of the plugin is meant to sound like, where its numbers come from, and how sure we are about them. **Read this before changing anything that affects the sound.**

Written by Claude, 2026-11-20 (Round 67 research). Section 7 has the research findings: what we may be getting wrong, with concrete experiments.

## 1. Reliability legend
Every value or claim below is tagged with one of these.

| Tag | Meaning | Can an agent change it? |
| :-- | :-- | :-- |
| **[circuit]** | From a published circuit analysis or schematic | Yes, if a better source shows it's wrong |
| **[measured]** | Measured in a REAPER render or the Python mirror | Re-measure, don't guess |
| **[ear]** | Devin's listening decision | **No.** Only Devin changes these |
| **[fan]** | Fan site, forum or gear database; not confirmed by the artist | Treat as a starting point, not a target |
| **[interview]** | The artist or engineer, in a named interview | Best historical evidence we have |

## 2. The goal (Devin's words)
- "the idea is that this is a simple plug in and start ripping black metal. we need some really good presets" (Round 56).
- He plays **live** through it, so latency matters (Round 20: 43 ms was "not playable"; now 128 samples).
- He owns Ugritone TRVE Cab and the Old School Black Metal IR pack. The built-in cab must also work switched off (Round 54).
- "i'm wondering now if we've overcomplicated this" (Round 42), so complexity has to earn its place.

## 2b. Release direction (Devin, 2026-11-20): this overrides older goals
- **Public release.** The plugin is for everyone, not tuned to one player's guitar or interface.
- **Default sound:** "a nice clean distortion of typical modern black metal records". Clear and defined, not a clean tone.
- **Presets:** a couple of early black metal showcase presets ("shows what the plugin is capable of"), plus atmospheric ones. Keep the chorus and reverb.
- **Simple to use:** "i just want to play." Don't add amp-modelling depth. §7-B (a JCM800-style amp model) is **dropped**.
- **Consequences an agent must respect:**
  - **IRs:** the Ugritone IRs cannot ship. The cab has to sound good for users who don't own them (better built-in cab, freely licensed IRs, or user-loadable IRs). This is a release blocker.
  - **Input level:** calibrate to an industry convention so it behaves the same on common interfaces (§7-A).
  - **Test DI:** use several guitars and players (free DI packs, plus Devin's), not one player.
  - **Preset names:** prefer descriptive names over band or album names for the public build. This is a suggestion, not legal advice.

## 3. What black metal guitar actually ran through
These are historical facts, which is not the same as what the plugin models. The pattern matters more than any single entry.

| Record / artist | Chain | Tag |
| :-- | :-- | :-- |
| Mayhem, *De Mysteriis Dom Sathanas* (Grieghallen, 1993) | Les Paul → "one yellow Boss distortion pedal" (as recalled) → Marshall JCM800 → Marshall 4x12. Close-miked with an AKG C414 and a B&K 4011, in a tight room. "What came out of the cab is what you hear." | [interview] Pytten, SOS 2024 |
| Euronymous generally | HM-2 into a Marshall; also listed: SD-1, Tube Screamer, Arion Metal Master | [fan] |
| Burzum, debut | One guitar track through a 10 W Marshall, one through a 60 W Peavey. A poor amp, on purpose. | [interview] Guitar World 2010 |
| Burzum, *Det Som Engang Var* / *Hvis Lyset* | 60 W Peavey | [interview] |
| Burzum, *Filosofem* | Westone guitar → fuzz/distortion pedals → his brother's **hi-fi stereo amp**, no guitar amp | [interview] + Wikipedia |
| Darkthrone, early 90s | Nocturno Culto: a Peavey as a teen, later a Fender Performer 1000 ("huge amount of sound"); albums not specified. *Transilvanian Hunger*: Fenriz played all instruments, on a 4-track. | [interview] Guitar World 2022; Wikipedia |
| Darkthrone, *Eternal Hails* (2021) | Hiwatt SA212 and WEM Clubman, a Tube Works Blue Tube pedal, tape echo; no click | [interview] Premier Guitar |
| Satyricon, *Nemesis Divina* | Fender Performer only, "no boxes at all" (no pedals) | [interview] Guitar World 2022 |
| Mayhem today | Peavey 6505 | [interview] Necromorbus, SOS 2024 |
| Kark (modern Norwegian producer) | High-gain amp (two SM57s, on and off axis) **blended with an unmiked low-gain amp through a Palmer PDI-03 speaker sim**. Tube Screamer only for colour. Prefers amp distortion to pedals. | [interview] SOS 2024 Part 2 |

**Pattern:**
- The classic sound is **a cheap pedal driving an amp that is itself distorting**: a JCM800, a Peavey, a Fender Performer, a hi-fi amp.
- The amp and the cab/mic are at least half the tone.
- Anders Nyström (HM-2 specialist): the HM-2 works best driving the amp's **dirty** channel, not a clean one. [interview] MusicRadar
- The pedal-only approach (pedal into a near-linear amp) is not how these records were made.

**Tonal consensus** [fan], from many practitioner sources and consistent with each other:
- Treble-forward and "icy". Low end largely absent or thin.
- Mids present but not scooped (unlike death metal), with a 2–4 kHz attack lift.
- Less gain than death metal standards. Euronymous's DMDS tone is often called relatively low-gain.

**Production notes** [interview] Pytten:
- Distorted guitar stops carrying musical information somewhere in the low-mids. Below that it's boom.
- Guitars and cymbals compete for the same top end, so don't brighten both in the same range.
- Choose added effects carefully. Reverb on DMDS came from the room and outboard (Lexicon 480), not the guitar rig.

## 4. Module references (what the code models)

### Pedals (`sepulchre_dsp_dist.jsfx-inc`)
| Pedal | Source | Notes |
| :-- | :-- | :-- |
| RAT | ElectroSmash *Pro Co RAT Analysis* [circuit] | The LM308's slew rate is what separates it from a DS-1. `rd/43` vs `rd/47` mismatch (audit L1, unresolved). |
| DS-1 | ElectroSmash *Boss DS-1 Analysis* [circuit] | Big-Muff-style tone stack, −12 dB loss. |
| Metal Zone | Electric Druid *Boss MT-2 Metal Zone Pedal Analysis* [circuit] + reader SPICE | Gyrators via `gyro_peak()` (constant pole Q). The Round 9 "whistle" was a pole Q of 6.7. |
| HM-2 | Atomium Amps' analysis of a 1990 HM-2 [circuit] | IC1B rail drive, 0.3 V Ge coring. Fixed "wet cardboard" (R23) and "muffled" (R27). |

**Level make-ups** (`MT_MK`, `HM_MK`, the 1.6 / 3.96 factors) are [measured]: the pedals are loudness-matched to each other (Round 13).

### GE-7 record presets (`sepulchre_presets.jsfx-inc`)
- The band settings were read off Devin's photos of "GE-7 settings for record X" images, to about ±1.5 dB. **[fan]**
- No interview says any of these records used a GE-7, so treat the curves as tone sketches, not reconstructions.
- Their Level values are [measured] (loudness-matched, Round 39).
- **TS BOOST** (slot 6, pre-pedal; Round 94, replaced Spectre at Devin's request: "it kind of sounds like shit"): a Tube-Screamer-style push, −8 / −3 / +2 / +6 / +3 / 0 / −3, Level +8. Generic TS voicing (bass cut, ~800 Hz hump, level into the pedal), not a measured circuit. Through the four pedals its output is +0.1..+1.0 LUFS vs EQ off (synthetic `di_input.wav`), so the boost mostly becomes drive, not volume.

### Amp (`sepulchre_dsp_amp_cab.jsfx-inc`, `proc_amp_stage`)
- **Not a model of any real amp.** One static soft-clip curve (Tube: asymmetric `soft_tanh`; Solid: clip blend).
- Followed by a 75 Hz HPF, a 10 Hz DC blocker, and RBJ shelves and peaks (Bass 125 Hz, Mid 520/620 Hz, Treble 2.4 kHz, Air 3.8 kHz).
- No preamp stage structure, no interactive tone stack, no power amp, no speaker load. See §7-B.

### Cab (`sepulchre_dsp_amp_cab.jsfx-inc` & `sepulchre_dsp_ir.jsfx-inc`)
- **WAV IR UPOLS** (128-sample latency): user-loadable `.wav` IRs via `slider53` folder browser (`Data/sepulchre_irs/`) or drag-and-drop (`@serialize` MRU). No commercial IRs ship in the repo (Devin's local `Data/sepulchre_irs/` includes Ugritone Old School Black Metal, which may not be redistributed).
- **Loudness matching:** broadband guitar+K weighting (`HP 180 Hz -> LP 4200 Hz -> Peak 900 Hz +3 dB`) normalized to `IR_E48 = 0.132771` **[measured]** (Round 73; per-slot trims dropped in Round 68; `IR_MATCH_DB` retired in Round 73/76); shared per-pedal cab trims `ir_ped_g_t` **[measured]** apply to both WAV IR and Built-in 4x12.
- **Built-in 4x12 IIR cab** (selectable zero-latency option via `slider52`, also fallback when no IR is loaded): Round 88 Candidate A (`f2 = 850 Hz -3.0 dB`, `f3 = 3100 Hz +4.5 dB`, `lp2 = 4950 Hz Q 0.85`, `lp1 = 5550 Hz`, `cab_comp_lin = 0.7028` + Round 90 `CAB_TRIM_DB = +1.0 dB` measured against `01_BlackWizard_Center.wav` on a broadband multi-note riff) **[measured]**. Chosen on research (mids present, top fizz down) + R83 IR measurement; level-matched A/B by ear (Devin) heard no clear difference, so tagged **[measured]** (not **[ear]**) so a later ear test on multi-riff double-tracked DI takes can still revise it.

### Chorus (`sepulchre_dsp_fx.jsfx-inc`)
- Boss CE-2 per ElectroSmash [circuit]: triangle LFO, BBD with 3rd-order anti-alias filters, 50/50 mix.
- The ×0.78 level is [measured].

### Reverb (`sepulchre_dsp_fx.jsfx-inc`)
- Schroeder/Moorer style: 4 parallel combs and 2 series allpasses per channel, with RT60-calibrated feedback.
- Not modelled on any hardware.
- **The damping coefficient is scaled wrongly with sample rate** (Antigravity R67 H-3; keep 48 kHz as the reference when fixing). See §7-D.

## 5. Ear-tuned values: do not "fix" without Devin
- ~~`IR_MATCH_DB = 3.8`~~: retired in Round 73 (spectral cab loudness matching matched Built-in 4x12 and WAV IRs to `0.00 dB`, approved by Devin in Round 74; constant removed in Round 76 R1).
- The preset Master levels: calibrated to −18.6 LUFS from Antigravity's R57 REAPER render ([measured]). The bank was accepted by ear.
- Amp OFF ×0.84 (R35) and the chorus ×0.78: [measured], but tied to the above.
- Pedal choice per preset and every preset's character: Devin's call (R56).

## 6. Devin's listening history (what failed before, and why)
| Round | Complaint | Root cause found |
| :-- | :-- | :-- |
| 7 | "sounds like blues overdrive, not crunchy distortion" | ~34 dB gain plus an LPF before the clippers. Notes cleaned up as they decayed. |
| 9 | Couldn't hear RAT vs MODERN | A generic distortion with different gain amounts; replaced by circuit models. |
| 11 | Metal Zone "whistle" | RBJ peak with a pole Q of 6.7 |
| 13 | DS-1 quieter | Peak matching instead of loudness matching |
| 19 | WAV IR "WAY better… more natural", but quieter | IR normalisation ignored spectral shape |
| 20 | Can't play live | 43 ms latency |
| 23, 27 | HM-2 "wet cardboard", then "muffled" | IC1B wasn't driving the clippers hard enough |
| 54 | Built-in cab A/B'd against a $70 commercial amp sim: "didn't sound any better" | (positive result) |

Note that rounds 7, 23 and 27 all describe **the same symptom: not enough saturation where the real gear is saturated**. §7-A is a likely common cause that was never tested.

## 7. Research findings: what we may be getting wrong
Ranked by expected impact on out-of-the-box sound. Each has an experiment that settles it. None of this is implemented.

### A. Input calibration (impact depends on the interface; for Devin's setup, unknown until measured)
> **Correction (Round 67, after Devin's answers):** Devin uses a **Behringer UMC22**, Hi-Z input, gain at about 12 o'clock.
> - At minimum gain the UMC22's instrument input clips at +2 dBu (B&H spec sheet and the manual excerpt; one listing says −2 dBu). That is 0 dBFS ≈ 1.4 V peak, so **1 V peak ≈ −3 dBFS, only about 3 dB from this plugin's 1 V = 0 dBFS**.
> - At 12 o'clock he adds gain on top (Behringer doesn't publish the knob's dB range), so his pedals may see *more* voltage than the real pedal would, not less.
> - The "12 dB too little" case below applies to Focusrite/UAD-style interfaces and to the test DI, not necessarily to Devin.
> - What settles it: the INPUT meter peak when he plays hard, at his usual gain. Until then this item is **lower priority than C and the clarity work**.

- **The plugin's convention:** 1.0 digital = 1 V at the pedal input, so 0 dBFS = 1 V peak (SPEC §3.2).
- **The industry convention:**
  - Neural DSP's support post: a **1 V peak sine reads about −13 dBFS** on a UAD Apollo or a Focusrite Scarlett at minimum gain. It is −13.1 to −15.1 dBFS across six common interfaces.
  - Neural's plugins are built around that reference, so "interface gain 0, plugin input 0" behaves like plugging into the real amp.
  - NAM stores the same information as `input_level_dbu` metadata.
- **Real guitar levels** (Elliott Sound Products, measured on a scope): humbucker bridge chords about **0.85 V peak** (average 0.62 V peak). Single coils 0.25–0.45 V peak. Expect about +6 dB more when picking hard.
- **Our test clip:** `tests/render/di_input.wav` is a **synthetic 0.45 s three-sine chord (82/164/247 Hz)** peaking at **−12.5 dBFS**, which the plugin treats as **0.24 V** (not a real recorded guitar DI). On a Scarlett at minimum gain, the same signal is about **1.06 V**, a normal hot humbucker.
  - So every pedal model is driven about **12.5 dB below** what the real pedal would get from the same guitar.
  - The INPUT meter's target zone (−18..−6 dBFS) tells the player to keep it there.
- **Why it matters:** these are nonlinear models with real thresholds (diodes at 0.6–0.7 V, rails at ±4 V, the HM-2's 0.3 V Ge coring dead band). At a quarter of the voltage:
  - decays drop below the clipping and coring thresholds sooner, so notes clean up and the buzz sputters out early;
  - the presets compensate with maxed knobs (DS-1 Dist 10, HM-2 Dist 10 in the defaults).
  - This fits the R7 / R23 / R27 complaints.
- **Experiment:** render each pedal on the same DI at +0 / +6 / +12 dB of *internal* pre-pedal gain, with the output level matched by loudness. Compare by ear and by "saturation over a decaying note" (crest factor vs time on `decay_low_e.wav`).
- **Possible fix:** a fixed internal input calibration, for example "0 dBFS = +12 dBu, so 1 Vp = −13 dBFS", applied before the gate and pedal. Then re-centre the Level make-ups and the preset knobs.
  - Optionally offer an "Interface" choice (Scarlett/Apollo, Clarett/Apogee, Custom dBu) like the commercial sims.
  - This changes every preset, so it needs Devin's approval and a re-voicing round.

### B. The amp is the weakest model, and the genre relies on it (high impact, larger work)
- §3 shows the classic rigs are pedal → **distorting amp** → 4x12. Here the amp is one static curve plus shelves.
- What a JCM800 2203-style amp adds that we lack (Robinette, *How the Marshall JCM800 Works*; Pakarinen & Yeh 2009):
  - two cascaded triode gain stages with coupling high-passes (these tighten the low end *before* clipping, which is the main reason a cranked Marshall stays articulate);
  - a cathode-follower stage that clips asymmetrically when pushed;
  - an **interactive passive tone stack** (bass, mid and treble affect each other; the Marshall stack has its own mid dip);
  - a power amp with negative feedback, presence and resonance controls, and some sag.
- **References:**
  - Yeh & Smith, *Discretization of the '59 Fender Bassman Tone Stack* (DAFx-06): closed-form coefficients for the Fender/Marshall/Vox tone stack, which are the same circuit with different values. An open implementation is in CAPS `ToneStack.cc`.
  - Yeh's PhD thesis (CCRMA 2009): preamp stage models.
  - Pakarinen & Yeh, *A Review of Digital Techniques for Modeling Vacuum-Tube Guitar Amplifiers* (Computer Music Journal 33(2), 2009).
- **Cheapest worthwhile step:** replace the amp's Bass/Mid/Treble shelves with the Yeh tone stack, using Marshall values, after a 2-stage preamp (HPF → clip → HPF → clip) driven by the pedal.
- Keep "Solid-State" as a separate voicing (Peavey Bandit / Fender Performer style), which also fits Burzum and Darkthrone.
- **Experiment:** prototype it in the Python mirror first. A/B it on Devin's DI against the current amp with the levels matched.

### C. The test and calibration material is too thin (high impact on preset quality, cheap)
- Every preset loudness and every "does it sound right" decision rests on `di_input.wav` (**a synthetic 0.45 s three-sine chord at 82/164/247 Hz**, not a recorded guitar DI) and synthetic tones. Because it has no energy above 400 Hz, it is a poor signal for judging cabinet brightness/fizz differences (3–8 kHz).
- Black metal is mostly sustained **tremolo-picked** notes and open chords, played double-tracked.
- **Needed:** Devin's own DI takes through his interface at a known gain, covering:
  - tremolo-picked single notes on the low strings;
  - open and barre chords;
  - palm-muted chugs;
  - a clean arpeggio;
  - and a **second take of each**.
- **Judge presets the way records are heard:** two takes panned hard L/R, and in context with drums. Pytten's guitar/cymbal top-end clash only shows up in context.
- **Free fallback DI:** SampleOddity's *Thrash DI* (check the licence before committing anything to the repo).

### D. The reverb architecture is the known-metallic kind (medium impact)
- Parallel combs plus series allpasses (Schroeder/Moorer) are documented as sounding "very metallic" on sharp transients (musicdsp reverb notes). Tremolo picking is a stream of sharp transients.
- Better-known designs:
  - **Dattorro**, *Effect Design Part 1* (JAES 1997): a plate reverb with every delay and coefficient published;
  - **Jot & Chaigne**: feedback-delay networks with per-line damping, so all modes decay together (no ringing modes).
- Valhalla DSP's *Getting Started With Reverb Design* lists the canonical papers.
- **Suggested:** a Dattorro plate for PLATE and an 8-line FDN for HALL/AMBIENT. Same knobs, so presets survive with a re-check.

### E. Objective reference matching (medium impact, tooling)
- "Sounds good" is subjective, but **long-term average spectrum (LTAS)** comparisons are not.
- Devin can pick reference records (the guitar-dominated ones: *Transilvanian Hunger*, *Filosofem*, *DMDS*). A script computes the 1/3-octave LTAS of each and compares it with each preset's double-tracked render.
- That turns "too dark" or "fizzy" into a dB-per-band number to discuss.
- The reference audio stays on Devin's machine (copyright). Only the curves go in the repo.

### F. Smaller ideas (low impact or optional)
- **Parallel low-gain blend** (Kark's technique): a mix control for a lower-gain path. It adds definition without less saturation.
- **ADAA** (Parker, Zavalishin & Le Bivic, DAFx-16; Bilbao et al., IEEE SPL 2017): antiderivative anti-aliasing could replace or reduce the 8x oversampling on the static clippers, saving CPU. The current aliasing already passes (−47 to −57 dB), so this is only worth it if CPU becomes a problem.
- **Speaker impedance / power amp interaction:** forum evidence says it's small next to the IR's frequency response. Skip unless the power amp is modelled (B).

## 8. Questions for Devin, and his answers (2026-11-20)
1. **Interface and gain:** Behringer UMC22, gain at about 12 o'clock. See the §7-A correction. Still open: the INPUT meter peak when playing hard.
2. **DI recordings (§7-C):** Devin will release publicly, so tuning to him alone is not the goal. Use varied free DI material; Devin's takes are optional extra coverage. The INPUT-meter reading from question 1 is no longer needed either: the input will be calibrated to a convention (§2b).
3. **Reference records (§7-E):** "they all sort of get there, but the clarity of the guitars is questionable… maybe i added too many settings… i really just want a clean black metal guitar plugin… i think i'm doing too much probably chasing down particular sounds from different eras." He likes the presets.
   - **This sets the direction:** clarity and simplicity over era-matching. Keep the preset bank, but don't spend more effort reproducing specific records. §7-E (LTAS matching to records) is dropped.
4. **Amp direction (§7-B):** "i think our amp stuff might be getting to complicated… i just want to play." Keep the amp as a simple voicing stage; §7-B dropped.

## 8b. Cabinet IRs for the public build (Devin, 2026-11-20)
Devin's call: **users can load their own IR files**, and the plugin should bundle one freeware IR if the license allows, ideally a 5150.

**License research (2026-11-20). No free 5150 IR is clearly cleared for bundling.**

| Candidate | Cab | Terms found | Verdict |
| :-- | :-- | :-- | :-- |
| Shift Line *Guitar HD IR Pack 1* | Paid full pack includes Peavey 5150 4x12 (Sheffield 1200) and open-back 1x12 combos (Fender Deluxe Reverb Jensen P12R, Yerasov Bluespace Greenback); free pack is 4 impulses with cab models unlisted | No license text published | **Ask first.** Contact page exists (link-only for now). |
| Jester Dyne *Brutal Pack* | Modified Behringer BG412S, V30 / G12F-60 / DV-77, 44.1 + 48 kHz | Author: free "even for commercial use"; silent on redistribution. (darwinscat calls it CC0, but the author's page doesn't.) | **Ask first.** Strongest non-5150 candidate. |
| overdriven.fr *US-412 / V30* | Mesa-style 4x12 V30 | Free for any use, but **software vendors may not distribute without written agreement**; link to the download instead | Not bundleable without permission |
| Origin Effects, Forward Audio free packs, Metal Cabs (Ekholm), fnpngn repo | various (Origin includes open-back 1x12 Fender-style combos) | Commercial music use OK; no redistribution grant, or redistribution prohibited (Origin, per darwinscat); Ekholm's link is dead | Not bundleable (link-only) |
| Soundwoofer (community IR library, `soundwoofer.com`) | Community 1x12 & open-back combo IRs | Free download; no blanket commercial/redistribution license (per-uploader copyright) | Not bundleable (link-only; check per-file terms) |
| Freesound.org (`CC0` / `CC-BY` filtered 1x12 IRs) | Community-captured 1x12 / open-back IRs | CC0 (public domain, commercial + redistribution, no attribution) or CC-BY (commercial + redistribution with attribution) | **Bundleable** only after verifying individual file's CC0/CC-BY tag and audio quality (search strategy only; **no bundleable 1x12 IR found yet**) |

**Recommendation:**
1. Ship with the **built-in cab as the default**, so the plugin sounds right for everyone with no files. It needs voicing work: model it on a 4x12 V30 or Sheffield response rather than the current generic curve.
2. Support **user IRs**.
3. Ask Shift Line (5150) and Jester Dyne (Brutal Pack) for written permission to bundle one IR, with attribution. **The email is Devin's to send.**
4. Until a reply arrives, the README links to free downloads, which is always allowed, including overdriven.fr.

**Status (2026-11-24):** user-loadable IRs shipped in Rounds 68/71; bundling and permission emails remain deferred. **11d outcome: no bundleable 1x12 IR found yet** (links only in README). Keep using the local Ugritone IRs for testing until Devin tests/clears a redistributable IR.

**User-IR design notes (for the implementing agent; verify each against the current JSFX reference):**
- **File slider:** replace the fixed `slider53` enum with a JSFX **file slider**, `slider53:/sepulchre_irs:<default>:Cabinet IR`. REAPER then lists every file in `<REAPER resource>/Data/sepulchre_irs/`, and `file_open(slider53)` opens the selected one.
- **No file dialog:** JSFX has none, so users copy IRs into that folder (document this in the README). The name for the UI can come from `strcpy_fromslider()`.
- **Remove the per-slot tables:** `get_ir_filename`, `get_ir_slot_name`, `get_ir_slot_trim_db`. Keep the generic weighted-energy loudness match (`IR_E48`) and `IR_MATCH_DB` **[ear]**. They work for any IR; the per-slot trims only fit the 10 Ugritone files.
- **Expect any format:** mono or stereo (use channel 0 or the mean), 44.1–192 kHz, 20 ms–1 s+.
  - Apply the Antigravity R67 H-4 clamps (`ir_filter_len ≤ 8192`, `ir_raw_len ≤ 32768 / nch`).
  - Fade out the truncation at 42.7 ms instead of hard-cutting it.
  - On a failed load, fall back to the built-in cab and say so in the UI (Claude R67 H1).
- **Defaults:** an empty folder, or no selection, means the built-in cab with no PDC latency.
- **Keep the Cabinet on/off switch** for users who run their own IR loader, and don't let presets force it on (Claude R67 H3).

## 9. Sources
- Sound On Sound, *Producing Norwegian Black Metal* Part 1 (Pytten, Mayhem): https://www.soundonsound.com/node/4931450 · Part 2 (Kark, Necromorbus): https://www.soundonsound.com/techniques/producing-norwegian-black-metal-part-2
- Guitar World, *Burzum: Heart of Darkness* (2010): https://www.guitarworld.com/gw-archive/burzum-heart-darkness
- Guitar World, Nocturno Culto interview (2022): https://www.guitarworld.com/features/darkthrones-nocturno-culto-i-would-like-metallica-to-record-on-our-equipment-what-would-they-do-to-express-themselves-through-that-gear
- Premier Guitar, Darkthrone *Eternal Hails* gear: https://www.premierguitar.com/artists/guitarists/darkthrone
- Wikipedia, Varg Vikernes / Filosofem / Transilvanian Hunger: https://en.wikipedia.org/wiki/Varg_Vikernes · https://en.wikipedia.org/wiki/Filosofem · https://en.wikipedia.org/wiki/Transilvanian_Hunger
- MusicRadar, Anders Nyström on the HM-2: https://musicradar.com/news/interview-boss-hm2-anders-nystrom
- Equipboard (fan-sourced): https://equipboard.com/pros/euronymous · Ultimate-Metal OSBM tone thread: https://ultimatemetal.com/threads/how-to-get-an-old-school-black-metal-tone-that-doesnt-suck.1762370
- Neural DSP input-level post: https://unity.neuraldsp.com/t/optimal-input-level-for-highest-accuracy-when-using-ndsp-plugins/11048/2
- NAM calibration docs: https://neural-amp-modeler.readthedocs.io/en/stable/tutorials/calibration.html
- Elliott Sound Products, *Guitar & Bass Pickup Output Voltages*: https://www.sound-au.com/articles/guitar-voltage.htm
- Yeh & Smith, Bassman tone stack (DAFx-06): https://dafx.de/paper-archive/details/bbvGpyU59H2nHvV3Iamezg · Yeh tone stack page: https://ccrma.stanford.edu/~dtyeh/tonestack · Yeh thesis: https://ccrma.stanford.edu/~dtyeh/papers/DavidYehThesisdoublesided.pdf · CAPS `ToneStack.cc`: https://sources.debian.org/src/caps/0.9.23-1/ToneStack.cc/
- Pakarinen & Yeh 2009 review: https://www.effectrode.com/wp-content/uploads/2018/08/a_review_of_digital_techniques_for_modeling_guitar_amplifiers.pdf
- Rob Robinette, *How the Marshall JCM800 Works*: https://robrobinette.com/How_the_Marshall_JCM800_Works.htm
- Parker, Zavalishin & Le Bivic, ADAA (DAFx-16): https://dafx.de/paper-archive/details/vem_XXF5qBbfiWOH2RVVAA · Jatin Chowdhury ADAA notes: https://ccrma.stanford.edu/~jatin/Notebooks/adaa.html
- Dattorro, *Effect Design Part 1*: https://ccrma.stanford.edu/~dattorro/EffectDesignPart1.pdf · Valhalla DSP reverb papers: https://valhalladsp.com/2021/09/22/getting-started-with-reverb-design-part-2-the-foundations/ · musicdsp reverb notes: https://musicdsp.readthedocs.io/en/latest/Effects/45-reverberation-techniques.html
- Electric Druid MT-2 analysis: https://electricdruid.net/boss-mt-2-metal-zone-pedal-analysis/ · ElectroSmash (RAT, DS-1, CE-2 analyses): https://www.electrosmash.com
- IR licensing: Shift Line *Guitar HD IR Pack 1*: https://shift-line.com/guitarhdirpack1 · Jester Dyne *Brutal Pack*: https://www.jester-dyne-productions.com/brutal-ir-pack/ · darwinscat IR utility: https://darwinscat.com/sound-utils/cabinet-ir-utility · overdriven.fr US-412: https://overdriven.fr/overdriven/index.php/us-412-v30-home-studio-edition-free-guitar-cab-impulse-responses-download/ · fnpngn free IR list: https://github.com/fnpngn/IR
- JSFX file sliders and `file_open`: https://www.reaper.fm/sdk/js/file.php · https://www.reaper.fm/sdk/js/js.php
- SampleOddity *Thrash DI* (free DI): https://bedroomproducersblog.com/2012/10/13/thrash-di-a-commercial-metal-guitar-sample-library-by-sampleoddity/
