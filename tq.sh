#!/usr/bin/env bash
set -euo pipefail
URL=${URL:-http://127.0.0.1:8091/translate}
SRC=${1:-de}; TGT=${2:-en}; shift 2 || true
TXT="$*"; [ -n "$TXT" ] || TXT="$(cat)"

REQ=$(jq -rn --arg s "$SRC" --arg t "$TGT" --arg x "$TXT" '{source:$s,target:$t,text:$x}')
RES=$(echo "$REQ" | curl -sS -H 'Content-Type: application/json' -d @- "$URL")
echo "$RES"

OK=$(echo "$RES" | jq -r '.checks.ok // "true"')
if [ "$OK" != "true" ]; then
  echo "❌ Quality checks failed" >&2
  exit 1
fi
