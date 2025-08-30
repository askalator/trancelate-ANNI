#!/usr/bin/env python3
import sys, json, urllib.request
URL="http://127.0.0.1:8093/gate"
def main():
    if len(sys.argv)<3:
        print("usage: anni_gate_cli.py <task> <var1> [<var2> <var3> ...]", file=sys.stderr); sys.exit(2)
    task=sys.argv[1]; vars=sys.argv[2:]
    payload={"task":task,"brief":{"brand_terms":["TranceLate"],"never_translate":["TranceLate"],"avoid":[],"key_points":[],"tone_markers_any":[]},
             "variants":vars}
    req=urllib.request.Request(URL, data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req) as r: res=json.load(r)
    print(json.dumps(res, ensure_ascii=False, indent=2))
if __name__=="__main__": main()
