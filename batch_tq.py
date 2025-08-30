#!/usr/bin/env python3
import sys, json, os, requests, time

"""
Input:  JSONL mit Zeilen wie
{"source":"de","target":"en","text":"Jetzt starten."}
Output: JSONL mit Zeilen wie
{"source":"de","target":"en","text":"Jetzt starten.","result":{"translated_text":"Start now",...},"ok":true,"lat_ms":42.1}
Exitcode != 0 wenn mind. ein Datensatz ok=false ist.
"""

URL = os.getenv("URL","http://127.0.0.1:8091/translate")
inp = sys.argv[1] if len(sys.argv) > 1 else "-"
outp = sys.argv[2] if len(sys.argv) > 2 else "-"

fin = sys.stdin if inp == "-" else open(inp, encoding="utf-8")
fout = sys.stdout if outp == "-" else open(outp, "w", encoding="utf-8")

session = requests.Session()
bad = 0; n = 0
for line in fin:
    line = line.strip()
    if not line or line.startswith("#"): 
        continue
    rec = json.loads(line)
    payload = {"source": rec["source"], "target": rec["target"], "text": rec["text"]}
    t0 = time.time()
    r = session.post(URL, json=payload, timeout=60)
    dt = (time.time()-t0)*1000
    r.raise_for_status()
    res = r.json()
    ok = bool(res.get("checks",{}).get("ok", True))
    n += 1
    if not ok: bad += 1
    out = {"source": rec["source"], "target": rec["target"], "text": rec["text"], "result": res, "ok": ok, "lat_ms": round(dt,1)}
    fout.write(json.dumps(out, ensure_ascii=False) + "\n")

if fin is not sys.stdin: fin.close()
if fout is not sys.stdout: fout.close()

print(f"done: {n} items, {bad} failed", file=sys.stderr)
sys.exit(1 if bad else 0)
