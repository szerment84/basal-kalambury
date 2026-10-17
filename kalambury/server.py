"""basal kalambury: gra w przeglądarce. Serwuje frontend i przekazuje kreski do basal-serve.

  python -m kalambury.server          # http://127.0.0.1:7860, basal-serve pod BASAL_URL (domyślnie :8000)
"""
import argparse
import base64
import json
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import basal_client
from .render import png
from .words import PL, WORDS

STATIC = Path(__file__).parent / "static"


class Handler(SimpleHTTPRequestHandler):
    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/api/words":
            return super().do_GET()
        try:
            model = basal_client.model_name()
        except OSError:
            model = None
        self.send_json({"model": model, "words": [{"key": k, "pl": PL[k]} for k in WORDS]})

    def do_POST(self):
        if self.path != "/api/guess":
            return self.send_error(404)
        strokes = json.loads(self.rfile.read(int(self.headers["content-length"]))).get("strokes")
        if not strokes:
            return self.send_json({"error": "pusty rysunek"}, 400)
        t = time.time()
        try:
            ans, usage = basal_client.guess(strokes)
        except OSError as e:
            return self.send_json({"error": f"basal-serve nie odpowiada pod {basal_client.BASAL_URL}: {e}"}, 502)
        ranking = sorted(ans["probabilities"].items(), key=lambda kv: -kv[1])
        self.send_json({"choice": ans["choice"], "confidence": ans["confidence"],
                        "ranking": [{"key": k, "pl": PL[k], "p": p} for k, p in ranking],
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
