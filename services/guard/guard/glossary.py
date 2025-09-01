import os, json, re, hashlib, unicodedata
from typing import List, Dict, Tuple

_SENT_FMT = "<|GLO:{id}:{crc}|>"
# tolerante Suche: optional Fullwidth-Varianten und Alt-Separators
_TOL_RE = re.compile(
    r"[<＜《【]?\s*[|｜︱∣]?\s*G\s*L\s*O\s*[:：| ]\s*(\d{1,4})\s*(?:[:：| ]\s*([0-9A-Fa-f]{4,8}))?\s*[|｜︱∣]?\s*[>＞》】]?",
    re.U
)

def _sha6(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:6].upper()

def load_terms(path: str | None, env_terms: str | None) -> List[Dict[str,str]]:
    terms: List[Dict[str,str]] = []
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
            for t in doc.get("terms", []):
                if not t.get("term"): continue
                terms.append({
                    "term": t["term"],
                    "canonical": t.get("canonical", t["term"]),
                    "langs": t.get("langs", ["*"]),
                    "regex": "1" if t.get("regex") else "0",
                })
    # ENV-CSV, z.B. "TranceLate,OpenAI"
    if env_terms:
        for raw in env_terms.split(","):
            w = raw.strip()
            if w:
                terms.append({"term": w, "canonical": w, "langs": ["*"], "regex":"0"})
    # deduplizieren nach canonical
    seen = set()
    out = []
    for t in terms:
        key = (t["canonical"], tuple(sorted(t["langs"])))
        if key in seen: continue
        seen.add(key); out.append(t)
    return out

def _build_matchers(terms: List[Dict[str,str]], lang_engine: str) -> List[Tuple[re.Pattern,str]]:
    pats: List[Tuple[re.Pattern,str]] = []
    for t in terms:
        langs = t.get("langs", ["*"])
        if "*" not in langs and lang_engine not in langs: continue
        s = t["term"]
        if t.get("regex","0") == "1":
            pat = re.compile(s, re.U)
        else:
            # Wortgrenzen für lateinische Skripte; sonst exakter Match
            if re.search(r"[A-Za-z]", s):
                pat = re.compile(rf"\b{re.escape(s)}\b", re.U|re.I)
            else:
                pat = re.compile(re.escape(s), re.U)
        pats.append((pat, t["canonical"]))
    # längere zuerst
    pats.sort(key=lambda x: -len(x[0].pattern))
    return pats

def freeze_glossary(text: str, lang_engine: str, terms: List[Dict[str,str]]):
    if not terms: 
        return text, []
    mapping = []
    t = text
    idx = 0
    for pat, canon in _build_matchers(terms, lang_engine):
        def repl(m):
            nonlocal idx
            raw = m.group(0)
            ph = _SENT_FMT.format(id=idx, crc=_sha6(raw))
            mapping.append({"ph": ph, "raw": canon})
            idx += 1
            return ph
        t = pat.sub(repl, t)
    return t, mapping

def to_safe_tokens(text: str, mapping: list[dict]) -> str:
    """
    Replace <|GLO:id:crc|> with ASCII-safe tokens [#GLO:id#] so models won't eat them.
    """
    out = text
    for i, m in enumerate(mapping):
        ph = m.get("ph")
        safe = f"[#GLO:{i}#]"
        if ph:
            out = out.replace(ph, safe)
    return out

def from_safe_tokens(text: str, mapping: list[dict]) -> str:
    """
    Restore safe tokens [#GLO:id#] back to original <|GLO:id:crc|> before unfreeze.
    """
    out = text
    for i, m in enumerate(mapping):
        ph = m.get("ph")
        safe = f"[#GLO:{i}#]"
        if ph:
            out = out.replace(safe, ph)
    return out

def unfreeze_glossary(text: str, mapping: List[Dict[str,str]]) -> Tuple[str, Dict]:
    if not mapping: 
        return text, {"replaced_total":0, "missing":0}
    replaced = 0
    missing = 0
    out = text
    for i, m in enumerate(mapping):
        ph = m["ph"]; raw = m["raw"]
        # strict
        if ph in out:
            out = out.replace(ph, raw); replaced += 1; continue
        # tolerant
        out2, n = _TOL_RE.subn(lambda mt: raw if mt.group(1) == str(i) else mt.group(0), out)
        if n > 0:
            out = out2; replaced += 1; continue
        # already present (canonical brand survived translation)
        # case-insensitive only for Latin; for other scripts exact match
        if re.search(r"[A-Za-z]", raw):
            if re.search(rf"(?i)\b{re.escape(raw)}\b", out):
                replaced += 1; continue
        else:
            if raw in out:
                replaced += 1; continue
        # truly missing
        missing += 1
    return out, {"replaced_total": replaced, "missing": missing}
