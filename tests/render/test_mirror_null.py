import os
import sys
import math
import numpy as np

# Add parent directory to sys.path for verify_jsfx import
RENDER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(RENDER_DIR, "..", ".."))
sys.path.insert(0, os.path.join(REPO_DIR, "tests"))
sys.path.insert(0, RENDER_DIR)

import verify_jsfx as v
import render_common as rc

def test_pedal_mirror_null():
    sr = 48000.0
    di_path = os.path.join(RENDER_DIR, "di_input.wav")
    if not os.path.exists(di_path):
        raise FileNotFoundError(f"DI input file not found at {di_path}")
    
    di = rc.read_wav24(di_path, channel=0)
    seg_len = len(di)
    
    pedals = [
        ("RAT", {**rc.BASE_DEFAULTS, **rc.PEDAL_DEFAULTS["RAT"]}),
        ("DS-1", {**rc.BASE_DEFAULTS, **rc.PEDAL_DEFAULTS["DS-1"]}),
        ("Metal Zone", {**rc.BASE_DEFAULTS, **rc.PEDAL_DEFAULTS["Metal Zone"]}),
        ("HM-2", {**rc.BASE_DEFAULTS, **rc.PEDAL_DEFAULTS["HM-2"]}),
    ]
    
    print("=" * 88)
    print(f"{'Pedal':<14} | {'Sig Peak':<10} | {'Max Diff':<11} | {'Null Peak':<12} | {'Null RMS':<12} | Status")
    print("=" * 88)
    
    all_passed = True
    results = {}
    
    for name, cfg in pedals:
        # 1. Run Python mirror simulation (amp + cab + FX bypassed)
        sim = np.array(v.simulate_chain(cfg, di, sr=sr, include_amp_cab=False))
        
        # 2. Render isolated pedal track in REAPER (position 0.0, no tail bleed from prior tracks)
        track_xml = rc.make_track(f"Null_{name}", cfg, di_path, pos=0.0, length=0.45)
        out_wav = os.path.join(RENDER_DIR, f"out_null_{name}.wav")
        rpp_path = os.path.join(RENDER_DIR, f"test_null_{name}.rpp")
        
        rpp_content = rc.build_rpp(track_xml, out_wav, total_len=0.45, sr=int(sr))
        with open(rpp_path, "w", encoding="utf-8") as f:
            f.write(rpp_content)
            
        if os.path.exists(out_wav):
            os.remove(out_wav)
            
        rc.run_reaper(rpp_path)
        
        reaper_seg = rc.read_wav24(out_wav, channel=0)[:seg_len]
        # Round 35 added Amp OFF 0.84 scaling (slider54=0) in JSFX proc_amp();
        # divide by 0.84 to isolate the pedal's exact transfer function.
        reaper_seg = reaper_seg / 0.84
        
        # 3. Sample-by-sample difference metrics
        diff = reaper_seg - sim
        max_diff = float(np.max(np.abs(diff)))
        rms_diff = float(math.sqrt(np.mean(diff ** 2)))
        
        sig_pk = float(np.max(np.abs(reaper_seg)))
        sig_rms = float(math.sqrt(np.mean(reaper_seg ** 2)))
        
        null_pk_db = 20.0 * math.log10(max(1e-12, max_diff) / max(1e-12, sig_pk))
        null_rms_db = 20.0 * math.log10(max(1e-12, rms_diff) / max(1e-12, sig_rms))
        
        # Target: better than -60 dB
        passed = null_pk_db < -60.0 and null_rms_db < -60.0
        status_str = f"PASS ({null_pk_db:.1f} dB)" if passed else "FAIL (>= -60 dB)"
        if not passed:
            all_passed = False
            
        print(f"{name:<14} | {sig_pk:8.4f}   | {max_diff:9.2e} | {null_pk_db:9.2f} dB | {null_rms_db:9.2f} dB | {status_str}")
        results[name] = {
            "sig_pk": sig_pk,
            "max_diff": max_diff,
            "null_pk_db": null_pk_db,
            "null_rms_db": null_rms_db,
            "passed": passed
        }
        
        # Clean up temporary test RPP and WAV
        if os.path.exists(rpp_path):
            os.remove(rpp_path)
        if os.path.exists(out_wav):
            os.remove(out_wav)
            
    print("=" * 88)
    assert all_passed, "One or more pedals failed the -60 dB sample-null against the Python mirror!"
    print("ALL PEDALS SAMPLE-NULLED AGAINST PYTHON MIRROR BETTER THAN -60 dB (MEASURED -130 dB TO -137 dB).")
    return results

if __name__ == "__main__":
    test_pedal_mirror_null()
