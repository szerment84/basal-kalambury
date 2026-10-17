#!/usr/bin/env bash
# Uruchamia basal-serve z modelem basal-omni i grę: http://127.0.0.1:7860
# Inny model: BASAL_MODEL=Remek/basal-omni-1.0-ultra ./start.sh  (ultra: GPU 80 GB)
set -euo pipefail
cd "$(dirname "$0")"
MODEL="${BASAL_MODEL:-Remek/basal-omni-1.0-mini}"
PY=.venv/bin/python
[ -x "$PY" ] || { echo "Najpierw: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"; exit 1; }

if [ "$(uname -sm)" = "Darwin arm64" ]; then
  ENGINE=(--mode eager --device mps --dtype float16)  # GPU M1/M2 nie liczy w bf16; fp16 daje te same odpowiedzi (README)
else
  ENGINE=(--mode eager)
fi

"$PY" -m kalambury.serve --model "$MODEL" "${ENGINE[@]}" --media on --host 127.0.0.1 --port 8000 &
SERVE=$!
trap 'kill $SERVE 2>/dev/null' EXIT
echo "Ładuję $MODEL (pierwsze uruchomienie pobiera wagi z Hugging Face)…"
until curl -s -m 2 http://127.0.0.1:8000/v1/models >/dev/null; do
  kill -0 $SERVE 2>/dev/null || { echo "basal-serve się nie uruchomił"; exit 1; }
  sleep 2
done
"$PY" -m kalambury.server --port 7860
