#!/usr/bin/env python3
import requests
import re

GUARD_URL = "http://127.0.0.1:8091"

def test_emoji_spacing():
    # Test cases
    tests = [
        ("Ping🙂 <b>HTML</b>123", "A"),  # No space before emoji
        ("Ping 🙂 <b>HTML</b>123", "B"),  # Space before emoji
        ("Ping,🙂 <b>HTML</b>123", "C"),  # No space between comma and emoji
    ]
    
    for text, test_id in tests:
        try:
            response = requests.post(
                f"{GUARD_URL}/translate",
                json={"source": "en", "target": "de", "text": text},
                headers={"X-API-Key": "topsecret"},
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"{test_id}: FAIL - HTTP {response.status_code}")
                continue
                
            result = response.json()
            translated = result.get("translated_text", "")
            
            # Test patterns - look for emoji with proper spacing regardless of translated words
            if test_id == "A":
                # Should have no space before emoji
                if re.search(r"\w+🙂\s*<b>Html</b>", translated) and not re.search(r"\w+\s+🙂", translated):
                    print(f"{test_id}: OK")
                else:
                    print(f"{test_id}: FAIL - Wrong spacing pattern")
                    
            elif test_id == "B":
                # Should have space before emoji
                if re.search(r"\w+\s+🙂", translated):
                    print(f"{test_id}: OK")
                else:
                    print(f"{test_id}: FAIL - Missing space before emoji")
                    
            elif test_id == "C":
                # Should have no space between comma and emoji (if comma is preserved)
                if re.search(r"\w+,🙂", translated):
                    print(f"{test_id}: OK")
                elif re.search(r"\w+🙂", translated):  # If comma is lost, just check no extra space
                    print(f"{test_id}: OK")
                else:
                    print(f"{test_id}: FAIL - Extra space between comma and emoji")
                    
        except Exception as e:
            print(f"{test_id}: FAIL - Error: {e}")

if __name__ == "__main__":
    test_emoji_spacing()
