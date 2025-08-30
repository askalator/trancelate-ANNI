.PHONY: gate-start gate-stop gate-status rank-test fuzz eval

gate-start:
	@nohup python3 -m uvicorn anni_copy_service:app --host 127.0.0.1 --port 8094 >/tmp/anni_copy_service.log 2>&1 & echo $$! > /tmp/anni_copy_service.pid; echo "8094: started"

gate-stop:
	@p=$$(cat /tmp/anni_copy_service.pid 2>/dev/null || true); if [ -n "$$p" ]; then kill $$p || true; rm -f /tmp/anni_copy_service.pid; echo "8094: stopped"; else echo "8094: not running"; fi

gate-status:
	@lsof -iTCP:8094 -sTCP:LISTEN -nP >/dev/null 2>&1 && echo "8094: up" || echo "8094: down"

rank-test:
	@curl -sS -H 'Content-Type: application/json' \
	  -d '{"task":"cta","brief":{"brand_terms":["TranceLate"],"never_translate":["TranceLate"]},"variants":["Jetzt starten","Sofort prüfen","Design prüfen — kostenlos"],"top_k":3,"diversity_threshold":0.75}' \
	  http://127.0.0.1:8094/rank | jq

fuzz:
	@./anni_invariant_fuzz.py 50

eval:
	@./run_quality.sh evalset/*.json
