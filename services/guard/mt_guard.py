from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import re, requests, os, csv, pathlib, json
from rapidfuzz import fuzz
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys
from typing import List, Dict, Any
import time

# Import shared functionality
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from libs.trance_common import mask, unmask, normalize, json_get, json_post, check_invariants, t, app_version

BACKEND = os.environ.get("MT_BACKEND","http://127.0.0.1:8090/translate")
PROVIDER = os.environ.get("PROVIDER_URL")
TIMEOUT = int(os.environ.get("MT_TIMEOUT", "60"))
TM_SOFT_THRESHOLD = float(os.environ.get("TM_SOFT_THRESHOLD", "0.90"))

def _build_session():
    session = requests.Session()
    session.trust_env = False
    session.proxies = {}
    session.headers.update({"Connection":"close"})
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

SESSION = _build_session()

def _backend_status():
    # Aus /translate die Basis ableiten
    base = BACKEND.rsplit("/", 1)[0] if BACKEND.endswith("/translate") else BACKEND
    health = f"{base}/health"
    url_for_meta = f"{base}/translate"
    ok = False
    try:
        r = SESSION.get(health, timeout=3)
        if r.status_code == 200:
            j = r.json()
            ok = bool(j.get("ok", False))
    except Exception:
        ok = False
    return {"backend_url": url_for_meta, "backend_alive": ok}

app = FastAPI()
METRICS = {"requests":0,"errors":0,"lat_sum":0.0,"lat_n":0}
METRICS_STARTED = time.time()

def metrics():
    up = int(time.time() - METRICS_STARTED)
    avg = (METRICS["lat_sum"]/METRICS["lat_n"]) if METRICS["lat_n"] else 0.0
    body = (
        f"anni_uptime_seconds {up}\n"
        f"anni_requests_total {METRICS['requests']}\n"
        f"anni_errors_total {METRICS['errors']}\n"
        f"anni_translate_latency_seconds_avg {avg:.3f}\n"
    )
    return Response(content=body, media_type="text/plain")

# -------- Regexes (keeping existing patterns for compatibility)
PH_RE    = re.compile(r"\{\{[^}]+\}\}")
SINGLE_PH_RE = re.compile(r"\{[A-Za-z0-9_]+\}")
TAG_RE   = re.compile(r"</?([a-zA-Z0-9]+)[^>]*>")
TAG_FULL_RE = re.compile(r"(</?[A-Za-z0-9]+(?:\s[^>]*?)?>)")
PUNC_KEEP_RE  = re.compile(r"[:–—]")  # Doppelpunkt & Gedankenstrich einfrieren
AMPM_RE  = re.compile(r"\b([1-9]|1[0-2])\s*(a\.?m\.?|p\.?m\.?)\b", re.I)  # 4pm, 6 p.m., etc.
RANGE_RE = re.compile(r"\b\d{1,4}\s*[–-]\s*\d{1,4}\b")                     # 1990–2014
VER_RE   = re.compile(r"\b([A-Za-z][A-Za-z0-9\-\+\.#/]{1,})\s?([0-9]{1,3}(?:\.[0-9]+)?)\b")  # Python 3, HTML5, ISO 9001
PURENUM_RE = re.compile(r"\d+(?:[.,]\d+)?")                                    # 4–6-stellig (Jahr/PLZ)

# -------- Robust number freeze/unfreeze
NUM_RE = re.compile(
    r'(?<!\w)('
    r'\d(?:[0-9\u00A0\u202F .,])*?\d'          # Zahl mit Trennzeichen/Spaces
    r'(?:[0-9\u00A0\u202F .,]*\d)*'             # weitere Ziffern mit Trennzeichen
    r'(?:\s*[–-]\s*\d(?:[0-9\u00A0\u202F .,])*?\d)*'  # optionaler Bereich 1990–2014 (greedy)
    r')(?=\D|$)'
)

def freeze_numbers(t: str):
    i = 0
    subst = {}
    def repl(m):
        nonlocal i
        key = f'__NUM{i}__'
        subst[key] = m.group(1)
        i += 1
        return key
    return NUM_RE.sub(repl, t), subst

# erkennt __NUM0__, _NUM0__, __NUM0_, NUM0, _NUM0_
NUM_TOKEN_RE = re.compile(r'_? _?  (NUM(\d+))  _? _?', re.X)

