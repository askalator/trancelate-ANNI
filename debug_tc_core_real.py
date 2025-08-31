import sys
sys.path.append('.')

from tc_stages.core import TcCoreStage

# Test the TcCoreStage with the real context from tc_server
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

print("Before TcCoreStage:")
print(f"  baseline: {ctx['baseline']}")
print(f"  baseline_text: {ctx['baseline_text']}")
print(f"  text: {ctx['text']}")

# Test tc_generate directly
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tc_server import tc_generate, generate_stable_seed

try:
    baseline_text = ctx.get('baseline', '')
    seed = ctx.get('seed')
    if seed is None:
        seed = generate_stable_seed(
            baseline_text,
            ctx.get('target', ''),
            ctx.get('profile', ''),
            ctx.get('persona', ''),
            ctx.get('level', 1)
        )
    
    transcreated_text, tc_model = tc_generate(
        baseline_text,
        ctx.get('target', ''),
        ctx.get('profile', ''),
        ctx.get('persona', ''),
        ctx.get('level', 1),
        seed
    )
    
    print(f"\nDirect tc_generate result:")
    print(f"  transcreated_text: {transcreated_text}")
    print(f"  tc_model: {tc_model}")
    
except Exception as e:
    print(f"\nERROR in tc_generate: {e}")
    import traceback
    traceback.print_exc()

# Run TcCoreStage
stage = TcCoreStage()
try:
    result = stage.run(ctx)
    print("\nAfter TcCoreStage:")
    print(f"  baseline_text: {result.get('baseline_text', 'N/A')}")
    print(f"  tc_candidate_text: {result.get('tc_candidate_text', 'N/A')}")
    print(f"  text: {result.get('text', 'N/A')}")
    print(f"  tc_equal_baseline: {result.get('trace', {}).get('tc_equal_baseline', 'N/A')}")
    print(f"  tc_model: {result.get('trace', {}).get('tc_model', 'N/A')}")
except Exception as e:
    print(f"\nERROR in TcCoreStage: {e}")
    import traceback
    traceback.print_exc()
