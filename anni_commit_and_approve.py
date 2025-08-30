#!/usr/bin/env python3
import os, json, sys, argparse, urllib.request

ANNI_KEY=os.environ["ANNI_ADMIN_KEY"]

def http_json(url, data=None, headers=None, method=None, timeout=30):
    h={"Content-Type":"application/json"}
    if headers: h.update(headers)
    req=urllib.request.Request(url, data=(json.dumps(data).encode() if data is not None else None),
                               headers=h, method=(method or ("POST" if data is not None else "GET")))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw=r.read()
        return json.loads(raw.decode()) if raw else {}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--org", required=True)
    ap.add_argument("--task", default="cta")
    ap.add_argument("--variants", required=True, help='z.B. ["Jetzt starten","Sofort prüfen","Design prüfen — kostenlos"]')
    ap.add_argument("--host8094", default="http://127.0.0.1:8094")
    ap.add_argument("--host8095", default="http://127.0.0.1:8095")
    args=ap.parse_args()

    variants=json.loads(args.variants)
    body={"task":args.task,"brief":{"brand_terms":["TranceLate"],"never_translate":["TranceLate"]},"variants":variants,"top_k":3,"diversity_threshold":0.75}
    commit=http_json(f"{args.host8094}/commit", body, headers={"x-anni-key":ANNI_KEY})
    picks=commit.get("picks") or commit.get("picked") or variants
    approve=http_json(f"{args.host8095}/approve",
                      {"org":args.org,"task":args.task,"texts":picks},
                      headers={"x-anni-key":ANNI_KEY})
    print(json.dumps({"commit":commit, "approve":approve}, ensure_ascii=False))
if __name__=="__main__": main()
