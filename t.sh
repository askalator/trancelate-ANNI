#!/usr/bin/env bash
set -euo pipefail
URL=${URL:-http://127.0.0.1:8091/translate}
SRC=${1:-de}; TGT=${2:-en}; shift 2 || true
TXT="$*"
if [ -z "$TXT" ]; then
  echo "Text über STDIN eingeben, mit Ctrl+D abschließen …" >&2
  TXT="$(cat)"
fi
jq -rn --arg s "$SRC" --arg t "$TGT" --arg x "$TXT" \
  '{source:$s,target:$t,text:$x}' 2>/dev/null \
  | curl -sS -H 'Content-Type: application/json' -d @- "$URL"
