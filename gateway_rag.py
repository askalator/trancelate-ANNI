import os, json, sqlite3, re
from functools import lru_cache
from fastapi import FastAPI, Request, Response
import httpx, numpy as np
from sentence_transformers import SentenceTransformer

UPSTREAM   = os.getenv("UPSTREAM", "http://127.0.0.1:8000")
TENANT_DIR = os.getenv("TENANT_DIR", "tenants/demo")
TOP_K      = int(os.getenv("TOP_K", "16"))
EMB_ID     = os.getenv("EMB_MODEL", "intfloat/multilingual-e5-base")
EMB        = SentenceTransformer(EMB_ID)

app = FastAPI()
SYS = {"role":"system","content":"Antworte ausschließlich in der Sprache des Website-Kontexts, sachlich. Nutze nur den bereitgestellten Kontext; falls Info fehlt, antworte exakt: Nicht im Kontext. Keine Klammer-Übersetzungen, kein Englisch-Beisatz."}

@lru_cache(maxsize=4)
def load_index():
    db = os.path.join(TENANT_DIR, "kb.sqlite")
    con = sqlite3.connect(db)
    rows = con.execute("select c.text, p.url from chunks c join pages p on p.id=c.page_id").fetchall()
    con.close()
    texts = [r[0] for r in rows]; urls = [r[1] for r in rows]
    vecs  = EMB.encode(["passage: " + t for t in texts], normalize_embeddings=True)
    return texts, urls, np.array(vecs, dtype=np.float32)

@lru_cache(maxsize=8)
def load_orgcard():
    p = os.path.join(TENANT_DIR, "orgcard.json")
    return json.load(open(p)) if os.path.isfile(p) else None

def postprocess(s: str) -> str:
    # Entferne Klammer-„Translation“-Anhänge, erhalte Umlaute
    s = re.sub(r"\(\s*(translation|übersetzung)\s*:[^)]*\)", "", s, flags=re.I)
    s = re.sub(r"\s+\n", "\n", s).strip()
    return s or "Nicht im Kontext"

@app.post("/v1/chat/completions")
async def chat(req: Request):
    body = await req.json()
    user_msgs = [m.get("content","") for m in body.get("messages", []) if m.get("role")=="user"]
    query = user_msgs[-1] if user_msgs else ""

    # RAG-Kontext bauen
    texts, urls, vecs = load_index()
    ctx_lines = []
    if len(texts):
        q = EMB.encode(["query: " + query], normalize_embeddings=True)[0]
        sims = (vecs @ q).tolist()
        top_idx = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:TOP_K]
        for j, i in enumerate(top_idx, 1):
            snippet = texts[i].replace("\n", " ")[:800]  # längere Snippets
            ctx_lines.append(f"[{j}] {urls[i]} — {snippet}")
    ctx_block = "\n".join(ctx_lines) if ctx_lines else "(kein Kontext)"

    org = load_orgcard()
    brand_line = ("Marke=" + org.get("brand","") + ". ") if org else ""

    stuffed = (
        brand_line +
        "Nutze AUSSCHLIESSLICH den folgenden Kontext:\n" + ctx_block +
        "\n\nAufgabe: " + (query or "Zusammenfassung der Website")
    )

    msgs = [
        SYS,
        {"role":"user","content": stuffed}
    ]

    body["messages"] = msgs
    body["temperature"] = 0
    body["top_p"] = 1
    body.setdefault("max_tokens", 1024)
    body.setdefault("stop", ["(Translation", "Translation:", "English:", "[EN]"])

    async with httpx.AsyncClient(timeout=180.0) as c:
        r = await c.post(UPSTREAM + "/v1/chat/completions", json=body, headers={"Content-Type":"application/json"})
    try:
        j = r.json()
        if "choices" in j and j["choices"]:
            j["choices"][0]["message"]["content"] = postprocess(j["choices"][0]["message"].get("content",""))
        return Response(content=json.dumps(j, ensure_ascii=False), status_code=r.status_code, media_type="application/json")
    except Exception:
        return Response(content=r.content, status_code=r.status_code, media_type=r.headers.get("content-type","application/json"))
