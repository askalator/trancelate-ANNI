#!/usr/bin/env python3
import sys, re, json, pathlib

if len(sys.argv) < 2:
    print("usage: qgate.py <proof_run.jsonl>", file=sys.stderr); sys.exit(2)

ph_re = re.compile(r"\{\{[^}]+\}\}")
num_re = re.compile(r"\d+[.,]?\d*")
tag_re = re.compile(r"</?([a-zA-Z0-9]+)[^>]*>")
bad = []

def digits_only(s): return re.sub(r"\D","",s)

def tags(sig):
    return [m.group(0).lower().replace(" ", "") for m in tag_re.finditer(sig)]

def check_case(name, src, out):
    issues = []
    # 1) Platzhalter: alle aus src müssen im out unverändert vorkommen
    phs = ph_re.findall(src)
    if not all(p in out for p in phs): issues.append("PH")
    # 2) Zahlen: jede Zahl aus src (nach digits-only) muss im out vorkommen
    src_nums = [digits_only(n) for n in num_re.findall(src)]
    out_dig  = digits_only(out)
    if not all(n and n in out_dig for n in src_nums): issues.append("NUM")
    # 3) HTML-Tags: gleiche Multimenge an Tags (Name + Richtung), Reihenfolge egal
    if sorted(tags(src)) != sorted(tags(out)): issues.append("HTML")
    # 4) Kein neuer Klammer-Block, wenn in src keine Klammern sind
    if ("(" not in src and ")" not in src) and (("(" in out) or (")" in out)): issues.append("PAREN")
    # 5) Keine "_"/"-" direkt nach Platzhaltern
    if re.search(r"\}\}[_-]", out): issues.append("PH_TAIL")
    # 6) Länge: ratio innerhalb [0.6, 1.6]
    if not (0.6 <= (len(out)+1)/(len(src)+1) <= 1.6): issues.append("LEN")
    return issues

total = 0; ok = 0
with open(sys.argv[1], encoding="utf-8") as f:
    for i,line in enumerate(f,1):
        if not line.strip(): continue
        rec = json.loads(line)
        src = rec["text"]; outs = {"mt": rec["mt"]["translated_text"], "polish": rec["polish"]["translated_text"]}
        row_bad = {}
        for name,out in outs.items():
            issues = check_case(name, src, out)
            if issues: row_bad[name] = issues
        total += 1
        if not row_bad: ok += 1
        else: bad.append((i, src, outs, row_bad))

print(f"✅ {ok}/{total} passed")
if bad:
    print("— failures (max 5):")
    for i,(ln,src,outs,issues) in enumerate(bad[:5],1):
        print(f"#{ln} SRC: {src}")
        for k in issues:
            print(f"  {k}: {issues[k]}")
        print(f"  MT: {outs['mt']}")
        print(f"  PL: {outs['polish']}")
