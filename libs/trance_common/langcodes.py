"""
Shared language code normalization for TranceLate services.
"""

def normalize(lang: str) -> str:
    """
    Normalize language code using aliases.
    
    Examples:
        en-US → en
        de-DE → de
        zh-CN → zh
        iw → he
        in → id
        pt-BR → pt
    """
    aliases = {
        "de-DE": "de",
        "en-US": "en",
        "en-GB": "en",
        "iw": "he",
        "in": "id",
        "pt-BR": "pt",
        "pt-PT": "pt",
        "zh-CN": "zh",
        "zh-TW": "zh",
        "zh-HK": "zh",
        "zh-SG": "zh"
    }
    
    return aliases.get(lang, lang.split('-')[0] if '-' in lang else lang)

def primary(lang: str) -> str:
    """
    Extract primary language subtag.
    
    Examples:
        en-US → en
        de-DE → de
        zh-CN → zh
    """
    return lang.split('-')[0] if '-' in lang else lang
