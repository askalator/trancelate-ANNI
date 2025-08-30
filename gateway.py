import os, json
from fastapi import FastAPI, Request, Response
import httpx

UPSTREAM = os.getenv("UPSTREAM", "http://127.0.0.1:8000")  # dein laufender llama.cpp-Server
app = FastAPI()

SYSTEM_DEFAULT = {
    "role": "system",
    "content": "Antworte auf Deutsch, kurz, sachlich. Bei Übersetzungen: nur Zielsprache, keine Erklärungen."
}

@app.post("/v1/chat/completions")
async def chat(req: Request):
    body = await req.json()
    msgs = body.get("messages", [])
    if not any(m.get("role") == "system" for m in msgs):
        msgs = [SYSTEM_DEFAULT] + msgs
    body["messages"] = msgs
    body.setdefault("temperature", 0.2)
    body.setdefault("top_p", 0.9)
    body.setdefault("max_tokens", 256)

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as c:
        r = await c.post(f"{UPSTREAM}/v1/chat/completions", json=body, headers={"Content-Type":"application/json"})
    return Response(content=r.content, status_code=r.status_code, media_type=r.headers.get("content-type","application/json"))
