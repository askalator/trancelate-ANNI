from fastapi import FastAPI, HTTPException, Response, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import re, requests, os, csv, pathlib, json
from rapidfuzz import fuzz
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys
from typing import List, Dict, Any
import time
import concurrent.futures as cf

# Import shared functionality
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from libs.trance_common import normalize, json_get, json_post, t, app_version
from libs.trance_common.http import session

# Import robust invariant system
import invariants

# Import language detection
import lang

def normalize_backend_url(u: str) -> str:
    """Normalize backend URL by removing trailing slashes and /translate suffix"""
    if not u: 
        return "http://127.0.0.1:8093"
    u = u.strip().rstrip("/")
    u = re.sub(r"/translate$", "", u, flags=re.IGNORECASE)
    return u

# Normalize backend URL to prevent double /translate
BACKEND_BASE = normalize_backend_url(os.environ.get("MT_BACKEND", "http://127.0.0.1:8093"))
print(f"Guard using BACKEND_BASE={BACKEND_BASE}")

# Log invariant system status
print("Guard Invariants ON: sentinel <|INV:ID:CRC|>")

PROVIDER = os.environ.get("PROVIDER_URL")
TIMEOUT = int(os.environ.get("MT_TIMEOUT", "60"))
TM_SOFT_THRESHOLD = float(os.environ.get("TM_SOFT_THRESHOLD", "0.90"))

# Environment switches for Phase-1 optimizations
MAXW = int(os.environ.get("MAX_WORKERS_GUARD", "3") or "3")
WT = float(os.environ.get("WORKER_TIMEOUT_S", "60") or "60")
USEB = os.environ.get("ENABLE_WORKER_BATCH", "1") not in ("0", "", "false", "False")

# -------- Legacy patterns (kept for compatibility)
PH_RE = re.compile(r"\{\{[^}]+\}\}")
SINGLE_PH_RE = re.compile(r"\{[A-Za-z0-9_]+\}")
TAG_RE = re.compile(r"</?([a-zA-Z0-9]+)[^>]*>")
TAG_FULL_RE = re.compile(r"(</?[A-Za-z0-9]+(?:\s[^>]*?)?>)")
PUNC_KEEP_RE = re.compile(r"[:–—]")  # Doppelpunkt & Gedankenstrich einfrieren
AMPM_RE = re.compile(r"\b([1-9]|1[0-2])\s*(a\.?m\.?|p\.?m\.?)\b", re.I)  # 4pm, 6 p.m., etc.
RANGE_RE = re.compile(r"\b\d{1,4}\s*[–-]\s*\d{1,4}\b")  # 1990–2014
VER_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9\-\+\.#/]{1,})\s?([0-9]{1,3}(?:\.[0-9]+)?)\b")  # Python 3, HTML5, ISO 9001
PURENUM_RE = re.compile(r"\d+(?:[.,]\d+)?")  # 4–6-stellig (Jahr/PLZ)

def _build_session():
    session = requests.Session()
    session.trust_env = False
    session.proxies = {}
    session.headers.update({"Connection": "close"})
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
    """Check backend status using normalized base URL"""
    health_url = f"{BACKEND_BASE}/health"
    ok = False
    try:
        r = SESSION.get(health_url, timeout=3)
        if r.status_code == 200:
            j = r.json()
            ok = bool(j.get("ok", False))
    except Exception:
        ok = False
    return {"backend_url": BACKEND_BASE, "backend_alive": ok}

app = FastAPI()

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
METRICS = {"requests": 0, "errors": 0, "lat_sum": 0.0, "lat_n": 0}
METRICS_STARTED = time.time()

def metrics():
    up = int(time.time() - METRICS_STARTED)
    avg = (METRICS["lat_sum"] / METRICS["lat_n"]) if METRICS["lat_n"] else 0.0
    body = (
        f"anni_uptime_seconds {up}\n"
        f"anni_requests_total {METRICS['requests']}\n"
        f"anni_errors_total {METRICS['errors']}\n"
        f"anni_translate_latency_seconds_avg {avg:.3f}\n"
    )
    return Response(content=body, media_type="text/plain")

