#!/usr/bin/env python3
import re

# Simpler regex approach
patterns = [
    r'(?<!\w)(\d[\d\u00A0\u202F .,–-]*\d)(?!\w)',  # Simple: digit + stuff + digit
    r'(?<!\w)(\d[\d\u00A0\u202F .,-–]*?\d)(?!\w)', # Non-greedy version
    r'(?<!\w)(\d+(?:[.,]\d+)?(?:\s*[–-]\s*\d+(?:[.,]\d+)?)?)(?!\w)',  # Traditional number format
]

test_cases = [
    "Valid period 1990–2014",
    "Price $1,234.56",
    "Price 1\u202F234,56 €"
]

for i, pattern in enumerate(patterns):
    print(f"\nPattern {i+1}: {pattern}")
    regex = re.compile(pattern)
    for test in test_cases:
        matches = regex.findall(test)
        print(f"  '{test}': {matches}")
