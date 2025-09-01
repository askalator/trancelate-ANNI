import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from guard.config import settings
from guard.locales import load_locales_list, map_locales_with_engine
from guard.styles_de import apply_style_de_safe
from guard.styles_romance import apply_style_romance_safe
from guard.capabilities import compute_capabilities
from guard.resilience import should_degrade
from guard.cache import LRUCache, build_key, style_signature, glossary_signature, cache as _CACHE
from guard.glossary import load_terms, freeze_glossary, unfreeze_glossary, to_safe_tokens, from_safe_tokens

from fastapi import FastAPI, HTTPException, Response, Header
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import re, requests, os, csv, pathlib, json
import json as _json
from rapidfuzz import fuzz
import unicodedata as _ud
import re as _re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Dict, Any, Optional
import time
import concurrent.futures as cf

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
BACKEND_BASE = normalize_backend_url(settings.MT_BACKEND)
print(f"Guard using BACKEND_BASE={BACKEND_BASE}")

# Locales configuration
_LOCALES_PATH = settings.LOCALES_PUBLIC_PATH or os.path.join(os.path.dirname(__file__), "..", "..", "config", "locales-public.json")

def _load_locales_list() -> list[str]:
    return load_locales_list(settings.LOCALES_PUBLIC_PATH, settings.LOCALES_EXTRA, settings.LOCALES_DISABLE)

# Log invariant system status
print("Guard Invariants ON: sentinel <|INV:ID:CRC|>")

PROVIDER = os.environ.get("PROVIDER_URL")
TIMEOUT = settings.MT_TIMEOUT
TM_SOFT_THRESHOLD = float(os.environ.get("TM_SOFT_THRESHOLD", "0.90"))

# Environment switches for Phase-1 optimizations
MAXW = settings.MAX_WORKERS_GUARD
WT = settings.WORKER_TIMEOUT_S
USEB = settings.ENABLE_WORKER_BATCH

# Strict invariants configuration
STRICT = os.environ.get("STRICT_INVARIANTS", "0") in ("1","true","True")
STRICT_EXCL = {s.strip() for s in os.environ.get("STRICT_INVARIANTS_EXCLUDE","").split(",") if s.strip()}

# Style configuration
STYLE_ENABLE = settings.ENABLE_STYLE_FILTER
STYLE_DEFAULT_ADDRESS = settings.STYLE_DEFAULT_ADDRESS.lower()
STYLE_DEFAULT_GENDER = settings.STYLE_DEFAULT_GENDER.lower()
STYLE_LANGS = {s.strip() for s in settings.STYLE_LANGS.split(",") if s.strip()}
STYLE_KEEP_TERMS = {s.strip() for s in settings.STYLE_KEEP_TERMS.split(",") if s.strip()}

def _strict_enforced_for(target_bcp47: str, target_engine: str) -> bool:
    if not STRICT:
        return False
    code = (target_bcp47 or "").strip()
    eng  = (target_engine or "").strip()
    base = code.split("-")[0] if code else ""
    # Exkludiere, wenn exakter BCP-47, Basis (z. B. "my") oder Engine-Code in STRICT_EXCL
    return not ({code, base, eng} & STRICT_EXCL)

def _is_de(bcp47: str, engine: str) -> bool:
    try:
        b = (bcp47 or "").lower()
        e = (engine or "").lower()
        return b.startswith("de") or e == "de"
    except Exception:
        return False

# Style-Funktionen sind jetzt in guard.styles_de ausgelagert

# Cache-Initialisierung
if settings.CACHE_ENABLE:
    from guard import cache as _cache_mod
    _cache_mod.cache = LRUCache(maxsize=settings.CACHE_MAX, ttl=settings.CACHE_TTL)
    _CACHE = _cache_mod.cache
else:
    _CACHE = None

# Glossary-Terms laden (global einmal)
_GLOSSARY_TERMS = load_terms(settings.GLOSSARY_PATH, settings.GLOSSARY_TERMS) if settings.GLOSSARY_ENABLE else []

def _collect_glossary_terms(req_glossary, item_glossary):
    terms = []
    if req_glossary and req_glossary.terms:
        for t in req_glossary.terms:
            terms.append({"term": t.term, "canonical": (t.canonical or t.term), "langs": (t.langs or ["*"]), "regex": "1" if t.regex else "0"})
    if item_glossary and item_glossary.terms:
        for t in item_glossary.terms:
            terms.append({"term": t.term, "canonical": (t.canonical or t.term), "langs": (t.langs or ["*"]), "regex": "1" if t.regex else "0"})
    # Server-global nur wenn explizit aktiviert
    try:
        from guard.config import settings
        if settings.GLOSSARY_ENABLE:
            from guard.glossary import load_terms as _lt
            terms += _lt(settings.GLOSSARY_PATH, settings.GLOSSARY_TERMS)
    except Exception:
        pass
    # Dedupe
    seen = set()
    out = []
    for x in terms:
        k = (x["canonical"], tuple(sorted(x["langs"])), x["regex"])
        if k in seen: continue
        seen.add(k)
        out.append(x)
    return out

# Hilfsfunktion: stabiler Freeze für Key (STANDARD Sentinel)
def _freeze_std_for_key(text: str):
    fstd, _ = invariants.freeze_invariants(text)
    return fstd






def _norm_target_pair(target_bcp47: str):
    try:
        nt = lang.normalize_lang_input(target_bcp47)
        return nt.get("bcp47") or target_bcp47, nt.get("engine") or (target_bcp47.split("-")[0] if target_bcp47 else "")
    except Exception:
        # Fallback: wenigstens Basiscode zurückgeben
        base = target_bcp47.split("-")[0] if target_bcp47 else ""
        return target_bcp47, base

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

