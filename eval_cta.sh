#!/usr/bin/env bash
set -euo pipefail
read -r -p "CTA #1: " v1
read -r -p "CTA #2: " v2
read -r -p "CTA #3: " v3
jq -n --arg v1 "$v1" --arg v2 "$v2" --arg v3 "$v3" '{
  task:"cta",
  brief:{brand_terms:["TranceLate"], never_translate:["TranceLate"], avoid:[], key_points:[], tone_markers_any:[]},
  variants: [$v1,$v2,$v3]
}' > eval_anni_cta_de.json
./anni_copy_gate.py eval_anni_cta_de.json | tee eval_anni_cta_de.out
./run_quality.sh eval_anni_cta_de.json
