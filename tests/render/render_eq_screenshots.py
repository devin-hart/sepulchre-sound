import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RENDER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(RENDER_DIR, "..", ".."))

# Palette definitions matching sepulchre_ui.jsfx-inc
RGB_VOID   = (9, 9, 9)
RGB_BONE   = (232, 227, 215)
RGB_LAB    = (163, 158, 148)
RGB_SOFT   = (154, 149, 139)
RGB_BORDER = (58, 56, 54)
RGB_TRACK  = (42, 41, 39)
RGB_FILL   = (143, 138, 128)
RGB_THUMB  = (239, 233, 220)
RGB_DET    = (86, 83, 78)
RGB_BLOOD  = (132, 18, 22)
RGB_EMBER  = (176, 28, 34)
RGB_MBG    = (29, 28, 27)
RGB_TICK   = (119, 114, 106)
RGB_INK    = (10, 10, 10)

FONT_BAHNSCHRIFT = "C:/Windows/Fonts/bahnschrift.ttf"
FONT_CONSOLAS = "C:/Windows/Fonts/consola.ttf"

def draw_letter_spaced_text(draw, x, y, text, font, fill, spacing=1.0):
    cur_x = x
    for ch in text:
        draw.text((cur_x, y), ch, font=font, fill=fill)
        # get length of character
        bbox = font.getbbox(ch)
        w = bbox[2] - bbox[0] if bbox else 6
        cur_x += w + spacing
    return cur_x - x

def draw_centered_letter_spaced(draw, cx, cy, text, font, fill, spacing=0.6):
    total_w = 0
    for ch in text:
        bbox = font.getbbox(ch)
        w = bbox[2] - bbox[0] if bbox else 6
        total_w += w + spacing
    total_w -= spacing
    bbox_h = font.getbbox("A")
    h = bbox_h[3] - bbox_h[1] if bbox_h else 10
    draw_letter_spaced_text(draw, cx - total_w * 0.5, cy - h * 0.5, text, font, fill, spacing)

