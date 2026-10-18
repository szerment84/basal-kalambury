"""Report on bench/run.py results: accuracy, calibration, mistakes + charts for the README and X, in Polish and English.

  python bench/report.py results/test.jsonl   # -> results/summary.json, RESULTS.md, RESULTS_en.md, *.png, *_en.png
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
from kalambury.words import LABELS  # noqa: E402

# dark theme (the dataviz skill's reference palette, dark mode)
SURFACE, INK, INK2, MUTED, GRID, AXIS, BLUE = "#1a1a19", "#f0efec", "#c3c2b7", "#898781", "#2c2c2a", "#383835", "#3987e5"
GOOD, BAD = "#0ca30c", "#d03b3b"
SUFFIX = {"pl": "", "en": "_en"}
TEXT = {
    "pl": {
        "title": "{model} · Quick, Draw! · 255 haseł w jednym pytaniu",
        "hero": "trafień za pierwszym razem (95% CI {lo}–{hi})",
        "top5": "hasło w top-5", "chance": "losowe zgadywanie", "tokens": "wygenerowanych tokenów",
        "drawings": ("rysunek testowy", "rysunki testowe", "rysunków testowych"),
        "footer": "basal 2.1 · {tag} · każdy rysunek = 1 przebieg modelu, {n} {tok} wejścia, 0 wyjścia",
        "tok": ("token", "tokeny", "tokenów"),
        "diag": "idealna kalibracja",
        "note": "pewność {lo}+: trafia w {acc}\n({n} {dr})", "dr": ("rysunek", "rysunki", "rysunków"),
        "x": "deklarowana pewność modelu", "y": "faktyczna trafność",
        "head": "Deklarowana pewność a faktyczna trafność",
        "sub1": "ECE {ece} · nad przekątną model trafia częściej, niż deklaruje, pod nią rzadziej",
        "sub2": "grupy co 10 pp. pewności (≥10 rysunków), wielkość punktu = liczba rysunków",
        "gal_quickdraw": "{n} losowych rysunków ze zbioru testowego i odpowiedź modelu (spośród 255 haseł)",
        "gal_nerd": "{n} nerdowych szkiców i odpowiedź modelu (spośród 255 haseł paczki „IT i nerdy”)",
        "ok": "trafione", "truth": "prawda: {w}",
    },
    "en": {
        "title": "{model} · Quick, Draw! · 255 words in one question",
        "hero": "right on the first guess (95% CI {lo}–{hi})",
        "top5": "word in the top 5", "chance": "random guessing", "tokens": "generated tokens",
        "drawings": ("test drawing", "test drawings", "test drawings"),
        "footer": "basal 2.1 · {tag} · one forward pass per drawing, {n} {tok} in, 0 out",
        "tok": ("token", "tokens", "tokens"),
        "diag": "perfect calibration",
        "note": "confidence {lo}+: right {acc} of the time\n({n} {dr})", "dr": ("drawing", "drawings", "drawings"),
        "x": "model's stated confidence", "y": "actual accuracy",
        "head": "Stated confidence vs actual accuracy",
        "sub1": "ECE {ece} · above the diagonal: right more often than it claims; below: less often",
        "sub2": "10-point confidence bins (≥10 drawings each), dot size = number of drawings",
        "gal_quickdraw": "{n} random test drawings and the model's answer (out of 255 words)",
        "gal_nerd": "{n} nerd sketches and the model's answer (out of the 255 words of the IT & nerd pack)",
        "ok": "correct", "truth": "answer: {w}",
    },
}


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
        "model": rows[0]["model"], "tag": rows[0]["tag"], "n": n, "options": 255, "chance": 1 / 255,
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


def plural(n, forms, lang):
    """forms: (one, few, many); few (2-4, not 12-14) exists only in Polish."""
    if n == 1:
        return forms[0]
    return forms[1] if lang == "pl" and 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else forms[2]


def num(x, d, lang):
    s = f"{x:.{d}f}"
    return s.replace(".", ",") if lang == "pl" else s


def pct(x, d=0, lang="pl"):
    return num(x * 100, d, lang) + "%"


def tag(s, lang):
    return s["tag"] if lang == "pl" else s["tag"].replace(" na ", " on ")


def scorecard(s, path, lang):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = TEXT[lang]
    plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": INK2,
                         "xtick.color": MUTED, "ytick.color": MUTED})
    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=SURFACE)
    fig.text(0.05, 0.93, t["title"].format(model=s["model"]), fontsize=20, color=INK2)
    fig.text(0.05, 0.62, pct(s["top1"], lang=lang), fontsize=110, weight="bold", color=INK)
    lo, hi = s["top1_ci95"]
    fig.text(0.05, 0.555, t["hero"].format(lo=pct(lo, lang=lang), hi=pct(hi, lang=lang)), fontsize=17, color=INK2)
    tiles = [(pct(s["top5"], lang=lang), t["top5"]), (pct(s["chance"], 1, lang), t["chance"]),
             (f"{s['output_tokens_total']}", t["tokens"]), (f"{s['n']}", plural(s["n"], t["drawings"], lang))]
    for i, (v, lab) in enumerate(tiles):
        x, y = 0.05 + (i % 2) * 0.2, 0.36 - (i // 2) * 0.16
        fig.text(x, y, v, fontsize=40, weight="bold", color=INK)
        fig.text(x, y - 0.045, lab, fontsize=15, color=MUTED)
    n_in = s["median_input_tokens"]
    fig.text(0.05, 0.06, t["footer"].format(tag=tag(s, lang), n=n_in, tok=plural(n_in, t["tok"], lang)), fontsize=13,
             color=MUTED)

    ax = fig.add_axes([0.53, 0.14, 0.42, 0.62], facecolor=SURFACE)
    ax.plot([0, 1], [0, 1], color=AXIS, lw=1, zorder=1)
    ax.text(0.36, 0.3, t["diag"], color=MUTED, fontsize=12, ha="center", va="top", rotation=41,
            rotation_mode="anchor", transform=ax.transAxes)
    shown = [b for b in s["bins"] if b["n"] >= 10]  # single drawings make random jumps to 0% / 100%
    bx, by = [b["conf"] for b in shown], [b["acc"] for b in shown]
    ax.plot(bx, by, color=BLUE, lw=2, solid_capstyle="round", zorder=2)
    ax.scatter(bx, by, s=[24 + 0.5 * b["n"] for b in shown], color=BLUE, edgecolors=SURFACE, linewidths=2,
               zorder=3)
    top = shown[-1]
    note = t["note"].format(lo=pct(top["lo"], lang=lang), acc=pct(top["acc"], lang=lang), n=top["n"],
                            dr=plural(top["n"], t["dr"], lang))
    ax.annotate(note, (top["conf"], top["acc"]), xytext=(0.98, 0.06), textcoords="axes fraction", ha="right",
                va="bottom", fontsize=13, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=1, shrinkB=6))
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
    ax.set_xlabel(t["x"], fontsize=14, labelpad=10)
    ax.set_ylabel(t["y"], fontsize=14, labelpad=10)
    fig.text(0.53, 0.86, t["head"], fontsize=17, color=INK)
    fig.text(0.53, 0.825, t["sub1"].format(ece=num(s["ece"], 3, lang)), fontsize=12, color=MUTED)
    fig.text(0.53, 0.797, t["sub2"], fontsize=12, color=MUTED)
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def gallery(rows, drawings, path, lang="pl", kind="quickdraw", n=12, seed=7, cols=4, cell=300):
    """Drawings with the model's answer: for the benchmark n random (not hand-picked) ones, for the sketches all."""
    from PIL import Image, ImageDraw, ImageFont
    import matplotlib.font_manager as fm
    t, face = TEXT[lang], fm.findfont("DejaVu Sans")

    def fit(text, size, width):  # a long word gets a smaller font instead of running out of the tile
        f = ImageFont.truetype(face, size)
        while d.textlength(text, font=f) > width:
            f = ImageFont.truetype(face, f.size - 1)
        return f

    if kind == "quickdraw":
        pick = random.Random(seed).sample(rows, n)
    else:
        pick, cols, cell = rows, 6, 260
    cap, pad = 74, 20
    nrows = (len(pick) + cols - 1) // cols
    im = Image.new("RGB", (cols * (cell + pad) + pad, nrows * (cell + cap + pad) + pad + 60), SURFACE)
    d = ImageDraw.Draw(im)
    d.text((pad, 18), t[f"gal_{kind}"].format(n=len(pick)), font=ImageFont.truetype(face, 22), fill=INK2)
    for i, r in enumerate(pick):
        x, y = pad + (i % cols) * (cell + pad), 60 + pad + (i // cols) * (cell + cap + pad)
        im.paste(render(drawings[r["key_id"]], cell), (x, y))
        ok = r["ok"]
        d.rectangle((x, y + cell, x + cell, y + cell + cap), fill="#232321")
        label = ("✓ " if ok else "✗ ") + f"{LABELS[r['choice']][lang]} {pct(r['confidence'], lang=lang)}"
        d.text((x + 12, y + cell + 10), label, font=fit(label, 22, cell - 24), fill=GOOD if ok else BAD)
        second = t["ok"] if ok else t["truth"].format(w=LABELS[r["word"]][lang])
        d.text((x + 12, y + cell + 42), second, font=fit(second, 18, cell - 24), fill=MUTED)
    im.save(path)


def markdown(s, lang):
    sel, L = s["selective"], lambda k: LABELS[k][lang]
    P = lambda x, d=0: pct(x, d, lang)  # noqa: E731
    n_in = s["median_input_tokens"]
    if lang == "pl":
        lines = [
            f"# Wyniki: {s['model']} na Quick, Draw!", "",
            f"- rysunków testowych: **{s['n']}** (255 haseł × {s['n'] // 255}), każdy oceniany spośród "
            "**255 haseł naraz**",
            f"- trafność top-1: **{P(s['top1'], 1)}** (95% CI {P(s['top1_ci95'][0], 1)}–{P(s['top1_ci95'][1], 1)}); "
            f"losowe zgadywanie: {P(s['chance'], 1)}",
            f"- hasło w top-5: **{P(s['top5'], 1)}**",
            f"- błąd kalibracji ECE: **{num(s['ece'], 3, lang)}**; średnia deklarowana pewność "
            f"{P(s['mean_confidence'], 1)}",
            f"- wygenerowane tokeny: **{s['output_tokens_total']}**; mediana wejścia {n_in} "
            f"{plural(n_in, TEXT[lang]['tok'], lang)}, mediana czasu {num(s['median_latency_s'], 1, lang)} s "
            f"({tag(s, lang)})",
            "", "| pewność modelu | odsetek rysunków | trafność w tej grupie |", "|---|---|---|",
        ]
        heads = ["| przedział pewności | rysunków | śr. pewność | trafność |"]
        mistakes = "Najczęstsze pomyłki (prawda → odpowiedź modelu): "
    else:
        lines = [
            f"# Results: {s['model']} on Quick, Draw!", "",
            f"- test drawings: **{s['n']}** (255 words × {s['n'] // 255}), each judged against **all 255 words at once**",
            f"- top-1 accuracy: **{P(s['top1'], 1)}** (95% CI {P(s['top1_ci95'][0], 1)}–{P(s['top1_ci95'][1], 1)}); "
            f"random guessing: {P(s['chance'], 1)}",
            f"- word in the top 5: **{P(s['top5'], 1)}**",
            f"- calibration error (ECE): **{num(s['ece'], 3, lang)}**; mean stated confidence "
            f"{P(s['mean_confidence'], 1)}",
            f"- generated tokens: **{s['output_tokens_total']}**; median input {n_in} tokens, median time "
            f"{num(s['median_latency_s'], 1, lang)} s ({tag(s, lang)})",
            "", "| model confidence | share of drawings | accuracy in this group |", "|---|---|---|",
        ]
        heads = ["| confidence bin | drawings | mean confidence | accuracy |"]
        mistakes = "Most common mistakes (truth → model's answer): "
    for t, v in sel.items():
        lines.append(f"| ≥ {P(float(t))} | {P(v['coverage'], 1)} ({v['n']}) | "
                     f"{P(v['acc'], 1) if v['acc'] is not None else '–'} |")
    lines += [""] + heads + ["|---|---|---|---|"]
    for b in s["bins"]:
        lines.append(f"| {P(b['lo'])}–{P(b['hi'])} | {b['n']} | {P(b['conf'], 1)} | {P(b['acc'], 1)} |")
    lines += ["", mistakes + ", ".join(f"{L(a)} → {L(b)} ({c})" for a, b, c in s["confusions"][:10]), ""]
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
    drawings = {d["key_id"]: d["drawing"] for d in map(json.loads, open(a.drawings))}
    for lang, sfx in SUFFIX.items():
        (out / f"RESULTS{sfx}.md").write_text(markdown(s, lang))
        scorecard(s, out / f"scorecard{sfx}.png", lang)
        gallery(rows, drawings, out / f"gallery{sfx}.png", lang)
    print(markdown(s, "en"))


if __name__ == "__main__":
    main()
