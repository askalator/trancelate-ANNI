#!/usr/bin/env bash
set -euo pipefail
URL=${URL:-http://127.0.0.1:8091/translate}  # Guard+MT
POLISH=${POLISH:-auto}                          # off | on | auto
SRC=${1:-de}; TGT=${2:-en}; shift 2 || true
TXT="$*"; [ -n "$TXT" ] || TXT="$(cat)"

# 1) MT (mit Provenienz)
MT_JSON=$(jq -rn --arg s "$SRC" --arg t "$TGT" --arg x "$TXT" \
  '{source:$s,target:$t,text:$x}' | curl -sS -H 'Content-Type: application/json' -d @- "$URL")
PROV=$(echo "$MT_JSON" | jq -c '.provenance // {}')

# 2) Polish-Modus
case "$POLISH" in
  on)
    echo "$MT_JSON" | jq -r '.translated_text' \
      | ./polish.py \
      | jq -Rn --argjson prov "$PROV" '{translated_text: input, provenance: $prov}'
    ;;
  auto)
    TM_KIND=$(echo "$MT_JSON" | jq -r '.provenance.tm // "miss"')
    if [ "$TM_KIND" = "miss" ]; then
      echo "$MT_JSON" | jq -r '.translated_text' \
        | ./polish.py \
        | jq -Rn --argjson prov "$PROV" '{translated_text: input, provenance: $prov}'
    else
      echo "$MT_JSON"
    fi
    ;;
  *)
    echo "$MT_JSON"
    ;;
esac
