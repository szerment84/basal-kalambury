"""Runs the drawings of a JSONL file through basal-serve and saves the probability distributions. Can be resumed.

  python bench/run.py data/quickdraw_test.jsonl results/test.jsonl
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kalambury.basal_client import guess, model_name  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("drawings")
    ap.add_argument("out")
    ap.add_argument("--option-keys", default="hide", choices=["hide", "show"])
    ap.add_argument("--detail", default="default", choices=["default", "high"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--tag", default="", help="any label saved with the results (e.g. the server's dtype)")
    a = ap.parse_args()

    out = Path(a.out)
    done = {json.loads(line)["key_id"] for line in out.open()} if out.exists() else set()
    rows = [json.loads(line) for line in open(a.drawings)]
    todo = [r for r in rows if r["key_id"] not in done][:a.limit]
    model, ok = model_name(), 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as f:
        for i, r in enumerate(todo, 1):
            t = time.time()
            ans, usage = guess(r["drawing"], option_keys=a.option_keys, detail=a.detail)
            p = ans["probabilities"]
            rec = {"key_id": r["key_id"], "word": r["word"], "choice": ans["choice"], "confidence": ans["confidence"],
                   "p_true": p[r["word"]], "rank_true": 1 + sum(v > p[r["word"]] for v in p.values()),
                   "p": {k: round(v, 4) for k, v in sorted(p.items(), key=lambda kv: -kv[1]) if v >= 5e-4},
                   "strokes": len(r["drawing"]), "latency_ms": usage.get("latency_ms"),
                   "wall_ms": round((time.time() - t) * 1000), "input_tokens": usage["input_tokens"],
                   "output_tokens": usage["output_tokens"], "model": model, "option_keys": a.option_keys,
                   "detail": a.detail, "tag": a.tag}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            ok += rec["choice"] == r["word"]
            print(f"[{i}/{len(todo)}] {r['word']} -> {rec['choice']} ({rec['confidence']:.2f})  "
                  f"top-1 {ok / i:.3f}  {rec['wall_ms'] / 1000:.1f}s", flush=True)


if __name__ == "__main__":
    main()
