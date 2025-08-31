from fastapi import FastAPI, Request
import httpx, os
BACK=os.environ.get("WORKER_URL","http://127.0.0.1:8093").rstrip("/")
app=FastAPI()
@app.get("/health")
async def health():
    async with httpx.AsyncClient(timeout=5) as c:
        r=await c.get(f"{BACK}/health")
    return r.json()
@app.post("/translate")
async def translate(req: Request):
    j=await req.json()
    async with httpx.AsyncClient(timeout=None) as c:
        r=await c.post(f"{BACK}/translate", json=j)
    return r.json()
