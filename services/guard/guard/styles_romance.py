import re as _re
from typing import Set

# Minimal-maps (konservativ): Pronomen + Possessiva. Keine Verbformen.
# Wir mappen "du/sie" (ANNI-Style) auf informal/formal je Sprache.

_FR_INFORMAL = [
    (r"\b[Vv]ous\b", "tu"),
    (r"\b[Vv]otre\b", "ton"),
    (r"\b[Vv]os\b", "tes")
]
_FR_FORMAL = [
    (r"\b[Tt]u\b", "vous"),
    (r"\b[Tt]on\b", "votre"),
    (r"\b[Tt]a\b", "votre"),
    (r"\b[Tt]es\b", "vos"),
]

_IT_INFORMAL = [
    (r"\b[Ll]ei\b", "tu"),
    (r"\b[Ll]e\b", "ti"),      # Dat/Obj grob
    (r"\b[Ss]uo[ai]\b", "tuo"), # sua/suo → tuo (grobe Vereinfachung)
    (r"\b[Ss]uoi\b", "tuoi"),
    (r"\b[Ss]ue\b", "tue"),
]
_IT_FORMAL = [
    (r"\b[Tt]u\b", "Lei"),
    (r"\b[Tt]i\b", "Le"),
    (r"\b[Tt]uo[ai]\b", "Suo"),  # tuo/tua → Suo
    (r"\b[Tt]uoi\b", "Suoi"),
    (r"\b[Tt]ue\b", "Sue"),
]

_ES_INFORMAL = [
    (r"\b[Uu]sted(es)?\b", "tú"),
    (r"\b[Ss]u(s)?\b", "tu"),        # su/sus → tu (vereinfachend)
    (r"\b[Ll]e(s)?\b", "te"),
]
_ES_FORMAL = [
    (r"\b[Tt]ú\b", "usted"),
    (r"\b[Tt]u\b", "su"),
    (r"\b[Tt]e\b", "le"),
]

_PT_INFORMAL = [
    (r"\b[Vv]ocê(s)?\b", "tu"),
    (r"\b[Ss]eu(s)?\b", "teu"),
    (r"\b[Ss]ua(s)?\b", "tua"),
]
_PT_FORMAL = [
    (r"\b[Tt]u\b", "você"),
    (r"\b[Tt]eu(s)?\b", "seu"),
    (r"\b[Tt]ua(s)?\b", "sua"),
]

def _apply_pairs(text: str, pairs: list[tuple[str,str]]) -> str:
    out = text
    for pat, rep in pairs:
        out = _re.sub(pat, rep, out)
    return out

def apply_style_romance_safe(text: str, lang_engine: str, address: str, invariants, keep_terms: Set[str] | None = None):
    # Invarianten schützen; wir operieren auf gefrorenem Text, die Tokens kollidieren nicht.
    frozen, mapping = invariants.freeze_invariants(text)
    t = frozen
    addr = (address or "").lower()
    le = (lang_engine or "").lower()

    if addr in ("", "auto", None):
        return text, {"ok": True}

    # du/sie -> informal/formal
    informal = addr in ("du", "informal")
    formal   = addr in ("sie", "formal")

    if le == "fr":
        if informal: t = _apply_pairs(t, _FR_INFORMAL)
        elif formal: t = _apply_pairs(t, _FR_FORMAL)
    elif le == "it":
        if informal: t = _apply_pairs(t, _IT_INFORMAL)
        elif formal: t = _apply_pairs(t, _IT_FORMAL)
    elif le == "es":
        if informal: t = _apply_pairs(t, _ES_INFORMAL)
        elif formal: t = _apply_pairs(t, _ES_FORMAL)
    elif le == "pt":
        if informal: t = _apply_pairs(t, _PT_INFORMAL)
        elif formal: t = _apply_pairs(t, _PT_FORMAL)
    else:
        return text, {"ok": True}

    # Validierung (Invarianten ident)
    _, full_map = invariants.freeze_invariants(text)
    checks = invariants.validate_invariants(text, t, full_map)
    return t if checks.get("ok", False) else text, checks