def unfreeze_numbers(text: str, table: dict) -> str:
    """
    Setzt NUM-Platzhalter zuverlässig zurück, auch wenn Unterstriche variieren.
    Erwartete Kanon-Keys im table: '__NUM{n}__'
    """
    if not table:
        return text
    
    # Erstelle Mapping von allen möglichen Varianten zu den Kanon-Keys
    variant_map = {}
    for canon_key in table.keys():
        if canon_key.startswith('__NUM') and canon_key.endswith('__'):
            # Extrahiere Nummer
            num_match = re.search(r'__NUM(\d+)__', canon_key)
            if num_match:
                num = num_match.group(1)
                # Erstelle alle möglichen Varianten
                variants = [
                    f'__NUM{num}__',  # Kanon
                    f'_NUM{num}__',   # Variante 1
                    f'__NUM{num}_',   # Variante 2
                    f'_NUM{num}_',    # Variante 3
                    f'NUM{num}',      # Variante 4
                    f'_NUM{num}',     # Variante 5
                ]
                for variant in variants:
                    variant_map[variant] = canon_key
    
    # Ersetze alle Varianten
    for variant, canon_key in variant_map.items():
        if variant in text and canon_key in table:
            text = text.replace(variant, table[canon_key])
    
    return text

def chunk_text(text: str, max_chars: int = 600) -> List[str]:
    """Split text into chunks, preserving sentence boundaries"""
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by sentences first
    sentences = re.split(r'([.!?]+)\s+', text)
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        punct = sentences[i + 1] if i + 1 < len(sentences) else ""
        
        if len(current_chunk + sentence + punct) <= max_chars:
            current_chunk += sentence + punct
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + punct
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def call_backend(text: str, source: str, target: str, max_new_tokens: int = 512) -> Dict[str, Any]:
    """Call backend translation service"""
    payload = {
        "source": source,
        "target": target,
        "text": text,
        "max_new_tokens": max_new_tokens
    }
    
    try:
        response = SESSION.post(BACKEND, json=payload, timeout=TIMEOUT)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Backend returned {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

class TranslationRequest(BaseModel):
    source: str
    target: str
    text: str
    max_new_tokens: int = 512

class TranslationResponse(BaseModel):
    translated_text: str
    checks: Dict[str, Any]

@app.get("/health")
async def health():
    """Health check endpoint"""
    backend_status = _backend_status()
    resp = {
        "ok": True,
        "ready": True,
        "backend_alive": backend_status["backend_alive"],
        "backend_url": backend_status["backend_url"]
    }
    resp.update(app_version())
    return resp

@app.get("/meta")
async def meta():
    """Service metadata"""
    backend_status = _backend_status()
    resp = {
        "service": "ANNI Guard",
        "backend_url": backend_status["backend_url"],
        "backend_alive": backend_status["backend_alive"]
    }
    resp.update(app_version())
    return resp

@app.post("/translate", response_model=TranslationResponse)
async def translate(request: TranslationRequest):
    """Main translation endpoint with invariant protection"""
    start_time = time.time()
    METRICS["requests"] += 1
    
    try:
        # Step 1: Freeze invariants using shared library
        masked_text, spans, table = mask(request.text)
        
        # Step 2: Chunk long texts
        chunks = chunk_text(masked_text, max_chars=600)
        
        # Step 3: Translate chunks
        translated_chunks = []
        for chunk in chunks:
            response = call_backend(chunk, request.source, request.target, request.max_new_tokens)
            if "error" in response:
                METRICS["errors"] += 1
                raise HTTPException(status_code=502, detail=response["error"])
            translated_chunks.append(response.get("translated_text", chunk))
        
        # Step 4: Unfreeze invariants
        result = "".join(translated_chunks)
        result = unmask(result, spans, table)
        
        # Step 5: Validate invariants using shared library
        checks = check_invariants(request.text, result)
        checks["ok"] = all([
            checks["ph_ok"],
            checks["html_ok"], 
            checks["num_ok"],
            checks["paren_ok"]
        ])
        
        # Update metrics
        latency = time.time() - start_time
        METRICS["lat_sum"] += latency
        METRICS["lat_n"] += 1
        
        return TranslationResponse(
            translated_text=result,
            checks=checks
        )
        
    except HTTPException:
        raise
    except Exception as e:
        METRICS["errors"] += 1
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return metrics()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8091)
