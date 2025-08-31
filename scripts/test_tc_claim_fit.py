import json, sys, urllib.request

BASE="http://127.0.0.1:8095"
H={"Content-Type":"application/json"}

def post(path,obj):
    r=urllib.request.Request(BASE+path, data=json.dumps(obj).encode(), headers=H)
    with urllib.request.urlopen(r, timeout=20) as h:
        return h.getcode(), json.loads(h.read().decode())

def put(path,obj):
    r=urllib.request.Request(BASE+path, data=json.dumps(obj).encode(), headers=H, method='PUT')
    with urllib.request.urlopen(r, timeout=20) as h:
        return h.getcode(), json.loads(h.read().decode())

# Test 1: DE Button (Überlänge → einkürzen auf Quell-Budget)
print("Test 1: DE Button shortening...")
c,j = put("/pipeline", {"stages": ["tc_core", "post_profile", "claim_fit", "policy_check", "degrade"]})
if c != 200:
    print("FAIL: Could not update pipeline"); sys.exit(1)

payload = {
    "source": "en",
    "target": "de", 
    "text": "<button>Jetzt registrieren</button>",
    "profile": "marketing",
    "persona": "ogilvy",
    "level": 1,
    "policies": {"max_change_ratio": 0.5}
}

# First get baseline
c,j = post("/transcreate", payload)
if c != 200:
    print("FAIL: Could not get baseline"); sys.exit(1)
baseline = j["transcreated_text"]

# Now test with longer target
payload["text"] = "<button>Jetzt sofort kostenlos anmelden und profitieren</button>"
c,j = post("/transcreate", payload)
if c != 200:
    print("FAIL: Could not transcreate"); sys.exit(1)

result = j["transcreated_text"]
claim_fit_trace = j.get("trace", {}).get("claim_fit", [])

if not claim_fit_trace:
    print("FAIL: No claim_fit trace"); sys.exit(1)

# Check if button was shortened
if len(result) >= len("<button>Jetzt sofort kostenlos anmelden und profitieren</button>"):
    print("FAIL: Button was not shortened"); sys.exit(1)

print("✓ PASS: DE Button shortening")

# Test 2: EN Placeholder
print("Test 2: EN Placeholder shortening...")
payload = {
    "source": "en",
    "target": "en",
    "text": 'placeholder="Enter email"',
    "profile": "marketing", 
    "persona": "ogilvy",
    "level": 1,
    "policies": {"max_change_ratio": 0.5}
}

# First get baseline
c,j = post("/transcreate", payload)
if c != 200:
    print("FAIL: Could not get baseline"); sys.exit(1)
baseline = j["transcreated_text"]

# Now test with longer target
payload["text"] = 'placeholder="Please enter your email address now"'
c,j = post("/transcreate", payload)
if c != 200:
    print("FAIL: Could not transcreate"); sys.exit(1)

result = j["transcreated_text"]
claim_fit_trace = j.get("trace", {}).get("claim_fit", [])

if not claim_fit_trace:
    print("FAIL: No claim_fit trace"); sys.exit(1)

# Check if placeholder was shortened
if len(result) >= len('placeholder="Please enter your email address now"'):
    print("FAIL: Placeholder was not shortened"); sys.exit(1)

print("✓ PASS: EN Placeholder shortening")

# Test 3: JA CTA (CJK ohne Spaces)
print("Test 3: JA CTA shortening...")
payload = {
    "source": "en",
    "target": "ja",
    "text": '<a role="button">Sign up</a>',
    "profile": "marketing",
    "persona": "ogilvy", 
    "level": 1,
    "policies": {"max_change_ratio": 0.5}
}

# First get baseline
c,j = post("/transcreate", payload)
if c != 200:
    print("FAIL: Could not get baseline"); sys.exit(1)
baseline = j["transcreated_text"]

# Now test with longer target
payload["text"] = '<a role="button">今すぐ無料でサインアップしてください</a>'
c,j = post("/transcreate", payload)
if c != 200:
    print("FAIL: Could not transcreate"); sys.exit(1)

result = j["transcreated_text"]
claim_fit_trace = j.get("trace", {}).get("claim_fit", [])

if not claim_fit_trace:
    print("FAIL: No claim_fit trace"); sys.exit(1)

# Check if CTA was shortened
if len(result) >= len('<a role="button">今すぐ無料でサインアップしてください</a>'):
    print("FAIL: CTA was not shortened"); sys.exit(1)

print("✓ PASS: JA CTA shortening")

# Test 4: Masking schützt
print("Test 4: Masking protection...")
payload = {
    "source": "en",
    "target": "ja",
    "text": '<button>{{ACTION}} {app}</button>',
    "profile": "marketing",
    "persona": "ogilvy",
    "level": 1,
    "policies": {"max_change_ratio": 0.5}
}

# First get baseline
c,j = post("/transcreate", payload)
if c != 200:
    print("FAIL: Could not get baseline"); sys.exit(1)
baseline = j["transcreated_text"]

# Now test with longer target
payload["text"] = '<button>{{ACTION}} すぐに {app} をご利用ください</button>'
c,j = post("/transcreate", payload)
if c != 200:
    print("FAIL: Could not transcreate"); sys.exit(1)

result = j["transcreated_text"]

# Check if placeholders and tokens are preserved
if "{{ACTION}}" not in result or "{app}" not in result:
    print("FAIL: Placeholders/tokens not preserved"); sys.exit(1)

print("✓ PASS: Masking protection")

# Test 5: No-op bei fehlendem Pairing
print("Test 5: No-op for missing pairing...")
payload = {
    "source": "en",
    "target": "de",
    "text": "No aria-label here",
    "profile": "marketing",
    "persona": "ogilvy",
    "level": 1,
    "policies": {"max_change_ratio": 0.5}
}

# First get baseline
c,j = post("/transcreate", payload)
if c != 200:
    print("FAIL: Could not get baseline"); sys.exit(1)
baseline = j["transcreated_text"]

# Now test with target that has aria-label but source doesn't
payload["text"] = 'aria-label="This should not be shortened"'
c,j = post("/transcreate", payload)
if c != 200:
    print("FAIL: Could not transcreate"); sys.exit(1)

result = j["transcreated_text"]
claim_fit_trace = j.get("trace", {}).get("claim_fit", [])

# Should not have any claim_fit operations
if claim_fit_trace:
    print("FAIL: Unexpected claim_fit operations"); sys.exit(1)

print("✓ PASS: No-op for missing pairing")

print("SUMMARY 5/5 PASS")
