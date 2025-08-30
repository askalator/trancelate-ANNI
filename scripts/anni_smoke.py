import os, json, urllib.request, sys, time

HOST=os.environ.get("HOST","http://127.0.0.1:8091").rstrip("/")
KEY=os.environ.get("ANNI_API_KEY","topsecret")
URL=f"{HOST}/translate"
HDRS={"Content-Type":"application/json","X-API-Key":KEY}

TEXT='Only today 🎉: {{COUNT}} seats at <strong>{app}</strong> — valid for 2 days (1990–2014). Price $1,234.56. Link: <a href="https://example.com">here</a> 🙂'
PAIRS=[("en","ja"),("en","zh"),("en","ko"),("en","hi"),("en","ar"),("en","sw"),("en","fa"),("en","he"),("en","th"),("en","vi")]

def call(src,tgt,text):
    data=json.dumps({"source":src,"target":tgt,"text":text}).encode()
    req=urllib.request.Request(URL,data=data,headers=HDRS)
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read().decode())

fails=0; total=0
print(f"HOST={HOST}  URL={URL}")
for s,t in PAIRS:
    total+=1
    try:
        j=call(s,t,TEXT)
        c=j.get("checks",{})
        ok=bool(c.get("ok")) and c.get("ph_ok") and c.get("html_ok") and c.get("num_ok")
        mark="OK " if ok else "FAIL"
        print(f"{s}->{t} {mark}  ph={c.get('ph_ok')} html={c.get('html_ok')} num={c.get('num_ok')} len={c.get('len_ratio')}")
        if not ok: fails+=1
    except Exception as e:
        fails+=1
        print(f"{s}->{t} ERROR {e}")
        time.sleep(0.2)
print(f"SUMMARY {total-fails}/{total} passed")
sys.exit(1 if fails else 0)
