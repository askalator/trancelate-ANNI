#!/usr/bin/env bash
set -euo pipefail
CMD=${1:-status}
PIDF=/tmp/anni_copy_service.pid
LOG=/tmp/anni_copy_service.log
case "$CMD" in
  start)
    if [[ -f "$PIDF" ]] && kill -0 $(cat "$PIDF") 2>/dev/null; then echo "8094: already running (pid $(cat $PIDF))"; exit 0; fi
    nohup python3 -m uvicorn anni_copy_service:app --host 127.0.0.1 --port 8094 >"$LOG" 2>&1 & echo $! >"$PIDF"
    echo "8094: started (pid $(cat $PIDF))"
    ;;
  stop)
    if [[ -f "$PIDF" ]] && kill -0 $(cat "$PIDF") 2>/dev/null; then kill $(cat "$PIDF") || true; rm -f "$PIDF"; echo "8094: stopped"; else echo "8094: not running"; fi
    ;;
  status)
    if lsof -iTCP:8094 -sTCP:LISTEN -nP >/dev/null 2>&1; then echo "8094: up"; else echo "8094: down"; fi
    ;;
  log)
    tail -n 50 -f "$LOG"
    ;;
  *)
    echo "usage: $0 {start|stop|status|log}"; exit 2
    ;;
esac
