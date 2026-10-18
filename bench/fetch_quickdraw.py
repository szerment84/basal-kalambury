"""Downloads random Google Quick, Draw! drawings (simplified ndjson, CC BY 4.0) for the game's 255 words.

Each category file is tens of MB, so the script reads only a few random chunks (HTTP Range) and keeps the complete
lines with recognized=true. Output:
  data/quickdraw_dev.jsonl   1 drawing per word: for engine checks, not part of the report
  data/quickdraw_test.jsonl  --per-word drawings per word: the test set
"""
import argparse
import json
import random
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kalambury.words import SEED, WORDS  # noqa: E402

URL = "https://storage.googleapis.com/quickdraw_dataset/full/simplified/{}.ndjson"
CHUNK = 64 * 1024


def get(req, tries=5):
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.headers, r.read()
        except OSError:
            if k == tries - 1:
                raise
            time.sleep(2 ** k)


def fetch(word, chunks):
    url = URL.format(urllib.parse.quote(word))
    size = int(get(urllib.request.Request(url, method="HEAD"))[0]["Content-Length"])
    rng = random.Random(f"{SEED}:{word}")
    out = []
    for start in sorted(rng.sample(range(size - CHUNK), chunks)):
        req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{start + CHUNK - 1}"})
        lines = get(req)[1].decode("utf-8", "replace").split("\n")[1:-1]  # the first and last lines are cut
        out += [json.loads(line) for line in lines]
    seen, rows = set(), []
    for d in out:
        if d["recognized"] and d["key_id"] not in seen:
            seen.add(d["key_id"])
            rows.append({"word": d["word"], "key_id": d["key_id"], "countrycode": d["countrycode"],
                         "drawing": d["drawing"]})
    rng.shuffle(rows)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-word", type=int, default=4, help="test drawings per word")
    ap.add_argument("--chunks", type=int, default=3, help="random file chunks per word")
    a = ap.parse_args()
    with ThreadPoolExecutor(8) as ex:
        got = dict(zip(WORDS, ex.map(lambda w: fetch(w, a.chunks), WORDS)))
    (ROOT / "data").mkdir(exist_ok=True)
    for w in WORDS:
        if len(got[w]) < 1 + a.per_word:
            raise SystemExit(f"{w}: only {len(got[w])} drawings, raise --chunks")
    with open(ROOT / "data/quickdraw_dev.jsonl", "w") as dev:
        dev.writelines(json.dumps(got[w][0]) + "\n" for w in WORDS)
    with open(ROOT / "data/quickdraw_test.jsonl", "w") as test:  # in turn: every word's 1st drawing, then 2nd, ...
        test.writelines(json.dumps(got[w][j]) + "\n" for j in range(1, 1 + a.per_word) for w in WORDS)
    print(f"{len(WORDS)} words: dev {len(WORDS)}, test {len(WORDS) * a.per_word} drawings")


if __name__ == "__main__":
    main()
