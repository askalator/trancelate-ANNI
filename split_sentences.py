#!/usr/bin/env python3
import sys, json, re

# Abkürzungen maskieren (Punkt -> §DOT§), damit nicht mitten drin gesplittet wird
ABBR_PATTERNS = [
    r"Mr\.", r"Mrs\.", r"Ms\.", r"Dr\.", r"Prof\.", r"Sr\.", r"Jr\.", r"vs\.",
    r"etc\.", r"e\.g\.", r"i\.e\.", r"U\.S\.", r"U\.K\.", r"Fig\.", r"No\.", r"ca\."
]
SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")  # nur 1-Zeichen-Lookbehind → fixed width (ok)

def norm(s): return re.sub(r"\s+"," ", s or "").strip()

def mask_abbr(text:str)->str:
    t = text
    for pat in ABBR_PATTERNS:
        t = re.sub(pat, lambda m: m.group(0).replace(".", "§DOT§"), t, flags=re.IGNORECASE)
    return t

def unmask_abbr(text:str)->str:
    return text.replace("§DOT§", ".")

if len(sys.argv) < 3:
    print("usage: split_sentences.py <in.jsonl> <out.jsonl>", file=sys.stderr); sys.exit(2)

inp, outp = sys.argv[1], sys.argv[2]
with open(inp, encoding="utf-8") as fin, open(outp, "w", encoding="utf-8") as fout:
    order = 0
    for line in fin:
        if not line.strip():
            continue
        rec = json.loads(line)
        if "_meta" in rec:
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            continue
        text = norm(rec.get("text", ""))
        if not text:
            continue
        masked = mask_abbr(text)
        parts = [norm(p) for p in SPLIT_RE.split(masked)]
        parts = [unmask_abbr(p) for p in parts if p]
        for s in parts:
            if len(s) < 6:
                continue
            fout.write(json.dumps({"order": order, "type": rec.get("type","p"), "text": s}, ensure_ascii=False) + "\n")
            order += 1
print(f"✅ wrote sentence-segments to {outp}")
