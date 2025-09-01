#!/usr/bin/env python3
"""
Language detection and BCP-47 canonicalization module for Guard service.
"""

import re
import os
from typing import Dict, List, Tuple, Any, Optional

# Try to import language detection libraries
try:
    import pycld3
    CLD3_AVAILABLE = True
except ImportError:
    CLD3_AVAILABLE = False

try:
    from langdetect import detect_langs, DetectorFactory
    DetectorFactory.seed = 0  # For reproducible results
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

# BCP-47 canonicalization aliases
BCP47_ALIASES = {
    # Regional variants
    "en-GB": "en-GB",
    "en-US": "en",
    "pt-BR": "pt-BR", 
    "pt-PT": "pt-PT",
    "de-AT": "de-AT",
    "de-CH": "de-CH",
    "fr-CA": "fr-CA",
    "es-MX": "es-MX",
    "es-AR": "es-AR",
    
    # Script variants
    "sr-Latn": "sr-Latn",
    "sr-Cyrl": "sr-Cyrl",
    "zh-CN": "zh-Hans",
    "zh-TW": "zh-Hant", 
    "zh-HK": "zh-Hant-HK",
    "zh-SG": "zh-Hans-SG",
    "zh-MO": "zh-Hant-MO",
    
    # Simple mappings
    "zh": "zh",
    "en": "en",
    "de": "de",
    "fr": "fr",
    "es": "es",
    "it": "it",
    "pt": "pt",
    "ru": "ru",
    "ja": "ja",
    "ko": "ko",
    "ar": "ar",
    "hi": "hi",
    "th": "th",
    "vi": "vi",
    "nl": "nl",
    "pl": "pl",
    "tr": "tr",
    "sv": "sv",
    "da": "da",
    "no": "no",
    "fi": "fi",
    "cs": "cs",
    "sk": "sk",
    "hu": "hu",
    "ro": "ro",
    "bg": "bg",
    "hr": "hr",
    "sl": "sl",
    "et": "et",
    "lv": "lv",
    "lt": "lt",
    "mt": "mt",
    "ga": "ga",
    "cy": "cy",
    "eu": "eu",
    "ca": "ca",
    "gl": "gl",
    "is": "is",
    "mk": "mk",
    "sq": "sq",
    "bs": "bs",
    "me": "me",
    "sr": "sr",
    "uk": "uk",
    "be": "be",
    "kk": "kk",
    "ky": "ky",
    "uz": "uz",
    "tg": "tg",
    "mn": "mn",
    "ka": "ka",
    "hy": "hy",
    "az": "az",
    "fa": "fa",
    "ps": "ps",
    "ur": "ur",
    "bn": "bn",
    "ta": "ta",
    "te": "te",
    "ml": "ml",
    "kn": "kn",
    "gu": "gu",
    "pa": "pa",
    "or": "or",
    "as": "as",
    "ne": "ne",
    "si": "si",
    "my": "my",
    "km": "km",
    "lo": "lo",
    "id": "id",
    "ms": "ms",
    "tl": "tl",
    "jv": "jv",
    "su": "su",
    "ceb": "ceb",
    "war": "war",
    "haw": "haw",
    "mi": "mi",
    "sm": "sm",
    "to": "to",
    "fj": "fj",
    "yue": "yue",
    "nan": "nan",
    "hak": "hak",
    "gan": "gan",
    "wuu": "wuu",
    "cmn": "zh",
    "cdo": "zh",
    "cjy": "zh",
    "hsn": "zh",
    "cpx": "zh",
    "czh": "zh",
    "czo": "zh",
    "gan": "zh",
    "hak": "zh",
    "nan": "zh",
    "wuu": "zh",
    "yue": "zh",
}

# Simple underscore to hyphen mappings
SIMPLE_MAP = {
    "en_GB": "en-GB",
    "en_US": "en-US", 
    "pt_BR": "pt-BR",
    "pt_PT": "pt-PT",
    "de_AT": "de-AT",
    "de_CH": "de-CH",
    "fr_CA": "fr-CA",
    "es_MX": "es-MX",
    "es_AR": "es-AR",
    "zh_CN": "zh-CN",
    "zh_TW": "zh-TW",
    "zh_HK": "zh-HK",
    "sr_Latn": "sr-Latn",
    "sr_Cyrl": "sr-Cyrl",
}

