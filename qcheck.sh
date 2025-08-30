#!/usr/bin/env bash
set -euo pipefail
URL=${URL:-http://127.0.0.1:8091/translate}
call(){ SRC=$1; TGT=$2; TXT=$3; curl -s "$URL" -H 'Content-Type: application/json' -d "{\"source\":\"$SRC\",\"target\":\"$TGT\",\"text\":\"$TXT\"}"; }

# 1) Placeholder unverändert
OUT=$(call de en "TranceLate Pro synchronisiert {{COUNT}} Seiten.")
echo "OUT1: $OUT"
echo "$OUT" | grep -q "{{COUNT}}" || { echo "❌ Placeholder drift"; exit 1; }

# 2) Zahlen unverfälscht (Komma ODER Punkt akzeptiert)
OUT=$(call de en "Preis: 19,90 € inkl. MwSt.")
echo "OUT2: $OUT"
echo "$OUT" | grep -E "19[,.]90" >/dev/null || { echo "❌ Number drift"; exit 1; }

echo "✅ Quality gate passed"
