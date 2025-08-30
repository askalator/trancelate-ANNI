#!/usr/bin/env python3
import sys, csv, pathlib, re, json
PH = re.compile(r"\{\{[^}]+\}\}")
if len(sys.argv) < 5:
    print("usage: tm_upsert.py <src_lang> <tgt_lang> <source_text> <target_text>", file=sys.stderr); sys.exit(2)
src_lang, tgt_lang, src_txt, tgt_txt = sys.argv[1], sys.argv[2], sys.argv[3], " ".join(sys.argv[4:])
# Guard: Placeholder-Sets müssen exakt gleich sein
if set(PH.findall(src_txt)) != set(PH.findall(tgt_txt)):
    print(json.dumps({"ok": False, "reason": "placeholder_mismatch"})); sys.exit(1)
p = pathlib.Path("tm.csv")
rows=[]
if p.exists():
    with p.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f, fieldnames=["source_lang","target_lang","source_text","target_text"])
        for row in r:
            if not row["source_text"] or str(row["source_text"]).strip().startswith("#"): 
                continue
            rows.append(row)
# Dupe-Check (gleiche vier Felder)
for r in rows:
    if r["source_lang"]==src_lang and r["target_lang"]==tgt_lang and r["source_text"]==src_txt and r["target_text"]==tgt_txt:
        print(json.dumps({"ok": True, "status": "exists"})); sys.exit(0)
with p.open("a", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow([src_lang, tgt_lang, src_txt, tgt_txt])
print(json.dumps({"ok": True, "status": "inserted"}))
