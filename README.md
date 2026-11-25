# Sepulchre Sound

A native Cockos REAPER JSFX guitar rig built for black metal — clear modern distortion out of the box, early-90s raw showcases, and atmospheric chorus/reverb washes.

## Signal Chain

```
Input Trim / Low Cut / Hysteresis Noise Gate
  -> [GE-7 7-Band EQ (Pre)]
  -> 8x-Oversampled Distortion (RAT / DS-1 / Metal Zone / HM-2)
  -> [GE-7 7-Band EQ (Post)]
  -> Amp Voicing (Off / Tube / Solid-State + Bass / Mid / Treble)
  -> Boss CE-2 Chorus (FX Loop)
  -> Diffused Modulated 4x4 Hadamard FDN Reverb (FX Loop: Hall / Plate / Ambient)
  -> Cabinet (User WAV IR via 128-sample UPOLS, or Built-in V30/Sheffield 4x12)
  -> Air / Master / -1.0 dBFS C1 Ceiling Limiter
```

## Installation

1. Copy all `sepulchre_*.jsfx*`, `sepulchre_bg.jpg`, and `sepulchre_titles.png` files into REAPER's `Effects/sepulchre_sound/` folder:
   - **Linux:** `~/.config/REAPER/Effects/sepulchre_sound/`
   - **Windows:** `%APPDATA%\REAPER\Effects\sepulchre_sound\`
   - **macOS:** `~/Library/Application Support/REAPER/Effects/sepulchre_sound/`
2. Restart REAPER (or press `F5` in the FX Browser) and insert **JS: Sepulchre Sound (Raw Black Metal Pedalboard)**.

## Loading Your Own Cabinet IRs

Sepulchre Sound ships with a built-in V30/Sheffield 4x12 cabinet model (zero latency) and supports any user `.wav` impulse response (mono or stereo, 44.1–192 kHz, 128-sample / 2.7 ms latency @ 48 kHz):

1. Create a `sepulchre_irs` folder inside REAPER's `Data/` directory:
   - **Linux:** `~/.config/REAPER/Data/sepulchre_irs/`
   - **Windows:** `%APPDATA%\REAPER\Data\sepulchre_irs\`
   - **macOS:** `~/Library/Application Support/REAPER/Data/sepulchre_irs/`
2. **Two ways to load IRs:**
   - **Drag-and-drop (quickest):** Drag any `.wav` IR file from your file manager onto the plugin window. Click the IR name in **VII CABINET** to open the popup menu (Built-in 4x12, Folder IR, and up to 8 recently dropped IRs; saved automatically with your REAPER project).
   - **Folder browser:** Drop `.wav` files into `Data/sepulchre_irs/`, set **VII CABINET** to **IR FILE**, and choose any IR from the **Cabinet IR** dropdown in REAPER's generic **UI** view (click the **UI** button in the top-right of the FX window).
   - Switch **VII CABINET** to **BUILT-IN** anytime for the zero-latency built-in 4x12, or toggle the cabinet power lamp off to use an external IR loader.

### Free Third-Party IR Packs
No commercial IRs are bundled in this repository. Good free starting points:
- **overdriven.fr US-412 / V30:** https://overdriven.fr/overdriven/index.php/us-412-v30-home-studio-edition-free-guitar-cab-impulse-responses-download/
- **Shift Line Guitar HD IR Pack (includes 4x12 & open-back 1x12 combos):** https://shift-line.com/guitarhdirpack1
- **Jester Dyne Brutal Pack:** https://www.jester-dyne-productions.com/brutal-ir-pack/
- **Soundwoofer (free community IR library, including 1x12 combos):** https://soundwoofer.com/
- **Origin Effects IR Cab Library (includes open-back 1x12 combos):** https://origineffects.com/ir-cab-library/

## Input Gain Calibration

The distortion pedals are calibrated to the `1 V peak ≈ -12 dBFS` interface convention (matching Focusrite Scarlett / UAD Apollo Hi-Z inputs at minimum gain). Set your interface gain or **I INPUT TRIM** so hard picking peaks inside the **−18 to −6 dBFS** target zone on the INPUT meter.

## Getting the Black Metal Sound

- **Double-tracking:** Record the riff twice and insert a Sepulchre Sound instance on each take, panned hard L/R, using a different pedal or cabinet IR on each side. Classic records get their width from two contrasting rigs rather than one tone duplicated.
- **Delay:** For a cavernous, drenched atmosphere, place a delay plugin *after* Sepulchre Sound in your FX chain. Delay is intentionally omitted from the plugin to keep the signal chain focused.
- **Clarity on open chords:** Raise **LOW CUT** (`40–180 Hz` in **I INPUT**) and switch **III EQUALIZER** to **PRE PEDAL** to trim sub-bass before the clipping stage. Starving the pedal of low-end energy prevents intermodulation from smearing minor and dissonant chords.
- **Gain:** Use less pedal **DIST** / **DISTORTION** than you think — moderate gain sounds heavier and clearer once double-tracked, keeping fast tremolo pick attack audible instead of collapsing into white noise.

## Verification

```bash
python3 tests/verify_jsfx.py
```
Requires Python 3 (`numpy` optional; enables real-IR loudness check `[9/9]` and live REAPER render tests in `tests/render/`).
