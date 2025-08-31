import sys
sys.path.append('.')

from tc_stages.core import TcCoreStage

# Test the TcCoreStage directly
ctx = {
    "source": "en",
    "target": "de", 
    "baseline": "<button>Short</button>",
    "text": "<button>Short</button>",
    "profile": "marketing",
    "persona": "ogilvy",
    "level": 1,
    "policies": {"max_change_ratio": 0.5},
    "seed": 12345,
    "trace": {},
    "degrade_reasons": []
}

print("Before TcCoreStage:")
print(f"  baseline: {ctx['baseline']}")
print(f"  text: {ctx['text']}")

# Run TcCoreStage
stage = TcCoreStage()
result = stage.run(ctx)

print("\nAfter TcCoreStage:")
print(f"  baseline_text: {result.get('baseline_text', 'N/A')}")
print(f"  tc_candidate_text: {result.get('tc_candidate_text', 'N/A')}")
print(f"  text: {result.get('text', 'N/A')}")
print(f"  tc_equal_baseline: {result.get('trace', {}).get('tc_equal_baseline', 'N/A')}")
print(f"  tc_model: {result.get('trace', {}).get('tc_model', 'N/A')}")
