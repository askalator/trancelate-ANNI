# ANNI Minimal Refactor Notes

## Overview
This refactor unified shared logic, stabilized service boundaries, and standardized configuration/logging/tests without changing external behavior. All endpoints and stage behaviors remain exactly the same (backward compatible).

## Repository Layout Changes

### New Structure
```
/services
  /guard              # mt_guard.py (+ small helpers)
  /worker             # m2m_worker.py (M2M100)
  /trancecreate       # tc_server.py, tc_pipeline.py, tc_stages/*
  /trancespell        # ts_server.py, ts_core.py
/libs
  /trance_common
    masking.py        # shared freeze/unfreeze/regex
    langcodes.py      # normalize, aliases
    http.py           # tiny JSON client (urllib)
    checks.py         # ph/html/num/paren/len_eff logic
    trace.py          # safe helpers (append-only)
/config
  ports.json          # service port configuration
/openapi
  guard.yaml
  trancecreate.yaml
  trancespell.yaml
/scripts
  smoke_stack.py
  smoke_tc_claim_guard.py
  smoke_trancespell.py
```

## Shared Library Details

### libs/trance_common/masking.py
- **mask(text: str)** → (masked_text, spans, table)
- **unmask(text: str, spans, table)** → str (1:1 restoration)
- Categories: PLACEHOLDER_DBL, TOKEN_SGL, HTML_TAG, URL, EMOJI, NUM
- Regexes identical to current best version used by Guard/TC/TS

### libs/trance_common/langcodes.py
- **normalize(lang: str)** → str (en-US→en, de-DE→de, zh-*→zh, iw→he, in→id, pt-BR→pt)
- **primary(lang: str)** → str (returns primary subtag)

### libs/trance_common/http.py
- **json_get(url: str, timeout: float=5.0)** → (status_code, response_dict)
- **json_post(url: str, obj: dict, timeout: float=60.0)** → (status_code, response_dict)
- Uses urllib only, sets Connection: close

### libs/trance_common/checks.py
- **check_invariants(src: str, out: str)** → dict
- Returns: ph_ok, html_ok, num_ok, paren_ok, len_ratio, len_ratio_eff, len_use
- Uses current effective-length logic (emoji/symbol run fold)

### libs/trance_common/trace.py
- **t(ctx: dict)** → dict (returns ctx.setdefault("trace", {}))
- **push(ctx: dict, key: str, entry: dict)** → None (list append)
- Guarantees append-only behavior

## Service Adjustments

### Guard (/services/guard/mt_guard.py)
- Replaced local masking/lang/checks helpers with trance_common.*
- Backend URL normalization left intact
- Before calling Worker: freeze numbers/… via shared masking
- After response: unmask, then check_invariants, merge trace with append-only

### Worker (/services/worker/m2m_worker.py)
- No functional changes
- /health and /translate unchanged

### TranceCreate (/services/trancecreate/*)
- tc_server.py, tc_pipeline.py, tc_stages/*:
- Use trance_common.masking/langcodes/trace
- Keep claim_guard & claim_fit alias mapping untouched
- Ensure tc_core stores baseline_text, tc_candidate_text
- claim_guard continues to write detailed trace and ratio vs original

### TranceSpell (/services/trancespell/*)
- Use shared masking/langcodes
- Keep detection-only behavior

## Configuration

### /config/ports.json
```json
{
  "guard": 8091,
  "worker": 8093,
  "trancecreate": 8095,
  "trancespell": 8096
}
```

## Heavy Artifacts Policy
- .gitignore excludes: .venv/, __pycache__/, *.pyc, *.cache, *.tgz, models/, *.bin, *.safetensors, *.onnx, *.pt, *.ckpt, *.gguf, logs/
- No git-lfs introduced
- Large weights kept out of repo altogether

## Test Suite
- **/scripts/smoke_stack.py**: Checks Guard /meta, Worker /health, TranceCreate /health, TranceSpell /health
- **/scripts/smoke_tc_claim_guard.py**: Pipeline with claim_guard, tests shortening behavior
- **/scripts/smoke_trancespell.py**: Spell checking with known misspelling, verifies invariant protection

## Backward Compatibility
- claim_fit alias continues to work as stage ID → ClaimGuardStage
- No JSON field removals/renames; only additive trace keys allowed
- Guard invariants keep passing previous green tests
- TranceSpell remains detection-only
- All existing endpoints/ports/JSON shapes intact

## Done Criteria Met
- ✅ Repo compiles/starts as before (no API changes)
- ✅ Shared imports active throughout
- ✅ Trace present throughout; no stage overwrites ctx["trace"]
- ✅ No heavy files in git status
- ✅ Three smoke scripts pass from fresh clone

## Non-Goals (Not Changed)
- No GUI or CLI changes
- No new env/launch agents
- No performance tuning beyond import consolidation
- No breaking changes to existing functionality