def draw_eq_slab_composite(preset_idx, preset_name, faders, is_dirty=False, hot_band=None, hot_val=None):
    dw, dh = 1376, 500
    bg_orig = Image.open(os.path.join(REPO_DIR, "sepulchre_bg.jpg")).convert("RGB")
    titles_orig = Image.open(os.path.join(REPO_DIR, "sepulchre_titles.png")).convert("RGBA")

    # Resize bg to design window
    canvas = bg_orig.resize((dw, dh), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(canvas)

    f_label = ImageFont.truetype(FONT_BAHNSCHRIFT, 11)
    f_val   = ImageFont.truetype(FONT_CONSOLAS, 13)
    f_small = ImageFont.truetype(FONT_BAHNSCHRIFT, 9)
    f_tiny  = ImageFont.truetype(FONT_BAHNSCHRIFT, 9)

    # Slot B coordinates (Slot index 1): x = 346, w = 162
    x = 346
    w = 162
    ix = x + 10
    iw = w - 20
    UI_BODY_Y = 158

    # Title sprite: numeral II (row 10), EQUALIZER (row 16)
    # Row height in 2x image is 48 px; in 1x design space it is 24 px
    # Numeral II: num_i = 2 -> row 8 + 2 = 10, t_num_w(2) = 33
    num_w_2x = 33
    num_row = 10
    num_crop = titles_orig.crop((0, num_row * 48, num_w_2x, (num_row + 1) * 48))
    num_crop = num_crop.resize((int(num_w_2x * 0.5), 24), Image.Resampling.LANCZOS)
    canvas.paste(num_crop, (x + 10, 115), num_crop)

    # EQUALIZER title: row 16, t_name_w = 191
    name_w_2x = 191
    name_crop = titles_orig.crop((0, 16 * 48, name_w_2x, 17 * 48))
    name_crop = name_crop.resize((int(name_w_2x * 0.5), 24), Image.Resampling.LANCZOS)
    title_x = x + int(num_w_2x * 0.5) + 16
    canvas.paste(name_crop, (title_x, 114), name_crop)

    # Power LED: x + w - 21 = 487, y = 121
    led_x = x + w - 21
    led_y = 121
    draw.rectangle([led_x - 3, led_y - 3, led_x + 14, led_y + 14], fill=(70, 15, 18))
    draw.rectangle([led_x, led_y, led_x + 10, led_y + 10], fill=RGB_EMBER)

    # Preset stepper box: u_frame(ix, UI_BODY_Y - 4, iw, 24)
    box_y = UI_BODY_Y - 4
    draw.rectangle([ix, box_y, ix + iw, box_y + 24], outline=RGB_BORDER, width=1)
    draw.text((ix + 5, UI_BODY_Y + 1), "<", font=f_val, fill=RGB_FILL)
    draw.text((ix + iw - 13, UI_BODY_Y + 1), ">", font=f_val, fill=RGB_FILL)

    # Preset name with optional dirty indicator
    pname = preset_name
    if is_dirty and preset_idx > 0:
        pname += " *"
    draw_centered_letter_spaced(draw, ix + iw * 0.5, UI_BODY_Y + 8, pname, f_tiny, RGB_BONE, 0.6)

    # Sub-header readout: "+15 / 0 / -15 dB" or hovered band
    if hot_band is not None and hot_val is not None:
        readout_txt = f"{hot_band}  {hot_val:+.1f} dB"
    else:
        readout_txt = "+15 / 0 / -15 dB"
    bbox_ro = f_val.getbbox(readout_txt)
    ro_w = bbox_ro[2] - bbox_ro[0] if bbox_ro else 80
    draw.text((ix + iw - ro_w, UI_BODY_Y + 24), readout_txt, font=f_val, fill=RGB_BONE)

    # Faders: 8 vertical sliders
    band_labels = ["100", "200", "400", "800", "1.6K", "3.2K", "6.4K", "LVL"]
    fader_top_y = UI_BODY_Y + 48
    fader_h = 210

    for p in range(8):
        fx = ix + 8 + p * int((iw - 16) / 7.0)
        val = faders[p]
        norm = np.clip((val - (-15.0)) / 30.0, 0.0, 1.0)
        fy = fader_top_y + (1.0 - norm) * fader_h
        cy = fader_top_y + fader_h * 0.5

        # Slider track: u_rect(x - 1, y, 3, h)
        draw.rectangle([fx - 1, fader_top_y, fx + 1, fader_top_y + fader_h], fill=RGB_TRACK)
        # Center detent: u_rect(x - 4, cy - 0.5, 9, 1)
        draw.rectangle([fx - 4, int(cy), fx + 4, int(cy)], fill=RGB_DET)
        # Slider fill: u_rect(x - 1, min(cy, fy), 3, max(1, abs(fy - cy)))
        y_fill_min = int(min(cy, fy))
        y_fill_max = int(max(cy, fy))
        if y_fill_max > y_fill_min:
            draw.rectangle([fx - 1, y_fill_min, fx + 1, y_fill_max], fill=RGB_FILL)
        # Thumb: u_rect(x - 5, fy - 1.5, 11, 3)
        draw.rectangle([fx - 5, int(fy - 1.5), fx + 5, int(fy + 1.5)], fill=RGB_THUMB)

        # Band label centered below
        lbl = band_labels[p]
        bbox_l = f_tiny.getbbox(lbl)
        lw = bbox_l[2] - bbox_l[0] if bbox_l else 14
        draw.text((fx - lw * 0.5, fader_top_y + fader_h + 8), lbl, font=f_tiny, fill=RGB_LAB)

    return canvas

def generate_screenshots():
    # Preset 5: Burzum - Filosofem (1996)
    # Bands: +3.5, +4.0, -5.0, +9.5, +12.5, +3.5, +14.0, Level: +3.0
    filosofem_faders = [3.5, 4.0, -5.0, 9.5, 12.5, 3.5, 14.0, 3.0]

    # Image 1: Preset loaded
    img1 = draw_eq_slab_composite(5, "FILOSOFEM '96", filosofem_faders, is_dirty=False)
    p1_path = os.path.join(RENDER_DIR, "screenshot_eq_preset_loaded.png")
    img1.save(p1_path)
    print(f"Saved: {p1_path}")

    # Crop close-up around EQ slab for immediate inspection (x=330 to 520, y=100 to 490)
    crop1 = img1.crop((330, 95, 525, 485))
    c1_path = os.path.join(RENDER_DIR, "screenshot_eq_slab_loaded.png")
    crop1.save(c1_path)
    print(f"Saved close-up: {c1_path}")

    # Image 2: Dirty fader moved (1.6 kHz fader moved from +12.5 to -2.0 dB)
    dirty_faders = list(filosofem_faders)
    dirty_faders[4] = -2.0 # 1.6 kHz band moved
    img2 = draw_eq_slab_composite(5, "FILOSOFEM '96", dirty_faders, is_dirty=True, hot_band="1.6K", hot_val=-2.0)
    p2_path = os.path.join(RENDER_DIR, "screenshot_eq_preset_dirty.png")
    img2.save(p2_path)
    print(f"Saved: {p2_path}")

    crop2 = img2.crop((330, 95, 525, 485))
    c2_path = os.path.join(RENDER_DIR, "screenshot_eq_slab_dirty.png")
    crop2.save(c2_path)
    print(f"Saved close-up: {c2_path}")

if __name__ == "__main__":
    generate_screenshots()
