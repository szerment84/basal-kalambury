"""Raport z wyników bench/run.py: trafność, kalibracja, pomyłki + wykresy do README i na X.

  python bench/report.py results/test.jsonl     # -> results/summary.json, results/RESULTS.md, results/*.png
"""
import argparse
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kalambury.render import render  # noqa: E402
from kalambury.words import PL  # noqa: E402

# ciemny motyw (paleta referencyjna skilla dataviz, tryb dark)
SURFACE, INK, INK2, MUTED, GRID, AXIS, BLUE = "#1a1a19", "#f0efec", "#c3c2b7", "#898781", "#2c2c2a", "#383835", "#3987e5"
GOOD, BAD = "#0ca30c", "#d03b3b"


def wilson(k, n, z=1.96):
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def bins(rows, edges=(0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0001)):
    out = []
    for lo, hi in zip(edges, edges[1:]):
        b = [r for r in rows if lo <= r["confidence"] < hi]
        if b:
            out.append({"lo": lo, "hi": min(hi, 1), "n": len(b), "conf": sum(r["confidence"] for r in b) / len(b),
                        "acc": sum(r["ok"] for r in b) / len(b)})
    return out


def summarize(rows):
    n, k1 = len(rows), sum(r["ok"] for r in rows)
    b = bins(rows)
    sel = {}
    for t in (0.5, 0.8, 0.9):
        s = [r for r in rows if r["confidence"] >= t]
        sel[str(t)] = {"coverage": len(s) / n, "n": len(s), "acc": sum(r["ok"] for r in s) / len(s) if s else None}
    per = defaultdict(list)
    for r in rows:
        per[r["word"]].append(r["ok"])
    conf = Counter((r["word"], r["choice"]) for r in rows if not r["ok"])
    lat = sorted(r["wall_ms"] for r in rows)
    return {
        "model": rows[0]["model"], "n": n, "options": 255, "chance": 1 / 255,
        "top1": k1 / n, "top1_ci95": wilson(k1, n),
        "top5": sum(r["rank_true"] <= 5 for r in rows) / n,
        "ece": sum(x["n"] * abs(x["acc"] - x["conf"]) for x in b) / n,
        "mean_confidence": sum(r["confidence"] for r in rows) / n,
        "selective": sel, "bins": b,
        "median_latency_s": lat[len(lat) // 2] / 1000,
        "median_input_tokens": sorted(r["input_tokens"] for r in rows)[n // 2],
        "output_tokens_total": sum(r["output_tokens"] for r in rows),
        "best_words": sorted(((w, sum(v) / len(v)) for w, v in per.items()), key=lambda x: -x[1])[:15],
        "worst_words": sorted(((w, sum(v) / len(v)) for w, v in per.items()), key=lambda x: x[1])[:15],
        "confusions": [[a, b, c] for (a, b), c in conf.most_common(15)],
    }


def plural(n, one, few, many):
    return one if n == 1 else few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many


def pct(x, d=0):
    return f"{x * 100:.{d}f}".replace(".", ",") + "%"


def scorecard(s, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": INK2,
                         "xtick.color": MUTED, "ytick.color": MUTED})
    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=SURFACE)
    fig.text(0.05, 0.9, "basal kalambury · Quick, Draw! · 255 haseł w jednym pytaniu", fontsize=20, color=INK2)
    fig.text(0.05, 0.62, pct(s["top1"]), fontsize=110, weight="bold", color=INK)
    lo, hi = s["top1_ci95"]
    fig.text(0.05, 0.555, f"trafień za pierwszym razem (95% CI {pct(lo)}–{pct(hi)})", fontsize=17, color=INK2)
    tiles = [(pct(s["top5"]), "hasło w top-5"), (pct(s["chance"], 1), "losowe zgadywanie"),
             (f"{s['output_tokens_total']}", "wygenerowanych tokenów"), (f"{s['n']}", plural(s["n"], "rysunek testowy", "rysunki testowe", "rysunków testowych"))]
    for i, (v, lab) in enumerate(tiles):
        x, y = 0.05 + (i % 2) * 0.2, 0.36 - (i // 2) * 0.16
        fig.text(x, y, v, fontsize=40, weight="bold", color=INK)
        fig.text(x, y - 0.045, lab, fontsize=15, color=MUTED)
    fig.text(0.05, 0.06, f"{s['model']} · basal 2.1 · każdy rysunek = 1 przebieg modelu, {s['median_input_tokens']} "
             f"{plural(s['median_input_tokens'], 'token', 'tokeny', 'tokenów')} "
             f"wejścia, 0 wyjścia", fontsize=13, color=MUTED)

    ax = fig.add_axes([0.53, 0.17, 0.42, 0.66], facecolor=SURFACE)
    ax.plot([0, 1], [0, 1], color=AXIS, lw=1, zorder=1)
    ax.text(0.97, 0.9, "idealna kalibracja", color=MUTED, fontsize=12, ha="right", rotation=36,
            transform=ax.transAxes)
    bx, by = [b["conf"] for b in s["bins"]], [b["acc"] for b in s["bins"]]
    ax.plot(bx, by, color=BLUE, lw=2, solid_capstyle="round", zorder=2)
    ax.scatter(bx, by, s=[30 + 0.35 * b["n"] for b in s["bins"]], color=BLUE, edgecolors=SURFACE, linewidths=2,
               zorder=3)
    top = s["bins"][-1]
    ax.annotate(f"pewność {pct(top['lo'])}+: trafia w {pct(top['acc'])}\n({top['n']} {plural(top['n'], 'rysunek', 'rysunki', 'rysunków')})",
                (top["conf"], top["acc"]), xytext=(-20, -70), textcoords="offset points", ha="right", fontsize=13,
                color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_yticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
    ax.grid(color=GRID, lw=1)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(length=0, labelsize=12)
    ax.set_xlabel("deklarowana pewność modelu", fontsize=14, labelpad=10)
    ax.set_ylabel("faktyczna trafność", fontsize=14, labelpad=10)
    fig.text(0.53, 0.86, f"Czy wie, kiedy nie wie? Błąd kalibracji (ECE) {s['ece']:.3f}".replace(".", ","),
             fontsize=17, color=INK)
    fig.text(0.53, 0.83, "punkty: rysunki pogrupowane wg pewności (co 10 pp.), wielkość = liczba rysunków",
             fontsize=12, color=MUTED)
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def gallery(rows, drawings, path, n=12, seed=7):
    """n losowych (nie wybranych ręcznie) rysunków testowych z odpowiedzią modelu."""
    from PIL import Image, ImageDraw, ImageFont
    import matplotlib.font_manager as fm
    font = ImageFont.truetype(fm.findfont("DejaVu Sans"), 22)
    small = ImageFont.truetype(fm.findfont("DejaVu Sans"), 18)
    pick = random.Random(seed).sample(rows, n)
    cols, cell, pad, cap = 4, 300, 20, 74
    im = Image.new("RGB", (cols * (cell + pad) + pad, (n // cols) * (cell + cap + pad) + pad + 60), SURFACE)
    d = ImageDraw.Draw(im)
    d.text((pad, 18), f"{n} losowych rysunków ze zbioru testowego i odpowiedź modelu (spośród 255 haseł)", font=font,
           fill=INK2)
    for i, r in enumerate(pick):
        x, y = pad + (i % cols) * (cell + pad), 60 + pad + (i // cols) * (cell + cap + pad)
        im.paste(render(drawings[r["key_id"]], cell), (x, y))
        ok = r["ok"]
        d.rectangle((x, y + cell, x + cell, y + cell + cap), fill="#232321")
        d.text((x + 12, y + cell + 10), ("✓ " if ok else "✗ ") + f"{PL[r['choice']]} {pct(r['confidence'])}",
               font=font, fill=GOOD if ok else BAD)
        d.text((x + 12, y + cell + 42), "trafione" if ok else f"prawda: {PL[r['word']]}", font=small, fill=MUTED)
    im.save(path)


def markdown(s):
    sel = s["selective"]
    lines = [
        f"# Wyniki: {s['model']} na Quick, Draw!", "",
        f"- rysunków testowych: **{s['n']}** (255 haseł × {s['n'] // 255}), każdy oceniany spośród **255 haseł naraz**",
        f"- trafność top-1: **{pct(s['top1'], 1)}** (95% CI {pct(s['top1_ci95'][0], 1)}–{pct(s['top1_ci95'][1], 1)}); "
        f"losowe zgadywanie: {pct(s['chance'], 1)}",
        f"- hasło w top-5: **{pct(s['top5'], 1)}**",
        f"- błąd kalibracji ECE: **{s['ece']:.3f}**; średnia deklarowana pewność {pct(s['mean_confidence'], 1)}",
        f"- wygenerowane tokeny: **{s['output_tokens_total']}**; mediana wejścia {s['median_input_tokens']} tokenów, "
        f"mediana czasu {s['median_latency_s']:.1f} s",
        "", "| pewność modelu | odsetek rysunków | trafność w tej grupie |", "|---|---|---|",
    ]
    for t, v in sel.items():
        lines.append(f"| ≥ {pct(float(t))} | {pct(v['coverage'], 1)} ({v['n']}) | "
                     f"{pct(v['acc'], 1) if v['acc'] is not None else '–'} |")
    lines += ["", "| przedział pewności | rysunków | śr. pewność | trafność |", "|---|---|---|---|"]
    for b in s["bins"]:
        lines.append(f"| {pct(b['lo'])}–{pct(b['hi'])} | {b['n']} | {pct(b['conf'], 1)} | {pct(b['acc'], 1)} |")
    lines += ["", "Najczęstsze pomyłki (prawda → odpowiedź modelu): " +
              ", ".join(f"{PL[a]} → {PL[b]} ({c})" for a, b, c in s["confusions"][:10]), ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("--drawings", default=str(ROOT / "data/quickdraw_test.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "results"))
    a = ap.parse_args()
    rows = [json.loads(line) for line in open(a.results)]
    for r in rows:
        r["ok"] = r["choice"] == r["word"]
    s = summarize(rows)
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    (out / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1))
    (out / "RESULTS.md").write_text(markdown(s))
    scorecard(s, out / "scorecard.png")
    drawings = {d["key_id"]: d["drawing"] for d in map(json.loads, open(a.drawings))}
    gallery(rows, drawings, out / "gallery.png")
    print(markdown(s))


if __name__ == "__main__":
    main()
