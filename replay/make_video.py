"""Wideo do posta: rysunki z Quick, Draw! odtwarzane kreska po kresce, po każdej kresce prawdziwa odpowiedź basala.

Model jest pytany o każdy częściowy rysunek (odpowiedzi zapisują się w cache), potem klatki są składane w MP4 przez
ffmpeg. Tempo jest przyspieszone: na wideo każda odpowiedź pojawia się zaraz po kresce.

  python replay/make_video.py --keys 5201136883597312,4647694628814848 --out results/kalambury.mp4
"""
import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kalambury.basal_client import guess, model_name  # noqa: E402
from kalambury.words import PL  # noqa: E402

W, H, FPS = 1280, 720, 30
BG, CARD, LINE, INK, MUTED, ACCENT, GOOD = "#0b0d10", "#14171c", "#262b33", "#e8eaed", "#8b939e", "#8ab4ff", "#4ade80"
PAPER, PM = 560, 40          # bok kartki i margines rysunku na kartce
PX, PY = 48, 112             # położenie kartki
BX, BY, ROWH, BARW = 680, 250, 58, 400  # słupki: x, y, wysokość wiersza, długość toru
TOP = 5


def font(size, bold=False):
    import matplotlib.font_manager as fm
    return ImageFont.truetype(fm.findfont(fm.FontProperties(family="DejaVu Sans", weight="bold" if bold else "normal")),
                              size)


F_TITLE, F_BIG, F_TXT, F_SMALL = font(30, True), font(46, True), font(24), font(18)


def answers(drawing, cache):
    """Odpowiedź modelu po każdej kresce: [(top TOP [(klucz, p)], wybór, pewność)]."""
    out = []
    for k in range(1, len(drawing) + 1):
        key = json.dumps(drawing[:k])
        if key not in cache:
            ans, _ = guess(drawing[:k])
            cache[key] = ans["probabilities"]
        p = cache[key]
        top = sorted(p.items(), key=lambda kv: -kv[1])[:TOP]
        out.append((top, top[0][0], top[0][1]))
    return out


def ease(t):
    return t * t * (3 - 2 * t)


def pct(p):
    return f"{p * 100:.0f}%" if p >= 0.1 else f"{p * 100:.1f}%".replace(".", ",")


class Scene:
    def __init__(self, model):
        self.base = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(self.base)
        d.text((PX, 36), "basal", font=F_TITLE, fill=INK)
        d.text((PX + 98, 36), "kalambury", font=F_TITLE, fill=ACCENT)
        d.text((PX + 300, 44), f"{model} · 255 haseł w jednym pytaniu · 0 generowanych tokenów", font=F_SMALL, fill=MUTED)
        d.rounded_rectangle((BX - 24, PY, W - 48, PY + PAPER), 16, fill=CARD, outline=LINE)
        d.text((BX, PY + 22), "basal zgaduje:", font=F_TXT, fill=MUTED)
        d.text((PX, H - 40), "rysunki: Google Quick, Draw! (CC BY 4.0) · odpowiedzi modelu prawdziwe, tempo przyspieszone",
               font=F_SMALL, fill=MUTED)

    def frame(self, paper, word, guess_now, rows, done):
        im = self.base.copy()
        im.paste(paper, (PX, PY))
        d = ImageDraw.Draw(im)
        if guess_now:
            key, p = guess_now
            label = ("Wiem! " if p >= 0.8 else "Chyba: " if p >= 0.4 else "Hmm… ") + PL[key]
            d.text((BX, PY + 62), label, font=F_BIG, fill=GOOD if (done and key == word) else INK)
        for key, y, w, p in rows:
            col = GOOD if key == word else ACCENT
            d.text((BX, y), PL[key], font=F_TXT, fill=INK if key != word else GOOD)
            d.rounded_rectangle((BX, y + 32, BX + BARW, y + 44), 6, fill="#1d2128")
            if w > 0.004:
                d.rounded_rectangle((BX, y + 32, BX + max(12, BARW * w), y + 44), 6, fill=col)
            d.text((BX + BARW + 16, y + 22), pct(p), font=F_TXT, fill=MUTED)
        if done:
            ok = guess_now and guess_now[0] == word
            d.text((BX, PY + PAPER - 50), ("✓ trafione, hasło: " if ok else "✗ hasło: ") + PL[word], font=F_TXT,
                   fill=GOOD if ok else "#f87171")
        return im


