import unicodedata as _ud, re as _re

_CYR_ENGINES = {"ru","bg","uk","sr","mk","be"}
_SAFE_PLACEHOLDER_RE = _re.compile(r"\[#INV:(\d+)#\]")
_STD_PLACEHOLDER_RE  = _re.compile(r"<\|INV:(\d+):([0-9A-Fa-f]{4,8})\|>")

def _norm(s:str)->str:
    return _ud.normalize("NFKC", (s or "")).strip()

def _looks_like_gibberish(s:str)->bool:
    t=_norm(s)
    if not t or len(t)<2: return True
    if _re.search(r"(.)\1{9,}", t): return True               # 10x gleich
    if _re.search(r"[<>]{8,}", t): return True                # <<<<<<<<
    toks=t.split()
    if len(toks)>=8:
        from collections import Counter
        c=Counter(toks); top=c.most_common(1)[0][1]
        if len(c)/len(toks) < 0.2 and top/len(toks) >= 0.25:  # low variety
            return True
    return False

def _count_ph(s:str)->int:
    return len(_SAFE_PLACEHOLDER_RE.findall(s)) + len(_STD_PLACEHOLDER_RE.findall(s))

def should_degrade(worker_raw: str | None,
                   checks: dict,
                   target_engine: str) -> tuple[bool, str]:
    """
    Entscheidet, ob wir auf Spans-Only degradieren sollen. Liefert (yes, reason).
    """
    try:
        if not worker_raw:
            return True, "empty_output"
        # Gibberish?
        if _looks_like_gibberish(worker_raw):
            return True, "gibberish"
        # Platzhalter/Mappings beschädigt?
        miss = int(((checks or {}).get("freeze") or {}).get("missing", 0))
        if miss >= 2:
            return True, f"missing_placeholders:{miss}"
        # Kyrillisch: noch konservativer degradieren
        if (target_engine in _CYR_ENGINES):
            ph_ok = bool((checks or {}).get("ph_ok", False))
            if not ph_ok:
                return True, "cyr_ph_fail"
            if miss > 0:
                return True, f"cyr_missing:{miss}"
        return False, ""
    except Exception:
        return False, ""
