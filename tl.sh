#!/usr/bin/env bash
set -euo pipefail

BASE="${HOME}/trancelate-onprem"
VENV="${BASE}/.venv"
LOGS="${BASE}/logs"
RUN="${BASE}/run"
TENANT_DIR="${BASE}/tenants/demo"

LLM_PORT=8000
GATEWAY_PORT=8088
MODEL="${BASE}/llm/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"

ensure_dirs(){ mkdir -p "$LOGS" "$RUN" "$TENANT_DIR"; }
ensure_venv(){ source "${VENV}/bin/activate"; }

wait_http(){  # $1 url $2 seconds
  local url="$1" t="${2:-30}" i=0
  until curl -sS --max-time 1 "$url" >/dev/null 2>&1; do
    ((i++)); [[ $i -ge $t ]] && { echo "TIMEOUT waiting for $url"; return 1; }
    sleep 1
  done
}

start_llm(){
  ensure_venv; ensure_dirs
  pkill -f "llama_cpp.server" >/dev/null 2>&1 || true
  export LLAMA_METAL=1
  nohup python -m llama_cpp.server \
    --host 127.0.0.1 --port ${LLM_PORT} \
    --model "${MODEL}" \
    --chat_format mistral-instruct \
    --n_ctx 8192 --n_threads 6 \
    > "${LOGS}/llm.log" 2>&1 & echo $! > "${RUN}/llm.pid"
  echo "LLM starting... (port ${LLM_PORT})"
  wait_http "http://127.0.0.1:${LLM_PORT}/docs" 60
  echo "LLM ready."
}

start_gateway(){
  ensure_venv; ensure_dirs
  pkill -f "uvicorn.*gateway_rag:app" >/dev/null 2>&1 || true
  UPSTREAM="http://127.0.0.1:${LLM_PORT}" \
  TENANT_DIR="${TENANT_DIR}" \
  EMB_MODEL="intfloat/multilingual-e5-base" \
  TOP_K="24" \
  nohup uvicorn gateway_rag:app --host 127.0.0.1 --port ${GATEWAY_PORT} \
    > "${LOGS}/gateway.log" 2>&1 & echo $! > "${RUN}/gateway.pid"
  echo "Gateway starting... (port ${GATEWAY_PORT})"
  wait_http "http://127.0.0.1:${GATEWAY_PORT}/openapi.json" 30
  echo "Gateway ready."
}

stop_all(){
  pkill -f "uvicorn.*gateway_rag:app" >/dev/null 2>&1 || true
  pkill -f "llama_cpp.server"       >/dev/null 2>&1 || true
  [[ -f "${RUN}/gateway.pid" ]] && rm -f "${RUN}/gateway.pid"
  [[ -f "${RUN}/llm.pid"     ]] && rm -f "${RUN}/llm.pid"
  echo "Stopped."
}

status(){
  echo "Ports:"
  lsof -nP -iTCP:${LLM_PORT}    -sTCP:LISTEN || true
  lsof -nP -iTCP:${GATEWAY_PORT} -sTCP:LISTEN || true
  echo; echo "Last logs:"
  tail -n 5 "${LOGS}/llm.log"     2>/dev/null || true
  tail -n 5 "${LOGS}/gateway.log" 2>/dev/null || true
}

scan(){
  ensure_venv; ensure_dirs
  local url="${1:-}"; local max="${2:-40}"
  [[ -z "$url" ]] && { echo "Usage: $0 scan <https://domain> [max_pages]"; exit 1; }
  python "${BASE}/scan_site.py" "$url" --out "${TENANT_DIR}" --max-pages "${max}"
}

test(){
  ensure_venv
  echo "Ping LLM:"
  curl -s "http://127.0.0.1:${LLM_PORT}/docs" >/dev/null && echo "OK" || echo "FAIL"
  echo "Ping Gateway:"
  curl -s "http://127.0.0.1:${GATEWAY_PORT}/openapi.json" >/dev/null && echo "OK" || echo "FAIL"
  echo "Chat sample:"
  curl -s "http://127.0.0.1:${GATEWAY_PORT}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{"model":"local","messages":[{"role":"user","content":"Antworte nur mit: OK"}],"temperature":0,"max_tokens":3}'
  echo
}

case "${1:-}" in
  start) start_llm; start_gateway ;;
  stop)  stop_all ;;
  status) status ;;
  scan) shift; scan "$@" ;;
  test) test ;;
  restart) stop_all; start_llm; start_gateway ;;
  *) echo "Usage: $0 {start|stop|restart|status|scan <url> [max_pages]|test}"; exit 1 ;;
esac
