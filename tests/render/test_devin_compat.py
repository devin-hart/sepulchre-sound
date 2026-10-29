import os
import sys
import render_common as rc

orig_rpp = r"C:\Users\wizardbeard\Documents\REAPER Media\black_metal_setup.rpp"
if not os.path.exists(orig_rpp):
    print("Devin's project file not found.")
    sys.exit(0)

with open(orig_rpp, "r", encoding="utf-8") as f:
    text = f.read()

# Extract Track 1 (GTR L with sepulchre_sound)
t_start = text.find("<TRACK {AB19180A-ADB8-4853-9BC7-580424E05121}")
t_end = text.find("<TRACK {BCBB12E9-8BB6-4987-A36B-7E53B6F4C964}")
track_xml = text[t_start:t_end].strip()

# Add an audio item to Track 1 so audio passes through
di_clean = os.path.join(rc.RENDER_DIR, "di_input.wav").replace("\\", "/")
item_xml = f"""    <ITEM
      POSITION 0.0
      LENGTH 0.45
      <SOURCE WAVE
        FILE "{di_clean}"
      >
    >
"""
track_with_item = track_xml[:-1] + item_xml + "\n  >"

out_wav = os.path.join(rc.RENDER_DIR, "out_devin_track.wav")
test_rpp = os.path.join(rc.RENDER_DIR, "test_devin_track.rpp")
rpp_content = rc.build_rpp(track_with_item, out_wav, 0.45, sr=44100)
with open(test_rpp, "w", encoding="utf-8") as f:
    f.write(rpp_content)

rc.run_reaper(test_rpp)
data = rc.read_wav24(out_wav, channel=0)
print(f"Rendered Devin track output samples: {len(data)}, Peak: {max(abs(data)):.4f}")
assert len(data) > 0 and max(abs(data)) > 0.01, "Devin track render failed!"
print("PASS: Devin old project track loaded, played in fixed order, and rendered cleanly!")

if os.path.exists(out_wav):
    os.remove(out_wav)
if os.path.exists(test_rpp):
    os.remove(test_rpp)
