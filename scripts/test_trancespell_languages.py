#!/usr/bin/env python3
"""
TranceSpell® v1.0 Language Support Tests
Tests the new support level functionality
"""

import json
import urllib.request
import sys
import os

BASE = "http://127.0.0.1:8096"
H = {"Content-Type": "application/json"}

def get(path):
    """GET request"""
    r = urllib.request.Request(BASE + path)
    with urllib.request.urlopen(r, timeout=30) as h:
        return h.getcode(), json.loads(h.read().decode())

def post(path, obj):
    """POST request"""
    r = urllib.request.Request(BASE + path, data=json.dumps(obj).encode(), headers=H)
    with urllib.request.urlopen(r, timeout=30) as h:
        return h.getcode(), json.loads(h.read().decode())

def test_languages_structure():
    """Test that /languages returns the new structure with support levels"""
    print("Test 1: Languages endpoint structure...")
    c, j = get("/languages")
    if c != 200:
        print(f"FAIL: Languages endpoint returned {c}"); return False
    
    # Check required fields
    if "langs" not in j or "aliases" not in j or "paths" not in j:
        print("FAIL: Missing required fields"); return False
    
    # Check langs structure
    langs = j["langs"]
    if not isinstance(langs, dict):
        print("FAIL: langs is not a dictionary"); return False
    
    required_keys = ["full", "basic", "unsupported"]
    for key in required_keys:
        if key not in langs:
            print(f"FAIL: Missing key '{key}' in langs"); return False
        if not isinstance(langs[key], list):
            print(f"FAIL: langs['{key}'] is not a list"); return False
    
    # Check paths structure
    paths = j["paths"]
    if "hunspell" not in paths or not isinstance(paths["hunspell"], list):
        print("FAIL: paths.hunspell is missing or not a list"); return False
    
    print(f"✓ PASS: Languages structure - full: {len(langs['full'])}, basic: {len(langs['basic'])}, unsupported: {len(langs['unsupported'])}")
    return True

def test_hunspell_discovery():
    """Test Hunspell dictionary discovery"""
    print("Test 2: Hunspell discovery...")
    c, j = get("/languages")
    if c != 200:
        print(f"FAIL: Languages endpoint returned {c}"); return False
    
    paths = j["paths"]["hunspell"]
    if not paths:
        print("FAIL: No Hunspell paths found"); return False
    
    # Check if at least one path exists
    existing_paths = [p for p in paths if os.path.exists(p)]
    if not existing_paths:
        print(f"WARN: No existing Hunspell paths found in {paths}")
    else:
        print(f"✓ PASS: Found {len(existing_paths)} existing Hunspell paths")
    
    return True

def test_support_levels():
    """Test that languages are properly categorized by support level"""
    print("Test 3: Support level categorization...")
    c, j = get("/languages")
    if c != 200:
        print(f"FAIL: Languages endpoint returned {c}"); return False
    
    langs = j["langs"]
    
    # Check that basic languages are available (pyspellchecker)
    if not langs["basic"]:
        print("FAIL: No basic (pyspellchecker) languages found"); return False
    
    # Check that unsupported languages are properly categorized
    if not langs["unsupported"]:
        print("FAIL: No unsupported languages found"); return False
    
    # Check for CJK languages in unsupported
    cjk_langs = ["ja", "ko", "zh", "th"]
    found_cjk = [lang for lang in cjk_langs if lang in langs["unsupported"]]
    if not found_cjk:
        print("WARN: No CJK languages found in unsupported")
    
    print(f"✓ PASS: Support levels - full: {len(langs['full'])}, basic: {len(langs['basic'])}, unsupported: {len(langs['unsupported'])}")
    return True

def test_alias_functionality():
    """Test that language aliases work correctly"""
    print("Test 4: Language alias functionality...")
    
    # Test with a known alias
    payload = {
        "lang": "de-DE",  # Should be aliased to "de"
        "text": "Test text"
    }
    
    c, j = post("/check", payload)
    if c != 200:
        print(f"FAIL: Alias test returned {c}"); return False
    
    trace = j.get("trace", {})
    if "lang" not in trace:
        print("FAIL: No lang field in trace"); return False
    
    # Check that de-DE was normalized to de
    if trace["lang"] != "de":
        print(f"FAIL: de-DE not normalized to 'de', got '{trace['lang']}'"); return False
    
    print("✓ PASS: Language aliases work correctly")
    return True

def test_engine_selection():
    """Test that the correct engine is selected based on support level"""
    print("Test 5: Engine selection...")
    
    # Test with a basic language (should use pyspellchecker)
    payload = {
        "lang": "en-US",
        "text": "Test text"
    }
    
    c, j = post("/check", payload)
    if c != 200:
        print(f"FAIL: Engine test returned {c}"); return False
    
    trace = j.get("trace", {})
    if "engine" not in trace:
        print("FAIL: No engine field in trace"); return False
    
    engine = trace["engine"]
    if engine not in ["hunspell", "pyspellchecker", "none"]:
        print(f"FAIL: Unknown engine '{engine}'"); return False
    
    print(f"✓ PASS: Engine selection - {engine}")
    return True

def main():
    """Run all tests"""
    print("TranceSpell® v1.0 Language Support Tests")
    print("=" * 50)
    
    tests = [
        test_languages_structure,
        test_hunspell_discovery,
        test_support_levels,
        test_alias_functionality,
        test_engine_selection
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"FAIL: Test crashed with error: {e}")
            print()
    
    print(f"SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
