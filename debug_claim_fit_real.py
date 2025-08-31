
import sys
sys.path.append('.')

from tc_stages.claim_fit import ClaimFitStage

# Test the ClaimFitStage with the real context
ctx = {
    "source": "en",
    "target": "de", 
    "baseline": "<button> Short </button>",
    "baseline_text": "<button> Short </button>",
    "tc_candidate_text": "<button> Short </button>",
    "text": "<button> Short </button>",
    "original_text": "<button>Short</button>",
    "profile": "marketing",
    "persona": "ogilvy",
    "level": 1,
    "policies": {"max_change_ratio": 0.5},
    "seed": 12345,
    "trace": {"tc_equal_baseline": True, "tc_model": "fallback"},
    "degrade_reasons": []
}

print("Before ClaimFitStage:")
print(f"  original_text: {ctx['original_text']}")
print(f"  tc_candidate_text: {ctx['tc_candidate_text']}")
print(f"  text: {ctx['text']}")

# Run ClaimFitStage
stage = ClaimFitStage()
try:
    result = stage.run(ctx)
    print("\nAfter ClaimFitStage:")
    print(f"  text: {result.get('text', 'N/A')}")
    print(f"  claim_fit trace: {result.get('trace', {}).get('claim_fit', [])}")
    print(f"  claim_fit_ratio_vs_original: {result.get('trace', {}).get('claim_fit_ratio_vs_original', 'N/A')}")
except Exception as e:
    print(f"\nERROR in ClaimFitStage: {e}")
    import traceback
    traceback.print_exc()
