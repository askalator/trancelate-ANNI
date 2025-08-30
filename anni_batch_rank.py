#!/usr/bin/env python3
import sys, json, urllib.request, time
URL="http://127.0.0.1:8094/rank"
LIB="copy_library.json"

def rank(task, brief, variants, top_k=3, div=0.75):
    payload={"task":task,"brief":brief,"variants":variants,"top_k":top_k,"diversity_threshold":div}
    req=urllib.request.Request(URL, data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req) as r: return json.load(r)

def main(path):
    batch=json.load(open(path,"r",encoding="utf-8"))
    try: lib=json.load(open(LIB,"r",encoding="utf-8"))
    except: lib={"items":[]}
    ts=int(time.time())
    for item in batch["items"]:
        res=rank(item["task"], item.get("brief",{}), item["variants"], item.get("top_k",3), item.get("diversity_threshold",0.75))
        picked=[p["text"] for p in res["picked"]]
        lib["items"].append({"ts":ts,"task":item["task"],"picked":picked,"input":item["variants"]})
        print("\n".join(picked))
    json.dump(lib, open(LIB,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

if __name__=="__main__":
    if len(sys.argv)<2:
        print("usage: anni_batch_rank.py <batch.json>"); sys.exit(2)
    main(sys.argv[1])
