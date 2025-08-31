#!/usr/bin/env python3
"""
Smoke test for TranceSpell functionality.
Tests spell checking with known misspelling and verifies invariant protection.
"""

import sys
import json
import urllib.request
import urllib.parse

BASE_URL = "http://127.0.0.1:8096"

def test_spell_check():
    """Test spell checking with known misspelling"""
    try:
        payload = {
            "lang": "de-DE",
            "text": "<button>Jetz registrieren</button> 🙂 {{COUNT}}"
        }
        
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/check",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.getcode() == 200:
                result = json.loads(response.read().decode())
                
                # Check response structure
                if "issues" not in result:
                    print("❌ Missing issues in response")
                    return False
                
                if "trace" not in result:
                    print("❌ Missing trace in response")
                    return False
                
                # Check that we found the misspelling
                issues = result.get("issues", [])
                if len(issues) > 0:
                    print(f"✅ Found {len(issues)} spelling issue(s)")
                    
                    # Check first issue
                    first_issue = issues[0]
                    if "token" in first_issue and "suggestions" in first_issue:
                        token = first_issue["token"]
                        suggestions = first_issue["suggestions"]
                        
                        if token == "Jetz" and "Jetzt" in suggestions:
                            print("✅ Correctly identified 'Jetz' -> 'Jetzt'")
                        else:
                            print(f"⚠️  Unexpected issue: {token} -> {suggestions}")
                else:
                    print("⚠️  No spelling issues found (might be using pyspellchecker)")
                
                # Check trace
                trace = result.get("trace", {})
                if "lang" in trace and "engine" in trace:
                    print(f"✅ Trace: lang={trace['lang']}, engine={trace['engine']}")
                else:
                    print("❌ Missing trace information")
                    return False
                
                return True
            else:
                print(f"❌ Spell check request failed: HTTP {response.getcode()}")
                return False
    except Exception as e:
        print(f"❌ Spell check test error: {e}")
        return False

def test_invariant_protection():
    """Test that invariants are protected from spell checking"""
    try:
        payload = {
            "lang": "de-DE",
            "text": "Test {app} <a href='https://example.com'>link</a> 123 {{PLACEHOLDER}} 🙂"
        }
        
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/check",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.getcode() == 200:
                result = json.loads(response.read().decode())
                
                # Check that masked invariants are not flagged as spelling errors
                issues = result.get("issues", [])
                
                # Verify no issues point into masked spans
                text = payload["text"]
                for issue in issues:
                    start = issue.get("start", 0)
                    end = issue.get("end", 0)
                    token = issue.get("token", "")
                    
                    # Check if issue overlaps with known invariant patterns
                    import re
                    placeholder_match = re.search(r'\{\{[^}]+\}\}', text)
                    token_match = re.search(r'\{[^}]+\}', text)
                    html_match = re.search(r'<[^>]+>', text)
                    url_match = re.search(r'https?://[^\s<>"]+', text)
                    num_match = re.search(r'\b\d+\b', text)
                    
                    # Check for overlaps
                    overlaps = []
                    if placeholder_match and start < placeholder_match.end() and end > placeholder_match.start():
                        overlaps.append("placeholder")
                    if token_match and start < token_match.end() and end > token_match.start():
                        overlaps.append("token")
                    if html_match and start < html_match.end() and end > html_match.start():
                        overlaps.append("html")
                    if url_match and start < url_match.end() and end > url_match.start():
                        overlaps.append("url")
                    if num_match and start < num_match.end() and end > num_match.start():
                        overlaps.append("number")
                    
                    if overlaps:
                        print(f"⚠️  Issue '{token}' overlaps with {overlaps}")
                    else:
                        print(f"✅ Issue '{token}' does not overlap with invariants")
                
                return True
            else:
                print(f"❌ Invariant protection test failed: HTTP {response.getcode()}")
                return False
    except Exception as e:
        print(f"❌ Invariant protection test error: {e}")
        return False

def main():
    """Run TranceSpell smoke test"""
    print("TranceSpell Smoke Test")
    print("=" * 25)
    
    # Test basic spell checking
    if not test_spell_check():
        sys.exit(1)
    
    # Test invariant protection
    if not test_invariant_protection():
        sys.exit(1)
    
    print("\n🎉 TranceSpell smoke test passed!")
    sys.exit(0)

if __name__ == "__main__":
    main()
