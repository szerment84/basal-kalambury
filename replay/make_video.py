"""Video for the post: drawings replayed stroke by stroke, with basal's real answer after every stroke.

The model is asked about every partial drawing (answers are cached per word pack), then the frames are put together
into an MP4 by ffmpeg. The pace is sped up: on the video every answer appears right after its stroke.

  python replay/make_video.py --drawings data/quickdraw_dev.jsonl --keys 4683353716424704,... --out results/kalambury.mp4
  python replay/make_video.py --pack nerd --sketches among_us,atom --lang en --out results/nerd_en.mp4
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
from kalambury.words import LABELS  # noqa: E402

W, H, FPS = 1280, 720, 30
BG, CARD, LINE, INK, MUTED, ACCENT, GOOD = "#0b0d10", "#14171c", "#262b33", "#e8eaed", "#8b939e", "#8ab4ff", "#4ade80"
PAPER, PM = 560, 40          # paper size and the drawing's margin on it
PX, PY = 48, 112             # paper position
BX, BY, ROWH, BARW = 680, 250, 58, 400  # bars: x, y, row height, track length
TOP = 5
TEXT = {
    "pl": {"sub": "{model} · {pack}255 haseł naraz · 0 generowanych tokenów", "nerd": "IT i nerdy · ",
           "guesses": "basal zgaduje:", "sure": "Wiem! ", "maybe": "Chyba: ", "hmm": "Hmm… ",
           "ok": "✓ trafione, hasło: ", "miss": "✗ hasło: ",
           "quickdraw": "rysunki: Google Quick, Draw! (CC BY 4.0) · odpowiedzi modelu prawdziwe, tempo przyspieszone",
           "sketches": "szkice: przygotowane do tego demo · odpowiedzi modelu prawdziwe, tempo przyspieszone"},
    "en": {"sub": "{model} · {pack}255 words at once · 0 generated tokens", "nerd": "IT & nerds · ",
           "guesses": "basal guesses:", "sure": "I know: ", "maybe": "Maybe: ", "hmm": "Hmm… ",
           "ok": "✓ correct: ", "miss": "✗ the answer: ",
           "quickdraw": "drawings: Google Quick, Draw! (CC BY 4.0) · real model answers, sped up",
           "sketches": "sketches: made for this demo · real model answers, sped up"},
}


def font(size, bold=False):
    import matplotlib.font_manager as fm
    return ImageFont.truetype(fm.findfont(fm.FontProperties(family="DejaVu Sans", weight="bold" if bold else "normal")),
                              size)


F_TITLE, F_BIG, F_TXT, F_SMALL = font(30, True), font(46, True), font(24), font(18)


def fit(d, text, f, width, bold=False):
    """A smaller font for text that would not fit in width."""
    while d.textlength(text, font=f) > width and f.size > 12:
        f = font(f.size - 2, bold)
    return f


def answers(drawing, pack, cache):
    """The model's answer after every stroke: [(top TOP [(key, p)], choice, confidence)]."""
    out = []
    for k in range(1, len(drawing) + 1):
        key = f"{pack}:{json.dumps(drawing[:k])}"
        if key not in cache:
            ans, _ = guess(drawing[:k], pack=pack)
            cache[key] = ans["probabilities"]
        p = cache[key]
        top = sorted(p.items(), key=lambda kv: -kv[1])[:TOP]
        out.append((top, top[0][0], top[0][1]))
    return out


def ease(t):
    return t * t * (3 - 2 * t)


def pct(p, lang):
    s = f"{p * 100:.0f}%" if p >= 0.1 else f"{p * 100:.1f}%"
    return s.replace(".", ",") if lang == "pl" else s


