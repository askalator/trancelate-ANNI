import sys
sys.path.append('.')

from tc_pipeline import build_pipeline

# Test the pipeline directly
stages = ["tc_core", "claim_fit", "policy_check", "degrade"]
pipeline = build_pipeline(stages)

print("Pipeline stages:")
for i, stage in enumerate(pipeline):
    print(f"  {i+1}. {stage.name}")

# Test with context - use a text that should be transcreated
ctx = {
    "original_text": "<button>Short</button>",
    "baseline": "<button>Short</button>",
    "text": "<button>Click here to register now</button>",  # Different text
    "trace": {}
}

print("\nRunning pipeline...")
for stage in pipeline:
    print(f"Running stage: {stage.name}")
    try:
        ctx = stage.run(ctx)
        print(f"  Result: {ctx.get('text', 'N/A')[:50]}...")
        if stage.name == "claim_fit":
            print(f"  Claim fit trace: {ctx.get('trace', {}).get('claim_fit', [])}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
