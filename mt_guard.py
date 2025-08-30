from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import re, requests, os, csv, pathlib, json
from rapidfuzz import fuzz
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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


# -------- Regexes
PH_RE    = re.compile(r"\{\{[^}]+\}\}")
SINGLE_PH_RE = re.compile(r"\{[A-Za-z0-9_]+\}")
NUM_RE   = re.compile(r"\d+[.,]?\d*")
TAG_RE   = re.compile(r"</?([a-zA-Z0-9]+)[^>]*>")
TAG_FULL_RE = re.compile(r"(</?[A-Za-z0-9]+(?:\s[^>]*?)?>)")
PUNC_KEEP_RE  = re.compile(r"[:–—]")  # Doppelpunkt & Gedankenstrich einfrieren
AMPM_RE  = re.compile(r"\b([1-9]|1[0-2])\s*(a\.?m\.?|p\.?m\.?)\b", re.I)  # 4pm, 6 p.m., etc.
RANGE_RE = re.compile(r"\b\d{1,4}\s*[–-]\s*\d{1,4}\b")                     # 1990–2014
VER_RE   = re.compile(r"\b([A-Za-z][A-Za-z0-9\-\+\.#/]{1,})\s?([0-9]{1,3}(?:\.[0-9]+)?)\b")  # Python 3, HTML5, ISO 9001
PURENUM_RE = re.compile(r"\d+(?:[.,]\d+)?")                                    # 4–6-stellig (Jahr/PLZ)

# -------- Emoji/Symbol folding for effective length calculation
EMOJI_SYMBOL_RE = re.compile(r'[☆★⭐✨🎉🙂😊😂🤣😅😉😍😘🤩🔥❗️‼️！？!?.。、，〜～ー・･•·]')

def _len_effective(text: str) -> int:
    """
    Calculate effective length by folding consecutive emoji/symbol runs to max 3 characters.
    Only used for measurement, does not modify the actual text.
    """
    if not text:
        return 0
    
    # Find all emoji/symbol positions
    matches = list(EMOJI_SYMBOL_RE.finditer(text))
    
    if not matches:
        return len(text)
    
    # Calculate effective length by folding consecutive runs
    effective_len = len(text)
    i = 0
    
    while i < len(matches):
        # Find consecutive emoji/symbol run
        run_start = matches[i].start()
        run_end = matches[i].end()
        
        # Count consecutive emoji/symbols
        run_length = 1
        j = i + 1
        while j < len(matches) and matches[j].start() == run_end:
            run_end = matches[j].end()
            run_length += 1
            j += 1
        
        # If run is longer than 3, reduce effective length
        if run_length > 3:
            effective_len -= (run_length - 3)
        
        i = j
    
    return effective_len

# -------- Satz-Split (universal, keine Phrasen-Sonderfälle)
ABBR_PAT = [
    r"Mr\.", r"Mrs\.", r"Ms\.", r"Dr\.", r"Prof\.", r"Sr\.", r"Jr\.", r"vs\.",
    r"etc\.", r"e\.g\.", r"i\.e\.", r"U\.S\.", r"U\.K\.", r"Fig\.", r"No\.", r"ca\."
]
SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")  # fixed-width lookbehind (OK)

def mask_abbr(t:str)->str:
    for p in ABBR_PAT:
        t = re.sub(p, lambda m: m.group(0).replace(".", "§DOT§"), t, flags=re.I)
    return t
def unmask_abbr(t:str)->str:
    return t.replace("§DOT§",".")

def sentence_split(text:str):
    t = mask_abbr(text)
    parts = [p.strip() for p in SPLIT_RE.split(t)]
    parts = [unmask_abbr(p) for p in parts if p]
    return parts if len(parts) > 1 else [text]

# -------- Glossar (never_translate)
TM_PATH = pathlib.Path("tm.csv")
GLOSSARY_PATH = pathlib.Path("glossary.json")
NEVER_TERMS = []
def load_glossary():
    global NEVER_TERMS
    NEVER_TERMS = []
    if GLOSSARY_PATH.exists():
        try:
            g = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
            NEVER_TERMS = list(dict.fromkeys((g.get("never_translate") or [])))
            NEVER_TERMS.sort(key=len, reverse=True)
        except Exception:
            NEVER_TERMS = []
    return len(NEVER_TERMS)

def protect_nt(text:str):
    hits=[]
    def make_re(term):
        if re.search(r"[A-Za-z0-9]", term):
            return re.compile(rf"(?i)(?<!\w){re.escape(term)}(?!\w)")
        return re.compile(re.escape(term), re.I)
    for term in NEVER_TERMS:
        pat = make_re(term)
        def repl(m):
            i=len(hits); hits.append(m.group(0)); return f"⟦NT{i}⟧"
        text = pat.sub(repl, text)
    return text, hits


