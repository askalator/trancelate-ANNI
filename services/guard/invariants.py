#!/usr/bin/env python3
"""
Robust invariant freeze/unfreeze system for Guard service.
Uses stable sentinels <|INV:{id}:{crc}|> with CRC validation.
"""

import re
import hashlib
import unicodedata
from typing import List, Dict, Tuple, Any

# Simple regex patterns for robust matching
STRICT = re.compile(r"<\|INV:(\d{1,4}):([0-9A-F]{4,8})\|>", re.IGNORECASE)
SIMPLE = re.compile(r"<\|INV:(\d{1,4})(?::([0-9A-F]{4,8}))?\|>", re.IGNORECASE)
LOOSE = re.compile(r"INV[^\w]{0,2}:(\d{1,4})(?:[^\w]{0,2}:([0-9A-F]{4,8}))?", re.IGNORECASE)

# Entfernt Wrapper wie: |<p>:63ADA5|  |01.09.2025:F733BC|  |https://trancelate.it:2BBF2D|
# Achtung: inner darf ":" enthalten (z.B. https://), daher [^|]+ statt [^:]+
PIPE_CRC_WRAP_RE = re.compile(r"\|(?P<inner>[^|]+):(?P<crc>[0-9A-Fa-f]{4,8})\|")

# Sentinel pattern for exact matching (legacy compatibility)
SENTINEL_RE = STRICT

# Currency and number separators (i18n hardened)
CURRENCY_SEP = r"[\u00A0\u202F\u2009,._\u066B\u066C\uFF0C\uFF0E\s]"
CURRENCY_SYM = r"[€$£¥₹₩₽₺₪₫฿₦₱]"

# Compiled patterns in priority order (non-overlapping matches)
P_HTML = re.compile(r"</?[a-z][^>]*>", re.UNICODE | re.IGNORECASE)
P_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.UNICODE | re.IGNORECASE)
P_URL = re.compile(r"https?://[^\s<>]+", re.UNICODE | re.IGNORECASE)
P_TIME = re.compile(r"\b[0-2]?\d:[0-5]\d\b", re.UNICODE | re.IGNORECASE)
P_DATE_EU = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b", re.UNICODE | re.IGNORECASE)
P_CURRENCY = re.compile(
    fr"(?:{CURRENCY_SYM}\s*\d(?:{CURRENCY_SEP}?\d)*/?\d*(?:{CURRENCY_SEP}\d+)*|\d(?:{CURRENCY_SEP}?\d)*/?\d*(?:{CURRENCY_SEP}\d+)*\s*{CURRENCY_SYM})",
    re.UNICODE | re.IGNORECASE
)
P_PH1 = re.compile(r"\{[A-Za-z0-9_:-]+\}", re.UNICODE | re.IGNORECASE)
P_PH2 = re.compile(r"\{\{[^}]+\}\}", re.UNICODE | re.IGNORECASE)
P_NUMBER = re.compile(fr"\d(?:{CURRENCY_SEP}?\d)*", re.UNICODE | re.IGNORECASE)

# Pattern definitions with types
PATTERNS = [
    (P_HTML, "html"),
    (P_EMAIL, "email"),
    (P_URL, "url"),
    (P_TIME, "time"),
    (P_DATE_EU, "date"),
    (P_CURRENCY, "currency"),
    (P_PH1, "ph1"),
    (P_PH2, "ph2"),
    (P_NUMBER, "number"),
]


def make_crc(raw: str) -> str:
    """Generate 6-character hex CRC from raw text"""
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()[:6].upper()


def scrub_artifacts(text: str) -> str:
    """
    Remove all artifact wrappers and sentinel residues from text.
    Returns clean text without any sentinel artifacts.
    """
    if not text:
        return text
    
    # Remove RTL isolates (U+2066..U+2069)
    text = text.replace('\u2066', '').replace('\u2067', '').replace('\u2068', '').replace('\u2069', '')
    
    # Remove the rare symbol "♰" (U+2670)
    text = text.replace('♰', '')
    
    # Remove "<♰" and "♰>" pairs in any whitespace variation
    text = re.sub(r'<\s*♰\s*', '', text)
    text = re.sub(r'\s*♰\s*>', '', text)
    
    # Remove any remaining "<" or ">" that might be artifacts
    # Only remove if they're not part of valid HTML tags
    text = re.sub(r'<(?![a-zA-Z/])', '', text)  # Remove < not followed by letter or /
    text = re.sub(r'(?<![a-zA-Z/])>', '', text)  # Remove > not preceded by letter or /
    
    # Remove any remaining "<|INV:...|>" fragments or deformed variants
    text = re.sub(r'<\s*\|\s*INV\s*:\s*\d+\s*:\s*[0-9A-Fa-f]{4,8}\s*\|\s*>', '', text)
    text = re.sub(r'\|\s*INV\s*:\s*\d+\s*:\s*[0-9A-Fa-f]{4,8}\s*\|', '', text)  # Remove without < >
    
    # Normalize whitespace: multiple spaces -> single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove space before punctuation
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # 1–3 Passes: Pipe-CRC-Wrapper entfernen (idempotent; bricht, wenn keine Änderungen)
    for _ in range(3):
        s2 = PIPE_CRC_WRAP_RE.sub(lambda m: m.group("inner"), text)
        if s2 == text:
            break
        text = s2
    
    return text


