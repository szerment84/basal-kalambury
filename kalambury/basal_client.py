"""A basal-serve request: the drawing as an image + one `choice` question over 255 words, no text generated."""
import base64
import json
import os
import urllib.request

from .render import png
from .words import LABELS, PACKS

BASAL_URL = os.environ.get("BASAL_URL", "http://127.0.0.1:8000")
# the model is asked in Polish, as in the benchmark: "A hand-drawn sketch made with a mouse in a game of charades:
# black lines on a white background." / "What does this drawing show?"
STATE = "Odręczny szkic narysowany myszką w grze w kalambury: czarne kreski na białym tle."
QUESTION = "Co przedstawia ten rysunek?"


def request_body(strokes, pack="quickdraw", option_keys="hide", detail="default"):
    return {
        "state": STATE,
        "questions": {"haslo": {"type": "choice", "instructions": QUESTION,
                                "criteria": {k: LABELS[k]["pl"] for k in PACKS[pack]["options"]},
                                "option_keys": option_keys}},
        "media": [{"type": "image", "data": base64.b64encode(png(strokes)).decode()}],
        "detail": detail,
        "lang": "pl",
    }


def guess(strokes, **kw):
    """-> (the answer to the "haslo" question, usage) from basal-serve."""
    req = urllib.request.Request(BASAL_URL + "/v1/systemone", data=json.dumps(request_body(strokes, **kw)).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        out = json.load(r)
    return out["answers"]["haslo"], out["usage"]


def model_info():
    """basal-serve's description of the served model (name, release_date, mode, ...)."""
    with urllib.request.urlopen(BASAL_URL + "/v1/models", timeout=10) as r:
        return json.load(r)["models"][0]


def model_name():
    return model_info()["name"]
