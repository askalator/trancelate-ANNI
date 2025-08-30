#!/usr/bin/env bash
set -euo pipefail
AQS_MIN=${AQS_MIN:-0.65}
DIVERSITY_ENFORCE=${DIVERSITY_ENFORCE:-1}
PASS=0; FAIL=0
for f in "$@"; do
  out=$(./anni_copy_gate.py "$f")
  avg=$(jq -r '.aggregate.avg_aqs' <<<"$out")
  div=$(jq -r '.aggregate.diversity_ok' <<<"$out")
  ok=1
  awk "BEGIN{ exit !($avg >= $AQS_MIN) }" || ok=0
  if [[ "$DIVERSITY_ENFORCE" == "1" && "$div" != "true" ]]; then ok=0; fi
  if [[ $ok -eq 1 ]]; then
    echo "PASS $f avg_aqs=$avg diversity=$div"
    PASS=$((PASS+1))
  else
    echo "FAIL $f avg_aqs=$avg diversity=$div"
    FAIL=$((FAIL+1))
  fi
done
echo "Summary: PASS=$PASS FAIL=$FAIL (AQS_MIN=$AQS_MIN DIVERSITY_ENFORCE=$DIVERSITY_ENFORCE)"
test $FAIL -eq 0
