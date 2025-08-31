import json, sys, urllib.request

BASE="http://127.0.0.1:8095"
H={"Content-Type":"application/json"}

def post(path,obj):
    r=urllib.request.Request(BASE+path, data=json.dumps(obj).encode(), headers=H)
    with urllib.request.urlopen(r, timeout=20) as h:
        return h.getcode(), json.loads(h.read().decode())

payload = {
  "source":"en","target":"de",
  "text":"Hello <b>HTML</b> 123 🙂 {{X}}",
  "profile":"marketing","persona":"ogilvy","level":1,
  "policies":{"preserve":["placeholders","single_brace","html","numbers","urls","emojis"],"max_change_ratio":0.25}
}

# A) Baseline == Cand → ratio=0 => kein Grund
c,j = post("/transcreate", payload)
if c!=200 or "max_change_ratio_exceeded" in j.get("degrade_reasons", []):
    print("FAIL A", j.get("degrade_reasons")); sys.exit(1)

# B) Kleine Änderung unter Budget
payload2 = dict(payload); payload2["text"] += "!"
c,j = post("/transcreate", payload2)
if c!=200 or "max_change_ratio_exceeded" in j.get("degrade_reasons", []):
    print("FAIL B", j.get("degrade_reasons")); sys.exit(1)

# C) Große Änderung über Budget - verwende einen komplett anderen Text
payload3 = dict(payload); payload3["text"] = "This is a completely different text that should exceed the change ratio"
c,j = post("/transcreate", payload3)
if c!=200 or "max_change_ratio_exceeded" not in j.get("degrade_reasons", []):
    print("FAIL C", j.get("degrade_reasons")); sys.exit(1)

print("SUMMARY 3/3 PASS")
