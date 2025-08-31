import sys
sys.path.append('.')

from tc_pipeline import compute_char_ratio
from tc_stages.core import PolicyCheckStage

# Test the PolicyCheckStage directly
ctx = {
    "baseline": "Hello <b>HTML</b> 123 🙂 {{X}}",
    "text": "Hallo <b> HTML </b> 123 🙂 {{X}}",
    "policies": {
        "max_change_ratio": 0.25,
        "preserve": ["placeholders", "single_brace", "html", "numbers", "urls", "emojis"]
    }
}

print("Before PolicyCheckStage:")
print(f"  baseline: {ctx['baseline']}")
print(f"  text: {ctx['text']}")
print(f"  policies: {ctx['policies']}")

# Test compute_char_ratio directly
ratio = compute_char_ratio(ctx['baseline'], ctx['text'])
print(f"  compute_char_ratio: {ratio}")

# Run PolicyCheckStage
stage = PolicyCheckStage()
result = stage.run(ctx)

print("\nAfter PolicyCheckStage:")
print(f"  degrade_reasons: {result.get('degrade_reasons', [])}")
print(f"  trace: {result.get('trace', {})}")
