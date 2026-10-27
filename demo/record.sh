#!/usr/bin/env bash
# Records demo/revenant-demo.gif in a throwaway zsh with a FABRICATED history. Needs: vhs, ollama with gemma3.
set -euo pipefail
cd "$(dirname "$0")/.."
export REVENANT_SRC="$PWD" PATH="$PWD/demo/bin:$PATH" DEMO_STATE="$(mktemp -d)" DEMO_HISTORY="$(mktemp)"
# safety check: the stand-ins must be what the shell finds, never the real tools
for t in docker git make npm; do [ "$(command -v $t)" = "$PWD/demo/bin/$t" ] || { echo "stand-in for $t is not first on PATH"; exit 1; }; done
python3 demo/make_history.py "$DEMO_HISTORY"
curl -s localhost:11434/api/generate -d '{"model":"gemma3:12b","prompt":"hi","stream":false,"keep_alive":"10m"}' >/dev/null  # warm the model
ZDOTDIR="$PWD/demo/zdot" vhs demo/demo.tape
rm -rf "$DEMO_STATE" "$DEMO_HISTORY"
