#!/usr/bin/env python3
import sys, json, sqlite3
if len(sys.argv)<3:
    print("usage: import_copy_library.py copy_library.json copy_library.sqlite"); sys.exit(2)
jpath, dbpath = sys.argv[1], sys.argv[2]
data = json.load(open(jpath,"r",encoding="utf-8"))
con = sqlite3.connect(dbpath); cur = con.cursor()
for it in data.get("items", []):
    cur.execute("INSERT INTO item(ts,task) VALUES(?,?)", (it["ts"], it["task"]))
    item_id = cur.lastrowid
    for r, txt in enumerate(it.get("picked", []), start=1):
        cur.execute("INSERT INTO pick(item_id,rank,text) VALUES(?,?,?)", (item_id, r, txt))
con.commit(); con.close()
print("ok")
