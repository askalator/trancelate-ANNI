import os, json, urllib.request, urllib.parse, urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ADMIN_KEY    = os.environ.get("ANNI_ADMIN_KEY","change-me-please")

def sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation"
    }

def sb_post(path, rows):
    url=f"{SUPABASE_URL}{path}"
    req=urllib.request.Request(url, data=json.dumps(rows).encode(), headers=sb_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        raw=r.read()
        return json.loads(raw.decode()) if raw else []

def sb_get(path_qs):
    url=f"{SUPABASE_URL}{path_qs}"
    req=urllib.request.Request(url, headers=sb_headers())
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

class H(BaseHTTPRequestHandler):
    def _auth(self):
        return self.headers.get("x-anni-key")==ADMIN_KEY
    def _json(self, code, obj):
        b=json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        if self.path!="/approve": self._json(404, {"detail":"Not Found"}); return
        if not self._auth(): self._json(401, {"detail":"Unauthorized"}); return
        try:
            ln=int(self.headers.get("Content-Length","0")); body=self.rfile.read(ln).decode() if ln>0 else "{}"; p=json.loads(body)
        except Exception: self._json(400, {"ok":False,"error":"bad_json"}); return
        org=p.get("org","default"); task=p.get("task","cta"); texts=p.get("texts") or []; src_item=p.get("source_item"); rank=p.get("rank")
        rows=[]; 
        for t in texts:
            if not t: continue
            row={"org":org,"task":task,"text":t}
            if src_item is not None: row["source_item"]=src_item
            if rank is not None: row["rank"]=rank
            rows.append(row)
        if not rows: self._json(200, {"ok":True,"inserted":0,"rows":[]}); return
        try:
            data=sb_post("/rest/v1/approved_copy?on_conflict=org,task,text", rows)
            self._json(200, {"ok":True,"inserted":len(data),"rows":data})
        except urllib.error.HTTPError as e:
            self._json(502, {"ok":False,"error":f"supabase_http_{e.code}","body":e.read().decode("utf-8","ignore")})
    def do_GET(self):
        if not self._auth(): self._json(401, {"detail":"Unauthorized"}); return
        if self.path.startswith("/approved/top"):
            q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            org=q.get("org",["default"])[0]; task=q.get("task",["cta"])[0]
            try: limit=min(100,max(1,int(q.get("limit",["10"])[0])))
            except Exception: limit=10
            qs=f"/rest/v1/approved_copy?org=eq.{urllib.parse.quote_plus(org)}&task=eq.{urllib.parse.quote_plus(task)}&select=id,text,created_ts&order=created_ts.desc&limit={limit}"
            try: rows=sb_get(qs); self._json(200, {"items":rows,"count":len(rows)})
            except urllib.error.HTTPError as e: self._json(502, {"ok":False,"error":f"supabase_http_{e.code}"})
        elif self.path=="/health":
            self._json(200, {"ok":True})
        else:
            self._json(404, {"detail":"Not Found"})
def run(port):
    HTTPServer(("0.0.0.0", port), H).serve_forever()
if __name__=="__main__":
    run(int(os.environ.get("APPROVE_PORT","8095")))
