"""Hand-made vector sketches for the "nerd" word pack (Pac-Man, Starship, Cybertruck, ...). Not from Quick, Draw!.

Every sketch is a list of strokes in the Quick, Draw! format ([[xs], [ys]] in 0..255), drawn in a natural order with
a little seeded jitter, so it looks drawn by hand rather than by a ruler. Running this file asks basal about every
finished sketch (255 options of the "nerd" pack) and writes results/nerd.jsonl and a gallery in Polish and English:

  python replay/nerd_sketches.py
"""
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _seg(a, b):
    n = max(2, int(math.dist(a, b) / 12) + 1)
    return [(a[0] + (b[0] - a[0]) * i / (n - 1), a[1] + (b[1] - a[1]) * i / (n - 1)) for i in range(n)]


def poly(*pts):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        out += _seg(a, b)[1:]
    return out


def arc(cx, cy, rx, ry, a0, a1, rot=0):
    """Ellipse arc from angle a0 to a1 in degrees (0 = right, 90 = up), the ellipse rotated by rot degrees."""
    n, r = max(4, int(abs(a1 - a0) / 10) + 1), math.radians(rot)
    out = []
    for i in range(n):
        t = math.radians(a0 + (a1 - a0) * i / (n - 1))
        x, y = rx * math.cos(t), -ry * math.sin(t)
        out.append((cx + x * math.cos(r) - y * math.sin(r), cy + x * math.sin(r) + y * math.cos(r)))
    return out


def circle(cx, cy, r):
    return arc(cx, cy, r, r, 90, 450)


def lerp(a, b, f):
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


def grid(p, q, r, s):
    """The two inner lines each way of a 3x3 grid on the quadrilateral p-q-r-s (corners in order)."""
    return [poly(lerp(p, q, f), lerp(s, r, f)) for f in (1 / 3, 2 / 3)] + \
           [poly(lerp(p, s, f), lerp(q, r, f)) for f in (1 / 3, 2 / 3)]


def _pacman():
    mouth = arc(100, 128, 88, 88, 35, 325)
    return [mouth + poly(mouth[-1], (100, 128), mouth[0])[1:], circle(106, 78, 7), circle(205, 128, 6),
            circle(240, 128, 6)]


def _starship():
    body = poly((110, 205), (110, 75)) + arc(128, 75, 18, 55, 180, 0)[1:] + poly((146, 75), (146, 205), (110, 205))[1:]
    return [body, poly((110, 165), (84, 215), (110, 205)), poly((146, 165), (172, 215), (146, 205)),
            circle(128, 105, 9), poly((116, 210), (121, 240), (128, 220), (135, 248), (140, 210))]


def _cybertruck():
    return [poly((18, 140), (110, 82), (240, 118), (240, 160), (18, 165), (18, 140)),
            poly((60, 126), (110, 98), (172, 113), (60, 126)), circle(68, 165, 20), circle(196, 165, 20)]


def _floppy():
    return [poly((30, 30), (205, 30), (226, 51), (226, 226), (30, 226), (30, 30)),
            poly((78, 30), (78, 96), (172, 96), (172, 30)), poly((142, 44), (158, 44), (158, 82), (142, 82), (142, 44)),
            poly((56, 226), (56, 138), (200, 138), (200, 226)), poly((72, 165), (184, 165)), poly((72, 192), (184, 192))]


def _wifi():
    return [arc(128, 205, r, r, 45, 135) for r in (45, 90, 135)] + [circle(128, 205, 9)]


def _lightsaber():
    blade = poly((121, 182), (121, 22)) + arc(128, 22, 7, 7, 180, 0)[1:] + poly((135, 22), (135, 182))[1:]
    return [blade, poly((112, 182), (144, 182), (144, 248), (112, 248), (112, 182)), poly((112, 202), (144, 202)),
            poly((112, 222), (144, 222))]


def _tetris():
    return [poly((40, 80), (190, 80), (190, 130), (140, 130), (140, 180), (90, 180), (90, 130), (40, 130), (40, 80)),
            poly((90, 80), (90, 130)), poly((140, 80), (140, 130)), poly((90, 130), (140, 130))]


