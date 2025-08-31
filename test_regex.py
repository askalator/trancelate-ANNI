#!/usr/bin/env python3
import re

NUM_RE = re.compile(
    r'(?<!\w)('
    r'\d(?:[0-9\u00A0\u202F .,])*?\d'          # Zahl mit Trennzeichen/Spaces
    r'(?:\s?[–-]\s?\d(?:[0-9\u00A0\u202F .,])*?\d)?'  # optionaler Bereich 1990–2014
    r')(?=\D|$)'
)

test_cases = [
    "Valid period 1990–2014",
    "Price $1,234.56",
    "Price 1\u202F234,56 €"
]

for test in test_cases:
    matches = NUM_RE.findall(test)
    print(f"'{test}': {matches}")
