import json, urllib.request, sys
BASE="http://127.0.0.1:8095"; H={"Content-Type":"application/json"}

def post(path,obj):
    r=urllib.request.Request(BASE+path,data=json.dumps(obj).encode(),headers=H)
    with urllib.request.urlopen(r,timeout=30) as h:
        return h.getcode(), json.loads(h.read().decode())

def put(path,obj):
    r=urllib.request.Request(BASE+path,data=json.dumps(obj).encode(),headers=H,method='PUT')
    with urllib.request.urlopen(r,timeout=30) as h:
        return h.getcode(), json.loads(h.read().decode())

# Pipeline mit claim_fit
put("/pipeline", {"stages":["tc_core","claim_fit","policy_check","degrade"]})

payload = {
  "source":"en","target":"de",
  "text":"<button>Sehr sehr langer Button-Text der gekürzt werden muss</button>",
  "profile":"marketing","persona":"ogilvy","level":1
}
c,j = post("/transcreate", payload)
trace = j.get("trace", {})
cf = (trace.get("claim_fit") or [])
ok = c==200 and isinstance(cf, list) and len(cf)>0 and "claim_fit_ratio_vs_original" in trace
print("OK" if ok else ("FAIL "+json.dumps(trace)))
sys.exit(0 if ok else 1)
