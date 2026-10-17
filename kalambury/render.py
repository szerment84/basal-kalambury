"""Kreski -> obraz, który dostaje model. Jedna funkcja dla gry, benchmarku i wideo, żeby model zawsze widział to samo.

Kreski w formacie Quick, Draw!: [[xs, ys], ...]. Rysunek jest kadrowany do swojego obrysu, skalowany do kwadratu
SIZE z marginesem MARGIN i rysowany czarną linią o grubości WIDTH na białym tle (z antyaliasingiem).
"""
import io

from PIL import Image, ImageDraw

SIZE, MARGIN, WIDTH, SS = 384, 32, 6, 3  # SS: nadpróbkowanie przy rysowaniu


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
        for px, py in (pts[0], pts[-1]):  # zaokrąglone końce kresek
            d.ellipse((px - r, py - r, px + r, py + r), fill=0)
    return big.resize((size, size), Image.LANCZOS).convert("RGB")


def png(strokes, size=SIZE):
    buf = io.BytesIO()
    render(strokes, size).save(buf, "PNG")
    return buf.getvalue()
