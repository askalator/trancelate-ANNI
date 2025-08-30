from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline
import os, threading, collections

try:
    import torch
except Exception:
    torch = None

if torch is not None:
    try:
        torch.set_num_threads(int(os.environ.get("ANNI_TORCH_THREADS","1")))
        torch.set_num_interop_threads(int(os.environ.get("ANNI_TORCH_INTEROP","1")))
    except Exception:
        pass

app = FastAPI()
pipes = {}
PIPE_LOCKS = collections.defaultdict(threading.Lock)
INFER_SEM = threading.Semaphore(int(os.environ.get("ANNI_MAX_CONCURRENCY","1")))

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/ready")
def ready():
    return {"ok": True, "loaded_pipes": sorted(pipes.keys())}

def get_pipe(src, tgt):
    key = f"{src}->{tgt}"
    if key in pipes:
        return pipes[key]
    lock = PIPE_LOCKS[key]
    with lock:
        if key in pipes:
            return pipes[key]
        if (src, tgt) == ("de", "en"):
            model = "Helsinki-NLP/opus-mt-de-en"
        elif (src, tgt) == ("en", "de"):
            model = "Helsinki-NLP/opus-mt-en-de"
        elif (src, tgt) == ("fr", "en"):
            model = "Helsinki-NLP/opus-mt-fr-en"
        elif (src, tgt) == ("en", "fr"):
            model = "Helsinki-NLP/opus-mt-en-fr"
        elif (src, tgt) == ("es", "en"):
            model = "Helsinki-NLP/opus-mt-es-en"
        elif (src, tgt) == ("en", "es"):
            model = "Helsinki-NLP/opus-mt-en-es"
        elif (src, tgt) == ("it", "en"):
            model = "Helsinki-NLP/opus-mt-it-en"
        elif (src, tgt) == ("en", "it"):
            model = "Helsinki-NLP/opus-mt-en-it"
        elif (src, tgt) == ("pt", "en"):
            model = "Helsinki-NLP/opus-mt-ROMANCE-en"
        elif (src, tgt) == ("en", "pt"):
            model = "Helsinki-NLP/opus-mt-tc-big-en-pt"
        elif (src, tgt) == ("nl", "en"):
            model = "Helsinki-NLP/opus-mt-nl-en"
        elif (src, tgt) == ("en", "nl"):
            model = "Helsinki-NLP/opus-mt-en-nl"
        else:
            raise ValueError("unsupported language pair")
        dev = os.environ.get("ANNI_DEVICE","cpu").lower()
        device_arg = {"device": -1} if dev == "cpu" else ({"device": 0} if dev in ("mps","gpu","cuda") else {})
        pipes[key] = pipeline("translation", model=model, **device_arg)
        return pipes[key]

class Req(BaseModel):
    source: str
    target: str
    text: str

@app.post("/translate")
def translate(r: Req):
    pipe = get_pipe(r.source, r.target)
    with INFER_SEM:
        out = pipe(r.text, max_length=256, num_beams=1, do_sample=False)
    return {"translated_text": out[0]["translation_text"]}
