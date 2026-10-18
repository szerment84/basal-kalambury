"""basal kalambury: the browser game. Serves the frontend and passes the strokes on to basal-serve.

  python -m kalambury.server          # http://127.0.0.1:7860, basal-serve at BASAL_URL (default :8000)
"""
import argparse
import base64
import importlib.metadata
import json
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import basal_client
from .render import png
from .words import LABELS, PACKS

STATIC = Path(__file__).parent / "static"
# parameter counts of the basal-omni models, from the basal README (/v1/models does not report them)
PARAMS = {"basal-omni-1.0-mini": "4B", "basal-omni-1.0-max": "12B", "basal-omni-1.1-max": "12B",
          "basal-omni-1.0-ultra": "31B", "basal-omni-1.0-ultra-FP8": "31B"}
try:
    ENGINE = "basal " + importlib.metadata.version("basal")
except importlib.metadata.PackageNotFoundError:
    ENGINE = None


def word(k):
    return {"key": k, "pl": LABELS[k]["pl"], "en": LABELS[k]["en"]}


def model():
    """The exact model basal-serve is serving, or None when it is down."""
    try:
        info = basal_client.model_info()
    except OSError:
        return None
    return {"name": info["name"], "params": PARAMS.get(info["name"]), "released": info.get("release_date"),
            "mode": info.get("mode"), "engine": ENGINE}


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")  # revalidate every time, so an update reaches the browser
        super().end_headers()

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path != "/api/words":
            return super().do_GET()
        pack = parse_qs(url.query).get("pack", ["quickdraw"])[0]
        if pack not in PACKS:
            return self.send_json({"error": f"unknown pack: {pack}"}, 400)
        self.send_json({"model": model(), "pack": pack, "words": [word(k) for k in PACKS[pack]["options"]],
                        "targets": PACKS[pack]["targets"]})

    def do_POST(self):
        if self.path != "/api/guess":
            return self.send_error(404)
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        strokes, pack = body.get("strokes"), body.get("pack", "quickdraw")
        if not strokes:
            return self.send_json({"error": "empty drawing"}, 400)
        if pack not in PACKS:
            return self.send_json({"error": f"unknown pack: {pack}"}, 400)
        t = time.time()
        try:
            ans, usage = basal_client.guess(strokes, pack=pack)
        except OSError as e:
            return self.send_json({"error": f"basal-serve is not answering at {basal_client.BASAL_URL}: {e}"}, 502)
        ranking = sorted(ans["probabilities"].items(), key=lambda kv: -kv[1])
        self.send_json({"choice": ans["choice"], "confidence": ans["confidence"],
                        "ranking": [{**word(k), "p": p} for k, p in ranking],
                        "usage": usage, "wall_ms": round((time.time() - t) * 1000),
                        "image": "data:image/png;base64," + base64.b64encode(png(strokes)).decode()})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7860)
    a = ap.parse_args()
    print(f"basal kalambury: http://{a.host}:{a.port}  (basal-serve: {basal_client.BASAL_URL})", flush=True)
    ThreadingHTTPServer((a.host, a.port), partial(Handler, directory=str(STATIC))).serve_forever()


if __name__ == "__main__":
    main()