class Scene:
    def __init__(self, model, lang, pack, source):
        self.lang, self.t = lang, TEXT[lang]
        self.base = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(self.base)
        d.text((PX, 36), "basal", font=F_TITLE, fill=INK)
        d.text((PX + 98, 36), "kalambury", font=F_TITLE, fill=ACCENT)
        sub = self.t["sub"].format(model=model, pack=self.t["nerd"] if pack == "nerd" else "")
        d.text((PX + 300, 44), sub, font=fit(d, sub, F_SMALL, W - PX - 348), fill=MUTED)
        d.rounded_rectangle((BX - 24, PY, W - 48, PY + PAPER), 16, fill=CARD, outline=LINE)
        d.text((BX, PY + 22), self.t["guesses"], font=F_TXT, fill=MUTED)
        d.text((PX, H - 40), self.t[source], font=F_SMALL, fill=MUTED)

    def label(self, key):
        return LABELS[key][self.lang]

    def frame(self, paper, word, guess_now, rows, done):
        im = self.base.copy()
        im.paste(paper, (PX, PY))
        d = ImageDraw.Draw(im)
        if guess_now:
            key, p = guess_now
            text = self.t["sure" if p >= 0.8 else "maybe" if p >= 0.4 else "hmm"] + self.label(key)
            d.text((BX, PY + 62), text, font=fit(d, text, F_BIG, W - 72 - BX, True),
                   fill=GOOD if (done and key == word) else INK)
        for key, y, w, p in rows:
            col = GOOD if key == word else ACCENT
            name = self.label(key)
            d.text((BX, y), name, font=fit(d, name, F_TXT, BARW + 60), fill=INK if key != word else GOOD)
            d.rounded_rectangle((BX, y + 32, BX + BARW, y + 44), 6, fill="#1d2128")
            if w > 0.004:
                d.rounded_rectangle((BX, y + 32, BX + max(12, BARW * w), y + 44), 6, fill=col)
            d.text((BX + BARW + 16, y + 22), pct(p, self.lang), font=F_TXT, fill=MUTED)
        if done:
            ok = guess_now and guess_now[0] == word
            text = self.t["ok" if ok else "miss"] + self.label(word)
            d.text((BX, PY + PAPER - 50), text, font=fit(d, text, F_TXT, W - 72 - BX), fill=GOOD if ok else "#f87171")
        return im


def paper_strokes(drawing):
    """Strokes scaled onto the paper (as kalambury/render.py does, at video size, 2x supersampled)."""
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
    ypos, width, prob = {}, {}, {}   # current position / width of every word's bar
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
        for i in range(1, len(pts) + per_frame, per_frame):  # a stroke is drawn over ~12 frames
            seg = pts[max(0, i - per_frame - 1):i + 1]
            if len(seg) > 1:
                pen.line(seg, fill=0, width=12, joint="curve")
            for px, py in (seg[0], seg[-1]):
                pen.ellipse((px - 6, py - 6, px + 6, py + 6), fill=0)
            draw_frame(target, 1.0)
        top, choice, conf = steps[k]
        new = {key: (BY + j * ROWH, p, p) for j, (key, p) in enumerate(top)}
        for key in target:
            if key not in new:   # a word drops out of the top 5: it slides down and disappears
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
    ap.add_argument("--keys", default=None, help="comma-separated key_ids of drawings (default: 6 random ones)")
    ap.add_argument("--sketches", default=None, help="comma-separated names from replay/nerd_sketches.py instead")
    ap.add_argument("--pack", default="quickdraw", choices=["quickdraw", "nerd"])
    ap.add_argument("--lang", default="pl", choices=["pl", "en"])
    ap.add_argument("--cache", default=str(ROOT / "results/replay_cache.json"))
    ap.add_argument("--out", default=str(ROOT / "results/kalambury.mp4"))
    a = ap.parse_args()
    if a.sketches:
        from replay.nerd_sketches import sketch
        items = [(name, sketch(name)) for name in a.sketches.split(",")]
    else:
        rows = {r["key_id"]: r for r in map(json.loads, open(a.drawings))}
        keys = a.keys.split(",") if a.keys else random.Random(1).sample(sorted(rows), 6)
        items = [(rows[k]["word"], rows[k]["drawing"]) for k in keys]
    cache_path = Path(a.cache)
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    plan = []
    for word, drawing in items:
        steps = answers(drawing, a.pack, cache)
        cache_path.write_text(json.dumps(cache))
        plan.append((word, drawing, steps))
        print(f"{word}: " + " → ".join(f"{LABELS[c][a.lang]} {p:.2f}" for _, c, p in steps), flush=True)
    scene = Scene(model_name(), a.lang, a.pack, "sketches" if a.sketches else "quickdraw")
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
