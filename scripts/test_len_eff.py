#!/usr/bin/env python3
"""
Test script for effective length checking in Guard
Tests that emoji/symbol runs don't cause false negatives in length checks
"""

import requests
import json
import sys

# Configuration
GUARD_URL = "http://127.0.0.1:8091"

def test_case_a_normal_sentence():
    """Test A: Normal sentence without emoji runs"""
    print("Test A: Normal sentence without emoji runs...")
    
    try:
        response = requests.post(
            f"{GUARD_URL}/translate",
            headers={"X-API-Key": "topsecret", "Content-Type": "application/json"},
            json={
                "source": "en",
                "target": "ja",
                "text": "Hello world!"
            },
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"FAIL: POST /translate returned {response.status_code}")
            return False
        
        data = response.json()
        checks = data.get("checks", {})
        
        if checks.get("ok", False):
            print("PASS: Normal sentence passed length check")
            return True
        else:
            print(f"FAIL: Normal sentence failed: {checks}")
            return False
            
    except Exception as e:
        print(f"FAIL: Test A failed: {e}")
        return False

def test_case_b_emoji_run_in_target():
    """Test B: Source with 1x 🎉, target provokes 20x 🎉 in one place"""
    print("Test B: Testing emoji run in target...")
    
    try:
        response = requests.post(
            f"{GUARD_URL}/translate",
            headers={"X-API-Key": "topsecret", "Content-Type": "application/json"},
            json={
                "source": "en",
                "target": "ja",
                "text": "Hello! 🎉"
            },
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"FAIL: POST /translate returned {response.status_code}")
            return False
        
        data = response.json()
        checks = data.get("checks", {})
        
        # Check that effective length is used
        if checks.get("len_use") != "effective":
            print(f"FAIL: Expected len_use='effective', got '{checks.get('len_use')}'")
            return False
        
        # Check that it passes despite emoji run
        if checks.get("ok", False):
            print("PASS: Emoji run in target passed effective length check")
            return True
        else:
            print(f"FAIL: Emoji run failed: {checks}")
            return False
            
    except Exception as e:
        print(f"FAIL: Test B failed: {e}")
        return False

def test_case_c_long_emoji_runs():
    """Test C: Very long emoji runs in source and target (different lengths)"""
    print("Test C: Testing long emoji runs in source and target...")
    
    try:
        response = requests.post(
            f"{GUARD_URL}/translate",
            headers={"X-API-Key": "topsecret", "Content-Type": "application/json"},
            json={
                "source": "en",
                "target": "ja",
                "text": "Hello! 🎉🎉🎉🎉🎉"
            },
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"FAIL: POST /translate returned {response.status_code}")
            return False
        
        data = response.json()
        checks = data.get("checks", {})
        
        # Check that effective length is used
        if checks.get("len_use") != "effective":
            print(f"FAIL: Expected len_use='effective', got '{checks.get('len_use')}'")
            return False
        
        # Check that it passes despite long emoji runs
        if checks.get("ok", False):
            print("PASS: Long emoji runs passed effective length check")
            return True
        else:
            print(f"FAIL: Long emoji runs failed: {checks}")
            return False
            
    except Exception as e:
        print(f"FAIL: Test C failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Guard Effective Length Checking")
    print("=" * 50)
    
    # Check if Guard service is running
    try:
        response = requests.get(f"{GUARD_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Guard service not running at {GUARD_URL}")
            sys.exit(1)
    except:
        print(f"❌ Cannot connect to Guard service at {GUARD_URL}")
        print("Please start the Guard service: python mt_guard.py")
        sys.exit(1)
    
    # Run tests
    tests = [
        test_case_a_normal_sentence,
        test_case_b_emoji_run_in_target,
        test_case_c_long_emoji_runs
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"FAIL: Test {test.__name__} crashed: {e}")
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed!")
        print("A OK")
        print("B OK")
        print("C OK")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