def paper_strokes(drawing):
    """Kreski przeskalowane na kartkę (jak kalambury/render.py, ale w rozmiarze wideo, z nadpróbkowaniem x2)."""
    xs = [x for s in drawing for x in s[0]]
    ys = [y for s in drawing for y in s[1]]
    x0, y0, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    sc = (PAPER - 2 * PM) / max(w, h, 1)
    ox, oy = (PAPER - w * sc) / 2, (PAPER - h * sc) / 2
    return [[((ox + (x - x0) * sc) * 2, (oy + (y - y0) * sc) * 2) for x, y in zip(s[0], s[1])] for s in drawing]


def play(scene, word, drawing, steps, emit):
    strokes = paper_strokes(drawing)
    big = Image.new("L", (PAPER * 2, PAPER * 2), 255)
    pen = ImageDraw.Draw(big)
    ypos, width, prob = {}, {}, {}   # aktualne położenie / szerokość słupka każdego hasła
    shown = None

    def draw_frame(target_rows, t, done=False):
        rows = []
        for key, (y0, w0, p0) in target_rows.items():
            y1, w1, p1 = ypos.get(key, y0), width.get(key, 0.0), prob.get(key, p0)
            rows.append((key, y1 + (y0 - y1) * ease(t), w1 + (w0 - w1) * ease(t), p1 + (p0 - p1) * ease(t)))
        paper = big.resize((PAPER, PAPER), Image.LANCZOS).convert("RGB")
        emit(scene.frame(paper, word, shown, rows, done))

    target = {}
    for k, pts in enumerate(strokes):
        per_frame = max(1, len(pts) // 12)
        for i in range(1, len(pts) + per_frame, per_frame):  # kreska rysuje się przez ~12 klatek
            seg = pts[max(0, i - per_frame - 1):i + 1]
            if len(seg) > 1:
                pen.line(seg, fill=0, width=12, joint="curve")
            for px, py in (seg[0], seg[-1]):
                pen.ellipse((px - 6, py - 6, px + 6, py + 6), fill=0)
            draw_frame(target, 1.0)
        top, choice, conf = steps[k]
        new = {key: (BY + j * ROWH, p, p) for j, (key, p) in enumerate(top)}
        for key in target:
            if key not in new:   # hasło wypada z top-5: zjeżdża w dół i znika
                new[key] = (BY + TOP * ROWH + 40, 0.0, 0.0)
        shown = (choice, conf)
        for f in range(12):
            draw_frame(new, (f + 1) / 12)
        for key, (y, w, p) in new.items():
            ypos[key], width[key], prob[key] = y, w, p
        target = {key: new[key] for key, _ in top}
        for _ in range(6):
            draw_frame(target, 1.0)
    for _ in range(int(FPS * 2.2)):
        draw_frame(target, 1.0, done=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drawings", default=str(ROOT / "data/quickdraw_test.jsonl"))
    ap.add_argument("--keys", default=None, help="key_id rysunków po przecinku (domyślnie 6 losowych)")
    ap.add_argument("--cache", default=str(ROOT / "results/replay_cache.json"))
    ap.add_argument("--out", default=str(ROOT / "results/kalambury.mp4"))
    a = ap.parse_args()
    rows = {r["key_id"]: r for r in map(json.loads, open(a.drawings))}
    keys = a.keys.split(",") if a.keys else random.Random(1).sample(sorted(rows), 6)
    cache_path = Path(a.cache)
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    plan = []
    for key in keys:
        r = rows[key]
        steps = answers(r["drawing"], cache)
        cache_path.write_text(json.dumps(cache))
        plan.append((r["word"], r["drawing"], steps))
        print(f"{r['word']}: " + " → ".join(f"{PL[c]} {p:.2f}" for _, c, p in steps), flush=True)
    scene = Scene(model_name())
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                           "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    for word, drawing, steps in plan:
        play(scene, word, drawing, steps, lambda im: ff.stdin.write(im.tobytes()))
    ff.stdin.close()
    ff.wait()
    print(a.out)


if __name__ == "__main__":
    main()