def restore_list(text:str, prefix:str, hits):
    # tolerant restore: case-insensitive + many marker variants (incl. blanks/hyphens)
    import re as _re
    def _alts(pref): return (pref, pref.lower(), pref.capitalize())
    for i, val in enumerate(hits):
        core = (
            "⟦{p}{i}⟧","<<{p}{i}>>","__{p}{i}__","_{p}{i}__","__{p}{i}_",
            "{p}{i}","{p} {i}","{p}-{i}","[{p}{i}]","({p}{i})"
        )
        patterns=[]
        for pref in _alts(prefix):
            patterns += [c.format(p=pref,i=i) for c in core]
        for pat in patterns:
            text = _re.sub(_re.escape(pat), val, text, flags=_re.I)
    return text

def protect_regex(text:str, rx:re.Pattern, prefix:str):
    hits=[]
    def repl(m):
        i=len(hits); hits.append(m.group(0)); return f"⟦{prefix}{i}⟧"
    return rx.sub(repl, text), hits

# -------- TM laden
TM = []
def load_tm():
    global TM
    TM = []
    if TM_PATH.exists():
        with TM_PATH.open("r", encoding="utf-8") as f:
            r = csv.DictReader(f, fieldnames=["source_lang","target_lang","source_text","target_text"])
            for row in r:
                st = (row["source_text"] or "").strip()
                if not st or st.startswith("#"): continue
                tgt = (row["target_text"] or "").strip()
                TM.append({
                    "src_lang": (row["source_lang"] or "").strip(),
                    "tgt_lang": (row["target_lang"] or "").strip(),
                    "src": st,
                    "tgt": tgt,
                    "ph_set": set(PH_RE.findall(st)),
                    "tgt_ph_set": set(PH_RE.findall(tgt))
                })
    return len(TM)

load_tm(); load_glossary()

@app.get("/health")
def health(): return {"ok": True}

@app.get("/meta")
def meta():
    data = {
        "engine": "Anni",
        "role": "Guard",

        "tm_entries": len(TM),
        "tm_soft_threshold": TM_SOFT_THRESHOLD,
        "provider_configured": bool(PROVIDER),
        "never_terms": len(NEVER_TERMS),
    }
    data.update(_backend_status())
    return data

@app.post("/admin/reload")
def admin_reload():
    return {"ok": True, "tm_entries": load_tm(), "never_terms": load_glossary()}

# -------- Payload & Backend
class Payload(BaseModel):
    source: str
    target: str
    text: str


