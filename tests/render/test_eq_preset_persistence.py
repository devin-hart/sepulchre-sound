import os
import sys
import numpy as np

RENDER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(RENDER_DIR, "..", ".."))
sys.path.insert(0, os.path.join(REPO_DIR, "tests"))
sys.path.insert(0, RENDER_DIR)

import render_common as rc

def test_eq_preset_persistence():
    """
    Verifies that:
    1. A project saved with slider75 = 5 (Filosofem '96) but a tweaked fader
       (e.g. 1.6 kHz slider70 set to -10.0 dB instead of preset's +12.5 dB)
       preserves the tweaked fader upon project load (does not overwrite with preset table).
    2. A project with standard Filosofem '96 has +12.5 dB at 1.6 kHz.
    """
    sr = 48000
    # Create an impulse input to measure frequency response
    impulse = np.zeros(sr, dtype=np.float32)
    impulse[100] = 0.5  # Impulse at sample 100
    imp_path = os.path.join(RENDER_DIR, "test_impulse.wav")
    rc.write_wav24(imp_path, impulse, sr=sr)

    # Clean signal chain with EQ ON, all amp/dist/FX off
    base = {
        1: 0.0, 2: 105.0, 3: -52.0, 4: 0, # Gate off
        5: 4, 6: 0, 7: 1, 8: 2, 74: 3,    # EQ first
        10: 0,                            # Dist off
        20: 0, 30: 0, 40: 0,              # FX off
        49: 0, 54: 0,                     # Cab & Amp off
        65: 1,                            # EQ Enabled
        75: 5,                            # Filosofem '96 preset id
        # Stock Filosofem '96 faders:
        66: 3.5, 67: 4.0, 68: -5.0, 69: 9.5, 70: 12.5, 71: 3.5, 72: 14.0, 73: 3.0
    }

    # Track 1: Stock Filosofem '96 loaded from project
    # Track 2: Project saved with slider75 = 5, but slider70 (1.6 kHz) tweaked to -10.0 dB
    tweaked = dict(base)
    tweaked[70] = -10.0 # User tweak

    item_len = 0.5
    tracks_xml = [
        rc.make_track("Stock_Filosofem", base, imp_path, 0.0, item_len),
        rc.make_track("Tweaked_Filosofem", tweaked, imp_path, 0.6, item_len),
    ]

    out_wav = os.path.join(RENDER_DIR, "out_eq_persistence.wav")
    rpp_path = os.path.join(RENDER_DIR, "test_eq_persistence.rpp")

    with open(rpp_path, "w", encoding="utf-8") as f:
        f.write(rc.build_rpp(tracks_xml, out_wav, 1.3, sr=sr))

    if os.path.exists(out_wav): os.remove(out_wav)
    print("Rendering EQ preset persistence test in live REAPER host...")
    rc.run_reaper(rpp_path)

    samples = rc.read_wav24(out_wav, channel=0)
    seg1 = samples[int(0.0 * sr) : int(0.5 * sr)]
    seg2 = samples[int(0.6 * sr) : int(1.1 * sr)]

    # Compute FFT to inspect 1.6 kHz bin (bin ~ 1600 Hz in 4096-pt FFT)
    fft_size = 4096
    fft1 = np.abs(np.fft.rfft(seg1[100:100+fft_size]))
    fft2 = np.abs(np.fft.rfft(seg2[100:100+fft_size]))
    freqs = np.fft.rfftfreq(fft_size, 1.0 / sr)

    bin_1600 = np.argmin(np.abs(freqs - 1600.0))
    gain1_db = 20.0 * np.log10(fft1[bin_1600] / 0.5)
    gain2_db = 20.0 * np.log10(fft2[bin_1600] / 0.5)

    print(f"1600 Hz measured response:")
    print(f"  Stock Filosofem (slider70 = +12.5 dB, level = +3 dB): {gain1_db:+.2f} dB")
    print(f"  Tweaked Filosofem (slider70 = -10.0 dB, level = +3 dB): {gain2_db:+.2f} dB")
    print(f"  Delta: {gain2_db - gain1_db:+.2f} dB (expected ~ -22.5 dB)")

    # Assert that the tweaked fader was preserved
    assert gain1_db > 15.0, f"Stock Filosofem should boost > 15 dB at 1.6k, got {gain1_db:.2f} dB"
    assert gain2_db < -5.0, f"Tweaked Filosofem should cut < -5 dB at 1.6k, got {gain2_db:.2f} dB"
    assert gain2_db - gain1_db < -24.0, f"Delta should be < -24 dB, got {gain2_db - gain1_db:.2f} dB"
    print("PASS: Project load preserved user tweaked faders while retaining slider75 preset tag.")

if __name__ == "__main__":
    test_eq_preset_persistence()
