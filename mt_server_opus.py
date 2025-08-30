from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline
import threading

app = FastAPI()
lock = threading.Lock()
PIPES = {}

MODELS = {
    ("en","de"): ("translation_en_to_de", "Helsinki-NLP/opus-mt-en-de"),
    ("de","en"): ("translation_de_to_en", "Helsinki-NLP/opus-mt-de-en"),
}

def get_pipe(src:str, tgt:str):
    key = (src, tgt)
    if key not in MODELS:
        raise HTTPException(status_code=501, detail=f"lang pair {src}->{tgt} not supported in OPUS backend")
    if key in PIPES:
        return PIPES[key]
    task, model = MODELS[key]
    with lock:
        if key not in PIPES:
            PIPES[key] = pipeline(task, model=model, device=-1)  # CPU ok; Torch ist vorhanden
    return PIPES[key]

class Payload(BaseModel):
    source: str
    target: str
    text: str

@app.post("/translate")
def translate(p: Payload):
    pipe = get_pipe(p.source, p.target)
    out = pipe(p.text, clean_up_tokenization_spaces=True, truncation=True, max_length=1024)
    txt = out[0]["translation_text"]
    return {"translated_text": txt}

from starlette.responses import Response

@app.options("/translate")
def _cors_preflight_translate():
    return Response(status_code=204, headers={"Access-Control-Allow-Origin":"*","Access-Control-Allow-Methods":"POST, OPTIONS","Access-Control-Allow-Headers":"content-type, x-anni-key, X-API-Key","Access-Control-Max-Age":"86400"})
