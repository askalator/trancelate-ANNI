#!/usr/bin/env bash
set -euo pipefail
ENV=${ENV:-tl311}
PORT_MT=${PORT_MT:-8090}
PORT_GUARD=${PORT_GUARD:-8091}
export MT_TIMEOUT=${MT_TIMEOUT:-300}
export HF_HOME="${HF_HOME:-$PWD/.hf}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HF_HOME/cache}"
export TOKENIZERS_PARALLELISM=${TOKENIZERS_PARALLELISM:-false}
mkdir -p logs "$HF_HOME" "$TRANSFORMERS_CACHE"

log(){ printf '%s %s\n' "$(date '+%H:%M:%S')" "$*"; }

# Ports räumen
lsof -tiTCP:$PORT_MT -sTCP:LISTEN 2>/dev/null | xargs -I{} kill -9 {} 2>/dev/null || true
lsof -tiTCP:$PORT_GUARD -sTCP:LISTEN 2>/dev/null | xargs -I{} kill -9 {} 2>/dev/null || true

# 1) MT starten & Health abwarten
log "Start MT ($PORT_MT)…"
conda run -n "$ENV" env ANNI_DEVICE="${ANNI_DEVICE:-cpu}" HF_HOME="$HF_HOME" TRANSFORMERS_CACHE="$TRANSFORMERS_CACHE" TOKENIZERS_PARALLELISM="$TOKENIZERS_PARALLELISM" \
  python -m uvicorn mt_server:app --host 127.0.0.1 --port $PORT_MT --workers ${MT_WORKERS:-2} > logs/mt.log 2>&1 &
echo $! > logs/mt.pid
for i in {1..90}; do
  curl -sf http://127.0.0.1:$PORT_MT/health >/dev/null && { log "MT up"; break; }
  sleep 1; [ $i -eq 90 ] && { log "❌ MT health timeout (siehe logs/mt.log)"; exit 1; }
done

# 2) Modelle am Worker vorwärmen (füllt lokalen HF-Cache)
pairs=( "de en" "en de" "fr en" "en fr" "es en" "en es" "it en" "en it" "pt en" "en pt" "nl en" "en nl" )
for p in "${pairs[@]}"; do
  set -- $p; src=$1; tgt=$2
  log "Prewarm $src->$tgt"
  conda run -n "$ENV" python - "$src" "$tgt" <<'PY' || true
import json, sys, urllib.request
src, tgt = sys.argv[1], sys.argv[2]
req=urllib.request.Request("http://127.0.0.1:8090/translate", method="POST",
    headers={"Content-Type":"application/json","Accept":"application/json"},
    data=json.dumps({"source":src,"target":tgt,"text":"ok"}).encode("utf-8"))
urllib.request.urlopen(req, timeout=600).read()
PY
done

# 3) Guard starten & Health abwarten
log "Start Guard ($PORT_GUARD)…"
conda run -n "$ENV" env MT_TIMEOUT="$MT_TIMEOUT" python -m uvicorn mt_guard:app --host 127.0.0.1 --port $PORT_GUARD > logs/mt_guard.log 2>&1 &
echo $! > logs/mt_guard.pid
for i in {1..60}; do
  curl -sf http://127.0.0.1:$PORT_GUARD/health >/dev/null && { log "Guard up"; break; }
  sleep 1; [ $i -eq 60 ] && { log "❌ Guard health timeout (siehe logs/mt_guard.log)"; exit 1; }
done

# 4) Provider binden bis backend_alive:true
for i in {1..60}; do
  curl -s -X POST http://127.0.0.1:$PORT_GUARD/admin/reload >/dev/null
  curl -s http://127.0.0.1:$PORT_GUARD/meta | grep -q '"backend_alive":true' && { log "Backend bound"; break; }
  sleep 1; [ $i -eq 60 ] && { log "❌ Bind timeout"; exit 1; }
done

# 5) Smokes
log "Smoke A"
curl -s -H 'Content-Type: application/json' -d '{"source":"de","target":"en","text":"Guten Morgen"}' http://127.0.0.1:$PORT_GUARD/translate && echo
log "Smoke B (PH+HTML+NUM)"
curl -s -H 'Content-Type: application/json' -d '{"source":"de","target":"en","text":"Nur heute: {{COUNT}} Plätze frei bei <strong>{app}</strong> – 2 Tage gültig!"}' http://127.0.0.1:$PORT_GUARD/translate && echo

log "READY"