# -------- Regexes (keeping existing patterns for compatibility)
PH_RE = re.compile(r"\{\{[^}]+\}\}")
SINGLE_PH_RE = re.compile(r"\{[A-Za-z0-9_]+\}")
TAG_RE = re.compile(r"</?([a-zA-Z0-9]+)[^>]*>")
TAG_FULL_RE = re.compile(r"(</?[A-Za-z0-9]+(?:\s[^>]*?)?>)")
PUNC_KEEP_RE = re.compile(r"[:–—]")  # Doppelpunkt & Gedankenstrich einfrieren
AMPM_RE = re.compile(r"\b([1-9]|1[0-2])\s*(a\.?m\.?|p\.?m\.?)\b", re.I)  # 4pm, 6 p.m., etc.
RANGE_RE = re.compile(r"\b\d{1,4}\s*[–-]\s*\d{1,4}\b")  # 1990–2014
VER_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9\-\+\.#/]{1,})\s?([0-9]{1,3}(?:\.[0-9]+)?)\b")  # Python 3, HTML5, ISO 9001
PURENUM_RE = re.compile(r"\d+(?:[.,]\d+)?")  # 4–6-stellig (Jahr/PLZ)

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

# -------- Phase-1 optimized backend calls
def _call_worker_translate(text, src, tgt, backend):
    """Call single translation with persistent session"""
    s = session()
    r = s.post(f"{backend.rstrip('/')}/translate", 
               json={"source": src, "target": tgt, "text": text}, 
               timeout=WT)
    r.raise_for_status()
    return r.json()["translated_text"]

def _call_worker_batch(texts, src, tgt, backend):
    """Call batch translation with persistent session"""
    s = session()
    r = s.post(f"{backend.rstrip('/')}/translate_batch",
               json={"source": src, "target": tgt, "texts": texts}, 
               timeout=WT)
    if r.status_code >= 400:
        raise Exception(f"batch_failed_{r.status_code}")
    j = r.json()
    return j.get("translated_texts") or []

def translate_via_worker(chunks, src, tgt, backend):
    """Optimized translation with batch fallback and parallel processing"""
    t0 = time.time()
    
    # 1) try batch if enabled and multiple chunks
    if USEB and len(chunks) > 1:
        try:
            outs = _call_worker_batch([c.text for c in chunks], src, tgt, backend)
            if len(outs) == len(chunks):
                for i, o in enumerate(outs):
                    chunks[i].out = o
                return time.time() - t0
        except Exception:
            pass
    
    # 2) fallback: parallel singles with capped workers
    with cf.ThreadPoolExecutor(max_workers=MAXW) as ex:
        futs = []
        for i, c in enumerate(chunks):
            futs.append((i, ex.submit(_call_worker_translate, c.text, src, tgt, backend)))
        for i, f in futs:
            chunks[i].out = f.result()
    
    return time.time() - t0

