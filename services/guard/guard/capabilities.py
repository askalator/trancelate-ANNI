from typing import Any, Dict, List
from .config import settings
from .locales import load_locales_list, map_locales_with_engine

# Sprachgruppen (für Marketing-Hinweise)
_SPANS_ONLY = ["zh-CN","zh-TW","ja-JP","ko-KR","th-TH","vi-VN","km-KH","lo-LA","my-MM","he-IL","ar-SA","fa-IR","ur-PK","ps-AF"]
_STYLE_DE = {
    "address": ["auto","du","sie","divers"],
    "gender": ["none","colon", "star", "innen"]
}
_STYLE_ROM = {
    "address": ["auto","du","sie"],
    "gender": ["none"]
}

def compute_capabilities(version: Dict[str, Any]) -> Dict[str, Any]:
    codes = load_locales_list(settings.LOCALES_PUBLIC_PATH, settings.LOCALES_EXTRA, settings.LOCALES_DISABLE)
    locs  = map_locales_with_engine(codes)
    engines = sorted({l["engine"] for l in locs if l.get("engine")})
    styles = {
        "de": _STYLE_DE,
        "fr": _STYLE_ROM,
        "it": _STYLE_ROM,
        "es": _STYLE_ROM,
        "pt": _STYLE_ROM
    }
    spans_only = [c for c in codes if c in _SPANS_ONLY]
    return {
        "version": version,
        "features": {
            "invariants": {
                "sentinel_format": "<|INV:ID:CRC|>",
                "protected": ["html","email","url","currency","number","date","time","placeholder"],
                "i18n_hardening": True
            },
            "styles": styles,
            "spans_only_locales": spans_only,
            "locales_count": len(locs),
            "engines": engines
        },
        "locales": locs
    }
