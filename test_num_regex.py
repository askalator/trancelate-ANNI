import re

NUM_RE = re.compile(
    r'(?<!\w)('
    r'\d(?:[0-9\u00A0\u202F .,])*?\d'          # Zahl mit Trennzeichen/Spaces
    r'(?:[0-9\u00A0\u202F .,]*\d)*'             # weitere Ziffern mit Trennzeichen
    r'(?:\s*[–-]\s*\d(?:[0-9\u00A0\u202F .,])*?\d)*'  # optionaler Bereich 1990–2014 (greedy)
    r')(?=\D|$)'
)

tests = [
    "Price 1,234.56",
    "Valid period 1990–2014", 
    "Price 1 234,56 €"
]

for test in tests:
    matches = NUM_RE.findall(test)
    print(f"'{test}': {matches}")
