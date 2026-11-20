#!/usr/bin/env python3
"""
Sepulchre Sound — Background Generator Tool
Generates sepulchre_bg.jpg (2408x1000) for the JSFX plugin.

Features:
- Subterranean stone masonry wall across full 2408x1000 canvas
- Chiseled monumental Roman "SEPULCHRE" letter cutouts revealing lighter raw stone
- Uniform continuous dark atmospheric overlay across the entire window (no horizontal seams)
- Translucent recessed burial niche cavities for the 7 pedal columns
"""

import os
import sys
import math
import argparse
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont

W, H = 2408, 1000

NICHES = [
    (28, 300),
    (348, 324),
    (692, 324),
    (1036, 324),
    (1380, 324),
    (1724, 300),
    (2044, 336),
]


def generate_background(wall_source=None, font_path=None, output_path="sepulchre_bg.jpg"):
    # 1. Base Wall Construction
    if wall_source and os.path.exists(wall_source):
        wall_img = Image.open(wall_source).convert("RGB")
        ww, wh = wall_img.size
        scale = 1000.0 / wh
        scaled_w = int(ww * scale)
        scaled_wall = wall_img.resize((scaled_w, 1000), Image.Resampling.LANCZOS)

        base_canvas = Image.new("RGB", (W, H), (20, 20, 18))
        tile1 = scaled_wall.crop((0, 0, min(scaled_w, W), H))
        base_canvas.paste(tile1, (0, 0))

        tile2 = scaled_wall.transpose(Image.FLIP_LEFT_RIGHT)
        overlap = scaled_w * 2 - W
        if overlap > 0:
            blend_x_start = scaled_w - 200
            blend_w = 400
            tile2_pos_x = W - scaled_w
            mask = Image.new("L", (W, H), 0)
            draw_m = ImageDraw.Draw(mask)
            for x in range(blend_x_start, blend_x_start + blend_w):
                t = (x - blend_x_start) / float(blend_w)
                alpha = int((1.0 - math.cos(t * math.pi)) * 0.5 * 255)
                draw_m.line([(x, 0), (x, H)], fill=alpha)
            draw_m.rectangle([(blend_x_start + blend_w, 0), (W, H)], fill=255)
            tile2_full = Image.new("RGB", (W, H), (0, 0, 0))
            tile2_full.paste(tile2, (tile2_pos_x, 0))
            base_canvas.paste(tile2_full, (0, 0), mask)
        else:
            x_off = scaled_w
            flip = True
            while x_off < W:
                src = tile2 if flip else scaled_wall
                base_canvas.paste(src.crop((0, 0, min(scaled_w, W - x_off), H)), (x_off, 0))
                x_off += scaled_w
                flip = not flip

        enhancer = ImageEnhance.Color(base_canvas)
        base_canvas = enhancer.enhance(0.75)
        enhancer_b = ImageEnhance.Brightness(base_canvas)
        base_canvas = enhancer_b.enhance(0.70)
        wall_arr = np.array(base_canvas, dtype=np.float32)
    else:
        # Fallback procedural stone texture if no external source image is provided
        np.random.seed(42)
        base = np.full((H, W, 3), 48.0, dtype=np.float32)
        noise = np.random.normal(0, 12, (H, W, 1)).astype(np.float32)
        wall_arr = np.clip(base + noise, 0, 255)

    # 2. Letter Mask for "SEPULCHRE"
    letter_mask = Image.new("L", (W, H), 0)
    draw_mask = ImageDraw.Draw(letter_mask)
    letters = ["S", "E", "P", "U", "L", "C", "H", "R", "E"]
    start_x, y_pos, spacing = 150, 58, 38

    font = None
    if font_path and os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, 96)
        except Exception:
            font = None

    if font:
        cur_x = start_x
        for ch in letters:
            draw_mask.text((cur_x, y_pos), ch, fill=255, font=font)
            bbox = font.getbbox(ch)
            cur_x += (bbox[2] - bbox[0]) + spacing
    else:
        cur_x = start_x
        for ch in letters:
            draw_mask.text((cur_x, y_pos), ch, fill=255)
            cur_x += 80

    letter_mask_blurred = letter_mask.filter(ImageFilter.GaussianBlur(1.0))
    letter_arr_smooth = np.array(letter_mask_blurred, dtype=np.float32) / 255.0

    shift_x, shift_y = 3, 3
    inner_shadow_mask = np.zeros_like(letter_arr_smooth)
    inner_shadow_mask[shift_y:, shift_x:] = letter_arr_smooth[:-shift_y, :-shift_x]
    chisel_shadow = np.clip(letter_arr_smooth - inner_shadow_mask, 0.0, 1.0)

    shift_ux, shift_uy = 2, 2
    outer_highlight_mask = np.zeros_like(letter_arr_smooth)
    outer_highlight_mask[:-shift_uy, :-shift_ux] = letter_arr_smooth[shift_uy:, shift_ux:]
    chisel_highlight = np.clip(letter_arr_smooth - outer_highlight_mask, 0.0, 1.0)

    # 3. Transparent Dark Overlay Across Entire Canvas (y: 0..1000)
    tint_dark = np.array([8.0, 8.0, 7.0], dtype=np.float32)
    full_overlay_alpha = np.full((H, W), 0.65, dtype=np.float32)
    full_overlay_alpha *= (1.0 - 0.95 * letter_arr_smooth)

    alpha_3d = np.expand_dims(full_overlay_alpha, axis=2)
    wall_arr = wall_arr * (1.0 - alpha_3d) + tint_dark * alpha_3d

    shadow_factor = np.expand_dims(chisel_shadow, axis=2)
    wall_arr *= (1.0 - 0.70 * shadow_factor)

    highlight_factor = np.expand_dims(chisel_highlight, axis=2)
    wall_arr += highlight_factor * np.array([32.0, 30.0, 26.0])

    # 4. Preset Socket (x: 1872, y: 72, w: 500, h: 56)
    px, py, pw, ph = 1872, 72, 500, 56
    socket_slice = wall_arr[py:py+ph, px:px+pw]
    wall_arr[py:py+ph, px:px+pw] = socket_slice * 0.45 + np.array([6, 6, 5]) * 0.55

    # 5. Niche Cavities (without separate title plates or border lines per Round 63)
    for nx, nw in NICHES:
        ny, nh = 212, 980 - 212
        niche_slice = wall_arr[ny:ny+nh, nx:nx+nw]
        cavity_tint = np.array([6.0, 6.0, 5.0], dtype=np.float32)
        wall_arr[ny:ny+nh, nx:nx+nw] = niche_slice * 0.65 + cavity_tint * 0.35

        # Soft top cavity shadow (14 px)
        for s in range(14):
            t = (1.0 - s / 14.0) ** 1.5
            wall_arr[ny + s, nx:nx+nw] *= (1.0 - 0.35 * t)

    out_img = Image.fromarray(np.clip(wall_arr, 0, 255).astype(np.uint8))
    out_img.save(output_path, "JPEG", quality=92)
    print(f"Generated background: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sepulchre Background Generator")
    parser.add_argument("--wall", help="Path to source wall texture image", default=None)
    parser.add_argument("--font", help="Path to Cinzel.ttf font file", default=None)
    parser.add_argument("--out", help="Output path for JPEG", default="sepulchre_bg.jpg")
    args = parser.parse_args()

    generate_background(args.wall, args.font, args.out)
