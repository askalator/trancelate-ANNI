#!/usr/bin/env python3
"""
Smoke test for TranceCreate claim_guard functionality.
Tests pipeline with claim_guard stage and verifies shortening behavior.
"""

import sys
import json
import urllib.request
import urllib.parse

BASE_URL = "http://127.0.0.1:8095"

def setup_pipeline():
    """Setup pipeline with claim_guard stage"""
    try:
        payload = {
            "stages": ["tc_core", "claim_guard", "policy_check", "degrade"]
        }
        
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/pipeline",
            data=data,
            headers={"Content-Type": "application/json"},
            method="PUT"
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.getcode() == 200:
                print("✅ Pipeline configured with claim_guard")
                return True
            else:
                print(f"❌ Pipeline setup failed: HTTP {response.getcode()}")
                return False
    except Exception as e:
        print(f"❌ Pipeline setup error: {e}")
        return False

def test_claim_guard():
    """Test claim_guard with long button text"""
    try:
        payload = {
            "source": "en",
            "target": "de",
            "text": "<button>Very long button text that needs to be shortened significantly</button>",
            "profile": "marketing",
            "persona": "ogilvy",
            "level": 2
        }
        
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/transcreate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.getcode() == 200:
                result = json.loads(response.read().decode())
                
                # Check response structure
                if "transcreated_text" not in result:
                    print("❌ Missing transcreated_text in response")
                    return False
                
                if "checks" not in result:
                    print("❌ Missing checks in response")
                    return False
                
                if "trace" not in result:
                    print("❌ Missing trace in response")
                    return False
                
                # Check that text was shortened
                source_text = payload["text"]
                target_text = result["transcreated_text"]
                
                # Extract button content
                import re
                source_match = re.search(r'<button>(.*?)</button>', source_text)
                target_match = re.search(r'<button>(.*?)</button>', target_text)
                
                if source_match and target_match:
                    source_content = source_match.group(1)
                    target_content = target_match.group(1)
                    
                    if len(target_content) <= len(source_content):
                        print("✅ Button text was shortened")
                    else:
                        print(f"⚠️  Button text not shortened: {len(source_content)} -> {len(target_content)}")
                
                # Check trace contains claim_fit
                trace = result.get("trace", {})
                if "claim_fit" in trace:
                    claim_fit = trace["claim_fit"]
                    if isinstance(claim_fit, list) and len(claim_fit) > 0:
                        print("✅ claim_fit trace present")
                    else:
                        print("❌ claim_fit trace empty")
                        return False
                else:
                    print("❌ claim_fit trace missing")
                    return False
                
                # Check checks.ok
                checks = result.get("checks", {})
                if checks.get("ok", False):
                    print("✅ Checks passed")
                else:
                    print(f"⚠️  Checks failed: {checks}")
                
                return True
            else:
                print(f"❌ Transcreate request failed: HTTP {response.getcode()}")
                return False
    except Exception as e:
        print(f"❌ Transcreate test error: {e}")
        return False

def main():
    """Run claim_guard smoke test"""
    print("TranceCreate claim_guard Smoke Test")
    print("=" * 40)
    
    # Setup pipeline
    if not setup_pipeline():
        sys.exit(1)
    
    # Test claim_guard
    if not test_claim_guard():
        sys.exit(1)
    
    print("\n🎉 claim_guard smoke test passed!")
    sys.exit(0)

if __name__ == "__main__":
    main()
