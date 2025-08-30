#!/usr/bin/env python3
"""
TranceCreate v1.1 Fallback Tests
Tests fallback functionality, policy enforcement, and deterministic behavior
"""

import requests
import json
import sys
import os

# Configuration
TC_URL = "http://127.0.0.1:8095"

def test_case_a_mistral_off():
    """Case A: Mistral off - TC_USE_MISTRAL=false"""
    print("🔍 Testing Case A: Mistral off (TC_USE_MISTRAL=false)")
    
    # Set environment variable
    os.environ["TC_USE_MISTRAL"] = "false"
    
    try:
        response = requests.post(
            f"{TC_URL}/transcreate",
            headers={"Content-Type": "application/json"},
            json={
                "target": "en",
                "baseline_text": "This is a test message about our products.",
                "profile": "marketing",
                "persona": "ogilvy",
                "level": 1
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check requirements
            checks = []
            
            # 1. Should return non-empty result
            if data['transcreated_text']:
                checks.append("✅ Non-empty result returned")
            else:
                checks.append("❌ Empty result returned")
            
            # 2. tc_model should be "fallback"
            if data['trace']['tc_model'] == "fallback":
                checks.append("✅ tc_model is 'fallback'")
            else:
                checks.append(f"❌ tc_model is '{data['trace']['tc_model']}', expected 'fallback'")
            
            # 3. degraded should be false
            if not data['degraded']:
                checks.append("✅ degraded is false")
            else:
                checks.append(f"❌ degraded is {data['degraded']}, expected false")
            
            # 4. degrade_reasons should be empty
            if not data['degrade_reasons']:
                checks.append("✅ degrade_reasons is empty")
            else:
                checks.append(f"❌ degrade_reasons is {data['degrade_reasons']}, expected empty")
            
            print(f"   Result: {data['transcreated_text']}")
            print(f"   Model: {data['trace']['tc_model']}")
            print(f"   Degraded: {data['degraded']}")
            print(f"   Reasons: {data['degrade_reasons']}")
            
            # All checks must pass
            if all("✅" in check for check in checks):
                print("   PASS: Case A - Mistral off")
                return True
            else:
                print("   FAIL: Case A - Mistral off")
                for check in checks:
                    print(f"     {check}")
                return False
        else:
            print(f"   FAIL: HTTP {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"   FAIL: Exception - {e}")
        return False

def test_case_b_forbidden_terms():
    """Case B: Forbidden terms policy enforcement"""
    print("\n🔍 Testing Case B: Forbidden terms policy")
    
    try:
        response = requests.post(
            f"{TC_URL}/transcreate",
            headers={"Content-Type": "application/json"},
            json={
                "target": "en",
                "baseline_text": "This is a test message about our products with guarantee.",
                "profile": "marketing",
                "persona": "halbert",
                "level": 2,
                "policies": {
                    "forbidden_terms": ["guarantee"]
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check requirements
            checks = []
            
            # 1. degraded should be true
            if data['degraded']:
                checks.append("✅ degraded is true")
            else:
                checks.append(f"❌ degraded is {data['degraded']}, expected true")
            
            # 2. degrade_reasons should contain "forbidden_term:guarantee"
            expected_reason = "forbidden_term:guarantee"
            if expected_reason in data['degrade_reasons']:
                checks.append(f"✅ degrade_reasons contains '{expected_reason}'")
            else:
                checks.append(f"❌ degrade_reasons is {data['degrade_reasons']}, expected to contain '{expected_reason}'")
            
            print(f"   Result: {data['transcreated_text']}")
            print(f"   Degraded: {data['degraded']}")
            print(f"   Reasons: {data['degrade_reasons']}")
            
            # All checks must pass
            if all("✅" in check for check in checks):
                print("   PASS: Case B - Forbidden terms")
                return True
            else:
                print("   FAIL: Case B - Forbidden terms")
                for check in checks:
                    print(f"     {check}")
                return False
        else:
            print(f"   FAIL: HTTP {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"   FAIL: Exception - {e}")
        return False

def test_case_c_change_budget():
    """Case C: Change budget limits"""
    print("\n🔍 Testing Case C: Change budget limits")
    
    try:
        response = requests.post(
            f"{TC_URL}/transcreate",
            headers={"Content-Type": "application/json"},
            json={
                "target": "en",
                "baseline_text": "This is a very simple test message.",
                "profile": "marketing",
                "persona": "halbert",
                "level": 3,  # High level to trigger changes
                "policies": {
                    "max_change_ratio": 0.05  # Very restrictive
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check requirements
            checks = []
            
            # 1. degraded should be true
            if data['degraded']:
                checks.append("✅ degraded is true")
            else:
                checks.append(f"❌ degraded is {data['degraded']}, expected true")
            
            # 2. degrade_reasons should contain "max_change_ratio_exceeded"
            expected_reason = "max_change_ratio_exceeded"
            if expected_reason in data['degrade_reasons']:
                checks.append(f"✅ degrade_reasons contains '{expected_reason}'")
            else:
                checks.append(f"❌ degrade_reasons is {data['degrade_reasons']}, expected to contain '{expected_reason}'")
            
            print(f"   Result: {data['transcreated_text']}")
            print(f"   Char Ratio: {data['diffs']['char_ratio']:.3f}")
            print(f"   Max Allowed: 0.05")
            print(f"   Degraded: {data['degraded']}")
            print(f"   Reasons: {data['degrade_reasons']}")
            
            # All checks must pass
            if all("✅" in check for check in checks):
                print("   PASS: Case C - Change budget")
                return True
            else:
                print("   FAIL: Case C - Change budget")
                for check in checks:
                    print(f"     {check}")
                return False
        else:
            print(f"   FAIL: HTTP {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"   FAIL: Exception - {e}")
        return False

def test_deterministic_seeds():
    """Test deterministic behavior with seeds"""
    print("\n🔍 Testing deterministic seeds")
    
    try:
        # First call with no seed
        response1 = requests.post(
            f"{TC_URL}/transcreate",
            headers={"Content-Type": "application/json"},
            json={
                "target": "en",
                "baseline_text": "Test message for seed verification.",
                "profile": "marketing",
                "persona": "ogilvy",
                "level": 1
            },
            timeout=30
        )
        
        if response1.status_code != 200:
            print(f"   FAIL: HTTP {response1.status_code} - {response1.text}")
            return False
        
        data1 = response1.json()
        seed1 = data1['trace']['seed']
        
        # Second call with same parameters (should generate same seed)
        response2 = requests.post(
            f"{TC_URL}/transcreate",
            headers={"Content-Type": "application/json"},
            json={
                "target": "en",
                "baseline_text": "Test message for seed verification.",
                "profile": "marketing",
                "persona": "ogilvy",
                "level": 1
            },
            timeout=30
        )
        
        if response2.status_code != 200:
            print(f"   FAIL: HTTP {response2.status_code} - {response2.text}")
            return False
        
        data2 = response2.json()
        seed2 = data2['trace']['seed']
        
        # Third call with explicit seed
        response3 = requests.post(
            f"{TC_URL}/transcreate",
            headers={"Content-Type": "application/json"},
            json={
                "target": "en",
                "baseline_text": "Test message for seed verification.",
                "profile": "marketing",
                "persona": "ogilvy",
                "level": 1,
                "seed": 12345
            },
            timeout=30
        )
        
        if response3.status_code != 200:
            print(f"   FAIL: HTTP {response3.status_code} - {response3.text}")
            return False
        
        data3 = response3.json()
        seed3 = data3['trace']['seed']
        
        # Check requirements
        checks = []
        
        # 1. Auto-generated seeds should be the same
        if seed1 == seed2:
            checks.append("✅ Auto-generated seeds are identical")
        else:
            checks.append(f"❌ Auto-generated seeds differ: {seed1} vs {seed2}")
        
        # 2. Explicit seed should be used
        if seed3 == 12345:
            checks.append("✅ Explicit seed is used correctly")
        else:
            checks.append(f"❌ Explicit seed is {seed3}, expected 12345")
        
        print(f"   Auto-seed 1: {seed1}")
        print(f"   Auto-seed 2: {seed2}")
        print(f"   Explicit seed: {seed3}")
        
        # All checks must pass
        if all("✅" in check for check in checks):
            print("   PASS: Deterministic seeds")
            return True
        else:
            print("   FAIL: Deterministic seeds")
            for check in checks:
                print(f"     {check}")
            return False
            
    except Exception as e:
        print(f"   FAIL: Exception - {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 TranceCreate v1.1 Fallback Tests")
    print("=" * 50)
    
    # Check if service is running
    try:
        health_response = requests.get(f"{TC_URL}/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ TranceCreate service is not running")
            print("   Start it with: python tc_server.py")
            return 1
    except Exception as e:
        print("❌ Cannot connect to TranceCreate service")
        print("   Start it with: python tc_server.py")
        return 1
    
    print("✅ TranceCreate service is running")
    
    # Run tests
    tests = [
        ("Case A: Mistral off", test_case_a_mistral_off),
        ("Case B: Forbidden terms", test_case_b_forbidden_terms),
        ("Case C: Change budget", test_case_c_change_budget),
        ("Deterministic seeds", test_deterministic_seeds)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! TranceCreate v1.1 is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the service configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
