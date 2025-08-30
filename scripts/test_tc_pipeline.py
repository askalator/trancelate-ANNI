#!/usr/bin/env python3
"""
Test script for TranceCreate Pipeline functionality
Tests pipeline configuration, hot-reload, and transcreation behavior
"""

import requests
import json
import time
import os
import sys

# Configuration
TC_URL = "http://127.0.0.1:8095"
TEST_TEXT = "Hello world! This is a test message with {{PLACEHOLDER}} and <b>HTML</b> tags."

def test_case_a_default_pipeline():
    """Test A: GET /pipeline returns default order"""
    print("Test A: Checking default pipeline configuration...")
    
    try:
        response = requests.get(f"{TC_URL}/pipeline", timeout=5)
        if response.status_code != 200:
            print(f"FAIL: GET /pipeline returned {response.status_code}")
            return False
        
        data = response.json()
        stages = [stage["name"] for stage in data.get("stages", [])]
        expected = ["tc_core", "post_profile", "policy_check", "degrade"]
        
        if stages == expected:
            print("PASS: Default pipeline configuration is correct")
            return True
        else:
            print(f"FAIL: Expected {expected}, got {stages}")
            return False
            
    except Exception as e:
        print(f"FAIL: GET /pipeline failed: {e}")
        return False

def test_case_b_pipeline_update():
    """Test B: PUT /pipeline updates configuration"""
    print("Test B: Testing pipeline configuration update...")
    
    try:
        # Update pipeline
        new_stages = ["tc_core", "policy_check", "degrade"]
        response = requests.put(
            f"{TC_URL}/pipeline",
            json={"stages": new_stages},
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"FAIL: PUT /pipeline returned {response.status_code}")
            return False
        
        # Verify update
        response = requests.get(f"{TC_URL}/pipeline", timeout=5)
        if response.status_code != 200:
            print(f"FAIL: GET /pipeline after update returned {response.status_code}")
            return False
        
        data = response.json()
        stages = [stage["name"] for stage in data.get("stages", [])]
        
        if stages == new_stages:
            print("PASS: Pipeline configuration updated successfully")
            return True
        else:
            print(f"FAIL: Expected {new_stages}, got {stages}")
            return False
            
    except Exception as e:
        print(f"FAIL: Pipeline update failed: {e}")
        return False

def test_case_c_fallback_transcreation():
    """Test C: POST /transcreate with TC_USE_MISTRAL=false"""
    print("Test C: Testing fallback transcreation...")
    
    try:
        # Set environment variable for this test
        original_env = os.environ.get("TC_USE_MISTRAL", "true")
        os.environ["TC_USE_MISTRAL"] = "false"
        
        # Restart service to pick up new env var (simulated)
        # In real test, you'd restart the service
        time.sleep(1)
        
        response = requests.post(
            f"{TC_URL}/transcreate",
            json={
                "source": "en",
                "target": "ja",
                "text": TEST_TEXT,
                "profile": "marketing",
                "persona": "ogilvy",
                "level": 2,
                "policies": {
                    "max_change_ratio": 0.25,
                    "forbidden_terms": [],
                    "preserve": ["placeholders", "html", "numbers"]
                }
            },
            timeout=10
        )
        
        # Restore environment
        os.environ["TC_USE_MISTRAL"] = original_env
        
        if response.status_code != 200:
            print(f"FAIL: POST /transcreate returned {response.status_code}")
            return False
        
        data = response.json()
        
        # Check requirements
        if data.get("trace", {}).get("tc_model") == "fallback":
            print("PASS: Fallback model used correctly")
        else:
            print(f"FAIL: Expected tc_model='fallback', got '{data.get('trace', {}).get('tc_model')}'")
            return False
        
        if not data.get("degraded", True):
            print("PASS: Not degraded with fallback")
        else:
            print(f"FAIL: Should not be degraded with fallback, got degraded={data.get('degraded')}")
            return False
        
        if not data.get("degrade_reasons"):
            print("PASS: No degrade reasons with fallback")
        else:
            print(f"FAIL: Should have no degrade reasons, got {data.get('degrade_reasons')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"FAIL: Fallback transcreation failed: {e}")
        return False

def test_case_d_policy_violation():
    """Test D: POST /transcreate with max_change_ratio=0.05"""
    print("Test D: Testing policy violation...")
    
    try:
        response = requests.post(
            f"{TC_URL}/transcreate",
            json={
                "source": "en",
                "target": "ja",
                "text": TEST_TEXT,
                "profile": "marketing",
                "persona": "ogilvy",
                "level": 2,
                "policies": {
                    "max_change_ratio": 0.05,  # Very low threshold
                    "forbidden_terms": [],
                    "preserve": ["placeholders", "html", "numbers"]
                }
            },
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"FAIL: POST /transcreate returned {response.status_code}")
            return False
        
        data = response.json()
        
        # Check that it's degraded due to max_change_ratio
        if data.get("degraded", False):
            print("PASS: Correctly degraded due to policy violation")
        else:
            print(f"FAIL: Should be degraded, got degraded={data.get('degraded')}")
            return False
        
        degrade_reasons = data.get("degrade_reasons", [])
        if "max_change_ratio_exceeded" in degrade_reasons:
            print("PASS: Correct degrade reason found")
        else:
            print(f"FAIL: Expected 'max_change_ratio_exceeded' in reasons, got {degrade_reasons}")
            return False
        
        return True
        
    except Exception as e:
        print(f"FAIL: Policy violation test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing TranceCreate Pipeline v1.2")
    print("=" * 50)
    
    # Check if service is running
    try:
        response = requests.get(f"{TC_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Service not running at {TC_URL}")
            sys.exit(1)
    except:
        print(f"❌ Cannot connect to service at {TC_URL}")
        print("Please start the service: python tc_server.py")
        sys.exit(1)
    
    # Run tests
    tests = [
        test_case_a_default_pipeline,
        test_case_b_pipeline_update,
        test_case_c_fallback_transcreation,
        test_case_d_policy_violation
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
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