# Static files support
PUBLIC_DIR = settings.PUBLIC_DIR or os.path.join(os.path.dirname(__file__), "..", "..", "public")
if os.path.isdir(PUBLIC_DIR):
    app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")

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
METRICS_LBL = {
    "spans_only_total": {},           # key: tgt_bcp47
    "degrade_total": {},              # key: reason
    "glossary_missing_total": {},     # key: tgt_bcp47
    "glossary_replaced_total": {},    # key: tgt_bcp47
}
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
    # labeled counters
    def line(name, labels: dict, value: int):
        kv = ",".join(f'{k}="{v}"' for k,v in labels.items())
        return f"{name}{{{kv}}} {value}\n"
    for tgt, v in METRICS_LBL["spans_only_total"].items():
        body += line("anni_spans_only_total", {"target": tgt}, v)
    for reason, v in METRICS_LBL["degrade_total"].items():
        body += line("anni_degrade_total", {"reason": reason}, v)
    for tgt, v in METRICS_LBL["glossary_missing_total"].items():
        body += line("anni_glossary_missing_total", {"target": tgt}, v)
    for tgt, v in METRICS_LBL["glossary_replaced_total"].items():
        body += line("anni_glossary_replaced_total", {"target": tgt}, v)
    return Response(content=body, media_type="text/plain")

def _inc(d: dict, key: str, n: int = 1):
    d[key] = d.get(key, 0) + n

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

# === HTML helper utils (fallback support) ===
import re as _re

def _strip_all_tags(text: str) -> str:
    return _re.sub(r"<[^>]+>", "", text or "")

def _is_open_tag(raw: str) -> bool:
    return bool(_re.match(r"^<[^/][^>]*>$", raw or ""))

def _is_close_tag(raw: str) -> bool:
    return bool(_re.match(r"^</[^>]+>$", raw or ""))

def _outer_html_wrappers(mapping: list[dict]) -> tuple[str, str]:
    opens  = [m.get("raw","") for m in mapping if m.get("type")=="html" and _is_open_tag(m.get("raw",""))]
    closes = [m.get("raw","") for m in mapping if m.get("type")=="html" and _is_close_tag(m.get("raw",""))]
    open_tag  = opens[0] if opens else ""
    close_tag = closes[-1] if closes else ""
    return open_tag, close_tag

def force_freeze_html_only(text: str) -> tuple[str, list[dict]]:
    """
    Notnagel: nur äußere HTML-Wrapper einfrieren, falls das reguläre Freezing fehlschlug.
    Liefert (text2, mapping) kompatibel zu invariants.unfreeze_invariants.
    """
    # finde erstes öffnendes und letztes schließendes Tag
    tags = list(_re.finditer(r"(</?[A-Za-z][^>]*>)", text or ""))
    if len(tags) < 2:
        return text, []
    first = tags[0]; last = tags[-1]
    open_tag  = first.group(1); close_tag = last.group(1)
    try:
        from invariants import make_crc
        crc0 = make_crc(open_tag); crc1 = make_crc(close_tag)
    except Exception:
        import hashlib
        crc0 = hashlib.sha1(open_tag.encode("utf-8")).hexdigest()[:6].upper()
        crc1 = hashlib.sha1(close_tag.encode("utf-8")).hexdigest()[:6].upper()
    ph0 = f"<|INV:0:{crc0}|>"
    ph1 = f"<|INV:1:{crc1}|>"
    text2 = text[:first.start()] + ph0 + text[first.end():last.start()] + ph1 + text[last.end():]
    mapping = [
        {"id":0,"crc":crc0,"raw":open_tag,"type":"html"},
        {"id":1,"crc":crc1,"raw":close_tag,"type":"html"},
    ]
    return text2, mapping

import re as _re, os as _os, unicodedata as _ud

_STD_SENT = _re.compile(r"<\|INV:(\d{1,4}):([0-9A-Fa-f]{4,8})\|>")
_SAFE_STRICT = _re.compile(r"\[#INV:(\d{1,4})#\]")
_SAFE_LOOSE  = _re.compile(r"(?:\[?#?\s*)?I\s*N\s*V\s*[:\-_ ]\s*(\d{1,4})(?:\s*#?\]?)?", _re.IGNORECASE)
_SPLIT_TAGS = _re.compile(r"(</?[A-Za-z][^>]*>)")

def _to_safe_sentinels(std_text: str) -> str:
    return _STD_SENT.sub(lambda m: f"[#INV:{m.group(1)}#]", std_text or "")

def _rehydrate_safe_to_std(s: str, mapping: list[dict]) -> str:
    if not mapping:
        return s or ""
    s0 = (s or "").translate({0x200B:None,0x200C:None,0x200D:None,0x2060:None,0xFEFF:None})
    s0 = _ud.normalize("NFKC", s0)
    def crc_for(i: int):
        if 0 <= i < len(mapping):
            c = (mapping[i].get("crc") or "").upper()
            if c: return c
        return "000000"
    def repl_strict(m):
        i = int(m.group(1))
        return f"<|INV:{i}:{crc_for(i)}|>"
    s1 = _SAFE_STRICT.sub(repl_strict, s0)
    def repl_loose(m):
        try: i = int(m.group(1))
        except: return m.group(0)
        return f"<|INV:{i}:{crc_for(i)}|>"
    s2 = _SAFE_LOOSE.sub(repl_loose, s1)
    return s2

def _split_html(text: str):
    return _SPLIT_TAGS.split(text or "")

def _to_safe_placeholders(std_text: str) -> str:
    return _STD_SENT.sub(lambda m: f"[[INV:{m.group(1)}]]", std_text or "")

def _from_safe_placeholders(s: str, mapping: list[dict]) -> str:
    if not mapping: return s or ""
    def repl(m):
        i = int(m.group(1))
        return mapping[i]["raw"] if 0 <= i < len(mapping) else m.group(0)
    return _re.sub(r"\[\[INV:(\d{1,4})\]\]", repl, s or "")

# Splitter: macht aus "foo <|INV:0:AAAAAA|> bar" -> [("T","foo "),("I",0),("T"," bar")]
def _split_by_std_inv(std_text: str):
    parts = []
    last = 0
    for m in _STD_SENT.finditer(std_text or ""):
        if m.start() > last:
            parts.append(("T", (std_text[last:m.start()])))
        parts.append(("I", int(m.group(1))))
        last = m.end()
    if last < len(std_text or ""):
        parts.append(("T", std_text[last:]))
    return parts

