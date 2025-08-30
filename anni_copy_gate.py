#!/usr/bin/env python3
import sys, json, re

# ---------- Budgets (sprachunabhängig) ----------
LEN_BUDGET = {
  "cta":      {"chars_max": 28},
  "headline": {"chars_max": 60},
  "subhead":  {"chars_min": 80, "chars_max": 140},
  "bullet":   {"words_min": 6,  "words_max": 14}
}

# ---------- Regex ----------
TAG = re.compile(r'</?[a-zA-Z][\w:-]*(\s[^<>]*?)?>', re.UNICODE)
PLACEHOLDER = re.compile(r'{{[^{}]+}}', re.UNICODE)
WORD = re.compile(r'\b[\w\-]+\b', re.UNICODE)
STARTS_WITH_LETTER = re.compile(r'^\s*[^\W\d_]', re.UNICODE)  # Unicode-Letter, kein Digit/_
ENDS_WITH_SENT_PUNCT = re.compile(r'[\.!?…,:;]\s*$', re.UNICODE)

# ---------- Helpers ----------
def strip_markup(s:str)->str:
  s = TAG.sub('', s)
  s = PLACEHOLDER.sub('', s)
  return s.strip()

def count_words(s:str)->int:
  return len(WORD.findall(s))

def length_ok(task, text):
  clean = strip_markup(text)
  if task=="bullet":
    mn = LEN_BUDGET["bullet"]["words_min"]; mx = LEN_BUDGET["bullet"]["words_max"]
    return mn <= count_words(clean) <= mx
  mx = LEN_BUDGET.get(task,{}).get("chars_max")
  mn = LEN_BUDGET.get(task,{}).get("chars_min", 0)
  n  = len(clean)
  return (mx is None or n <= mx) and (n >= mn)

def brand_ok(text, brands, never_translate):
  ok=True; t=text
  keys = set(brands or []) | set(never_translate or [])
  for b in keys:
    if not b: continue
    if re.search(re.escape(b), t, flags=re.IGNORECASE) and (b not in t):
      ok=False
  return ok

def avoid_ok(text, avoid):
  if not avoid: return True
  low = text.lower()
  return all(a.lower() not in low for a in avoid)

def exclaim_ok(text, max_bang=1):
  return text.count('!') <= max_bang

def coverage_score(brief, text):
  keys = [k.lower() for k in brief.get("key_points", [])]
  if not keys: return 1.0
  low = text.lower()
  hit = sum(1 for k in keys if k in low)
  return hit / max(1, len(keys))

def tone_fit_generic(brief, text):
  # Optional marker-basierte Prüfung (sprachagnostisch). Ohne Marker => 1.0
  any_mark = [m for m in brief.get("tone_markers_any", []) if m]
  all_mark = [m for m in brief.get("tone_markers_all", []) if m]
  if not any_mark and not all_mark: return 1.0
  low = text.lower()
  any_ok = True if not any_mark else any(m.lower() in low for m in any_mark)
  all_ok = True if not all_mark else all(m.lower() in low for m in all_mark)
  return 1.0 if (any_ok and all_ok) else 0.0

def cta_form_ok(text):
  clean = strip_markup(text)
  if not STARTS_WITH_LETTER.search(clean): return 0.0
  if ENDS_WITH_SENT_PUNCT.search(clean):  return 0.0
  wc = count_words(clean)
  return 1.0 if 1 <= wc <= 4 else 0.0

def jaccard(a:str,b:str)->float:
  ta=set(WORD.findall(strip_markup(a).lower()))
  tb=set(WORD.findall(strip_markup(b).lower()))
  if not ta and not tb: return 1.0
  return len(ta & tb) / len(ta | tb)

def diversity_ok(texts, thresh=0.75):
  n=len(texts)
  if n<2: return True
  for i in range(n):
    for j in range(i+1,n):
      if jaccard(texts[i],texts[j]) >= thresh:
        return False
  return True

def aqs(task, brief, text):
  tf  = tone_fit_generic(brief, text)
  cov = coverage_score(brief, text)
  cla = 1.0 if (length_ok(task, text)
                and avoid_ok(text, brief.get("avoid", []))
                and brand_ok(text, brief.get("brand_terms", []), brief.get("never_translate", []))
                and exclaim_ok(text)) else 0.0
  cta = cta_form_ok(text) if task=="cta" else 1.0
  return round(0.40*tf + 0.25*cov + 0.20*cla + 0.15*cta, 3)

def evaluate(payload):
  task = payload["task"].lower()
  brief = payload.get("brief", {})
  variants = payload["variants"]
  results=[]
  for t in variants:
    r = {
      "text": t,
      "length_ok": length_ok(task, t),
      "avoid_ok": avoid_ok(t, brief.get("avoid", [])),
      "brand_ok": brand_ok(t, brief.get("brand_terms", []), brief.get("never_translate", [])),
      "exclaim_ok": exclaim_ok(t),
      "coverage": coverage_score(brief, t),
      "tone_fit": tone_fit_generic(brief, t),
      "cta_form_ok": cta_form_ok(t) if task=="cta" else None
    }
    r["aqs"] = aqs(task, brief, t)
    results.append(r)
  agg = {
    "diversity_ok": diversity_ok(variants),
    "avg_aqs": round(sum(r["aqs"] for r in results)/max(1,len(results)),3)
  }
  return {"task":task,"results":results,"aggregate":agg}

def main():
  data=json.load(sys.stdin) if len(sys.argv)<2 else json.load(open(sys.argv[1],"r",encoding="utf-8"))
  print(json.dumps(evaluate(data), ensure_ascii=False, indent=2))

if __name__=="__main__":
  main()
