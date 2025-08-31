import sys
sys.path.append('.')

from tc_stages.claim_fit import ClaimFitStage

# Test the ClaimFitStage with different source and target lengths
ctx = {
    "original_text": "<button>Short</button>",  # Source: 5 characters
    "baseline_text": "<button>Short</button>",
    "tc_candidate_text": "<button>Very long button text that should be shortened</button>",  # Target: 46 characters
    "text": "<button>Very long button text that should be shortened</button>",
    "trace": {}
}

print("Before ClaimFitStage:")
print(f"  original_text: {ctx['original_text']}")
print(f"  baseline_text: {ctx['baseline_text']}")
print(f"  tc_candidate_text: {ctx['tc_candidate_text']}")
print(f"  text: {ctx['text']}")

# Run ClaimFitStage
stage = ClaimFitStage()
result = stage.run(ctx)

print("\nAfter ClaimFitStage:")
print(f"  text: {result['text']}")
print(f"  claim_fit trace: {result.get('trace', {}).get('claim_fit', [])}")
print(f"  claim_fit_ratio_vs_original: {result.get('trace', {}).get('claim_fit_ratio_vs_original', 'N/A')}")

# Test UI element detection
print("\nUI Element Detection:")
source_elements = stage._detect_ui_elements(ctx['original_text'])
target_elements = stage._detect_ui_elements(ctx['tc_candidate_text'])

print(f"  Source elements: {source_elements}")
print(f"  Target elements: {target_elements}")