# Sehr kurze/„rauschige" Segmente (nur Whitespace/Punktuation) einfach durchlassen.
_PUNCT_ONLY = _re.compile(r"^\s*$|^[\s\.\,\!\?\:\;–—\-•··‧·／/\\\(\)\[\]\{\}…~]+$")

def _is_noise_segment(s: str) -> bool:
    return bool(_PUNCT_ONLY.match(s or "")) or len((s or "").strip()) <= 1

# Kleines Cache, um gleiche Segmente nicht mehrfach zu übersetzen
class _SpanCache:
    def __init__(self): self.d = {}
    def get(self, k):   return self.d.get(k)
    def set(self, k, v): self.d[k] = v

def _spans_only_translate(n_src, n_tgt, text: str, max_new_tokens, call_worker, invariants, keep_terms: list[str] | None = None):
    # 1) HTML in [text, <tag>, text, ...] zerlegen
    import re as _re
    _SPLIT_TAGS = _re.compile(r"(</?[A-Za-z][^>]*>)")
    chunks = _SPLIT_TAGS.split(text or "")
    out_chunks = []
    cache = _SpanCache()
    # --- Leak/Pivot Konfiguration ---
    _pivot_langs = {s.strip() for s in (_os.environ.get("PIVOT_LANGS", "km,lo,my").split(",")) if s.strip()}
    _pivot_mid  = _os.environ.get("PIVOT_MID_LANG", "en").strip() or "en"
    _leak_max   = float(_os.environ.get("LEAK_LATIN_MAX", "0.15") or "0.15")
    _LATIN_RE   = _re.compile(r"[A-Za-z]")

    def _latin_leak_ratio(s: str) -> float:
        # Zähle nur Buchstaben (E-Mail/URL/Keep-Terms sind bereits als Invarianten raus)
        letters = [ch for ch in (s or "") if ch.isalpha()]
        if not letters: 
            return 0.0
        return len([ch for ch in letters if _LATIN_RE.match(ch)]) / len(letters)

    def _pivot_translate(src_engine: str, mid_engine: str, tgt_engine: str, seg: str):
        # First translation: src -> mid
        try:
            t1 = _call_worker_translate(seg, src_engine, mid_engine, BACKEND_BASE)
        except Exception:
            t1 = seg  # fallback to original if first translation fails
        
        # Second translation: mid -> tgt
        try:
            t2 = _call_worker_translate(t1, mid_engine, tgt_engine, BACKEND_BASE)
            return t2
        except Exception:
            return t1  # fallback to intermediate result if second translation fails

    # Keep-Terms auf den gesamten Text anwenden, bevor wir in Chunks aufteilen
    if keep_terms:
        # Erstelle eine temporäre Mapping für Keep-Terms
        temp_mapping = []
        temp_text = text
        
        # Finde die nächste verfügbare ID
        next_id = 0
        
        for term in keep_terms:
            if not term or term not in temp_text:
                continue
                
            # Erstelle einen neuen Invariant für diesen Keep-Term
            crc = invariants.make_crc(term)
            sentinel = f"<|INV:{next_id}:{crc}|>"
            
            # Ersetze den Term mit dem Sentinel
            temp_text = temp_text.replace(term, sentinel)
            
            # Füge zur temporären Mapping hinzu
            temp_mapping.append({
                "id": next_id,
                "crc": crc,
                "raw": term,
                "type": "keep_term"
            })
            
            next_id += 1
        
        # Verwende den modifizierten Text für die weitere Verarbeitung
        text = temp_text

    for i, chunk in enumerate(chunks):
        # Tags unverändert übernehmen
        if i % 2 == 1 and chunk.startswith("<"):
            out_chunks.append(chunk)
            continue

        # Leere Text-Abschnitte durchlassen
        if not (chunk or "").strip():
            out_chunks.append(chunk)
            continue

        # 2) Sichtbaren Text invarianten-sicher einfrieren (non-HTML)
        frozen, mapping = invariants.freeze_invariants(chunk)

        # 3) In (Text|Invariant)-Teile splitten
        parts = _split_by_std_inv(frozen)

        # 4) Nur "T"-Segmente übersetzen; "I" wird aus mapping eingefügt
        out_parts = []
        for kind, val in parts:
            if kind == "I":
                # val ist die id im mapping
                raw = mapping[val]["raw"] if 0 <= val < len(mapping) else ""
                out_parts.append(raw)
                continue

            seg = val or ""
            if _is_noise_segment(seg):
                out_parts.append(seg)
                continue

            # Cache verwenden
            cached = cache.get(seg)
            if cached is None:
                payload = {"source": n_src["engine"], "target": n_tgt["engine"], "text": seg}
                if max_new_tokens: payload["max_new_tokens"] = max_new_tokens
                
                # Call worker using the existing worker infrastructure
                try:
                    response = SESSION.post(f"{BACKEND_BASE}/translate", json=payload, timeout=max(120, TIMEOUT))
                    if response.status_code == 200:
                        w = response.json()
                    else:
                        w = {"translated_text": ""}
                except Exception:
                    w = {"translated_text": ""}
                
                cached = (w.get("translated_text","") or "")
                cached = invariants.scrub_artifacts(cached)

                # --- Anti-Loop-Guard: repetitiven/aufgeblasenen Output abfangen ---
                import re as _re
                def _is_bad_repetition(s: str) -> bool:
                    if not s or len(s) < 16: 
                        return False
                    # 1) Zeichen-Diversität sehr gering
                    if (len(set(s)) / len(s)) < 0.12:
                        return True
                    # 2) Kurzes Muster (1–4 Zeichen) sehr oft wiederholt
                    for n in (1,2,3,4):
                        unit = s[:n]
                        if unit and unit * max(8, len(s)//max(1,n)) in (unit * ((len(s)//n)+8)):
                            # grob: viele Wiederholungen eines Mikro-Patterns
                            return True
                    # 3) Token-Dominanz
                    toks = _re.findall(r'\w+', s)
                    if len(toks) >= 10:
                        from collections import Counter
                        top = Counter(toks).most_common(1)[0][1] / len(toks)
                        if top > 0.65:
                            return True
                    # 4) Überlänge relativ zur Quelle
                    if len(s) > (len(seg) * 6 + 64):
                        return True
                    return False

                if _is_bad_repetition(cached):
                    # Fail-soft: lieber Quellspan beibehalten als Spam ausgeben
                    cached = seg
                    # optional: markiere im Check/Fallback (falls du ein checks-dict hier hast)
                    # (wir setzen lediglich den Text; Checks bleiben später grün wegen Preserves)

                cache.set(seg, cached)

            # --- Latin-Leak-Detektor + Pivot-Fallback ---
            if (n_tgt["engine"] in _pivot_langs) and (len(seg.strip()) >= 4):
                leak = _latin_leak_ratio(cached)
                if leak > _leak_max:
                    cached2 = _pivot_translate(n_src["engine"], _pivot_mid, n_tgt["engine"], seg)
                    cached2 = invariants.scrub_artifacts(cached2)
                    if _latin_leak_ratio(cached2) < leak:
                        cached = cached2
                        cache.set(seg, cached2)
            out_parts.append(cached)

        rendered = "".join(out_parts)
        # 5) Letzter Feinschliff für Wrapper/Artefakte bezogen auf das span
        rendered = invariants.unwrap_spurious_wrappers(rendered, mapping, chunk)
        out_chunks.append(rendered)

    out = "".join(out_chunks)

    # 6) Gesamtvalidierung (original HTML + invarianten)
    full_frozen, full_map = invariants.freeze_invariants(text)
    
    # Keep-Terms-Mapping zur finalen Validierung hinzufügen
    if keep_terms and 'temp_mapping' in locals():
        full_map.extend(temp_mapping)
    
    checks = invariants.validate_invariants(text, out, full_map)
    checks["fallback_used"] = "spans_only_text_segments"
    
    # Create debug info for spans-only mode
    debug_info = {
        "spans_only_mode": True,
        "fallback_used": "spans_only_text_segments",
        "chunks_count": len(chunks),
        "html_chunks": [i for i, c in enumerate(chunks) if i % 2 == 1 and c.startswith("<")],
        "text_chunks": [i for i, c in enumerate(chunks) if i % 2 == 0 and c.strip()]
    }
    
    return out, checks, debug_info

def _invariant_interleave_translate(n_src, n_tgt, text: str, max_new_tokens, call_worker, invariants):
    # Reuse helpers from spans-only:
    #  - _split_by_std_inv(std_text)
    #  - _is_noise_segment(s)
    #  - _SpanCache
    cache = _SpanCache()

    # Pivot/Leak-Heuristik begrenzt auch hier verfügbar (gleich wie in Spans-only)
    _pivot_langs = {s.strip() for s in (_os.environ.get("PIVOT_LANGS", "km,lo,my").split(",")) if s.strip()}
    _pivot_mid  = _os.environ.get("PIVOT_MID_LANG", "en").strip() or "en"
    _leak_max   = float(_os.environ.get("LEAK_LATIN_MAX", "0.15") or "0.15")
    _LATIN_RE   = _re.compile(r"[A-Za-z]")

    def _latin_leak_ratio(s: str) -> float:
        letters = [ch for ch in (s or "") if ch.isalpha()]
        if not letters: return 0.0
        return len([ch for ch in letters if _LATIN_RE.match(ch)]) / len(letters)

    def _pivot_translate(src_engine: str, mid_engine: str, tgt_engine: str, seg: str):
        # First translation: src -> mid
        try:
            t1 = _call_worker_translate(seg, src_engine, mid_engine, BACKEND_BASE)
        except Exception:
            t1 = seg  # fallback to original if first translation fails
        
        # Second translation: mid -> tgt
        try:
            t2 = _call_worker_translate(t1, mid_engine, tgt_engine, BACKEND_BASE)
            return t2
        except Exception:
            return t1  # fallback to intermediate result if second translation fails

    # 1) Invarianten einfrieren (ohne HTML-Splitting, kompletter String)
    frozen, mapping = invariants.freeze_invariants(text)

    # 2) In (T|I)-Teile splitten
    parts = _split_by_std_inv(frozen)

    out_parts = []
    for kind, val in parts:
        if kind == "I":
            raw = mapping[val]["raw"] if 0 <= val < len(mapping) else ""
            out_parts.append(raw)
            continue

        seg = val or ""
        if _is_noise_segment(seg):
            out_parts.append(seg)
            continue

        cached = cache.get(seg)
        if cached is None:
            payload = {"source": n_src["engine"], "target": n_tgt["engine"], "text": seg}
            if max_new_tokens: payload["max_new_tokens"] = max_new_tokens
            w = call_worker(payload)
            cached = (w.get("translated_text","") or "")
            cached = invariants.scrub_artifacts(cached)

            # Anti-Loop (wie in Spans-only)
            def _is_bad_repetition(s: str) -> bool:
                if not s or len(s) < 16: return False
                if (len(set(s)) / len(s)) < 0.12: return True
                for n in (1,2,3,4):
                    unit = s[:n]
                    if unit and s.count(unit) * n > max(len(s)*0.65, 16): return True
                if len(s) > (len(seg) * 6 + 64): return True
                return False
            if _is_bad_repetition(cached):
                cached = seg

            cache.set(seg, cached)

        # Pivot bei starken Latin-Leaks (für Non-Latin-Ziele)
        if (n_tgt["engine"] in _pivot_langs) and (len(seg.strip()) >= 4):
            leak = _latin_leak_ratio(cached)
            if leak > _leak_max:
                cached2 = _pivot_translate(n_src["engine"], _pivot_mid, n_tgt["engine"], seg)
                cached2 = invariants.scrub_artifacts(cached2)
                def _llr(x): 
                    letters = [ch for ch in (x or "") if ch.isalpha()]
                    return 0.0 if not letters else len([ch for ch in letters if _LATIN_RE.match(ch)]) / len(letters)
                if _llr(cached2) < leak:
                    cached = cached2
                    cache.set(seg, cached2)

        out_parts.append(cached)

    out = "".join(out_parts)

    # 3) Validierung gegen das Original
    full_frozen, full_map = invariants.freeze_invariants(text)
    checks = invariants.validate_invariants(text, out, full_map)
    checks["fallback_used"] = "invariant_interleave"
    return out, checks

def _freeze_visible(text: str):
    """
    Friert alle non-HTML Invarianten im sichtbaren Text ein.
    Wir verwenden invariants.freeze_invariants, da text keine HTML-Tags mehr enthält.
    """
    return invariants.freeze_invariants(text)

def _validate_core(out: str, mapping: list[dict]) -> dict:
    # Reuse invariants.validate_invariants, aber original=out (da wir nur non-HTML hatten)
    return invariants.validate_invariants(out, out, mapping)

# Pydantic models for API requests
class Context(BaseModel):
    keep_terms: List[str] = []
    formatting: Optional[dict] = None
    page_type: Optional[str] = None
    domain: Optional[str] = None

class StyleSpec(BaseModel):
    address: str | None = Field(default=None, description="du|sie|divers|auto")
    gender: str | None = Field(default=None, description="none|colon|star|innen")
    keep_terms: list[str] | None = None

class GlossaryItem(BaseModel):
    term: str
    canonical: str | None = None
    langs: list[str] | None = None
    regex: bool = False

class GlossarySpec(BaseModel):
    terms: list[GlossaryItem] = []

def translate_one(source_bcp47: str, target_bcp47: str, text: str, max_new_tokens: int | None = None, debug: bool = False, keep_terms: list[str] | None = None, request_style: StyleSpec | None = None, req_glossary: GlossarySpec | None = None, item_glossary: GlossarySpec | None = None) -> tuple[str, dict, dict]:
    """
    Unified translation pipeline for single text with enhanced HTML-only fallback v2.
    
    Args:
        source_bcp47: Source language code (e.g., "de-AT", "en-GB")
        target_bcp47: Target language code (e.g., "en-GB", "zh-CN")
        text: Text to translate
        max_new_tokens: Optional max tokens for generation
        debug: Whether to include debug information
        
    Returns:
        Tuple of (translated_text, checks_dict, debug_dict)
    """
    # Defensive initialization
    debug_info: dict = {}
    final_out: str | None = None
    final_checks: dict = {}
    worker_out: str | None = None
    
    # Normalize language codes
    n_src = lang.normalize_lang_input(source_bcp47)
    n_tgt = lang.normalize_lang_input(target_bcp47)
    
    # Style-Signatur wie bisher ermittelt (nutze deine existierenden Variablen/Default-Logik):
    s_addr = None
    s_gender = None
    if 'request_style' in globals() and request_style:
        s_addr = (request_style.address or settings.STYLE_DEFAULT_ADDRESS) if hasattr(request_style,'address') else settings.STYLE_DEFAULT_ADDRESS
        s_gender = (request_style.gender  or settings.STYLE_DEFAULT_GENDER)  if hasattr(request_style,'gender')  else settings.STYLE_DEFAULT_GENDER
    else:
        s_addr = settings.STYLE_DEFAULT_ADDRESS
        s_gender = settings.STYLE_DEFAULT_GENDER

    # Glossary-Terms sammeln und Freeze
    glossary_terms = _collect_glossary_terms(req_glossary, item_glossary)
    g_mapping = []
    gstats = {}
    if glossary_terms:
        text_for_gloss, g_mapping = freeze_glossary(text, n_tgt["engine"], glossary_terms)
    else:
        text_for_gloss = text

    # Cache-Signatur inkl. Glossary
    s_addr = settings.STYLE_DEFAULT_ADDRESS
    s_gender = settings.STYLE_DEFAULT_GENDER
    cache_sig = style_signature(s_addr, s_gender) + ";" + glossary_signature(glossary_terms)
    cache_key = None
    cache_hit = False
    # CACHE: Schlüssel auf Basis von text_for_gloss (nicht raw text)
    if settings.CACHE_ENABLE and _CACHE is not None:
        fstd_for_key = _freeze_std_for_key(text_for_gloss)
        cache_key = build_key(n_src["engine"], n_tgt["engine"], fstd_for_key, cache_sig)
        citem = _CACHE.get(cache_key)
        if citem:
            final_out = citem.get("translated_text","")
            final_checks = citem.get("checks",{})
            final_checks["cache_used"] = "hit"
            if debug:
                debug_info["cache_key"] = cache_key
                debug_info["cache"] = "hit"
            # KEIN return hier! Danach normal weiter zum Metrics/Return-Block.
    
    # -------- SAFE MODE: Force Spans-Only per ENV --------
    tgt_bcp = target_bcp47
    tgt_eng = n_tgt["engine"]
    force_spans = (tgt_bcp in settings.SPANS_ONLY_FORCE_BCP47) or (tgt_eng in settings.SPANS_ONLY_FORCE_ENGINES)
    if force_spans:
        spans_input = text
        # Falls Glossary aktiv ist: in Safe-Tokens hüllen, damit es nicht kaputtgeht
        g_mapping = None
        if req_glossary or item_glossary:
            try:
                spans_input, g_mapping = freeze_glossary(spans_input, n_tgt["engine"], glossary_terms)
            except Exception:
                g_mapping = None
        # invariants freeze
        text2, mapping = invariants.freeze_invariants(spans_input)
        # reiner spans-only Lauf
        out_spans, checks_spans, debug_spans = _spans_only_translate(n_src, n_tgt, text2, max_new_tokens, _call_worker_translate, invariants, keep_terms)
        # invariants unfreeze
        out_spans, _stats_inv = invariants.unfreeze_invariants(out_spans, mapping)
        # glossary unfreeze (tolerant)
        if g_mapping:
            out_spans, gstats = unfreeze_glossary(out_spans, g_mapping)
            checks_spans["glossary"] = gstats
        checks_spans["fallback_used"] = "force_spans_only"
        final_out, final_checks = out_spans, checks_spans
        # Debug-Header freundlich setzen
        if debug:
            debug_info.setdefault("xhdr", {})["X-Forced-Spans"] = "1"
        # Gemeinsamer Return-Block am Ende (keine weiteren Worker/Aktionen)
        # -> springe ans Funktionsende: (Metrics/Headers greifen weiter unten)
    # -------- Ende SAFE MODE Block --------
    
    # Invariants auf text_for_gloss:
    text2, mapping = invariants.freeze_invariants(text_for_gloss)
    
    # Keep-Terms injizieren falls vorhanden
    if keep_terms:
        text2, mapping = invariants._freeze_keep_terms_into(text2, mapping, keep_terms)
    
    # ASSERT: Check if frozen text contains sentinels when HTML is present
    html_mappings = [m for m in mapping if m.get("type") == "html"]
    if html_mappings and "<|INV:" not in text2:
        print(f"ERROR: freeze assert failed; sending forced html-only sentinels")
        text2, mapping = force_freeze_html_only(text)
    
    # Convert to safe sentinels for worker transport
    text2_safe = _to_safe_sentinels(text2)
    
    # Log translation info
    html_count = len(html_mappings)
    print(f"INFO: translate_one: src={source_bcp47}/{n_src['engine']} → tgt={target_bcp47}/{n_tgt['engine']}, mapped_html={html_count}")
    
    # Step 2: Prepare payload for Worker (ALWAYS use safe sentinels)
    payload = {
        "source": n_src["engine"],
        "target": n_tgt["engine"],
        "text": text2_safe  # Use safe sentinels for worker transport
    }
    if max_new_tokens:
        payload["max_new_tokens"] = max_new_tokens
    
    # Step 3: Call Worker
    worker_out_raw = ""
    try:
        response = SESSION.post(f"{BACKEND_BASE}/translate", json=payload, timeout=max(120, TIMEOUT))
        if response.status_code == 200:
            worker_json = response.json()
            worker_out_raw = (worker_json.get("translated_text", "") or "")
            # Rehydrate safe sentinels back to standard format
            worker_out = _rehydrate_safe_to_std(worker_out_raw, mapping)
        else:
            # Return error as failed translation
            return "", {"ok": False, "error": f"Worker returned {response.status_code}"}, {}
    except Exception as e:
        # Return error as failed translation
        return "", {"ok": False, "error": str(e)}, {}
    
    # Unfreeze-Reihenfolge NACH worker:
    # 1) invariants
    out, stats = invariants.unfreeze_invariants(worker_out, mapping)
    # 2) glossary
    if g_mapping:
        out, gstats = unfreeze_glossary(out, g_mapping)
        # checks wird später definiert, speichere gstats temporär
        _gstats = gstats
    else:
        _gstats = None
    
    # Step 5: Scrub artifacts
    out = invariants.scrub_artifacts(out)
    
    # Step 6: Unwrap spurious wrappers
    out = invariants.unwrap_spurious_wrappers(out, mapping, text)
    
    # Step 7: Validate invariants
    checks = invariants.validate_invariants(text, out, mapping)
    checks["freeze"] = stats
    
    # Add glossary stats if available
    if _gstats is not None:
        checks["glossary"] = _gstats
    
    # HTML-Fallback disabled for CJK/Thai languages (using spans-only mode instead)
    # Fallback v3b: Only as last resort when normal flow fails (for non-CJK languages)
    if (not checks.get("ok", False)) or stats.get("replaced_total", 0) == 0:
        if any(m["type"] == "html" for m in mapping):
            print(f"WARN: Normal flow failed, using fallback v3b: {source_bcp47}→{target_bcp47}")
            
            core_src = _strip_all_tags(text).strip()
            if core_src:
                # 1) Sichtbaren Text extrahieren und mit invariants.freeze_invariants einfrieren (non-HTML)
                core_freeze, core_map = _freeze_visible(core_src)
                
                # 2) DIESE Sentinels in "safe" Form ohne "<" wandeln: [#INV:{id}#]
                safe_freeze = _to_safe_sentinels(core_freeze)
                
                # 3) Worker mit safe-Sentinels aufrufen
                payload2 = {"source": n_src["engine"], "target": n_tgt["engine"], "text": safe_freeze}
                if max_new_tokens:
                    payload2["max_new_tokens"] = max_new_tokens
                
                try:
                    response2 = SESSION.post(f"{BACKEND_BASE}/translate", json=payload2, timeout=max(120, TIMEOUT))
                    if response2.status_code == 200:
                        worker2 = response2.json()
                        core_raw = (worker2.get("translated_text", "") or "")
                        
                        if core_raw.strip():
                            # 4) Tolerant unfreezen via safe-Unfreeze → genaues Wiederherstellen der Invarianten
                            core_out = _rehydrate_safe_to_std(core_raw, core_map)
                            
                            # 5) Ergebnis zwischen äußeren HTML-Tags einbetten
                            open_tag, close_tag = _outer_html_wrappers(mapping)
                            out = f"{open_tag} {core_out} {close_tag}".strip()
                            
                            # 6) checks aus den Core-Checks übernehmen
                            core_checks = _validate_core(core_out, core_map)
                            checks.update(core_checks)
                            checks["html_ok"] = True
                            checks["artifact_ok"] = True
                            checks["ok"] = True
                            checks["fallback_used"] = "html_visible_freeze_safe_v3b"
                            return out, checks, debug_info
                except Exception as e:
                    print(f"ERROR: HTML visible freeze safe fallback v3b failed: {e}")
    
    # Step 4: Unfreeze invariants
    out, stats = invariants.unfreeze_invariants(worker_out, mapping)
    
    # Step 5: Scrub artifacts
    out = invariants.scrub_artifacts(out)
    
    # Step 6: Unwrap spurious wrappers
    out = invariants.unwrap_spurious_wrappers(out, mapping, text)
    
    # Step 7: Validate invariants
    checks = invariants.validate_invariants(text, out, mapping)
    checks["freeze"] = stats
    
    # Falls Standardpfad Invarianten verliert → Interleave-Fallback
    if not checks.get("ok", False):
        miss = 0
        frz = checks.get("freeze") or {}
        try:
            miss = int(frz.get("missing", 0))
        except Exception:
            miss = 0
        if miss > 0 or not checks.get("html_ok", True):
            out2, checks2 = _invariant_interleave_translate(n_src, n_tgt, text, max_new_tokens, lambda payload: SESSION.post(f"{BACKEND_BASE}/translate", json=payload, timeout=max(120, TIMEOUT)).json(), invariants)
            # Übernehmen, wenn eindeutig besser oder ok
            better = (checks2.get("ok", False) or ( (frz.get("missing", 0) or 0) > (checks2.get("freeze",{}).get("missing",0) or 0) ))
            if better:
                out = out2
                checks = checks2
    
    # Circuit Breaker - Check if degradation is needed
    degrade, reason = (False,"")
    try:
        degrade, reason = should_degrade(worker_out_raw, checks, n_tgt["engine"])
    except Exception:
        degrade, reason = (False,"")

    if degrade:
        # DEGRADE/BREAKER path: Apply the exact same sequence for the breaker fallback
        spans_input2 = text2
        if g_mapping:
            spans_input2 = to_safe_tokens(spans_input2, g_mapping)

        out2, checks2, debug2 = _spans_only_translate(n_src, n_tgt, text, max_new_tokens, _call_worker_translate, invariants, keep_terms)

        if g_mapping:
            out2 = from_safe_tokens(out2, g_mapping)

        out2, _stats_inv2 = invariants.unfreeze_invariants(out2, mapping)
        if g_mapping:
            out2, gstats = unfreeze_glossary(out2, g_mapping)
            checks2["glossary"] = gstats
        if checks2.get("ok", False):
            out, checks = out2, checks2
            checks["fallback_used"] = f"breaker_degrade_spans_only:{reason}"
            if debug:
                debug_info["breaker_reason"] = reason
        else:
            checks["fallback_used"] = f"breaker_attempt_failed:{reason}"
    
    # Style-Postfilter (nur falls aktiviert und de-Ziel)
    if settings.ENABLE_STYLE_FILTER and ("de" in settings.STYLE_LANGS.split(",")) and _is_de(n_tgt["bcp47"], n_tgt["engine"]):
        s_addr = (request_style.address.lower() if (request_style and request_style.address) else settings.STYLE_DEFAULT_ADDRESS.lower())
        s_gender = (request_style.gender.lower() if (request_style and request_style.gender) else settings.STYLE_DEFAULT_GENDER.lower())
        keep = set([s.strip() for s in settings.STYLE_KEEP_TERMS.split(",") if s.strip()])
        if request_style and request_style.keep_terms:
            keep |= set(request_style.keep_terms)
        out2, checks2 = apply_style_de_safe(out, s_addr, s_gender, keep, invariants)
        # Übernehmen nur, wenn Invarianten ok bleiben
        if checks2.get("ok", False):
            out, checks = out2, checks2
            checks["style_used"] = {"address": s_addr, "gender": s_gender}
    
    # Romance T/V (fr/it/es/pt) – nur Anrede/Possessiva
    if settings.ENABLE_STYLE_FILTER and n_tgt["engine"] in ("fr","it","es","pt"):
        s_addr = (request_style.address.lower() if (request_style and request_style.address) else settings.STYLE_DEFAULT_ADDRESS.lower())
        keep = set([s.strip() for s in settings.STYLE_KEEP_TERMS.split(",") if s.strip()])
        if request_style and request_style.keep_terms:
            keep |= set(request_style.keep_terms)
        out2, checks2 = apply_style_romance_safe(out, n_tgt["engine"], s_addr, invariants, keep)
        if checks2.get("ok", False):
            out, checks = out2, checks2
            checks["style_used"] = {"address": s_addr}
    
    # Set final output and checks for normal pipeline
    final_out, final_checks = out, checks
    
    # Prepare debug information if requested
    if debug:
        debug_info = {
            "freeze_text_std": text2,
            "freeze_text_safe": text2_safe,
            "worker_raw": worker_out_raw,
            "fallback_used": final_checks.get("fallback_used")
        }
        # Add breaker reason if degradation was triggered
        if degrade:
            debug_info["breaker_reason"] = reason
    
    # Cache erfolgreiche Übersetzungen (nur bei Cache-Miss)
    if worker_out is not None and settings.CACHE_ENABLE and _CACHE is not None and cache_key and final_checks.get("ok", False):
        try:
            _CACHE.set(cache_key, {"translated_text": final_out, "checks": final_checks}, ttl=settings.CACHE_TTL)
            final_checks["cache_used"] = "miss_store"
        except Exception:
            pass
    
    # -------- Metrics & Debug-Header (immer) ----------
    try:
        fb = str(final_checks.get("fallback_used", ""))
        g  = final_checks.get("glossary") or {"replaced_total": 0, "missing": 0}
        tgt_bcp47 = target_bcp47
        def _inc(d: dict, key: str, n: int = 1): d[key] = d.get(key, 0) + int(n)
        if fb == "spans_only_text_segments" or fb.startswith("breaker_degrade_spans_only"):
            _inc(METRICS_LBL["spans_only_total"], tgt_bcp47, 1)
        # SAFE MODE zählt hier mit:
        if fb == "force_spans_only":
            _inc(METRICS_LBL["spans_only_total"], tgt_bcp47, 1)
        if fb.startswith("breaker_degrade_"):
            _inc(METRICS_LBL["degrade_total"], fb.split(":",1)[0], 1)
        _inc(METRICS_LBL["glossary_replaced_total"], tgt_bcp47, int(g.get("replaced_total", 0)))
        _inc(METRICS_LBL["glossary_missing_total"],  tgt_bcp47, int(g.get("missing", 0)))
        if debug:
            debug_info.setdefault("xhdr", {})
            debug_info["xhdr"]["X-Fallback"] = fb
            debug_info["xhdr"]["X-Glossary-Replaced"] = str(g.get("replaced_total", 0))
            debug_info["xhdr"]["X-Glossary-Missing"]  = str(g.get("missing", 0))
    except Exception:
        pass
    return final_out, final_checks, debug_info

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
    context: Optional[Context] = None
    style: StyleSpec | None = None
    glossary: GlossarySpec | None = None

class TranslationResponse(BaseModel):
    translated_text: str
    checks: Dict[str, Any]
    debug: Dict[str, Any] = None

from typing import Optional

class BatchItem(BaseModel):
    id: Optional[str] = None
    text: str
    glossary: GlossarySpec | None = None
    
    class Config:
        extra = "forbid"

class BatchRequest(BaseModel):
    source: str
    target: str
    items: List[Any]  # Can be strings or objects
    max_new_tokens: int = 512
    debug: bool = False
    context: Optional[Context] = None
    style: StyleSpec | None = None
    glossary: GlossarySpec | None = None
    
    def __init__(self, **data):
        super().__init__(**data)
        # Normalize items: convert strings to {"text": "..."} objects
        normalized_items = []
        for item in self.items:
            if isinstance(item, str):
                normalized_items.append(BatchItem(text=item))
            elif isinstance(item, dict):
                # Handle {"id": "seg-2", "text": "...", "glossary": {...}} format
                text = item.get("text", "")
                item_id = item.get("id")
                item_glossary = item.get("glossary")
                normalized_items.append(BatchItem(text=text, id=item_id, glossary=item_glossary))
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

@app.get("/locales")
def get_locales():
    locs = _load_locales_list()
    out = map_locales_with_engine(locs)
    return {"locales": out, "count": len(out), "version": app_version()}

@app.get("/capabilities")
def get_capabilities():
    meta = {"version": app_version(), "commit": os.environ.get("GIT_COMMIT", "")}
    caps = compute_capabilities(meta)
    return JSONResponse(content=caps)

@app.get("/cache/stats")
def cache_stats():
    from guard.cache import cache as C
    if not settings.CACHE_ENABLE or C is None:
        return JSONResponse(content={"enabled": False})
    return JSONResponse(content={"enabled": True, "stats": C.stats(), "config": {"max": settings.CACHE_MAX, "ttl": settings.CACHE_TTL}})

@app.get("/locales.csv")
def get_locales_csv():
    locs = _load_locales_list()
    mapped = map_locales_with_engine(locs)
    rows = ["bcp47,engine"]
    for item in mapped:
        rows.append(f"{item['bcp47']},{item['engine']}")
    body = "\n".join(rows) + "\n"
    return PlainTextResponse(content=body, media_type="text/csv")

@app.post("/translate", response_model=TranslationResponse)
async def translate(request: TranslationRequest, x_debug: str = Header(None)):
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

        # Enable debug mode via header or request field
        debug_enabled = request.debug or x_debug == "1"

        # Extract keep_terms from context
        keep_terms = []
        if request.context and request.context.keep_terms:
            keep_terms = [s for s in request.context.keep_terms if s and isinstance(s, str)]

        # Normalize target language and calculate strict flag before translation
        tgt_bcp47_norm, tgt_engine_norm = _norm_target_pair(request.target)
        strict_for_this = _strict_enforced_for(tgt_bcp47_norm, tgt_engine_norm)

        # Use unified translation pipeline
        result, checks, debug_info = translate_one(request.source, request.target, request.text, request.max_new_tokens, debug_enabled, keep_terms, request.style, req_glossary=request.glossary, item_glossary=None)
        
        # add debug headers for quick smoke
        debug_headers = {}
        if debug_enabled and isinstance(debug_info.get("xhdr"), dict):
            for k,v in debug_info["xhdr"].items():
                debug_headers[k] = v
        
        # Check for strict invariant mode with exclusions
        if not checks.get("ok", False) and strict_for_this:
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
        if debug_enabled:
            response_data.debug = debug_info
        
        # Return JSONResponse with custom headers
        headers = {
            "X-Source-Lang": source_norm["bcp47"],
            "X-Source-Engine-Lang": source_norm["engine"],
            "X-Target-Lang": target_norm["bcp47"],
            "X-Target-Engine-Lang": target_norm["engine"]
        }
        # Add cache header if available
        if checks.get("cache_used"):
            headers["X-Cache"] = checks.get("cache_used", "miss")
        # Add debug headers if available
        headers.update(debug_headers)
        
        return JSONResponse(
            content=response_data.dict(),
            headers=headers
        )

    except HTTPException:
        raise
    except Exception as e:
        METRICS["errors"] += 1
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/translate_batch", response_model=BatchResponse)
async def translate_batch(request: BatchRequest, x_debug: str = Header(None)):
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
        
        # Enable debug mode via header or request field
        debug_enabled = request.debug or x_debug == "1"

        # Extract keep_terms from context
        keep_terms = []
        if request.context and request.context.keep_terms:
            keep_terms = [s for s in request.context.keep_terms if s and isinstance(s, str)]

        # Normalize target language and calculate strict flag before processing
        tgt_bcp47_norm, tgt_engine_norm = _norm_target_pair(request.target)
        strict_for_this = _strict_enforced_for(tgt_bcp47_norm, tgt_engine_norm)

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
                    future = executor.submit(translate_one, request.source, request.target, item.text, request.max_new_tokens, debug_enabled, keep_terms, request.style, req_glossary=request.glossary, item_glossary=item.glossary)
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
                        if debug_enabled:
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
                    translated_text, checks, debug_info = translate_one(request.source, request.target, item.text, request.max_new_tokens, debug_enabled, keep_terms, request.style, req_glossary=request.glossary, item_glossary=item.glossary)
                    batch_item = BatchItemResponse(
                        index=i,
                        id=item.id if hasattr(item, 'id') else None,
                        translated_text=translated_text,
                        checks=checks
                    )
                    if debug_enabled:
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

        # Check for strict invariant mode with exclusions
        if failed_count > 0 and strict_for_this:
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
        
        # aggregate debug headers (batch-level sum)
        batch_headers = {
            "X-Source-Lang": source_norm["bcp47"],
            "X-Source-Engine-Lang": source_norm["engine"],
            "X-Target-Lang": target_norm["bcp47"],
            "X-Target-Engine-Lang": target_norm["engine"]
        }
        if debug_enabled:
            g_rep = 0; g_mis = 0
            for it in results:
                gl = ((it or {}).get("checks") or {}).get("glossary") or {}
                try:
                    g_rep += int(gl.get("replaced_total", 0))
                    g_mis += int(gl.get("missing", 0))
                except Exception:
                    pass
            batch_headers["X-Glossary-Replaced-Total"] = str(g_rep)
            batch_headers["X-Glossary-Missing-Total"] = str(g_mis)
        
        # Return JSONResponse with custom headers
        return JSONResponse(
            content=response_data.dict(),
            headers=batch_headers
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
