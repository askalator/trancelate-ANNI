import sys
sys.path.append('.')

from tc_stages.core import TcCoreStage
from tc_stages.claim_fit import ClaimFitStage
from tc_stages.core import PolicyCheckStage
from tc_stages.core import DegradeStage

# Test the full pipeline with the real context
ctx = {
    "source": "en",
    "target": "de", 
    "baseline": "<button> Short </button>",
    "baseline_text": "<button> Short </button>",
    "text": "<button> Short </button>",
    "original_text": "<button>Short</button>",
    "profile": "marketing",
    "persona": "ogilvy",
    "level": 1,
    "policies": {"max_change_ratio": 0.5},
    "seed": 12345,
    "trace": {},
    "degrade_reasons": []
}

print("Initial context:")
print(f"  baseline: {ctx['baseline']}")
print(f"  baseline_text: {ctx['baseline_text']}")
print(f"  text: {ctx['text']}")
print(f"  original_text: {ctx['original_text']}")

# Run pipeline stages
stages = [TcCoreStage(), ClaimFitStage(), PolicyCheckStage(), DegradeStage()]

for i, stage in enumerate(stages):
    print(f"\n--- Stage {i+1}: {stage.name} ---")
    try:
        ctx = stage.run(ctx)
        print(f"  text: {ctx.get('text', 'N/A')}")
        print(f"  trace keys: {list(ctx.get('trace', {}).keys())}")
        if 'claim_fit' in ctx.get('trace', {}):
            print(f"  claim_fit: {ctx['trace']['claim_fit']}")
    except Exception as e:
        print(f"  ERROR in {stage.name}: {e}")
        import traceback
        traceback.print_exc()

print(f"\nFinal result:")
print(f"  text: {ctx.get('text', 'N/A')}")
print(f"  claim_fit trace: {ctx.get('trace', {}).get('claim_fit', [])}")
print(f"  claim_fit_ratio_vs_original: {ctx.get('trace', {}).get('claim_fit_ratio_vs_original', 'N/A')}")
