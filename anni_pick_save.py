#!/usr/bin/env python3
import sys, json, time, urllib.request
URL="http://127.0.0.1:8094/rank"
LIB="copy_library.json"

def rank(task, brief, variants, top_k=3, div=0.75):
    payload={"task":task,"brief":brief,"variants":variants,"top_k":top_k,"diversity_threshold":div}
    req=urllib.request.Request(URL, data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req) as r: return json.load(r)

def main():
    task=sys.argv[1]
    vars=sys.argv[2:]
    brief={"brand_terms":["TranceLate"],"never_translate":["TranceLate"],"avoid":[],"key_points":[],"tone_markers_any":[]}
    res=rank(task, brief, vars)
    picked=[p["text"] for p in res["picked"]]
    try:
        lib=json.load(open(LIB,"r",encoding="utf-8"))
    except Exception:
        lib={"items":[]}
    lib["items"].append({"ts":int(time.time()),"task":task,"picked":picked,"input":vars})
    with open(LIB,"w",encoding="utf-8") as f: json.dump(lib,f,ensure_ascii=False,indent=2)
    print("\n".join(picked))
if __name__=="__main__":
    if len(sys.argv)<3:
        print("usage: anni_pick_save.py <task> <variant1> [<variant2> ...]"); sys.exit(2)
    main()
