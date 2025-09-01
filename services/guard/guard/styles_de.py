import re as _re
from typing import Set, Tuple, List

# Determiner & stems
_GENDER_STEMS: List[Tuple[str,str]] = [
    ("Kunde","Kunden"),
    ("Nutzer","Nutzer"),
    ("Benutzer","Benutzer"),
    ("Teilnehmer","Teilnehmer"),
    ("Abonnent","Abonnenten"),
    ("Leser","Leser"),
    ("Student","Studenten"),
    ("Mitarbeiter","Mitarbeiter")
]
_PLURAL_BASE = { "Kunde":"Kund","Nutzer":"Nutzer","Benutzer":"Benutzer","Teilnehmer":"Teilnehmer","Abonnent":"Abonnent","Leser":"Leser","Student":"Student","Mitarbeiter":"Mitarbeiter" }
_DE_DU = { r"\bSie\b": "du", r"\bIhnen\b": "dir", r"\bIhrer\b": "deiner", r"\bIhrem\b": "deinem", r"\bIhren\b": "deinen", r"\bIhre\b": "deine", r"\bIhr\b": "dein" }
_DE_SIE = { r"\bdu\b": "Sie", r"\bdir\b": "Ihnen", r"\bdich\b": "Sie", r"\bdeiner\b": "Ihrer", r"\bdeinem\b": "Ihrem", r"\bdeinen\b": "Ihren", r"\bdeine\b": "Ihre", r"\bdein\b": "Ihr" }
_DET_PLURAL = r"(unsere|alle|viele|neue|zahlreiche|mehrere|diese|jene|solche|manche)"

def _plural_suffix(mode: str) -> str:
    return ":innen" if mode=="colon" else "*innen" if mode=="star" else "Innen" if mode=="innen" else ""

def _sing_suffix(mode: str) -> str:
    return ":in" if mode=="colon" else "*in" if mode=="star" else "In" if mode=="innen" else ""

def _genderize_token(tok: str, mode: str) -> str:
    if mode in ("none","",None): return tok
    cap = tok[0].isupper()
    t = tok
    for sg, pl in _GENDER_STEMS:
        if t == sg:
            base = sg
            t = base + (":in" if mode=="colon" else "*in" if mode=="star" else "In")
            break
        if t == pl:
            base = _PLURAL_BASE.get(sg, sg)
            t = base + (":innen" if mode=="colon" else "*innen" if mode=="star" else "Innen")
            break
    if cap: t = t[0].upper() + t[1:]
    return t

def _apply_gender_de(text: str, mode: str, keep_terms: Set[str]) -> str:
    if mode in ("none","",None): return text
    out = []
    for tok in _re.split(r"(\W+)", text):
        if not tok or _re.fullmatch(r"\W+", tok): out.append(tok); continue
        if tok in keep_terms: out.append(tok); continue
        out.append(_genderize_token(tok, mode))
    return "".join(out)

def _apply_address_de(text: str, address: str) -> str:
    if address in (None,"","auto"): return text
    repls = _DE_DU if address=="du" else _DE_SIE if address=="sie" else None
    if address=="divers":
        text = _re.sub(r"\b(Sie|Ihnen|Ihrer|Ihrem|Ihren|Ihre|Ihr|du|dir|dich|deiner|deinem|deinen|deine|dein)\b", "", text)
        return _re.sub(r"\s{2,}", " ", text).strip()
    if not repls: return text
    for pat,rep in repls.items(): text = _re.sub(pat, rep, text)
    return text

def _de_plural_harmonize(text: str, mode: str) -> str:
    if mode in ("none","",None): return text
    sing, pl = _sing_suffix(mode), _plural_suffix(mode)
    out = text
    for sg, plword in _GENDER_STEMS:
        base = _PLURAL_BASE.get(sg, sg)
        out = _re.sub(rf"\b{_DET_PLURAL}\s+{_re.escape(sg)}{_re.escape(sing)}\b", rf"\g<1> {base}{pl}", out, flags=_re.IGNORECASE)
        out = _re.sub(rf"\b{_DET_PLURAL}\s+{_re.escape(plword)}{_re.escape(sing)}\b", rf"\g<1> {base}{pl}", out, flags=_re.IGNORECASE)
    if mode=="colon":
        out = _re.sub(rf"({_DET_PLURAL}\b[^.!?]{{0,120}}?):in\b", r"\1:innen", out, flags=_re.IGNORECASE)
    elif mode=="star":
        out = _re.sub(rf"({_DET_PLURAL}\b[^.!?]{{0,120}}?)\*in\b", r"\1*innen", out, flags=_re.IGNORECASE)
    elif mode=="innen":
        out = _re.sub(rf"({_DET_PLURAL}\b[^.!?]{{0,120}}?)In\b", r"\1Innen", out, flags=_re.IGNORECASE)
    return out

def _de_article_harmonize(text: str, mode: str) -> str:
    if mode in ("none","",None): return text
    if mode=="colon":
        return _re.sub(r"\b(Jeder|Jede|Jedes)\s+([A-Za-zÄÖÜäöüß\-]+):in\b", r"Jede:r \2:in", text)
    if mode=="star":
        return _re.sub(r"\b(Jeder|Jede|Jedes)\s+([A-Za-zÄÖÜäöüß\-]+)\*in\b", r"Jede*r \2*in", text)
    if mode=="innen":
        return _re.sub(r"\b(Jeder|Jede|Jedes)\s+([A-Za-zÄÖÜäöüß\-]+)In\b", r"Jede/r \2In", text)
    return text

def _de_label_normalize(text: str) -> str:
    out = text
    out = _re.sub(r"\bMail\s*(zu|an)?\s*:", "E-Mail: ", out, flags=_re.IGNORECASE)
    out = _re.sub(r"\b(Budget|E-?Mail):\s*", r"\1: ", out, flags=_re.IGNORECASE)
    return out

def _de_punct_ws_normalize(text: str) -> str:
    out = _re.sub(r"\s{2,}", " ", text)
    out = _re.sub(r"\s*([,.;!?])", r"\1", out)
    out = _re.sub(r"([,;:])(\S)", r"\1 \2", out)
    return out

def apply_style_de_safe(text: str, address: str, gender: str, keep_terms: set[str], invariants):
    frozen, mapping = invariants.freeze_invariants(text)
    parts = [("T", frozen)]
    buf = []
    for kind, val in parts:
        if kind == "I":
            raw = mapping[val]["raw"] if 0 <= val < len(mapping) else ""
            buf.append(raw)
        else:
            seg = _apply_address_de(val, address)
            seg = _apply_gender_de(seg, gender, keep_terms)
            seg = _de_plural_harmonize(seg, gender)
            seg = _de_article_harmonize(seg, gender)
            seg = _de_label_normalize(seg)
            seg = _de_punct_ws_normalize(seg)
            buf.append(seg)
    out = "".join(buf)
    _, full_map = invariants.freeze_invariants(text)
    checks = invariants.validate_invariants(text, out, full_map)
    return out, checks