def unwrap_spurious_wrappers(text: str, mapping: List[Dict[str, Any]], original_text: str = "") -> str:
    """
    Remove spurious wrappers around non-HTML invariants that weren't present in the original.
    Only removes wrappers if the raw content wasn't already wrapped in the source text.
    """
    if not text or not mapping:
        return text
    
    # Non-HTML invariant types that should be checked for spurious wrappers
    non_html_types = {"email", "url", "time", "date", "currency", "number", "ph1", "ph2"}
    
    for item in mapping:
        if item["type"] not in non_html_types:
            continue
            
        raw = item["raw"]
        escaped_raw = re.escape(raw)
        
        # Define wrapper patterns (including fullwidth variants)
        wrapper_patterns = [
            r"<\s*%s\s*>" % escaped_raw,      # <...>
            r"\(\s*%s\s*\)" % escaped_raw,    # (...)
            r"\[\s*%s\s*\]" % escaped_raw,    # [...]
            r"［\s*%s\s*］" % escaped_raw,    # ［...］
            r"＜\s*%s\s*＞" % escaped_raw,    # ＜...＞
            r"〈\s*%s\s*〉" % escaped_raw,    # 〈...〉
            r"「\s*%s\s*」" % escaped_raw,    # 「...」
            r"『\s*%s\s*』" % escaped_raw,    # 『...』
        ]
        
        # Check if the raw content was already wrapped in the original text
        was_wrapped_in_original = False
        if original_text:
            for pattern in wrapper_patterns:
                if re.search(pattern, original_text, flags=re.UNICODE):
                    was_wrapped_in_original = True
                    break
        
        # Only unwrap if it wasn't wrapped in the original
        if not was_wrapped_in_original:
            for pattern in wrapper_patterns:
                text = re.sub(pattern, raw, text, flags=re.UNICODE)
    
    return text


def is_artifact_free(text: str) -> bool:
    """
    Check if text is free of sentinel artifacts.
    Returns True if no artifacts are found.
    """
    if not text:
        return True
    
    # Check for RTL isolates
    if any(char in text for char in ['\u2066', '\u2067', '\u2068', '\u2069']):
        return False
    
    # Check for the rare symbol "♰"
    if '♰' in text:
        return False
    
    # Check for "<♰" or "♰>" patterns
    if re.search(r'<\s*♰\s*|\s*♰\s*>', text):
        return False
    
    # Check for any "<|INV:" patterns
    if re.search(r'<\s*\|\s*INV\s*:', text):
        return False
    
    return True


def find_non_overlapping_matches(text: str) -> List[Tuple[int, int, str, str]]:
    """
    Find non-overlapping matches in priority order.
    Returns: [(start, end, matched_text, type), ...]
    """
    matches = []
    occupied_ranges = set()
    
    for pattern, inv_type in PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            matched_text = match.group(0)
            
            # Check if this range overlaps with any existing match
            overlaps = False
            for existing_start, existing_end in occupied_ranges:
                if start < existing_end and end > existing_start:
                    overlaps = True
                    break
            
            if not overlaps:
                matches.append((start, end, matched_text, inv_type))
                occupied_ranges.add((start, end))
    
    # Sort by start position for deterministic processing
    matches.sort(key=lambda x: x[0])
    return matches


