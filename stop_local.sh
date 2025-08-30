#!/usr/bin/env bash
set -euo pipefail
for f in logs/mt_guard.pid logs/mt.pid; do
  [ -f "$f" ] && kill -9 "$(cat "$f")" 2>/dev/null || true
done
lsof -tiTCP:8090 -sTCP:LISTEN 2>/dev/null | xargs -I{} kill -9 {} 2>/dev/null || true
lsof -tiTCP:8091 -sTCP:LISTEN 2>/dev/null | xargs -I{} kill -9 {} 2>/dev/null || true
echo "✅ stopped"
