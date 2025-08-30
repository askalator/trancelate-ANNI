#!/usr/bin/env python3
import os, re, json, sqlite3, urllib.request, urllib.error, uvicorn, hashlib
from urllib.parse import quote_plus
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from anni_copy_gate import evaluate

SUPABASE_URL = os.environ.get("SUPABASE_URL","").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY","")
ADMIN_KEY    = os.environ.get("ANNI_ADMIN_KEY","")  # <— API-Key
DB = os.environ.get("ANNI_COPY_DB","copy_library.sqlite")

WORD = re.compile(r'\b[\w\-]+\b', re.UNICODE)

def jaccard(a,b):
    ta=set(WORD.findall(a.lower())); tb=set(WORD.findall(b.lower()))
    return 1.0 if not ta and not tb else len(ta&tb)/len(ta|tb)

def ensure_view():
    con=sqlite3.connect(DB); cur=con.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS item (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, task TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS pick (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL REFERENCES item(id) ON DELETE CASCADE, rank INTEGER NOT NULL, text TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_pick_item ON pick(item_id);
    CREATE VIEW IF NOT EXISTS v_pick_freq AS
      SELECT p.text, i.task, COUNT(*) AS freq, MIN(i.ts) AS first_ts, MAX(i.ts) AS last_ts
      FROM pick p JOIN item i ON p.item_id=i.id
      GROUP BY p.text, i.task
      ORDER BY freq DESC, last_ts DESC;
    """); con.commit(); con.close()

def sb_headers():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY not set")
    return {
        "Content-Type":"application/json",
        "apikey":SUPABASE_KEY,
        "Authorization":f"Bearer {SUPABASE_KEY}",
        "Prefer":"return=representation"
    }

def sb_post(path:str, payload):
    url=f"{SUPABASE_URL}/rest/v1/{path.lstrip('/')}"
    req=urllib.request.Request(url, data=json.dumps(payload).encode(), headers=sb_headers())
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def sb_get(path:str, qs:str):
    url=f"{SUPABASE_URL}/rest/v1/{path.lstrip('/')}?{qs}"
    req=urllib.request.Request(url, headers=sb_headers())
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def require_key(req: Request):
    """Erlaubt: Header 'x-anni-key: <key>' oder 'Authorization: Bearer <key>'."""
    if not ADMIN_KEY:
        return
    auth = req.headers.get("x-anni-key") or req.headers.get("authorization","")
    token = auth.replace("Bearer","").strip() if auth else ""
    if token != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

app = FastAPI(title="ANNI Copy Service")

@app.get("/health")
async def health(): return {"ok": True}

@app.post("/gate")
async def gate(req: Request):
    require_key(req)
    p = await req.json()
    return JSONResponse(evaluate({"task": p["task"], "brief": p.get("brief", {}), "variants": p["variants"]}))

@app.post("/rank")
async def rank(req: Request):
    require_key(req)
    p = await req.json()
    top_k = int(p.get("top_k", 3)); div_th = float(p.get("diversity_threshold", 0.75))
    ev = evaluate({"task": p["task"], "brief": p.get("brief", {}), "variants": p["variants"]})
    scored = [{**r, "index": i} for i,r in enumerate(ev["results"])]
    scored.sort(key=lambda r: r["aqs"], reverse=True)
    picked=[]
    for cand in scored:
        if len(picked)>=top_k: break
        if all(jaccard(cand["text"], prev["text"])<div_th for prev in picked):
            picked.append(cand)
    return JSONResponse({"task":ev["task"],"aggregate":ev["aggregate"],"ranked":scored,"picked":picked,
                         "params":{"top_k":top_k,"diversity_threshold":div_th}})

@app.post("/check")
async def check(req: Request):
    require_key(req)
    p = await req.json()
    aqs_min = float(p.get("aqs_min", 0.65)); enforce_div = bool(p.get("enforce_diversity", True))
    ev = evaluate({"task": p["task"], "brief": p.get("brief", {}), "variants": p["variants"]})
    reasons=[]
    if ev["aggregate"]["avg_aqs"] < aqs_min: reasons.append("aqs_below_min")
    if enforce_div and not ev["aggregate"]["diversity_ok"]: reasons.append("diversity_fail")
    return JSONResponse({"ok": not reasons, "aggregate": ev["aggregate"], "reasons": reasons},
                        status_code=200 if not reasons else 422)

@app.get("/picks/top")
async def picks_top(task: str | None = None, limit: int = 10):
    # bewusst offen für internes Reporting
    ensure_view()
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row; cur=con.cursor()
    if task:
        cur.execute("SELECT task,text,freq,first_ts,last_ts FROM v_pick_freq WHERE task=? ORDER BY freq DESC,last_ts DESC LIMIT ?", (task, limit))
    else:
        cur.execute("SELECT task,text,freq,first_ts,last_ts FROM v_pick_freq ORDER BY freq DESC,last_ts DESC LIMIT ?", (limit,))
    rows=[dict(r) for r in cur.fetchall()]
    con.close()
    return JSONResponse({"items": rows, "count": len(rows)})

@app.post("/commit")
async def commit(req: Request):
    require_key(req)
    p = await req.json()
    request_key = p.get("request_key")
    if not request_key:
        canon = json.dumps({"task":p.get("task"),"brief":p.get("brief",{}),"variants":p.get("variants",[])}, sort_keys=True, ensure_ascii=False)
        request_key = hashlib.sha256(canon.encode("utf-8")).hexdigest()

    try:
        rows = sb_get("commit_req", f"request_key=eq.{quote_plus(request_key)}&select=item_id")
        if rows:
            item_id = rows[0]["item_id"]
            picks = sb_get("pick", f"item_id=eq.{item_id}&select=text,rank&order=rank.asc")
            return JSONResponse({"ok":True,"item_id":item_id,"picks":[r["text"] for r in picks],"idempotent":True})
    except Exception:
        pass

    body = {"task": p["task"], "brief": p.get("brief", {}), "variants": p["variants"]}
    ev = evaluate(body)
    scored = [{**r, "index": i} for i,r in enumerate(ev["results"])]
    scored.sort(key=lambda r: r["aqs"], reverse=True)
    top_k = int(p.get("top_k", 3)); div_th = float(p.get("diversity_threshold", 0.75))
    picked=[]
    for cand in scored:
        if len(picked)>=top_k: break
        if all(jaccard(cand["text"], prev["text"])<div_th for prev in picked):
            picked.append(cand)

    try:
        item_rows = sb_post("item", {"task": p["task"]})
        item_id = item_rows[0]["id"]
        picks_payload = [{"item_id": item_id, "rank": i+1, "text": x["text"]} for i,x in enumerate(picked)]
        pick_rows = sb_post("pick", picks_payload)
        sb_post("commit_req", {"request_key": request_key, "item_id": item_id})
    except urllib.error.HTTPError as e:
        return JSONResponse({"ok":False,"error":f"supabase_http_{e.code}"}, status_code=502)
    except Exception as e:
        return JSONResponse({"ok":False,"error":str(e)}, status_code=500)

    return JSONResponse({"ok":True,"item_id":item_id,"picks":[r["text"] for r in pick_rows],
                         "aggregate":ev["aggregate"],"params":{"top_k":top_k,"diversity_threshold":div_th},
                         "idempotent":False})
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8094)
