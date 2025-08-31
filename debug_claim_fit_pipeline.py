import sys
sys.path.append('.')

from tc_stages.claim_fit import ClaimFitStage

# Test the ClaimFitStage with the actual pipeline context
ctx = {
    "original_text": "<button>Short</button>",
    "baseline": "<button>Short</button>",
    "text": "<button>Very long button text that should be shortened</button>",  # This should be the transcreated text
    "trace": {}
}

print("Before ClaimFitStage:")
print(f"  original_text: {ctx['original_text']}")
print(f"  baseline: {ctx['baseline']}")
print(f"  text: {ctx['text']}")

# Run ClaimFitStage
stage = ClaimFitStage()
result = stage.run(ctx)

print("\nAfter ClaimFitStage:")
print(f"  text: {result['text']}")
print(f"  claim_fit trace: {result.get('trace', {}).get('claim_fit', [])}")

# Test what happens if tc_core sets text to baseline
ctx2 = {
    "original_text": "<button>Short</button>",
    "baseline": "<button>Short</button>",
    "text": "<button>Short</button>",  # tc_core set this to baseline
    "trace": {}
}

print("\n\nTesting with tc_core output:")
print(f"  original_text: {ctx2['original_text']}")
print(f"  baseline: {ctx2['baseline']}")
print(f"  text: {ctx2['text']}")

result2 = stage.run(ctx2)

print("\nAfter ClaimFitStage:")
print(f"  text: {result2['text']}")
print(f"  claim_fit trace: {result2.get('trace', {}).get('claim_fit', [])}")
