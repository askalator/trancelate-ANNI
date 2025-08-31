"""
Shared masking functionality for TranceLate services.
Identical behavior to current Guard/TC/TS implementations.
"""

import re
from typing import Tuple, List, Dict

# Regex patterns for invariants (identical to current best version)
PLACEHOLDER_DBL_RE = re.compile(r'\{\{[^}]+\}\}')
TOKEN_SGL_RE = re.compile(r'\{[^}]+\}')
HTML_TAG_RE = re.compile(r'<[^>]+>')
URL_RE = re.compile(r'https?://[^\s<>"]+')
EMOJI_RE = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF]')
NUM_RE = re.compile(r'\b\d+(?:[,\d]*\d)*(?:\.\d+)?(?:[–—]\d+(?:[,\d]*\d)*(?:\.\d+)?)?\b')

def mask(text: str) -> Tuple[str, List[Tuple[int, int, str]], Dict[str, str]]:
    """
    Mask protected spans in text.
    
    Returns:
        (masked_text, spans, table)
        spans: list of (start, end, span_type)
        table: mapping from span_key to original content
    """
    masked_text = text
    spans = []
    table = {}
    span_id = 0
    
    # Find all protected spans
    patterns = [
        (PLACEHOLDER_DBL_RE, "PLACEHOLDER_DBL"),
        (TOKEN_SGL_RE, "TOKEN_SGL"),
        (HTML_TAG_RE, "HTML_TAG"),
        (URL_RE, "URL"),
        (EMOJI_RE, "EMOJI"),
        (NUM_RE, "NUM")
    ]
    
    for pattern, span_type in patterns:
        matches = list(pattern.finditer(text))
        for match in reversed(matches):  # Process in reverse to maintain offsets
            start, end = match.span()
            content = match.group(0)
            span_key = f"__{span_type}{span_id}__"
            
            # Store span info
            spans.append((start, end, span_type))
            
            # Replace in masked text
            masked_text = masked_text[:start] + span_key + masked_text[end:]
            table[span_key] = content
            span_id += 1
    
    return masked_text, spans, table

def unmask(text: str, spans: List[Tuple[int, int, str]], table: Dict[str, str]) -> str:
    """
    Restore masked content (1:1 restoration).
    
    Args:
        text: Text with masked spans
        spans: List of (start, end, span_type) - not used in current implementation
        table: Mapping from span_key to original content
    
    Returns:
        Text with all masked spans restored
    """
    result = text
    for span_key, original_content in table.items():
        result = result.replace(span_key, original_content)
    return result
