#!/usr/bin/env python3
import sys, json, urllib.request
URL="http://127.0.0.1:8094/rank"
def main():
    if len(sys.argv)<3:
        print("usage: anni_rank_cli.py <task> <var1> [<var2> ...]"); sys.exit(2)
    task=sys.argv[1]; vars=sys.argv[2:]
    payload={"task":task,"brief":{"brand_terms":["TranceLate"],"never_translate":["TranceLate"],"avoid":[],"key_points":[],"tone_markers_any":[]},
             "variants":vars,"top_k":3,"diversity_threshold":0.75}
    req=urllib.request.Request(URL, data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req) as r: res=json.load(r)
    for p in res["picked"]:
        print(p["text"])
if __name__=="__main__": main()