def call_backend(url, src, tgt, text):
    import time, pathlib, urllib.request, json
    t0 = time.time()
    data = json.dumps({"source": src, "target": tgt, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, method="POST",
        headers={"Content-Type":"application/json","Connection":"close"},
        data=data)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        body = r.read().decode("utf-8")
    dt = time.time() - t0
    try:
        pathlib.Path("logs").mkdir(exist_ok=True)
        with open("logs/guard_backend_timing.log","a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {src}->{tgt} len={len(text)} url={url} dt={dt:.3f}s\n")
    except Exception:
        pass
    return (json.loads(body) if body else {}).get("translated_text","")

# -------- TM Lookup
def tm_lookup_exact(src_lang, tgt_lang, text):
    phs = set(PH_RE.findall(text))
    for it in TM:
        if it["src_lang"] == src_lang and it["tgt_lang"] == tgt_lang and it["src"] == text:
            if it["tgt_ph_set"] == phs:
                return {"tgt": it["tgt"], "provenance": {"tm":"exact","engine":"tm"}}
    return None

def tm_lookup_fuzzy(src_lang, tgt_lang, text):
    phs = set(PH_RE.findall(text))
    cands = [it for it in TM if it["src_lang"]==src_lang and it["tgt_lang"]==tgt_lang and it["ph_set"]==phs]
    if not cands: return None
    L = len(text)
    pool = [it for it in cands if 0.8*L <= len(it["src"]) <= 1.2*L] or cands
    best=None; best_score=0.0; q=text.lower()
    for it in pool:
        s = fuzz.ratio(q, it["src"].lower())/100.0
        if s>best_score: best_score, best = s, it
    if best and best_score >= TM_SOFT_THRESHOLD and best["tgt_ph_set"] == phs:
        return {"tgt": best["tgt"], "provenance": {"tm":"fuzzy","engine":"tm","score": round(best_score,3)}}
    return None

# -------- EN sentence case helper
EN_SENTENCE_CASE_PATTERNS = [
    (re.compile(r'(\{\{[^}]+\}\}\s+)([A-Z][a-z]+\b)'), 1, 2),
    (re.compile(r'(</[^>]+>\s+)([A-Z][a-z]+\b)'), 1, 2),
    (re.compile(r'(–\s+)([A-Z][a-z]+\b)'), 1, 2),
    (re.compile(r'(\d+\s+)([A-Z][a-z]+\b)'), 1, 2),
]
EN_LIKELY = re.compile(r"\b(the|and|you|we|in|on|with|pages?|price|incl|vat|now|send|save|synchronized)\b", re.I)
def fix_sentence_case_en(text:str)->str:
    if not EN_LIKELY.search(text): return text
    prev=None; t=text
    while prev!=t:
        prev=t
        for pat,g1,g2 in EN_SENTENCE_CASE_PATTERNS:
            t = pat.sub(lambda m: m.group(g1)+m.group(g2).lower(), t)
    return t

# -------- CP1252 Artefakt-Cleanup
def cp1252_cleanup(text:str)->str:
    return (text
        .replace("Â©","©").replace("Â®","®").replace("Â·","·").replace("Â","")
    )

# -------- Checks
def digits_only(s): return re.sub(r"\D","",s or "")
def tags(sig): return [m.group(0).lower().replace(" ", "") for m in TAG_RE.finditer(sig)]

def numbers_ok(src:str, out:str)->bool:
    out_dig = digits_only(out)
    # 1) direkter Check
    src_nums = NUM_RE.findall(src)
    direct_ok = True
    for n in src_nums:
        n_d = digits_only(n)
        if n_d and n_d not in out_dig:
            direct_ok = False; break
    if direct_ok: return True
    # 2) AM/PM-Heuristik
    out_parts = re.findall(r"\d{1,4}", out)
    present = lambda x: x in out_dig or x in out_parts
    had_ampm = False
    for m in AMPM_RE.finditer(src):
        had_ampm = True
        val = int(m.group(1)); mer = m.group(2).lower(); raw = str(val)
        if ('p' in mer) and (1 <= val <= 11):
            if not (present(raw) or present(str(val+12))): return False
        else:
            if not present(raw): return False
    return had_ampm  # falls kein am/pm: False → num_ok bleibt vom direkten Check bestimmt

def check_invariants(src:str, out:str):
    ph = PH_RE.findall(src); ph_ok = all(p in out for p in ph)
    num_ok = numbers_ok(src, out)
    html_ok = sorted(tags(src)) == sorted(tags(out))
    paren_ok = (("(" not in src) and (")" not in src) and ("(" not in out) and (")" not in out)) or (("(" in src) or (")" in src))
    
    # Original length ratio (for diagnosis)
    src_len = len(src); ratio = (len(out)+1)/(src_len+1)
    len_ok = (0.4 <= ratio <= 4.0) if src_len < 20 else (0.5 <= ratio <= 2.2)
    
    # Effective length ratio (for decision)
    src_eff = _len_effective(src) or 1
    tgt_eff = _len_effective(out) or 1
    ratio_eff = tgt_eff / src_eff
    len_ok_eff = (0.4 <= ratio_eff <= 4.0) if src_eff < 20 else (0.5 <= ratio_eff <= 2.2)
    
    # Use effective length check for overall decision
    ok = ph_ok and num_ok and html_ok and paren_ok and len_ok_eff
    
    return {
        "ok": ok, 
        "ph_ok": ph_ok, 
        "num_ok": num_ok, 
        "html_ok": html_ok, 
        "paren_ok": paren_ok, 
        "len_ratio": round(ratio, 2),
        "len_ratio_eff": round(ratio_eff, 2),
        "len_use": "effective"
    }

# -------- Core: ein Satz/Chunk übersetzen (mit Schutz)
def translate_chunk(src_lang, tgt_lang, text):
    """
    Single backend call: mask PH/TAG globally, preserve numbers, no PUNC masking.
    """
    ph_hits=[]; tag_hits=[]
    def _mask(tok):
        if PH_RE.fullmatch(tok):
            i=len(ph_hits); ph_hits.append(tok); return f"⟦PH{i}⟧"
        if TAG_FULL_RE.fullmatch(tok):
            i=len(tag_hits); tag_hits.append(tok); return f"⟦TAG{i}⟧"
        return tok
    # 1) Build masked string (PH/TAG only)
    tokens = re.split(rf"({PH_RE.pattern}|{TAG_FULL_RE.pattern})", text)
    masked = "".join(_mask(t) for t in tokens if t)

    # 2) Protect glossary/versions/ranges (global); numbers & punctuation unmasked
    masked, nt_hits  = protect_nt(masked)
    masked, ver_hits = protect_regex(masked, VER_RE,   "VER")
    masked, rng_hits = protect_regex(masked, RANGE_RE, "RNG")

    # 3) Backend single call
    try:
        out = call_backend(BACKEND, src_lang, tgt_lang, masked); eng="self_host_mt"
    except Exception:
        if not PROVIDER:
            raise HTTPException(status_code=502, detail="self_host backend failed and no provider configured")
        out = call_backend(PROVIDER, src_lang, tgt_lang, masked); eng="provider_backup"

    # 4) Restore in correct order
    out = restore_list(out, "NT",  nt_hits)
    out = restore_list(out, "RNG", rng_hits)
    out = restore_list(out, "VER", ver_hits)
    out = restore_list(out, "PH",  ph_hits)
    out = restore_list(out, "TAG", tag_hits)

    # 5) Cleanup

    out = re.sub(r"\s*:\s*", ": ", out)
    out = re.sub(r"\s*([–—-])\s*", r" \1 ", out)
    PH_NUM  = r"(?:\{\{[^}]+\}\}|\{[A-Za-z0-9_]+\}|\d+(?:[.,]\d+)?)"
    TAG_ANY = r"(?:</?[A-Za-z0-9]+(?:\s[^>]*?)?>)"
    out = re.sub(rf"([A-Za-z0-9])({PH_NUM}|{TAG_ANY})", r"\1 \2", out)
    out = re.sub(rf"({PH_NUM}|{TAG_ANY})([A-Za-z0-9])", r"\1 \2", out)
    def _collapse_dupe_tags(t):
        prev=None
        while prev!=t:
            prev=t
            t=re.sub(r"<([A-Za-z0-9]+)(?:\s[^>]*)?>\s*<\1(?:\s[^>]*)?>", r"<\1>", t)
            t=re.sub(r"</([A-Za-z0-9]+)>\s*</\1>", r"</\1>", t)
        return t
    out = _collapse_dupe_tags(out)
    out = re.sub(r"\bonly\s+today['’]?s\s*:", "Only today:", out, flags=re.I)
    out = re.sub(r"\s{2,}", " ", out).strip()
    out = fix_sentence_case_en(out)
    out = cp1252_cleanup(out)
    return out, eng

def _singlecall_masked(src_lang, tgt_lang, text):
    import re
    ph=[]; tag=[]; sb=[]
    def r_ph(m):
        i=len(ph); ph.append(m.group(0)); return f"PHX{i}"
    def r_tag(m):
        i=len(tag); tag.append(m.group(0)); return f"TAGX{i}"
    def r_sb(m):
        i=len(sb); sb.append(m.group(0)); return f"SBX{i}"
    t = PH_RE.sub(r_ph, text)
    t = TAG_FULL_RE.sub(r_tag, t)
    t = re.sub(r"\{[A-Za-z0-9_]+\}", r_sb, t)
    out = call_backend(BACKEND, src_lang, tgt_lang, t)
    for i,v in enumerate(tag): out = out.replace(f"TAGX{i}", v)
    for i,v in enumerate(sb): out = out.replace(f"SBX{i}", v)
    for i,v in enumerate(ph): out = out.replace(f"PHX{i}", v)
    out = re.sub(r"\s+([,.;:!?])", r"", out)
    out = re.sub(r"\s*:\s*", ": ", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    out = fix_sentence_case_en(out)
    out = cp1252_cleanup(out)
    return out, "self_host_mt"

# -------- API
class Payload(BaseModel):
    source: str
    target: str
    text: str

@app.post("/translate")
def translate(p: Payload):
    if (p.source, p.target) == ("nl","en"):
        o = call_backend(BACKEND, p.source, p.target, p.text)
        return {"translated_text": o, "provenance": {"tm":"miss","engine":"self_host_mt","route":"fastpath_nl_en"}, "checks": check_invariants(p.text, o)}

    # TM exact/fuzzy zuerst (universell)
    hit = tm_lookup_exact(p.source, p.target, p.text)
    if hit:
        out = cp1252_cleanup(hit["tgt"])
        return {"translated_text": out, "provenance": hit["provenance"], "checks": check_invariants(p.text, out)}
    hit = tm_lookup_fuzzy(p.source, p.target, p.text)
    if hit:
        out = cp1252_cleanup(hit["tgt"])
        return {"translated_text": out, "provenance": hit["provenance"], "checks": check_invariants(p.text, out)}

    # fast-path for de/it -> en
    if (p.source,p.target) in (("de","en"),("it","en")):
        out, eng = _singlecall_masked(p.source,p.target,p.text)
        return {"translated_text": out, "provenance": {"tm":"miss","engine": eng}, "checks": check_invariants(p.text, out)}

    # universell: satzweise Übersetzung (verhindert Inhaltsverlust)
    sents = sentence_split(p.text)
    outs = []
    engine_used = None
    for s in sents:
        o, eng = translate_chunk(p.source, p.target, s)
        engine_used = engine_used or eng
        outs.append(o)
    out = " ".join(outs).strip()

    return {"translated_text": out, "provenance": {"tm":"miss","engine":engine_used or "self_host_mt"}, "checks": check_invariants(p.text, out)}
