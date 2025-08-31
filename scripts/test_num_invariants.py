#!/usr/bin/env python3
"""
Test script for number invariants in Guard
"""
import sys
import os
import requests
import json

def test_number_invariants():
    """Test that numbers are preserved as single tokens"""
    base_url = "http://127.0.0.1:8091"
    
    tests = [
        {
            "name": "A) Price $1,234.56",
            "text": "Price $1,234.56",
            "source": "en",
            "target": "de",
            "expected_pattern": "1,234.56",
            "description": "Decimal number with commas"
        },
        {
            "name": "B) 1990–2014",
            "text": "Valid period 1990–2014",
            "source": "en", 
            "target": "de",
            "expected_pattern": "1990–2014",
            "description": "Year range with en dash"
        },
        {
            "name": "C) 1 234,56 € (U+202F)",
            "text": "Price 1\u202F234,56 €",
            "source": "de",
            "target": "en", 
            "expected_pattern": "1\u202F234,56",
            "description": "Number with narrow non-breaking space"
        }
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\n{test['name']}: {test['description']}")
        print(f"Input: {test['text']}")
        
        payload = {
            "source": test["source"],
            "target": test["target"],
            "text": test["text"]
        }
        
        try:
            response = requests.post(f"{base_url}/translate", json=payload, timeout=30)
            
            if response.status_code != 200:
                print(f"✗ FAIL: HTTP {response.status_code}")
                continue
            
            result = response.json()
            translated_text = result.get("translated_text", "")
            checks = result.get("checks", {})
            
            print(f"Output: {translated_text}")
            print(f"Checks: {checks}")
            
            # Check that num_ok is True
            if not checks.get("num_ok", False):
                print(f"✗ FAIL: checks.num_ok is not True")
                continue
            
            # Check that expected pattern is preserved
            if test["expected_pattern"] not in translated_text:
                print(f"✗ FAIL: Expected pattern '{test['expected_pattern']}' not found in output")
                continue
            
            # Check for digit splitting patterns (should not exist)
            digit_splits = [
                "1 23 4", "1, 23 4", "1 23 4. 56",
                "1 99 0", "1 99 0–", "–2 01 4",
                "1 23 4, 56"
            ]
            
            split_found = False
            for split_pattern in digit_splits:
                if split_pattern in translated_text:
                    print(f"✗ FAIL: Digit splitting detected: '{split_pattern}'")
                    split_found = True
                    break
            
            if split_found:
                continue
            
            print(f"✓ PASS: {test['name']}")
            passed += 1
            
        except Exception as e:
            print(f"✗ FAIL: {e}")
            continue
    
    print(f"\nSUMMARY {passed}/{total} PASS")
    return passed == total

if __name__ == "__main__":
    print("🧪 Testing number invariants in Guard...")
    
    success = test_number_invariants()
    
    if success:
        print("\n✅ All number invariant tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some number invariant tests failed!")
        sys.exit(1)