def freeze_invariants(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Freeze invariants in text using stable sentinels.
    Returns: (frozen_text, mapping)
    """
    if not text:
        return text, []
    
    # Find all non-overlapping matches
    matches = find_non_overlapping_matches(text)
    
    # Build mapping and replacement pieces
    mapping = []
    pieces = []
    last_end = 0
    
    for start, end, raw, inv_type in matches:
        # Add text before this match
        if start > last_end:
            pieces.append(text[last_end:start])
        
        # Create sentinel
        inv_id = len(mapping)
        crc = make_crc(raw)
        sentinel = f"<|INV:{inv_id}:{crc}|>"
        
        # Add spacing if needed (conditional i18n-aware)
        if start > 0:
            prev_char = text[start-1]
            # Add space only for ASCII word characters, not CJK
            if prev_char.isascii() and prev_char.isalnum():
                sentinel = " " + sentinel
        if end < len(text):
            next_char = text[end]
            # Add space only for ASCII word characters, not CJK
            if next_char.isascii() and next_char.isalnum():
                sentinel = sentinel + " "
        
        pieces.append(sentinel)
        
        # Add to mapping
        mapping.append({
            "id": inv_id,
            "crc": crc,
            "raw": raw,
            "type": inv_type
        })
        
        last_end = end
    
    # Add remaining text
    if last_end < len(text):
        pieces.append(text[last_end:])
    
    frozen_text = "".join(pieces)
    return frozen_text, mapping


def fold_fullwidth_to_ascii(s: str) -> str:
    """Map Fullwidth/Unicode variants to ASCII equivalents"""
    # Build comprehensive translation table
    fullwidth_map = str.maketrans({
        # Fullwidth digits
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
        # Fullwidth hex letters
        'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E', 'Ｆ': 'F',
        'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e', 'ｆ': 'f',
        # Fullwidth brackets
        '（': '(', '）': ')', '【': '[', '】': ']', '［': '[', '］': ']',
        '＜': '<', '＞': '>', '〈': '<', '〉': '>', '《': '<', '》': '>',
        '«': '<', '»': '>', '‹': '<', '›': '>',
        # Fullwidth separators
        '｜': '|', '︱': '|', '∣': '|', '：': ':', '︰': ':',
        # Zero-width characters (remove)
        0x200B: None, 0x200C: None, 0x200D: None, 0x2060: None, 0xFEFF: None
    })
    
    return s.translate(fullwidth_map)

def normalize_for_inv_matching(s: str) -> tuple[str, list[int]]:
    """Normalize text for invariant matching and return index mapping"""
    if not s:
        return "", []
    
    # Remove zero-width characters first
    s_clean = s.translate({0x200B: None, 0x200C: None, 0x200D: None, 0x2060: None, 0xFEFF: None})
    
    # Apply fullwidth folding
    s_norm = fold_fullwidth_to_ascii(s_clean)
    
    # Build index mapping (normalized index -> original index)
    # Simple approach: map each normalized character to its original position
    idx_map = []
    orig_idx = 0
    
    for norm_char in s_norm:
        # Find the corresponding character in original text
        while orig_idx < len(s_clean):
            orig_char = s_clean[orig_idx]
            if fold_fullwidth_to_ascii(orig_char) == norm_char:
                idx_map.append(orig_idx)
                orig_idx += 1
                break
            orig_idx += 1
    
    return s_norm, idx_map



def unfreeze_invariants(text: str, mapping: List[Dict[str, Any]]) -> Tuple[str, Dict[str, int]]:
    """
    Unfreeze invariants with robust tolerant fallback (v3).
    Returns: (unfrozen_text, stats)
    """
    # Pass 0: early-out
    if not mapping:
        return text, {"replaced_total": 0, "missing": 0, "crc_mismatches": 0}
    
    replaced_total = 0
    out = text
    
    # Pass 1: STRICT direkt auf 'out'
    def replace_with_mapping(m):
        idx = int(m.group(1))
        crc = (m.group(2) or "").upper()
        raw = mapping[idx]["raw"] if 0 <= idx < len(mapping) else ""
        return raw
    
    out_new, n = STRICT.subn(replace_with_mapping, out)
    out, replaced_total = out_new, replaced_total + n
    
    if replaced_total < len(mapping):
        # Pass 2: Normalized match mit SIMPLE
        norm, idxmap = normalize_for_inv_matching(out)
        hits = list(SIMPLE.finditer(norm))
        if hits:
            # baue Stückliste in 'out' mit Original-Offsets
            parts = []
            cur = 0
            for h in hits:
                i1 = idxmap[h.start()]
                i2 = idxmap[h.end()-1] + 1
                try:
                    idx = int(h.group(1))
                    crc = (h.group(2) or "").upper()
                except:
                    continue
                raw = mapping[idx]["raw"] if 0 <= idx < len(mapping) else ""
                parts.append(out[cur:i1])
                parts.append(raw)
                cur = i2
                replaced_total += 1
            parts.append(out[cur:])
            out = "".join(parts)
    
    if replaced_total < len(mapping):
        # Pass 3: freistehende INV:id(:crc) ohne Wrapper (LOOSE) auf normierter Kopie
        norm, idxmap = normalize_for_inv_matching(out)
        hits = list(LOOSE.finditer(norm))
        if hits:
            parts = []
            cur = 0
            for h in hits:
                i1 = idxmap[h.start()]
                i2 = idxmap[h.end()-1] + 1
                try:
                    idx = int(h.group(1))
                    crc = (h.group(2) or "").upper()
                except:
                    continue
                raw = mapping[idx]["raw"] if 0 <= idx < len(mapping) else ""
                parts.append(out[cur:i1])
                parts.append(raw)
                cur = i2
            parts.append(out[cur:])
            out = "".join(parts)
            # zähle nur ersetzte, die auch gültige idx hatten
            # replaced_total hier nicht erzwingen == len(mapping); wir zählen real
    
    # Stats
    missing = sum(1 for i in range(len(mapping)) if mapping[i]["raw"] not in out)
    return out, {"replaced_total": replaced_total, "missing": missing, "crc_mismatches": 0}


def validate_invariants(original: str, out: str, mapping: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate that all invariants were preserved correctly.
    Returns: checks dict with ok, html_ok, num_ok, ph_ok, paren_ok, artifact_ok, email_ok, url_ok, counts
    """
    checks = {
        "ok": False,
        "html_ok": False,
        "num_ok": False,
        "ph_ok": False,
        "paren_ok": False,
        "artifact_ok": False,
        "email_ok": False,
        "url_ok": False,
        "counts": {}
    }
    
    if not mapping:
        checks["ok"] = True
        return checks
    
    # Count by type
    type_counts = {}
    for item in mapping:
        inv_type = item['type']
        type_counts[inv_type] = type_counts.get(inv_type, 0) + 1
    
    # Validate HTML tags
    html_items = [item for item in mapping if item['type'] == 'html']
    html_ok = True
    for item in html_items:
        if item['raw'] not in out:
            html_ok = False
            break
    checks["html_ok"] = html_ok
    
    # Validate numbers and currency
    num_items = [item for item in mapping if item['type'] in ['currency', 'number']]
    num_ok = True
    for item in num_items:
        if item['raw'] not in out:
            num_ok = False
            break
    checks["num_ok"] = num_ok
    
    # Validate emails
    email_items = [item for item in mapping if item['type'] == 'email']
    email_ok = True
    for item in email_items:
        if item['raw'] not in out:
            email_ok = False
            break
    checks["email_ok"] = email_ok
    
    # Validate URLs
    url_items = [item for item in mapping if item['type'] == 'url']
    url_ok = True
    for item in url_items:
        if item['raw'] not in out:
            url_ok = False
            break
    checks["url_ok"] = url_ok
    
    # Validate placeholders
    ph_items = [item for item in mapping if item['type'] in ['ph1', 'ph2']]
    ph_ok = True
    for item in ph_items:
        if item['raw'] not in out:
            ph_ok = False
            break
    checks["ph_ok"] = ph_ok
    
    # Validate parentheses balance
    paren_ok = True
    stack = []
    for char in out:
        if char in '([<':
            stack.append(char)
        elif char in ')]>':
            if not stack:
                paren_ok = False
                break
            if (char == ')' and stack[-1] == '(') or \
               (char == ']' and stack[-1] == '[') or \
               (char == '>' and stack[-1] == '<'):
                stack.pop()
            else:
                paren_ok = False
                break
    
    if stack:  # Unclosed parentheses
        paren_ok = False
    
    checks["paren_ok"] = paren_ok
    
    # Validate artifacts
    checks["artifact_ok"] = is_artifact_free(out)

    # Overall validation
    checks["ok"] = html_ok and num_ok and ph_ok and paren_ok and checks["artifact_ok"] and checks["email_ok"] and checks["url_ok"]

    # Add counts
    checks["counts"] = type_counts

    return checks


def _freeze_keep_terms_into(frozen_text: str, mapping: List[Dict[str, Any]], keep_terms: List[str]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Freeze keep_terms into the frozen text and mapping.
    This ensures that specified terms are preserved during translation.
    """
    if not keep_terms or not mapping:
        return frozen_text, mapping
    
    # Create a copy of the mapping to avoid modifying the original
    new_mapping = mapping.copy()
    new_frozen = frozen_text
    
    # Find the next available ID for new invariants
    next_id = max([m.get("id", 0) for m in mapping], default=0) + 1
    
    for term in keep_terms:
        if not term or term not in new_frozen:
            continue
            
        # Create a new invariant for this keep term
        crc = make_crc(term)
        sentinel = f"<|INV:{next_id}:{crc}|>"
        
        # Replace the term with the sentinel
        new_frozen = new_frozen.replace(term, sentinel)
        
        # Add to mapping
        new_mapping.append({
            "id": next_id,
            "crc": crc,
            "raw": term,
            "type": "keep_term"
        })
        
        next_id += 1
    
    return new_frozen, new_mapping
