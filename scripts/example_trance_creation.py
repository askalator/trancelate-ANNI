#!/usr/bin/env python3
"""
TranceCreation v1 Example Usage
Demonstrates how to use the TranceCreation API with different profiles, personas, and policies
"""

import requests
import json
import sys

# Configuration
TC_URL = "http://127.0.0.1:8095"

def print_response(data, title):
    """Pretty print response data"""
    print(f"\n{'='*60}")
    print(f"📝 {title}")
    print(f"{'='*60}")
    print(f"Baseline:     {data['baseline_text']}")
    print(f"Transcreated: {data['transcreated_text']}")
    print(f"Char Ratio:   {data['diffs']['char_ratio']:.3f}")
    print(f"Degraded:     {data['degraded']}")
    print(f"Profile:      {data['applied']['profile']}")
    print(f"Persona:      {data['applied']['persona']}")
    print(f"Level:        {data['applied']['level']}")
    print(f"Guard Latency: {data['trace']['guard_latency_ms']}ms")
    print(f"TC Latency:    {data['trace']['tc_latency_ms']}ms")

def example_marketing_ogilvy():
    """Example: Marketing profile with Ogilvy persona"""
    print("\n🚀 Example 1: Marketing + Ogilvy (Level 2)")
    
    response = requests.post(
        f"{TC_URL}/transcreate",
        headers={"Content-Type": "application/json"},
        json={
            "source": "en",
            "target": "ja",
            "text": "Discover our amazing products with {{COUNT}} items available. Visit our website at https://example.com for more information.",
            "profile": "marketing",
            "persona": "ogilvy",
            "level": 2
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print_response(data, "Marketing + Ogilvy (Level 2)")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

def example_social_halbert():
    """Example: Social profile with Halbert persona"""
    print("\n🚀 Example 2: Social + Halbert (Level 3)")
    
    response = requests.post(
        f"{TC_URL}/transcreate",
        headers={"Content-Type": "application/json"},
        json={
            "source": "en",
            "target": "de",
            "text": "Check out our new collection! Limited time offer with {{DISCOUNT}}% off.",
            "profile": "social",
            "persona": "halbert",
            "level": 3
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print_response(data, "Social + Halbert (Level 3)")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

def example_with_baseline():
    """Example: Using provided baseline text"""
    print("\n🚀 Example 3: Using Baseline Text")
    
    baseline = "素晴らしい製品を発見してください。{{COUNT}}個のアイテムが利用可能です。詳細については、https://example.com のウェブサイトをご覧ください。"
    
    response = requests.post(
        f"{TC_URL}/transcreate",
        headers={"Content-Type": "application/json"},
        json={
            "target": "ja",
            "baseline_text": baseline,
            "profile": "marketing",
            "persona": "brand-warm",
            "level": 1
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print_response(data, "Using Baseline Text")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

def example_policy_enforcement():
    """Example: Policy enforcement with forbidden terms"""
    print("\n🚀 Example 4: Policy Enforcement")
    
    response = requests.post(
        f"{TC_URL}/transcreate",
        headers={"Content-Type": "application/json"},
        json={
            "target": "en",
            "baseline_text": "This is a test message about our products.",
            "profile": "marketing",
            "persona": "halbert",
            "level": 2,
            "policies": {
                "forbidden_terms": ["guarantee", "free shipping", "limited time"],
                "max_change_ratio": 0.15
            }
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print_response(data, "Policy Enforcement")
        print(f"Forbidden Found: {data['checks'].get('forbidden_found', [])}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

def example_multiple_languages():
    """Example: Multiple target languages"""
    print("\n🚀 Example 5: Multiple Languages")
    
    source_text = "Discover our amazing products with {{COUNT}} items available."
    languages = ["ja", "zh", "ar"]
    
    for lang in languages:
        print(f"\n--- {lang.upper()} ---")
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
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Transcreated: {data['transcreated_text']}")
            print(f"Char Ratio: {data['diffs']['char_ratio']:.3f}")
        else:
            print(f"❌ Error: {response.status_code}")

def example_conservative_level():
    """Example: Conservative level (0)"""
    print("\n🚀 Example 6: Conservative Level (0)")
    
    response = requests.post(
        f"{TC_URL}/transcreate",
        headers={"Content-Type": "application/json"},
        json={
            "source": "en",
            "target": "fr",
            "text": "Our products are designed for quality and reliability.",
            "profile": "technical",
            "persona": "default",
            "level": 0
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print_response(data, "Conservative Level (0)")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

def main():
    """Run all examples"""
    print("🎨 TranceCreation v1 Examples")
    print("=" * 60)
    
    # Check if service is running
    try:
        health_response = requests.get(f"{TC_URL}/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ TranceCreation service is not running")
            print("   Start it with: ./start_trance_creation.sh")
            return 1
    except Exception as e:
        print("❌ Cannot connect to TranceCreation service")
        print("   Start it with: ./start_trance_creation.sh")
        return 1
    
    print("✅ TranceCreation service is running")
    
    # Run examples
    examples = [
        example_marketing_ogilvy,
        example_social_halbert,
        example_with_baseline,
        example_policy_enforcement,
        example_multiple_languages,
        example_conservative_level
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"❌ Example failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Examples completed!")
    print("\n📚 Available Profiles:")
    print("   - marketing: Persuasive, benefit-focused")
    print("   - social: Casual, engaging, shareable")
    print("   - technical: Precise, detailed, professional")
    print("   - creative: Imaginative, expressive, artistic")
    
    print("\n👤 Available Personas:")
    print("   - ogilvy: Clear, precise, elegant, subtle")
    print("   - halbert: Bold, direct-response, urgency, proof")
    print("   - default: Clear, professional, balanced")
    print("   - direct-response: Urgent, action-oriented")
    print("   - brand-warm: Friendly, approachable, trustworthy")
    print("   - luxury: Sophisticated, exclusive, premium")
    print("   - casual: Relaxed, informal, friendly")
    print("   - authoritative: Confident, expert, trustworthy")
    
    print("\n📊 Levels:")
    print("   - 0: Minimal changes, very conservative")
    print("   - 1: Light improvements, subtle enhancements")
    print("   - 2: Moderate changes, noticeable improvements")
    print("   - 3: Significant changes, bold enhancements")

if __name__ == "__main__":
    sys.exit(main())
