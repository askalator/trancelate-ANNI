#!/usr/bin/env python3
"""
Test script for TerminologyStage functionality
"""
import sys
import os
import requests
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_terminology_stage():
    """Test TerminologyStage functionality"""
    base_url = "http://127.0.0.1:8095"
    
    # Test A: German preferred term replacement
    print("Test A: German preferred term replacement...")
    test_a = {
        "source": "en",
        "target": "de",
        "text": "Besuchen Sie unsere Web Seite für mehr Informationen.",
        "profile": "marketing",
        "persona": "professional",
        "level": 2
    }
    
    try:
        response = requests.post(f"{base_url}/transcreate", json=test_a, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if "Website" in result.get("transcreated_text", ""):
                print("✓ A) PASS: 'Web Seite' → 'Website' replacement successful")
            else:
                print("✗ A) FAIL: Preferred term replacement failed")
                return False
        else:
            print(f"✗ A) FAIL: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ A) FAIL: {e}")
        return False
    
    # Test B: English forbidden term detection
    print("Test B: English forbidden term detection...")
    test_b = {
        "source": "en", 
        "target": "en",
        "text": "Get free shipping on all orders today!",
        "profile": "marketing",
        "persona": "casual",
        "level": 1
    }
    
    try:
        response = requests.post(f"{base_url}/transcreate", json=test_b, timeout=30)
        if response.status_code == 200:
            result = response.json()
            degrade_reasons = result.get("degrade_reasons", [])
            forbidden_found = any("forbidden_term:free shipping" in reason for reason in degrade_reasons)
            
            if forbidden_found:
                print("✓ B) PASS: 'free shipping' forbidden term detected")
                if result.get("degraded", False):
                    print("✓ B) PASS: Text degraded to baseline after forbidden term")
                else:
                    print("✗ B) FAIL: Text should be degraded but isn't")
                    return False
            else:
                print("✗ B) FAIL: Forbidden term not detected")
                return False
        else:
            print(f"✗ B) FAIL: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ B) FAIL: {e}")
        return False
    
    # Test C: Masking protection
    print("Test C: Masking protection...")
    test_c = {
        "source": "en",
        "target": "en", 
        "text": "Visit {{COUNT}} times, click <b>{app}</b>, go to https://example.com for 123 items",
        "profile": "marketing",
        "persona": "casual",
        "level": 1
    }
    
    try:
        response = requests.post(f"{base_url}/transcreate", json=test_c, timeout=30)
        if response.status_code == 200:
            result = response.json()
            transcreated = result.get("transcreated_text", "")
            
            # Check that protected content remains unchanged
            protected_ok = (
                "{{COUNT}}" in transcreated and
                "<b>{app}</b>" in transcreated and
                "https://example.com" in transcreated and
                "123" in transcreated
            )
            
            if protected_ok:
                print("✓ C) PASS: All protected spans preserved")
            else:
                print("✗ C) FAIL: Some protected content was modified")
                print(f"  Expected: {{COUNT}}, <b>{{app}}</b>, https://example.com, 123")
                print(f"  Got: {transcreated}")
                return False
        else:
            print(f"✗ C) FAIL: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ C) FAIL: {e}")
        return False
    
    print("\n🎉 All tests PASSED!")
    return True

if __name__ == "__main__":
    print("🧪 Testing TerminologyStage functionality...\n")
    
    success = test_terminology_stage()
    
    if success:
        print("\n✅ All terminology tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some terminology tests failed!")
        sys.exit(1)