def translate_one(source_bcp47: str, target_bcp47: str, text: str, max_new_tokens: int | None = None, debug: bool = False) -> tuple[str, dict, dict]:
    """
    Unified translation pipeline for single text.
    
    Args:
        source_bcp47: Source language code (e.g., "de-AT", "en-GB")
        target_bcp47: Target language code (e.g., "en-GB", "zh-CN")
        text: Text to translate
        max_new_tokens: Optional max tokens for generation
        debug: Whether to include debug information
        
    Returns:
        Tuple of (translated_text, checks_dict, debug_dict)
    """
    # Normalize language codes
    n_src = lang.normalize_lang_input(source_bcp47)
    n_tgt = lang.normalize_lang_input(target_bcp47)
    
    # Step 1: Freeze invariants
    text2, mapping = invariants.freeze_invariants(text)
    
    # Step 2: Prepare payload for Worker
    payload = {
        "source": n_src["engine"],
        "target": n_tgt["engine"],
        "text": text2  # Use frozen text, not original
    }
    if max_new_tokens:
        payload["max_new_tokens"] = max_new_tokens
    
    # Step 3: Call Worker
    worker_out_raw = ""
    try:
        response = SESSION.post(f"{BACKEND_BASE}/translate", json=payload, timeout=max(120, TIMEOUT))
        if response.status_code == 200:
            worker_json = response.json()
            worker_out_raw = worker_json.get("translated_text", "")
            worker_out = worker_out_raw
        else:
            # Return error as failed translation
            return "", {"ok": False, "error": f"Worker returned {response.status_code}"}, {}
    except Exception as e:
        # Return error as failed translation
        return "", {"ok": False, "error": str(e)}, {}
    
    # Step 4: Unfreeze invariants
    out, stats = invariants.unfreeze_invariants(worker_out, mapping)
    
    # Step 5: Scrub artifacts
    out = invariants.scrub_artifacts(out)
    
    # Step 6: Unwrap spurious wrappers
    out = invariants.unwrap_spurious_wrappers(out, mapping, text)
    
    # Step 7: Validate invariants
    checks = invariants.validate_invariants(text, out, mapping)
    checks["freeze"] = stats
    
    # Prepare debug information if requested
    debug_info = {}
    if debug:
        # Get normalized text for invariant matching
        normalized_text, _ = invariants.normalize_for_inv_matching(worker_out_raw)
        
        debug_info = {
            "freeze": {
                "text2": text2,
                "mapping_len": len(mapping)
            },
            "worker": {
                "raw": worker_out_raw[:5000] if len(worker_out_raw) > 5000 else worker_out_raw
            },
            "unfreeze": {
                "normalized": normalized_text[:5000] if len(normalized_text) > 5000 else normalized_text,
                "strict_matches": bool(invariants.STRICT.search(worker_out_raw)),
                "simple_matches": bool(invariants.SIMPLE.search(worker_out_raw)),
                "loose_matches": bool(invariants.LOOSE.search(worker_out_raw))
            }
        }
    
    # Log debug info
    html_count = len([m for m in mapping if m["type"] == "html"])
    print(f"DEBUG: len(text)={len(text)}, replaced_total={stats.get('replaced_total', 0)}, engine-langs={n_src['engine']}→{n_tgt['engine']}, html_tags={html_count}")
    
    return out, checks, debug_info

def call_backend(text: str, source: str, target: str, max_new_tokens: int = 512) -> Dict[str, Any]:
    """Call backend translation service (legacy compatibility)"""
    payload = {
        "source": source,
        "target": target,
        "text": text,
        "max_new_tokens": max_new_tokens
    }

    try:
        response = SESSION.post(f"{BACKEND_BASE}/translate", json=payload, timeout=TIMEOUT)
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
    debug: bool = False

class TranslationResponse(BaseModel):
    translated_text: str
    checks: Dict[str, Any]
    debug: Dict[str, Any] = None

from typing import Optional

class BatchItem(BaseModel):
    id: Optional[str] = None
    text: str
    
    class Config:
        extra = "forbid"

class BatchRequest(BaseModel):
    source: str
    target: str
    items: List[Any]  # Can be strings or objects
    max_new_tokens: int = 512
    debug: bool = False
    
    def __init__(self, **data):
        super().__init__(**data)
        # Normalize items: convert strings to {"text": "..."} objects
        normalized_items = []
        for item in self.items:
            if isinstance(item, str):
                normalized_items.append(BatchItem(text=item))
            elif isinstance(item, dict):
                # Handle {"id": "seg-2", "text": "..."} format
                text = item.get("text", "")
                item_id = item.get("id")
                normalized_items.append(BatchItem(text=text, id=item_id))
            else:
                raise ValueError(f"Invalid item format: {item}")
        self.items = normalized_items

class BatchItemResponse(BaseModel):
    index: int
    id: Optional[str] = None
    translated_text: str
    checks: Dict[str, Any]
    debug: Dict[str, Any] = None
    
    class Config:
        extra = "forbid"

class BatchResponse(BaseModel):
    source: str
    target: str
    items: List[BatchItemResponse]
    counts: Dict[str, int]
    provider: str = "anni-guard"

class DetectRequest(BaseModel):
    text: str
    top_k: int = 3

