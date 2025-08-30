#!/usr/bin/env python3
import os, sys, json, argparse, urllib.request, urllib.error

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ANNI_KEY     = os.environ["ANNI_ADMIN_KEY"]

def http_json(url, data=None, headers=None, method=None, timeout=30):
    h={"Content-Type":"application/json"}
    if headers: h.update(headers)
    req=urllib.request.Request(
        url,
        data=(json.dumps(data).encode() if data is not None else None),
        headers=h,
        method=method or ("POST" if data is not None else "GET"),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            if not raw:
                return {"_status": getattr(r, "status", None)}
            try:
                return json.loads(raw.decode())
            except Exception:
                return {"_status": getattr(r, "status", None), "_raw": raw.decode("utf-8","ignore")}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8","ignore")
        raise SystemExit(f"HTTP {e.code} {e.reason}: {body}")

def main():
    ap=argparse.ArgumentParser(description="ANNI commit with enforced org")
    ap.add_argument("--host", default="http://127.0.0.1:8094")
    ap.add_argument("--org", required=True)
    ap.add_argument("--task", required=True, choices=["cta","headline","subhead","bullets"])
    ap.add_argument("--variants", required=True, help='JSON array of strings')
    ap.add_argument("--request-key", default=None)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--diversity-threshold", type=float, default=0.75)
    args=ap.parse_args()

    variants=json.loads(args.variants)
    payload={
        "request_key": args.request_key or f"{args.task}-{args.org}-auto",
        "org": args.org,
        "task": args.task,
        "variants": variants,
        "top_k": args.top_k,
        "diversity_threshold": args.diversity_threshold
    }

    # 1) Commit
    commit = http_json(f"{args.host}/commit", data=payload,
                       headers={"x-anni-key": ANNI_KEY})

    item_id = commit["item_id"]

    # 2) org sicher setzen (PATCH) – mit Prefer, tolerant bei 204
    patch_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "return=representation"
    }
    patch = http_json(f"{SUPABASE_URL}/rest/v1/item?id=eq.{item_id}",
                      data={"org": args.org},
                      headers=patch_headers,
                      method="PATCH")

    out = {
        "item_id": item_id,
        "picks": commit.get("picks", []),
        "org_patch": patch,
        "idempotent": commit.get("idempotent", False)
    }
    print(json.dumps(out, ensure_ascii=False))
if __name__ == "__main__":
    main()