def _space_invader():
    return [poly((62, 112), (84, 88), (172, 88), (194, 112), (194, 152), (62, 152), (62, 112)),
            poly((96, 88), (78, 58)), poly((160, 88), (178, 58)),
            poly((98, 108), (114, 108), (114, 124), (98, 124), (98, 108)),
            poly((142, 108), (158, 108), (158, 124), (142, 124), (142, 108)),
            poly((62, 128), (36, 150), (36, 180)), poly((194, 128), (220, 150), (220, 180)),
            poly((92, 152), (78, 184)), poly((164, 152), (178, 184)),
            poly((112, 152), (112, 172), (126, 172)), poly((144, 152), (144, 172), (130, 172))]


def _among_us():
    body = poly((80, 232), (80, 95)) + arc(128, 95, 48, 52, 180, 0)[1:] + \
        poly((176, 95), (176, 232), (146, 232), (146, 198), (110, 198), (110, 232), (80, 232))[1:]
    return [body, arc(150, 104, 40, 20, 0, 360), poly((80, 122), (54, 122), (54, 196), (80, 196))]


def _pokeball():
    return [circle(128, 128, 100), poly((28, 128), (96, 128)), poly((160, 128), (228, 128)), circle(128, 128, 32),
            circle(128, 128, 12)]


def _x_logo():
    return [poly((40, 30), (84, 30), (216, 226), (172, 226), (40, 30)), poly((214, 30), (142, 112)),
            poly((116, 142), (42, 226))]


def _rubber_duck():
    return [arc(135, 172, 95, 50, 0, 360), circle(92, 96, 40), poly((54, 92), (26, 104), (56, 114)),
            circle(88, 86, 5), arc(150, 168, 38, 20, 190, 350)]


def _atom():
    return [arc(128, 128, 105, 38, 0, 360, rot) for rot in (0, 60, 120)] + [circle(128, 128, 11)]


def _death_star():
    return [circle(128, 128, 105), poly((24, 132), (232, 132)), circle(86, 88, 28), circle(86, 88, 7)]


def _tardis():
    s = [poly((72, 46), (184, 46), (184, 240), (72, 240), (72, 46)), poly((64, 46), (64, 32), (192, 32), (192, 46)),
         poly((120, 32), (120, 14), (136, 14), (136, 32)), poly((76, 52), (180, 52), (180, 66), (76, 66), (76, 52)),
         poly((128, 66), (128, 240))]
    for x0, x1 in ((86, 118), (138, 170)):
        s += [poly((x0, 80), (x1, 80), (x1, 108), (x0, 108), (x0, 80)), poly(((x0 + x1) / 2, 80), ((x0 + x1) / 2, 108)),
              poly((x0, 94), (x1, 94))]
        s += [poly((x0, y0), (x1, y0), (x1, y0 + 36), (x0, y0 + 36), (x0, y0)) for y0 in (124, 176)]
    return s


def _mario_mushroom():
    stem = poly((84, 132), (84, 206)) + arc(128, 206, 44, 30, 180, 360)[1:] + poly((172, 206), (172, 132))[1:]
    return [arc(128, 132, 106, 100, 0, 180) + poly((22, 132), (234, 132))[1:], circle(128, 72, 24),
            circle(62, 108, 17), circle(194, 108, 17), stem, poly((112, 150), (112, 176)), poly((144, 150), (144, 176))]


def _gameboy():
    body = poly((62, 16), (194, 16), (194, 214)) + arc(164, 214, 30, 26, 0, -90)[1:] + \
        poly((164, 240), (62, 240), (62, 16))[1:]
    dpad = poly((92, 150), (104, 150), (104, 138), (116, 138), (116, 150), (128, 150), (128, 162), (116, 162),
                (116, 174), (104, 174), (104, 162), (92, 162), (92, 150))
    return [body, poly((80, 36), (176, 36), (176, 118), (80, 118), (80, 36)), dpad, circle(168, 150, 9),
            circle(148, 166, 9), poly((150, 222), (166, 206)), poly((160, 228), (176, 212)), poly((170, 234), (186, 218))]


