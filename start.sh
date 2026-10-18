#!/usr/bin/env bash
# Starts basal-serve with a basal-omni model and the game: http://127.0.0.1:7860
# Another model: BASAL_MODEL=Remek/basal-omni-1.0-ultra ./start.sh  (ultra needs an 80 GB GPU)
set -euo pipefail
cd "$(dirname "$0")"
MODEL="${BASAL_MODEL:-Remek/basal-omni-1.0-mini}"
PY=.venv/bin/python
[ -x "$PY" ] || { echo "First run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"; exit 1; }

if [ "$(uname -sm)" = "Darwin arm64" ]; then
  ENGINE=(--mode eager --device mps --dtype float16)  # bf16 runs at half speed on the M1; fp16 gives the same answers (README)
else
  ENGINE=(--mode eager)
fi

"$PY" -m kalambury.serve --model "$MODEL" "${ENGINE[@]}" --media on --host 127.0.0.1 --port 8000 &
SERVE=$!
trap 'kill $SERVE 2>/dev/null' EXIT
echo "Loading $MODEL (the first run downloads the weights from Hugging Face)…"
until curl -s -m 2 http://127.0.0.1:8000/v1/models >/dev/null; do
  kill -0 $SERVE 2>/dev/null || { echo "basal-serve did not start"; exit 1; }
  sleep 2
done
"$PY" -m kalambury.server --port 7860