def canonicalize(code: str) -> Dict[str, Any]:
    """
    Canonicalize a language code to BCP-47 format.
    
    Args:
        code: Input language code (e.g., "en", "en-GB", "zh-CN")
        
    Returns:
        Dict with canonicalized BCP-47 info:
        {
            "input": "en-GB",
            "lang": "en", 
            "script": None,
            "region": "GB",
            "bcp47": "en-GB",
            "alias_applied": True
        }
    """
    if not code:
        return {
            "input": code,
            "lang": None,
            "script": None, 
            "region": None,
            "bcp47": None,
            "alias_applied": False
        }
    
    original_code = code
    alias_applied = False
    
    # Step 1: Normalize separators (underscore to hyphen)
    if code in SIMPLE_MAP:
        code = SIMPLE_MAP[code]
        alias_applied = True
    
    # Step 2: Handle lowercase inputs for common codes
    if code.lower() in ["zh-cn", "zh-tw", "zh-hk", "zh-sg", "zh-mo"]:
        code = code.lower()
        alias_applied = True
    
    # Step 3: Apply BCP-47 aliases
    if code in BCP47_ALIASES:
        code = BCP47_ALIASES[code]
        alias_applied = True
    
    # Step 3: Parse BCP-47 components
    parts = code.split('-')
    lang = parts[0].lower() if parts else None
    
    script = None
    region = None
    
    if len(parts) > 1:
        # Check if second part is script (4 chars, Titlecase) or region (2-3 chars, UPPER)
        second_part = parts[1]
        if len(second_part) == 4 and second_part[0].isupper():
            script = second_part
            if len(parts) > 2:
                region = parts[2].upper()
        else:
            region = second_part.upper()
            if len(parts) > 2:
                script = parts[2]
    
    # Step 4: Build canonical BCP-47
    bcp47_parts = [lang]
    if script:
        bcp47_parts.append(script)
    if region:
        bcp47_parts.append(region)
    
    bcp47 = '-'.join(bcp47_parts) if bcp47_parts else None
    
    return {
        "input": original_code,
        "lang": lang,
        "script": script,
        "region": region,
        "bcp47": bcp47,
        "alias_applied": alias_applied
    }

def parse_accept_language(header: str) -> List[Dict[str, Any]]:
    """
    Parse Accept-Language header according to RFC 7231.
    
    Args:
        header: Accept-Language header value (e.g., "en-GB,en;q=0.8,de;q=0.6")
        
    Returns:
        List of {"code": "en-GB", "q": 1.0} dicts, sorted by quality (highest first)
    """
    if not header:
        return []
    
    result = []
    
    # Split by comma and parse each language range
    for part in header.split(','):
        part = part.strip()
        if not part:
            continue
            
        # Split by semicolon to separate language from quality
        if ';' in part:
            lang_part, q_part = part.split(';', 1)
            lang = lang_part.strip()
            
            # Extract quality value
            q_match = re.search(r'q=([0-9.]+)', q_part)
            if q_match:
                try:
                    q = float(q_match.group(1))
                except ValueError:
                    q = 1.0
            else:
                q = 1.0
        else:
            lang = part.strip()
            q = 1.0
        
        if lang and q >= 0:
            result.append({"code": lang, "q": q})
    
    # Sort by quality (highest first)
    result.sort(key=lambda x: x["q"], reverse=True)
    return result

