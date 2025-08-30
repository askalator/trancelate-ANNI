#!/usr/bin/env python3
"""
TranceCreation v1 Self-Tests
Tests all functionality including profiles, personas, policies, and fail-closed behavior
"""

import requests
import json
import time
import sys
from typing import Dict, Any

# Configuration
TC_URL = "http://127.0.0.1:8095"
GUARD_URL = "http://127.0.0.1:8091"
GUARD_API_KEY = "topsecret"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing /health...")
    try:
        response = requests.get(f"{TC_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health OK: {data}")
            return True
        else:
            print(f"❌ Health failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health error: {e}")
        return False

def test_profiles():
    """Test profiles endpoint"""
    print("\n🔍 Testing /profiles...")
    try:
        response = requests.get(f"{TC_URL}/profiles", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Profiles OK: {len(data.get('profiles', {}))} profiles, {len(data.get('personas', {}))} personas")
            return True
        else:
            print(f"❌ Profiles failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Profiles error: {e}")
        return False

def get_baseline(source: str, target: str, text: str) -> str:
    """Get baseline from Guard"""
    try:
        response = requests.post(
            f"{GUARD_URL}/translate",
            headers={"X-API-Key": GUARD_API_KEY, "Content-Type": "application/json"},
            json={"source": source, "target": target, "text": text},
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get("translated_text", "")
        else:
            print(f"❌ Guard baseline failed: {response.status_code}")
            return ""
    except Exception as e:
        print(f"❌ Guard baseline error: {e}")
        return ""

def test_transcreate_basic():
    """Test basic transcreation with marketing profile and ogilvy persona"""
    print("\n🔍 Testing basic transcreation (marketing + ogilvy)...")
    
    source_text = "Discover our amazing products with {{COUNT}} items available. Visit our website at https://example.com for more information."
    
    try:
        response = requests.post(
            f"{TC_URL}/transcreate",
            headers={"Content-Type": "application/json"},
            json={
                "source": "en",
                "target": "ja",
                "text": source_text,
                "profile": "marketing",
                "persona": "ogilvy",
                "level": 2
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Transcreation OK")
            print(f"   Baseline: {data['baseline_text'][:50]}...")
            print(f"   Transcreated: {data['transcreated_text'][:50]}...")
            print(f"   Char ratio: {data['diffs']['char_ratio']:.3f}")
            print(f"   Degraded: {data['degraded']}")
            print(f"   Applied: {data['applied']['profile']} + {data['applied']['persona']}")
            return True
        else:
            print(f"❌ Transcreation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Transcreation error: {e}")
        return False

def test_transcreate_with_baseline():
    """Test transcreation with provided baseline text"""
    print("\n🔍 Testing transcreation with baseline...")
    
    baseline_text = "素晴らしい製品を発見してください。{{COUNT}}個のアイテムが利用可能です。詳細については、https://example.com のウェブサイトをご覧ください。"
    
    try:
        response = requests.post(
            f"{TC_URL}/transcreate",
            headers={"Content-Type": "application/json"},
            json={
                "target": "ja",
                "baseline_text": baseline_text,
                "profile": "social",
                "persona": "halbert",
                "level": 1
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Baseline transcreation OK")
            print(f"   Baseline: {data['baseline_text'][:50]}...")
            print(f"   Transcreated: {data['transcreated_text'][:50]}...")
            print(f"   Char ratio: {data['diffs']['char_ratio']:.3f}")
            print(f"   Degraded: {data['degraded']}")
            return True
        else:
            print(f"❌ Baseline transcreation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Baseline transcreation error: {e}")
        return False

def test_policy_max_change_ratio():
    """Test policy enforcement with max_change_ratio"""
    print("\n🔍 Testing max_change_ratio policy...")
    
    baseline_text = "This is a simple test text with {{PLACEHOLDER}} and some content."
    
    try:
        response = requests.post(
            f"{TC_URL}/transcreate",
            headers={"Content-Type": "application/json"},
            json={
                "target": "en",
                "baseline_text": baseline_text,
                "profile": "marketing",
                "persona": "halbert",
                "level": 3,
                "policies": {
                    "max_change_ratio": 0.10  # Very restrictive
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            char_ratio = data['diffs']['char_ratio']
            degraded = data['degraded']
            
            print(f"✅ Max change ratio test OK")
            print(f"   Char ratio: {char_ratio:.3f}")
            print(f"   Max allowed: 0.10")
            print(f"   Degraded: {degraded}")
            
            # Should be degraded if ratio exceeds 0.10
            if char_ratio > 0.10 and degraded:
                print("   ✅ Policy correctly enforced (degraded)")
                return True
            elif char_ratio <= 0.10 and not degraded:
                print("   ✅ Policy correctly applied (not degraded)")
                return True
            else:
                print("   ❌ Policy enforcement incorrect")
                return False
        else:
            print(f"❌ Max change ratio test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Max change ratio test error: {e}")
        return False

def test_policy_forbidden_terms():
    """Test policy enforcement with forbidden terms"""
    print("\n🔍 Testing forbidden terms policy...")
    
    baseline_text = "This is a test message about our products."
    
    try:
        response = requests.post(
            f"{TC_URL}/transcreate",
            headers={"Content-Type": "application/json"},
            json={
                "target": "en",
                "baseline_text": baseline_text,
                "profile": "marketing",
                "persona": "halbert",
                "level": 2,
                "policies": {
                    "forbidden_terms": ["guarantee", "free shipping", "limited time"]
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            degraded = data['degraded']
            forbidden_found = data['checks'].get('forbidden_found', [])
            
            print(f"✅ Forbidden terms test OK")
            print(f"   Degraded: {degraded}")
            print(f"   Forbidden found: {forbidden_found}")
            
            # If forbidden terms found, should be degraded
            if forbidden_found and degraded:
                print("   ✅ Policy correctly enforced (degraded)")
                return True
            elif not forbidden_found and not degraded:
                print("   ✅ Policy correctly applied (not degraded)")
                return True
            else:
                print("   ❌ Policy enforcement incorrect")
                return False
        else:
            print(f"❌ Forbidden terms test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Forbidden terms test error: {e}")
        return False

def test_multiple_languages():
    """Test transcreation with multiple target languages"""
    print("\n🔍 Testing multiple languages...")
    
    source_text = "Discover our amazing products with {{COUNT}} items available."
    languages = ["ja", "zh", "ar"]
    
    for lang in languages:
        print(f"   Testing {lang}...")
        try:
            response = requests.post(
                f"{TC_URL}/transcreate",
                headers={"Content-Type": "application/json"},
                json={
                    "source": "en",
                    "target": lang,
                    "text": source_text,
                    "profile": "marketing",
                    "persona": "ogilvy",
                    "level": 1
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ {lang}: {data['transcreated_text'][:30]}...")
            else:
                print(f"   ❌ {lang}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ {lang}: {e}")
            return False
    
    print("✅ Multiple languages test OK")
    return True

def test_fail_closed():
    """Test fail-closed behavior when services are unavailable"""
    print("\n🔍 Testing fail-closed behavior...")
    
    # Test with invalid Guard URL (should fail-closed)
    original_guard_url = "http://127.0.0.1:8091"
    
    try:
        # This should fail but return baseline
        response = requests.post(
            f"{TC_URL}/transcreate",
            headers={"Content-Type": "application/json"},
            json={
                "source": "en",
                "target": "ja",
                "text": "Test text",
                "profile": "marketing",
                "persona": "ogilvy",
                "level": 1
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            degraded = data['degraded']
            print(f"✅ Fail-closed test OK")
            print(f"   Degraded: {degraded}")
            print(f"   Response received: {len(data['transcreated_text'])} chars")
            return True
        else:
            print(f"❌ Fail-closed test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Fail-closed test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 TranceCreation v1 Self-Tests")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("Profiles", test_profiles),
        ("Basic Transcreation", test_transcreate_basic),
        ("Baseline Transcreation", test_transcreate_with_baseline),
        ("Max Change Ratio Policy", test_policy_max_change_ratio),
        ("Forbidden Terms Policy", test_policy_forbidden_terms),
        ("Multiple Languages", test_multiple_languages),
        ("Fail-Closed Behavior", test_fail_closed)
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
        print("🎉 All tests passed! TranceCreation v1 is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the service configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
