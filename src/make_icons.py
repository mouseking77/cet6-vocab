# -*- coding: utf-8 -*-
"""Generate the app icons (icon-192.png / icon-512.png) with Pillow.

Usage:
    python src/make_icons.py
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONT_CANDIDATES = [
    r'C:\Windows\Fonts\msyhbd.ttc',
    r'C:\Windows\Fonts\msyh.ttc',
    r'C:\Windows\Fonts\simhei.ttf',
]

ACCENT = (124, 108, 255)
ACCENT2 = (56, 189, 248)
BG = (13, 16, 23)


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def make(size):
    img = Image.new('RGB', (size, size), BG)
    draw = ImageDraw.Draw(img)
    # diagonal gradient background
    grad = Image.new('RGB', (size, size))
    gd = ImageDraw.Draw(grad)
    for i in range(size):
        gd.line([(i, 0), (i, size)], fill=lerp((34, 26, 84), (12, 18, 34), i / max(1, size - 1)))
    img.paste(grad, (0, 0))

    # soft accent blob
    blob = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blob)
    r = int(size * 0.52)
    bd.ellipse([size * 0.30, -size * 0.28, size * 0.30 + r * 2, -size * 0.28 + r * 2],
               fill=ACCENT + (120,))
    bd.ellipse([-size * 0.30, size * 0.52, -size * 0.30 + r * 2, size * 0.52 + r * 2],
               fill=ACCENT2 + (70,))
    img = Image.alpha_composite(img.convert('RGBA'), blob).convert('RGB')
    draw = ImageDraw.Draw(img)

    # rounded card with a letter slot motif
    pad = size * 0.17
    draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=size * 0.13,
                           fill=(24, 30, 44), outline=(58, 70, 96), width=max(2, size // 96))

    font = None
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, int(size * 0.34))
                break
            except Exception:
                continue
    glyph = '词'
    if font is None:
        font = ImageFont.load_default()
        glyph = 'A'
    box = draw.textbbox((0, 0), glyph, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.text(((size - tw) / 2 - box[0], (size - th) / 2 - box[1] - size * 0.04), glyph,
              font=font, fill=(232, 236, 245))

    # three slot marks under the glyph
    w, h = size * 0.10, max(3, size * 0.022)
    gap = size * 0.055
    total = 3 * w + 2 * gap
    y = size * 0.70
    for i in range(3):
        x = (size - total) / 2 + i * (w + gap)
        color = ACCENT2 if i == 0 else (60, 72, 98)
        draw.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=color)
    return img


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for s in (192, 512):
        out = os.path.join(ROOT, 'icon-%d.png' % s)
        make(s).save(out, optimize=True)
        print('wrote', out, os.path.getsize(out), 'bytes')