def detect_lang(text: str, top_k: int = 3, accept_lang: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Detect language of text using multiple engines with improved robustness.
    
    Args:
        text: Text to analyze
        top_k: Number of top candidates to return
        accept_lang: Optional list of Accept-Language codes for hints
        
    Returns:
        Dict with detection results:
        {
            "engine": "cld3|langdetect|heuristic",
            "candidates": [
                {"lang": "de", "score": 0.99, "reliable": True, "bcp47": "de"},
                ...
            ]
        }
    """
    if not text or len(text.strip()) == 0:
        candidates = [{"lang": "en", "score": 0.5, "reliable": False, "bcp47": "en"}]
        recommendation = build_recommendation(candidates, accept_lang)
        return {
            "engine": "heuristic",
            "candidates": candidates,
            "recommendation": recommendation
        }
    
    # Helper function to calculate ASCII quote
    def get_ascii_quote(text: str) -> float:
        ascii_chars = len(re.findall(r'[A-Za-z0-9 ,.;:!?$%/()-]', text))
        return ascii_chars / len(text) if text else 0.0
    
    # Helper function to apply boosts with improved EN detection
    def apply_boosts(candidates: List[Dict[str, Any]], text: str, accept_lang: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        text_lower = text.lower()
        
        # Enhanced English lexeme hints
        EN_HINTS = {"the", "and", "to", "for", "see", "only", "now", "usd", "price", "click", "here", "learn", "more", "buy", "with", "from", "this", "that", "have", "are", "was", "will", "can", "get", "use", "time", "way", "day", "work", "first", "new", "good", "other", "some", "very", "when", "make", "like", "into", "him", "two", "has", "look", "go", "no", "way", "could", "my", "than", "been", "call", "who", "its", "find", "long", "down", "did", "come", "made", "may", "part"}
        
        # Count English lexeme hits
        import re
        words = re.findall(r'\w+', text_lower)
        en_hits = sum(1 for word in words if word in EN_HINTS)
        boost_en = min(0.02 * en_hits, 0.12) + (0.13 if "usd" in text_lower else 0)
        
        # Find English candidate or create one
        en_candidate = None
        for candidate in candidates:
            if candidate["lang"] == "en":
                en_candidate = candidate
                break
        
        if en_candidate:
            en_candidate["score"] += boost_en
        elif boost_en > 0.05:  # Only add if significant boost
            # Create English candidate
            en_canon = canonicalize("en")
            en_candidate = {
                "lang": "en",
                "score": boost_en,
                "reliable": boost_en > 0.1,
                "bcp47": en_canon["bcp47"]
            }
            candidates.append(en_candidate)
        
        # Apply Accept-Language weighting (stronger)
        for candidate in candidates:
            if accept_lang:
                for accept_code in accept_lang:
                    accept_canon = canonicalize(accept_code)
                    if accept_canon["lang"] == candidate["lang"]:
                        # For now, use default q=1.0 since accept_lang is list of strings
                        candidate["score"] += 0.3
                        break
            
            # Clamp score to [0, 1]
            candidate["score"] = max(0.0, min(1.0, candidate["score"]))
        
        return candidates
    
    # Helper function for improved recommendation logic
    def build_recommendation(candidates: List[Dict[str, Any]], accept_lang: Optional[List[str]] = None) -> Dict[str, Any]:
        """Build recommendation with threshold logic and Accept-Language preference"""
        if not candidates:
            return {"bcp47": "en", "from": "fallback"}
        
        # Sort by score
        candidates.sort(key=lambda x: x["score"], reverse=True)
        best = candidates[0]
        
        # Check if Accept-Language should override
        if accept_lang:
            for accept_code in accept_lang:
                accept_canon = canonicalize(accept_code)
                accept_lang_prefix = accept_canon["lang"]
                
                # Find candidates with matching language prefix
                for candidate in candidates:
                    if candidate["lang"] == accept_lang_prefix:
                        # If score is within 0.25 of best score, prefer Accept-Language
                        if best["score"] - candidate["score"] <= 0.25:
                            best = candidate
                            break
                if best["lang"] == accept_lang_prefix:
                    break
        
        # Build recommendation
        recommendation = {
            "bcp47": best["bcp47"],
            "from": "model"
        }
        
        # If chosen language is "en" and Accept-Language has region info, use it
        if best["lang"] == "en" and accept_lang:
            for accept_code in accept_lang:
                accept_canon = canonicalize(accept_code)
                if accept_canon["lang"] == "en" and accept_canon["region"]:
                    recommendation["bcp47"] = accept_canon["bcp47"]
                    recommendation["from"] = "accept-language"
                    break
        
        return recommendation
    
    # Step 1: Try pycld3
    if CLD3_AVAILABLE:
        try:
            results = pycld3.get_frequent_languages(text, num_langs=top_k)
            candidates = []
            
            for result in results:
                lang_code = result.language
                prob = result.probability
                is_reliable = result.is_reliable
                
                # Canonicalize the language code
                canon = canonicalize(lang_code)
                
                candidates.append({
                    "lang": lang_code,
                    "score": prob,
                    "reliable": is_reliable,
                    "bcp47": canon["bcp47"]
                })
            
            if candidates:
                # Apply boosts and re-sort
                candidates = apply_boosts(candidates, text, accept_lang)
                candidates.sort(key=lambda x: x["score"], reverse=True)
                
                # Build recommendation
                recommendation = build_recommendation(candidates, accept_lang)
                
                return {
                    "engine": "cld3",
                    "candidates": candidates,
                    "recommendation": recommendation
                }
        except Exception:
            pass
    
    # Step 2: Try langdetect with short-text smoothing
    if LANGDETECT_AVAILABLE:
        try:
            # Multiple runs for short texts (increased for better accuracy)
            n_runs = 9 if len(text) < 140 else 1
            all_results = []
            
            for _ in range(n_runs):
                try:
                    results = detect_langs(text)
                    all_results.extend(results)
                except Exception:
                    continue
            
            if all_results:
                # Aggregate results by language
                lang_counts = {}
                lang_scores = {}
                
                for result in all_results:
                    lang = result.lang
                    prob = result.prob
                    
                    if lang not in lang_counts:
                        lang_counts[lang] = 0
                        lang_scores[lang] = 0.0
                    
                    lang_counts[lang] += 1
                    lang_scores[lang] += prob
                
                # Calculate average scores
                candidates = []
                for lang, count in lang_counts.items():
                    avg_score = lang_scores[lang] / count
                    # Normalize by frequency for short texts
                    if n_runs > 1:
                        avg_score = avg_score * (count / n_runs)
                    
                    # Canonicalize the language code
                    canon = canonicalize(lang)
                    
                    candidates.append({
                        "lang": lang,
                        "score": avg_score,
                        "reliable": avg_score > 0.5,
                        "bcp47": canon["bcp47"]
                    })
                
                # Sort and take top_k
                candidates.sort(key=lambda x: x["score"], reverse=True)
                candidates = candidates[:top_k]
                
                if candidates:
                    # Apply boosts and re-sort
                    candidates = apply_boosts(candidates, text, accept_lang)
                    candidates.sort(key=lambda x: x["score"], reverse=True)
                    
                    # Build recommendation
                    recommendation = build_recommendation(candidates, accept_lang)
                    
                    return {
                        "engine": "langdetect",
                        "candidates": candidates,
                        "recommendation": recommendation
                    }
        except Exception:
            pass
    
    # Step 3: Fallback heuristic with improved detection
    text_lower = text.lower()
    
    # Devanagari script (Hindi, Marathi, etc.)
    if re.search(r'[\u0900-\u097F]', text):
        candidates = [{"lang": "hi", "score": 0.8, "reliable": True, "bcp47": "hi"}]
        recommendation = build_recommendation(candidates, accept_lang)
        return {
            "engine": "heuristic",
            "candidates": candidates,
            "recommendation": recommendation
        }
    
    # Hangul script (Korean)
    if re.search(r'[\uAC00-\uD7AF]', text):
        candidates = [{"lang": "ko", "score": 0.8, "reliable": True, "bcp47": "ko"}]
        recommendation = build_recommendation(candidates, accept_lang)
        return {
            "engine": "heuristic",
            "candidates": candidates,
            "recommendation": recommendation
        }
    
    # CJK Unified Ideographs (Chinese, Japanese)
    if re.search(r'[\u4E00-\u9FFF]', text):
        candidates = [{"lang": "zh", "score": 0.7, "reliable": True, "bcp47": "zh"}]
        recommendation = build_recommendation(candidates, accept_lang)
        return {
            "engine": "heuristic",
            "candidates": candidates,
            "recommendation": recommendation
        }
    
    # Hiragana/Katakana (Japanese)
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
        candidates = [{"lang": "ja", "score": 0.8, "reliable": True, "bcp47": "ja"}]
        recommendation = build_recommendation(candidates, accept_lang)
        return {
            "engine": "heuristic",
            "candidates": candidates,
            "recommendation": recommendation
        }
    
    # Arabic script
    if re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text):
        candidates = [{"lang": "ar", "score": 0.7, "reliable": True, "bcp47": "ar"}]
        recommendation = build_recommendation(candidates, accept_lang)
        return {
            "engine": "heuristic",
            "candidates": candidates,
            "recommendation": recommendation
        }
    
    # Thai script
    if re.search(r'[\u0E00-\u0E7F]', text):
        candidates = [{"lang": "th", "score": 0.8, "reliable": True, "bcp47": "th"}]
        recommendation = build_recommendation(candidates, accept_lang)
        return {
            "engine": "heuristic",
            "candidates": candidates,
            "recommendation": recommendation
        }
    
    # Default to English with ASCII quote consideration
    ascii_quote = get_ascii_quote(text)
    en_score = 0.5 + (ascii_quote * 0.3)  # Boost English for high ASCII content
    
    candidates = [{"lang": "en", "score": en_score, "reliable": ascii_quote > 0.7, "bcp47": "en"}]
    recommendation = build_recommendation(candidates, accept_lang)
    return {
        "engine": "heuristic",
        "candidates": candidates,
        "recommendation": recommendation
    }

def canonicalize_bcp47(code: str) -> Dict[str, Any]:
    """
    Canonicalize a BCP-47 language code with proper normalization.
    
    Args:
        code: Input BCP-47 code (e.g., "en-GB", "pt-BR", "de-AT", "zh-CN")
        
    Returns:
        Dict with canonicalized BCP-47 info:
        {
            "input": "en-GB",
            "lang": "en", 
            "script": None,
            "region": "GB",
            "bcp47": "en-GB",
            "alias_applied": True
        }
    """
    if not code:
        return {
            "input": code,
            "lang": None,
            "script": None, 
            "region": None,
            "bcp47": None,
            "alias_applied": False
        }
    
    # Use existing canonicalize function
    result = canonicalize(code)
    
    # Ensure proper BCP-47 formatting
    if result["bcp47"]:
        parts = result["bcp47"].split('-')
        lang = parts[0].lower() if parts else None
        
        script = None
        region = None
        
        if len(parts) > 1:
            # Check if second part is script (4 chars, Titlecase) or region (2-3 chars, UPPER)
            second_part = parts[1]
            if len(second_part) == 4 and second_part[0].isupper():
                script = second_part
                if len(parts) > 2:
                    region = parts[2].upper()
            else:
                region = second_part.upper()
                if len(parts) > 2:
                    script = parts[2]
        
        # Build canonical BCP-47
        bcp47_parts = [lang]
        if script:
            bcp47_parts.append(script)
        if region:
            bcp47_parts.append(region)
        
        result["bcp47"] = '-'.join(bcp47_parts) if bcp47_parts else None
    
    return result

def engine_lang_from_bcp47(bcp47: str) -> str:
    """
    Map BCP-47 code to engine language code for M2M100.
    
    Args:
        bcp47: Canonicalized BCP-47 code
        
    Returns:
        Engine language code (e.g., "en", "pt", "de", "zh")
    """
    if not bcp47:
        return "en"  # Default fallback
    
    # Extract language part (first subtag)
    lang = bcp47.split('-')[0].lower()
    
    # Special mappings for languages with variants
    engine_mappings = {
        "en": "en",      # en-GB, en-US, en-AU, etc. → en
        "pt": "pt",      # pt-BR, pt-PT → pt
        "de": "de",      # de-AT, de-CH, de-DE → de
        "fr": "fr",      # fr-CA, fr-CH, fr-FR → fr
        "es": "es",      # es-MX, es-AR, es-ES → es
        "zh": "zh",      # zh-CN, zh-TW, zh-HK → zh
        "sr": "sr",      # sr-Latn, sr-Cyrl → sr
        "bs": "bs",      # bs-Latn, bs-Cyrl → bs
        "kk": "kk",      # kk-Cyrl, kk-Latn → kk
        "uz": "uz",      # uz-Cyrl, uz-Latn → uz
        "it": "it",      # it-CH, it-IT → it
        "nl": "nl",      # nl-BE, nl-NL → nl
        "sv": "sv",      # sv-FI, sv-SE → sv
        "da": "da",      # da-DK, da-GL → da
        "no": "no",      # no-NO, no-NB, no-NN → no
        "fi": "fi",      # fi-FI → fi
        "pl": "pl",      # pl-PL → pl
        "cs": "cs",      # cs-CZ → cs
        "sk": "sk",      # sk-SK → sk
        "hu": "hu",      # hu-HU → hu
        "ro": "ro",      # ro-RO → ro
        "bg": "bg",      # bg-BG → bg
        "hr": "hr",      # hr-HR → hr
        "sl": "sl",      # sl-SI → sl
        "et": "et",      # et-EE → et
        "lv": "lv",      # lv-LV → lv
        "lt": "lt",      # lt-LT → lt
        "mt": "mt",      # mt-MT → mt
        "ga": "ga",      # ga-IE → ga
        "cy": "cy",      # cy-GB → cy
        "eu": "eu",      # eu-ES → eu
        "ca": "ca",      # ca-ES → ca
        "gl": "gl",      # gl-ES → gl
        "is": "is",      # is-IS → is
        "mk": "mk",      # mk-MK → mk
        "sq": "sq",      # sq-AL → sq
        "me": "me",      # me-ME → me
        "uk": "uk",      # uk-UA → uk
        "be": "be",      # be-BY → be
        "ky": "ky",      # ky-KG → ky
        "tg": "tg",      # tg-TJ → tg
        "mn": "mn",      # mn-MN → mn
        "ka": "ka",      # ka-GE → ka
        "hy": "hy",      # hy-AM → hy
        "az": "az",      # az-AZ → az
        "fa": "fa",      # fa-IR → fa
        "ps": "ps",      # ps-AF → ps
        "ur": "ur",      # ur-PK → ur
        "bn": "bn",      # bn-BD → bn
        "ta": "ta",      # ta-IN → ta
        "te": "te",      # te-IN → te
        "ml": "ml",      # ml-IN → ml
        "kn": "kn",      # kn-IN → kn
        "gu": "gu",      # gu-IN → gu
        "pa": "pa",      # pa-IN → pa
        "or": "or",      # or-IN → or
        "as": "as",      # as-IN → as
        "ne": "ne",      # ne-NP → ne
        "si": "si",      # si-LK → si
        "my": "my",      # my-MM → my
        "km": "km",      # km-KH → km
        "lo": "lo",      # lo-LA → lo
        "id": "id",      # id-ID → id
        "ms": "ms",      # ms-MY → ms
        "tl": "tl",      # tl-PH → tl
        "jv": "jv",      # jv-ID → jv
        "su": "su",      # su-ID → su
        "ceb": "ceb",    # ceb-PH → ceb
        "war": "war",    # war-PH → war
        "haw": "haw",    # haw-US → haw
        "mi": "mi",      # mi-NZ → mi
        "sm": "sm",      # sm-WS → sm
        "to": "to",      # to-TO → to
        "fj": "fj",      # fj-FJ → fj
        "yue": "yue",    # yue-HK → yue
        "nan": "nan",    # nan-TW → nan
        "hak": "hak",    # hak-TW → hak
        "gan": "gan",    # gan-CN → gan
        "wuu": "wuu",    # wuu-CN → wuu
        "cmn": "zh",     # cmn-CN → zh (Mandarin)
        "cdo": "zh",     # cdo-CN → zh (Min Dong)
        "cjy": "zh",     # cjy-CN → zh (Jinyu)
        "hsn": "zh",     # hsn-CN → zh (Xiang)
        "cpx": "zh",     # cpx-CN → zh (Pu-Xian)
        "czh": "zh",     # czh-CN → zh (Hui)
        "czo": "zh",     # czo-CN → zh (Min Zhong)
        "gan": "zh",     # gan-CN → zh (Gan)
        "hak": "zh",     # hak-CN → zh (Hakka)
        "nan": "zh",     # nan-CN → zh (Min Nan)
        "wuu": "zh",     # wuu-CN → zh (Wu)
        "yue": "zh",     # yue-CN → zh (Yue)
    }
    
    return engine_mappings.get(lang, lang)

def normalize_lang_input(code: str) -> Dict[str, Any]:
    """
    Normalize language input by canonicalizing BCP-47 and mapping to engine code.
    
    Args:
        code: Input language code (e.g., "en-GB", "pt-BR", "de-AT")
        
    Returns:
        Dict with normalized language info:
        {
            "input": "en-GB",
            "bcp47": "en-GB",
            "engine": "en"
        }
    """
    if not code:
        return {
            "input": code,
            "bcp47": "en",
            "engine": "en"
        }
    
    # Canonicalize BCP-47
    canon = canonicalize_bcp47(code)
    
    # Map to engine code
    engine = engine_lang_from_bcp47(canon["bcp47"])
    
    return {
        "input": canon["input"],
        "bcp47": canon["bcp47"],
        "engine": engine
    }

def get_detector_preference() -> str:
    """Get preferred detector from environment variable."""
    return os.environ.get("DETECTOR_PREFERRED", "auto").lower()
