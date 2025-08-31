import json, sys, urllib.request

BASE="http://127.0.0.1:8095"
H={"Content-Type":"application/json"}

def post(path,obj):
    r=urllib.request.Request(BASE+path, data=json.dumps(obj).encode(), headers=H)
    with urllib.request.urlopen(r, timeout=30) as h:
        return h.getcode(), json.loads(h.read().decode())

def put(path,obj):
    r=urllib.request.Request(BASE+path, data=json.dumps(obj).encode(), headers=H, method='PUT')
    with urllib.request.urlopen(r, timeout=10) as h:
        return h.getcode(), json.loads(h.read().decode())

# Test 1: Enable claim_fit stage
print("Test 1: Enable claim_fit stage...")
c,j = put("/pipeline", {"stages": ["tc_core", "claim_fit", "policy_check", "degrade"]})
if c != 200:
    print("FAIL: Could not update pipeline"); sys.exit(1)
print("✓ PASS: Pipeline updated")

# Test 2: Simple button shortening with baseline_text
print("Test 2: Simple button shortening...")
payload = {
    "source": "en",
    "target": "de", 
    "baseline_text": "<button>Short</button>",  # Provide baseline directly
    "text": "<button>Very long button text that should be shortened</button>",
    "profile": "marketing",
    "persona": "ogilvy",
    "level": 1,
    "policies": {"max_change_ratio": 0.5}
}

c,j = post("/transcreate", payload)
if c != 200:
    print("FAIL: Could not transcreate"); sys.exit(1)

result = j["transcreated_text"]
claim_fit_trace = j.get("trace", {}).get("claim_fit", [])

print(f"Result: {result}")
print(f"Claim fit trace: {claim_fit_trace}")

if not claim_fit_trace:
    print("FAIL: No claim_fit trace"); sys.exit(1)

# Check if button was shortened
if len(result) >= len("<button>Very long button text that should be shortened</button>"):
    print("FAIL: Button was not shortened"); sys.exit(1)

print("✓ PASS: Button shortening")

print("SUMMARY 2/2 PASS")