def _rubik():
    t, r, b, l = (128, 30), (222, 80), (128, 130), (34, 80)
    bb, lb, rb = (128, 236), (34, 186), (222, 186)
    return [poly(t, r, b, l, t), poly(l, lb, bb, b), poly(r, rb, bb)] + grid(t, r, b, l) + grid(l, b, bb, lb) + \
        grid(b, r, rb, bb)


def _bitcoin():
    top = poly((102, 66), (146, 66)) + arc(146, 94, 28, 28, 90, -90)[1:] + poly((146, 122), (102, 122))[1:]
    bottom = poly((102, 122), (152, 122)) + arc(152, 156, 34, 34, 90, -90)[1:] + poly((152, 190), (102, 190))[1:]
    return [circle(128, 128, 104), poly((102, 66), (102, 190)), top, bottom, poly((116, 50), (116, 66)),
            poly((136, 50), (136, 66)), poly((116, 190), (116, 206)), poly((136, 190), (136, 206))]


def _triforce():
    return [poly((128, 24), (230, 214), (26, 214), (128, 24)), poly((77, 119), (179, 119), (128, 214), (77, 119))]


def _terminal():
    return [poly((20, 40), (236, 40), (236, 216), (20, 216), (20, 40)), poly((20, 70), (236, 70)), circle(38, 55, 5),
            circle(56, 55, 5), circle(74, 55, 5), poly((48, 108), (80, 134), (48, 160)), poly((96, 162), (144, 162))]


def _cursor():
    return [poly((84, 26), (84, 206), (122, 168), (148, 228), (174, 216), (148, 156), (200, 156), (84, 26))]


def _error404():
    return [poly((70, 52), (24, 150), (94, 150)), poly((76, 100), (76, 206)), arc(128, 128, 30, 74, 90, 450),
            poly((222, 52), (176, 150), (246, 150)), poly((228, 100), (228, 206))]


def _gpu():
    s = [poly((14, 70), (242, 70), (242, 176), (14, 176), (14, 70))]
    for cx in (76, 180):
        s += [circle(cx, 123, 38), poly((cx, 123), (cx, 95)), poly((cx, 123), (cx + 24, 137)), poly((cx, 123), (cx - 24, 137))]
    return s + [poly((40, 176), (40, 196), (150, 196), (150, 176)), poly((160, 176), (160, 196), (220, 196), (220, 176))]


def _chip():
    s = [poly((62, 62), (194, 62), (194, 194), (62, 194), (62, 62)), poly((96, 96), (160, 96), (160, 160), (96, 160), (96, 96))]
    for p in (84, 112, 140, 168):
        s += [poly((p, 62), (p, 34)), poly((p, 194), (p, 222)), poly((62, p), (34, p)), poly((194, p), (222, p))]
    return s


def _r2d2():
    return [arc(128, 92, 58, 52, 0, 180) + poly((70, 92), (186, 92))[1:], poly((70, 92), (70, 206), (186, 206), (186, 92)),
            circle(128, 62, 10), poly((104, 112), (152, 112), (152, 150), (104, 150), (104, 112)),
            poly((70, 110), (46, 118), (40, 226), (70, 226), (70, 206)),
            poly((186, 110), (210, 118), (216, 226), (186, 226), (186, 206)), poly((112, 206), (108, 226), (148, 226), (144, 206))]


def _drone():
    s = [poly((104, 104), (152, 104), (152, 152), (104, 152), (104, 104))]
    s += [poly(a, b) for a, b in (((104, 104), (62, 62)), ((152, 104), (194, 62)), ((104, 152), (62, 194)),
                                  ((152, 152), (194, 194)))]
    return s + [arc(x, y, 40, 12, 0, 360) for x, y in ((62, 62), (194, 62), (62, 194), (194, 194))]


def _dna():
    ys = range(18, 239, 6)
    strand = [[(128 + 62 * math.sin((y - 18) / 220 * 3 * math.pi + ph), y) for y in ys] for ph in (0, math.pi)]
    rungs = [poly(strand[0][i], strand[1][i]) for i in range(2, len(strand[0]), 4)
             if abs(strand[0][i][0] - strand[1][i][0]) > 40]
    return strand + rungs