class DetectResponse(BaseModel):
    engine: str
    candidates: List[Dict[str, Any]]
    recommendation: Dict[str, Any]
    accept_language: List[Dict[str, Any]] = []



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
    """Main translation endpoint with robust invariant protection and Phase-1 optimizations"""
    start_time = time.time()
    METRICS["requests"] += 1

    try:
        # Validate source language (Worker doesn't accept "auto")
        if request.source == "auto":
            raise HTTPException(
                status_code=400, 
                detail="Source language 'auto' not supported. Please specify a valid source language."
            )

        # Use unified translation pipeline
        result, checks, debug_info = translate_one(request.source, request.target, request.text, request.max_new_tokens, request.debug)
        
        # Check for strict invariant mode
        if os.environ.get("STRICT_INVARIANTS", "0") == "1" and not checks["ok"]:
            raise HTTPException(
                status_code=422,
                detail="Invariant validation failed",
                headers={"X-Invariant-Checks": str(checks)}
            )

        # Update metrics
        latency = time.time() - start_time
        METRICS["lat_sum"] += latency
        METRICS["lat_n"] += 1

        # Get normalized language codes for headers
        source_norm = lang.normalize_lang_input(request.source)
        target_norm = lang.normalize_lang_input(request.target)
        
        # Create response with language headers
        response_data = TranslationResponse(
            translated_text=result,
            checks=checks
        )
        
        # Add debug information if requested
        if request.debug:
            response_data.debug = debug_info
        
        # Return JSONResponse with custom headers
        return JSONResponse(
            content=response_data.dict(),
            headers={
                "X-Source-Lang": source_norm["bcp47"],
                "X-Source-Engine-Lang": source_norm["engine"],
                "X-Target-Lang": target_norm["bcp47"],
                "X-Target-Engine-Lang": target_norm["engine"]
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        METRICS["errors"] += 1
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/translate_batch", response_model=BatchResponse)
async def translate_batch(request: BatchRequest):
    """Batch translation endpoint with robust invariant protection"""
    start_time = time.time()
    METRICS["requests"] += 1

    try:
        # Validate source language (Worker doesn't accept "auto")
        if request.source == "auto":
            raise HTTPException(
                status_code=400, 
                detail="Source language 'auto' not supported. Please specify a valid source language."
            )

        # Validate items array
        if not request.items or len(request.items) == 0:
            raise HTTPException(
                status_code=400,
                detail="Items array cannot be empty"
            )
        
        if len(request.items) > 200:
            raise HTTPException(
                status_code=400,
                detail="Maximum 200 items allowed per batch"
            )

        # Validate individual items
        for i, item in enumerate(request.items):
            if not item.text or len(item.text.strip()) == 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Item {i}: Text cannot be empty"
                )
            
            if len(item.text) > 2000:
                raise HTTPException(
                    status_code=400,
                    detail=f"Item {i}: Text cannot exceed 2000 characters"
                )

        # Get batch concurrency setting
        batch_concurrency = int(os.environ.get("BATCH_CONCURRENCY", "8"))
        
        # Process items with unified pipeline
        results = []
        if len(request.items) > 1 and batch_concurrency > 1:
            # Parallel processing
            with cf.ThreadPoolExecutor(max_workers=batch_concurrency) as executor:
                futures = []
                for item in request.items:
                    future = executor.submit(translate_one, request.source, request.target, item.text, request.max_new_tokens, request.debug)
                    futures.append(future)
                
                for i, future in enumerate(futures):
                    try:
                        translated_text, checks, debug_info = future.result()
                        batch_item = BatchItemResponse(
                            index=i,
                            id=item.id if hasattr(item, 'id') else None,
                            translated_text=translated_text,
                            checks=checks
                        )
                        if request.debug:
                            batch_item.debug = debug_info
                        results.append(batch_item)
                    except Exception as e:
                        batch_item = BatchItemResponse(
                            index=i,
                            id=item.id if hasattr(item, 'id') else None,
                            translated_text="",
                            checks={"ok": False, "error": str(e)}
                        )
                        results.append(batch_item)
        else:
            # Sequential processing
            for i, item in enumerate(request.items):
                try:
                    translated_text, checks, debug_info = translate_one(request.source, request.target, item.text, request.max_new_tokens, request.debug)
                    batch_item = BatchItemResponse(
                        index=i,
                        id=item.id if hasattr(item, 'id') else None,
                        translated_text=translated_text,
                        checks=checks
                    )
                    if request.debug:
                        batch_item.debug = debug_info
                    results.append(batch_item)
                except Exception as e:
                    batch_item = BatchItemResponse(
                        index=i,
                        id=item.id if hasattr(item, 'id') else None,
                        translated_text="",
                        checks={"ok": False, "error": str(e)}
                    )
                    results.append(batch_item)

        # Calculate counts
        total = len(results)
        ok_count = sum(1 for r in results if r.checks.get("ok", False))
        failed_count = total - ok_count

        # Check for strict invariant mode
        if os.environ.get("STRICT_INVARIANTS", "0") == "1" and failed_count > 0:
            # Return 422 with all results for inspection
            raise HTTPException(
                status_code=422,
                detail="Batch contains items with failed invariant validation",
                headers={"X-Batch-Counts": f"total={total},ok={ok_count},failed={failed_count}"}
            )

        # Update metrics
        latency = time.time() - start_time
        METRICS["lat_sum"] += latency
        METRICS["lat_n"] += 1

        # Log batch processing
        print(f"BATCH: items={total}, {request.source}→{request.target}, {ok_count}/{failed_count} ok/failed, {latency:.2f}s")

        # Get normalized language codes for headers
        source_norm = lang.normalize_lang_input(request.source)
        target_norm = lang.normalize_lang_input(request.target)
        
        # Create response with language headers
        response_data = BatchResponse(
            source=request.source,
            target=request.target,
            items=results,
            counts={
                "total": total,
                "ok": ok_count,
                "failed": failed_count
            }
        )
        
        # Return JSONResponse with custom headers
        return JSONResponse(
            content=response_data.dict(),
            headers={
                "X-Source-Lang": source_norm["bcp47"],
                "X-Source-Engine-Lang": source_norm["engine"],
                "X-Target-Lang": target_norm["bcp47"],
                "X-Target-Engine-Lang": target_norm["engine"]
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        METRICS["errors"] += 1
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/detect", response_model=DetectResponse)
async def detect_language(request: DetectRequest, accept_language: str = Header(None)):
    """Language detection endpoint with BCP-47 canonicalization"""
    start_time = time.time()
    METRICS["requests"] += 1

    try:
        # Validate text length
        if not request.text or len(request.text.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )
        
        if len(request.text) > 4000:
            raise HTTPException(
                status_code=400,
                detail="Text cannot exceed 4000 characters"
            )
        
        # Validate top_k
        if request.top_k < 1 or request.top_k > 5:
            raise HTTPException(
                status_code=400,
                detail="top_k must be between 1 and 5"
            )

        # Parse Accept-Language header if present
        accept_lang_list = []
        accept_lang_codes = []
        if accept_language:
            accept_lang_list = lang.parse_accept_language(accept_language)
            accept_lang_codes = [item["code"] for item in accept_lang_list]
        
        # Detect language with Accept-Language hints
        detection_result = lang.detect_lang(request.text, request.top_k, accept_lang_codes)
        
        # Use recommendation from detection result
        recommendation = detection_result.get("recommendation", {
            "bcp47": "en",
            "from": "fallback"
        })

        # Update metrics
        latency = time.time() - start_time
        METRICS["lat_sum"] += latency
        METRICS["lat_n"] += 1

        return DetectResponse(
            engine=detection_result["engine"],
            candidates=detection_result["candidates"],
            recommendation=recommendation,
            accept_language=accept_lang_list
        )

    except HTTPException:
        raise
    except Exception as e:
        METRICS["errors"] += 1
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/detect")
async def detect_language_get(text: str, top_k: int = 3, accept_language: str = None):
    """Quick language detection endpoint (GET)"""
    # Create a DetectRequest object for validation
    request = DetectRequest(text=text, top_k=top_k)
    
    # Call the POST endpoint logic
    return await detect_language(request, accept_language)

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return metrics()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8091)
