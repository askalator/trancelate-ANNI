import os, json
from typing import List
# lang wird über sys.path in mt_guard.py importiert

def _default_list() -> list[str]:
    return ["en-US","en-GB","de-DE","de-AT","fr-FR","it-IT","es-ES","pt-PT","pt-BR","nl-NL","sv-SE","da-DK","nb-NO","fi-FI","pl-PL","cs-CZ","sk-SK","sl-SI","hr-HR","ro-RO","hu-HU","tr-TR","el-GR","ru-RU","uk-UA","he-IL","ar-SA","fa-IR","ur-PK","ps-AF","hi-IN","bn-BD","ta-IN","te-IN","mr-IN","gu-IN","pa-IN","ja-JP","ko-KR","zh-CN","zh-TW","th-TH","vi-VN","id-ID","ms-MY","fil-PH","km-KH","lo-LA","my-MM"]

def load_locales_list(locales_path: str | None, locales_extra: str, locales_disable: str) -> list[str]:
    base: List[str] = []
    if locales_path:
        try:
            with open(locales_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("locales"), list):
                base = [str(x).strip() for x in data["locales"] if str(x).strip()]
            elif isinstance(data, list):
                base = [str(x).strip() for x in data if str(x).strip()]
        except Exception:
            base = _default_list()
    else:
        base = _default_list()

    extra = [s.strip() for s in locales_extra.split(",") if s.strip()]
    disable = {s.strip() for s in locales_disable.split(",") if s.strip()}
    all_codes = [c for c in (base + extra) if c not in disable]
    uniq: list[str] = []
    seen: set[str] = set()
    for c in all_codes:
        try:
            # lang wird über sys.path in mt_guard.py importiert
            import lang
            norm = lang.canonicalize_bcp47(c)
            if isinstance(norm, dict):
                norm = norm.get("bcp47", c)
            elif not isinstance(norm, str):
                norm = c
        except Exception:
            norm = c
        if norm and norm not in seen:
            seen.add(norm)
            uniq.append(norm)
    return sorted(uniq)

def map_locales_with_engine(codes: list[str]) -> list[dict]:
    out = []
    for code in codes:
        try:
            # lang wird über sys.path in mt_guard.py importiert
            import lang
            n = lang.normalize_lang_input(code)
            out.append({"bcp47": n.get("bcp47", code), "engine": n.get("engine", (code.split("-")[0] if code else ""))})
        except Exception:
            out.append({"bcp47": code, "engine": (code.split("-")[0] if code else "")})
    return out