def _starlink():
    s = [poly((108, 104), (148, 104), (148, 152), (108, 152), (108, 104))]
    for x0, x1 in ((20, 100), (156, 236)):
        s += [poly((x0, 112), (x1, 112), (x1, 144), (x0, 144), (x0, 112))]
        s += [poly((x, 112), (x, 144)) for x in range(x0 + 20, x1, 20)]
    return s + [poly((100, 128), (108, 128)), poly((148, 128), (156, 128)), arc(128, 104, 18, 12, 0, 180),
                poly((128, 92), (128, 76))]


def _neural_net():
    layers = [(40, (70, 128, 186)), (128, (44, 100, 156, 212)), (216, (100, 156))]
    nodes = [[(x, y) for y in ys] for x, ys in layers]
    s = [circle(x, y, 12) for layer in nodes for x, y in layer]
    for a_layer, b_layer in zip(nodes, nodes[1:]):
        for a in a_layer:
            for b in b_layer:
                d = math.dist(a, b)
                s.append(poly(lerp(a, b, 12 / d), lerp(b, a, 12 / d)))
    return s


SKETCHES = {
    "pacman": _pacman, "starship": _starship, "cybertruck": _cybertruck, "floppy": _floppy, "wifi": _wifi,
    "lightsaber": _lightsaber, "tetris": _tetris, "space_invader": _space_invader, "among_us": _among_us,
    "pokeball": _pokeball, "x_logo": _x_logo, "rubber_duck": _rubber_duck, "atom": _atom, "death_star": _death_star,
    "tardis": _tardis, "mario_mushroom": _mario_mushroom, "gameboy": _gameboy, "rubik": _rubik, "bitcoin": _bitcoin,
    "triforce": _triforce, "terminal": _terminal, "cursor": _cursor, "error404": _error404, "gpu": _gpu, "chip": _chip,
    "r2d2": _r2d2, "drone": _drone, "dna": _dna, "starlink": _starlink, "neural_net": _neural_net,
}


def sketch(name):
    """The sketch as Quick, Draw! strokes, with a seeded hand-drawn jitter of about one pixel."""
    rng = random.Random(name)
    return [[[min(255, max(0, round(x + rng.uniform(-1.2, 1.2)))) for x, _ in s],
             [min(255, max(0, round(y + rng.uniform(-1.2, 1.2)))) for _, y in s]] for s in SKETCHES[name]()]


def main():
    from bench.report import gallery
    from kalambury.basal_client import guess, model_name
    model, rows = model_name(), []
    out = ROOT / "results/nerd.jsonl"
    with out.open("w") as f:
        for name in SKETCHES:
            ans, usage = guess(sketch(name), pack="nerd")
            p = ans["probabilities"]
            rows.append({"key_id": name, "word": name, "choice": ans["choice"], "confidence": ans["confidence"],
                         "p_true": p[name], "rank_true": 1 + sum(v > p[name] for v in p.values()),
                         "top3": sorted(p.items(), key=lambda kv: -kv[1])[:3], "strokes": len(SKETCHES[name]()),
                         "input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"], "model": model})
            f.write(json.dumps(rows[-1], ensure_ascii=False) + "\n")
            print(f"{name:>15} -> {ans['choice']:<15} {ans['confidence']:.2f}  rank {rows[-1]['rank_true']}", flush=True)
    for r in rows:
        r["ok"] = r["choice"] == r["word"]
    hits = sum(r["ok"] for r in rows)
    print(f"top-1 {hits}/{len(rows)}, top-3 {sum(r['rank_true'] <= 3 for r in rows)}/{len(rows)}")
    drawings = {name: sketch(name) for name in SKETCHES}
    for lang, suffix in (("pl", ""), ("en", "_en")):
        gallery(rows, drawings, ROOT / f"results/nerd_gallery{suffix}.png", lang=lang, kind="nerd")


if __name__ == "__main__":
    main()
