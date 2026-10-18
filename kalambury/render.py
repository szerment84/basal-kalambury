"""Strokes -> the image the model gets. One function for the game, the benchmark and the videos, so the model always
sees the same thing.

Strokes in the Quick, Draw! format: [[xs, ys], ...]. The drawing is cropped to its bounding box, scaled into a SIZE
square with a MARGIN and drawn as a black WIDTH-pixel line on white (antialiased).
"""
import io

from PIL import Image, ImageDraw

SIZE, MARGIN, WIDTH, SS = 384, 32, 6, 3  # SS: supersampling while drawing


def render(strokes, size=SIZE):
    xs = [x for s in strokes for x in s[0]]
    ys = [y for s in strokes for y in s[1]]
    x0, y0 = min(xs), min(ys)
    w, h = max(xs) - x0, max(ys) - y0
    scale = (size - 2 * MARGIN) / max(w, h, 1)
    ox, oy = (size - w * scale) / 2, (size - h * scale) / 2
    big = Image.new("L", (size * SS, size * SS), 255)
    d, r = ImageDraw.Draw(big), WIDTH * SS / 2
    for s in strokes:
        pts = [((ox + (x - x0) * scale) * SS, (oy + (y - y0) * scale) * SS) for x, y in zip(s[0], s[1])]
        if len(pts) > 1:
            d.line(pts, fill=0, width=WIDTH * SS, joint="curve")
        for px, py in (pts[0], pts[-1]):  # round stroke ends
            d.ellipse((px - r, py - r, px + r, py + r), fill=0)
    return big.resize((size, size), Image.LANCZOS).convert("RGB")


def png(strokes, size=SIZE):
    buf = io.BytesIO()
    render(strokes, size).save(buf, "PNG")
    return buf.getvalue()
