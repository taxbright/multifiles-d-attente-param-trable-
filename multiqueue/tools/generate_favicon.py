#!/usr/bin/env python3
"""
Generate a simple colorful favicon.ico and favicon.png in the project's static folder.
Requires Pillow (PIL). If not installed, install with: pip install pillow
"""
import os
from pathlib import Path

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

out_dir = Path(__file__).resolve().parents[1] / 'queueapp' / 'static' / 'queueapp' / 'img'
out_dir.mkdir(parents=True, exist_ok=True)
ico_path = out_dir / 'favicon.ico'
png_path = out_dir / 'favicon.png'

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception as e:
    print('Pillow not installed. Install with: pip install pillow')
    raise

# Palette matching theme
c1 = hex_to_rgb('#ff6b6b')
c2 = hex_to_rgb('#845ef7')
size = (64, 64)
img = Image.new('RGBA', size)
draw = ImageDraw.Draw(img)
# vertical gradient
for y in range(size[1]):
    t = y / (size[1] - 1)
    r = int(c1[0] * (1 - t) + c2[0] * t)
    g = int(c1[1] * (1 - t) + c2[1] * t)
    b = int(c1[2] * (1 - t) + c2[2] * t)
    draw.line([(0, y), (size[0], y)], fill=(r, g, b))

# draw rounded rect background (slightly inset)
rect_margin = 6
bbox = [rect_margin, rect_margin, size[0]-rect_margin, size[1]-rect_margin]
try:
    # Pillow >= 5.0 has rounded_rectangle
    draw.rounded_rectangle(bbox, radius=12, fill=None, outline=(255,255,255,48))
except Exception:
    pass

# Draw letters 'MQ'
text = 'MQ'
# Try to select a reasonably nice font; fallback to default
font = None
possible_fonts = [
    'arial.ttf',
    'DejaVuSans-Bold.ttf',
]
for f in possible_fonts:
    try:
        font = ImageFont.truetype(f, 34)
        break
    except Exception:
        font = None

if font is None:
    font = ImageFont.load_default()
    # default font small; scale via drawing transform
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
    except Exception:
        try:
            w, h = font.getsize(text)
        except Exception:
            w, h = draw.textsize(text, font=font)
    # center
    draw.text(((size[0]-w)/2, (size[1]-h)/2), text, font=font, fill=(255,255,255))
else:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
    except Exception:
        try:
            w, h = font.getsize(text)
        except Exception:
            w, h = draw.textsize(text, font=font)
    draw.text(((size[0]-w)/2, (size[1]-h)/2-2), text, font=font, fill=(255,255,255))

# Save png and ico
img.save(png_path, format='PNG')
# Save ICO (can contain multiple sizes). Pillow will create an ICO from the image.
img.save(ico_path, format='ICO')

print('Generated:', ico_path)
print('Also saved:', png_path)
