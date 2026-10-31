## Round 58 — Claude: Round 57 accepted; Spectre EQ preset, EQ names without years, preset levels from REAPER

### Round 57
Accepted, and thank you: the loudness audit caught a real problem in my Round 55 calibration. The mirror match (synthetic chord, IIR reference cab, no chorus or reverb) left an **11.7 dB** spread on the real WAV IR path.
- Nit for next time: your "Mono LUFS" and "Stereo LUFS" columns differ by about 3 dB because LUFS sums the channels. Report mono only.

### Changes
1. **Spectre EQ preset (#8).** Devin found the 6-band EQ curve Glenn Fricker (Spectre Sound Studios) uses: a JOYO JF-11, ±18 dB per band. I read it off his photo to about ±2 dB.
   - Curve: −9 / −5 / +8 / +14 / +12 / +4 / 6.4k 0 / Level 0.
   - It loads **before the pedal**: a tightening mid push into the drive.
   - New `eq_preset_pos(i)` in presets returns 0 for Spectre and 1 for the others. `recall_eq_preset` and `gp_eq` both use it.
   - `EQ_COUNT = 8` drives the < > wrap. `slider75` is 0..8.
   - Mirror estimate of Spectre's level change into the four pedals: DS-1 +0.8, MT-2 +0.1, RAT +0.4, HM-2 +0.2 dB. So Level stays at 0, like the real pedal, which has no level control.
2. **Years dropped from the EQ preset names** (UI and `slider75` enum): BATHORY, DEATHCRUSH, TRANSILVANIAN, NIGHTSIDE, FILOSOFEM, IN SORTE, EVANGELION, SPECTRE.
3. **Preset levels recalibrated from your Round 57 table** to the mono median of −18.62 LUFS, using `slider51` Master only. Master comes after everything except the limiter, so the corrections are exact.

   | Preset | Master |
   |---|---|
   | 01 | −3.8 |
   | 02 | −0.9 |
   | 03 | −0.9 |
   | 05 | −0.7 |
   | 06 | −1.4 |
   | 07 | +0.2 |
   | 08 | −2.6 |
   | 09 | +1.9 |
   | 10 | −1.8 |

   - Preset 01's slider defaults were updated to match.
   - **Buzzsaw is a compromise.** It needed +7.5 dB, but before the cab its signal is already hot: the Bathory treble gets eaten by the IR. I gave it Master +4.5 and HM-2 Level 5.0 → 5.6. With the cab off it peaks at −3.6 dBFS, just under the limiter knee. Expect it to stay about 4 dB under the median. Devin will decide whether to re-voice it (milder EQ curve or a lower HM-2 High).
   - Freezing Clean drops 4.1 dB, which also takes it off the limiter knee.
4. **`verify_jsfx.py` check [2/7]** no longer pretends to measure loudness. It checks that every preset peaks below the −3.1 dBFS knee with the cab on (reference cab) and the cab off, plus DC. The mirror's K-loudness is printed for reference only. The `gp_eq` parser handles Spectre's pre position.
   - I asked for the real IR folder so the mirror could calibrate against slot 0 directly, but folder access was denied. REAPER renders stay the loudness reference.

### Line counts
| File | Lines |
|---|---|
| `sepulchre_sound.jsfx` | 169 |
| `sepulchre_dsp_core.jsfx-inc` | 222 |
| `sepulchre_dsp_dist.jsfx-inc` | 198 |
| `sepulchre_dsp_fx.jsfx-inc` | 195 |
| `sepulchre_dsp_amp_cab.jsfx-inc` | 256 |
| `sepulchre_presets.jsfx-inc` | 162 |
| `sepulchre_ui.jsfx-inc` | 263 |
| `sepulchre_ui_panels.jsfx-inc` | 216 |

Total: 1,681.

### For Antigravity (Round 59)
1. Deploy and recompile.
2. Re-run the Round 57 preset loudness table (mono LUFS only, true peak).
   - Expect every preset within ±1 dB of −18.6 LUFS, except Buzzsaw at about −22.6.
   - Flag anything over 1.5 dB off. Change nothing.
3. Make that table a REAPER test that asserts ±1.5 dB from the median (Buzzsaw excepted, and named in the test) and no peak above −3.1 dBFS. From now on this is the loudness gate.
4. EQ presets:
   - Spectre loads with PRE PEDAL selected, and the other seven with POST.
   - < > wraps through all 8.
   - Add Spectre to `test_eq_preset_headroom` in the pre position, and report its LUFS delta vs EQ off for the four pedals.
5. UI: confirm the EQ name strip shows the new names. Otherwise write "UI not visually verified".
