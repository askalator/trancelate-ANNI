#!/usr/bin/env python3
"""
Smoke test for ANNI stack.
Checks all services are running and responding.
"""

import sys
import json
import urllib.request
import urllib.parse

BASE_URLS = {
    "guard": "http://127.0.0.1:8091",
    "worker": "http://127.0.0.1:8093", 
    "trancecreate": "http://127.0.0.1:8095",
    "trancespell": "http://127.0.0.1:8096"
}

def check_service(name, url, endpoint="/health"):
    """Check if a service is responding"""
    try:
        full_url = f"{url}{endpoint}"
        req = urllib.request.Request(full_url)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode())
                print(f"✅ {name}: OK")
                return True
            else:
                print(f"❌ {name}: HTTP {response.getcode()}")
                return False
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False

def main():
    """Run smoke tests"""
    print("ANNI Stack Smoke Test")
    print("=" * 30)
    
    results = {}
    
    # Check Guard
    results["guard"] = check_service("Guard", BASE_URLS["guard"], "/meta")
    
    # Check Worker
    results["worker"] = check_service("Worker", BASE_URLS["worker"])
    
    # Check TranceCreate
    results["trancecreate"] = check_service("TranceCreate", BASE_URLS["trancecreate"])
    
    # Check TranceSpell
    results["trancespell"] = check_service("TranceSpell", BASE_URLS["trancespell"])
    
    # Summary
    print("\nSummary:")
    print("=" * 30)
    passed = sum(results.values())
    total = len(results)
    
    for service, ok in results.items():
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{service}: {status}")
    
    print(f"\nOverall: {passed}/{total} services responding")
    
    if passed == total:
        print("🎉 All services are running!")
        sys.exit(0)
    else:
        print("⚠️  Some services are not responding")
        sys.exit(1)

if __name__ == "__main__":
    main()
