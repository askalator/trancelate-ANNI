"""
Shared invariant checking functionality.
Uses current effective-length logic (emoji/symbol run fold).
"""

import re
from typing import Dict, Any

# Emoji/symbol regex for effective length calculation
EMOJI_SYMBOL_RE = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\u2600-\u26FF\u2700-\u27BF]')

def _len_effective(text: str) -> int:
    """
    Calculate effective length by folding consecutive emoji/symbol runs to max 3 characters.
    """
    if not text:
        return 0
    
    # Find all emoji/symbol runs
    runs = []
    for match in EMOJI_SYMBOL_RE.finditer(text):
        runs.append((match.start(), match.end()))
    
    if not runs:
        return len(text)
    
    # Calculate effective length
    effective_len = len(text)
    for start, end in runs:
        run_len = end - start
        if run_len > 3:
            effective_len -= (run_len - 3)
    
    return effective_len

def check_invariants(src: str, out: str) -> Dict[str, Any]:
    """
    Check invariant preservation between source and output.
    
    Returns:
        Dict with ph_ok, html_ok, num_ok, paren_ok, len_ratio, len_ratio_eff, len_use
    """
    # Check placeholders
    ph_src = re.findall(r'\{\{[^}]+\}\}', src)
    ph_out = re.findall(r'\{\{[^}]+\}\}', out)
    ph_ok = len(ph_src) == len(ph_out) and set(ph_src) == set(ph_out)
    
    # Check HTML tags
    html_src = re.findall(r'<[^>]+>', src)
    html_out = re.findall(r'<[^>]+>', out)
    html_ok = len(html_src) == len(html_out) and set(html_src) == set(html_out)
    
    # Check numbers
    num_src = re.findall(r'\b\d+(?:[,\d]*\d)*(?:\.\d+)?(?:[–—]\d+(?:[,\d]*\d)*(?:\.\d+)?)?\b', src)
    num_out = re.findall(r'\b\d+(?:[,\d]*\d)*(?:\.\d+)?(?:[–—]\d+(?:[,\d]*\d)*(?:\.\d+)?)?\b', out)
    num_ok = len(num_src) == len(num_out) and set(num_src) == set(num_out)
    
    # Check parentheses
    paren_src = re.findall(r'[\(\)\[\]\{\}]', src)
    paren_out = re.findall(r'[\(\)\[\]\{\}]', out)
    paren_ok = len(paren_src) == len(paren_out) and set(paren_src) == set(paren_out)
    
    # Calculate length ratios
    len_src = len(src)
    len_out = len(out)
    len_ratio = len_out / max(1, len_src)
    
    len_eff_src = _len_effective(src)
    len_eff_out = _len_effective(out)
    len_ratio_eff = len_eff_out / max(1, len_eff_src)
    
    # Determine which length to use
    len_use = "effective" if len_eff_src != len_src or len_eff_out != len_out else "raw"
    
    return {
        "ph_ok": ph_ok,
        "html_ok": html_ok,
        "num_ok": num_ok,
        "paren_ok": paren_ok,
        "len_ratio": len_ratio,
        "len_ratio_eff": len_ratio_eff,
        "len_use": len_use
    }
