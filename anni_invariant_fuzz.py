#!/usr/bin/env python3
import json, random, re, subprocess, shlex, sys

GUARD="./anni_mt_guard.py"

TAGS=["strong","em","b","i","u","span","a"]
HREFS=[
  "https://x.y/?q=a+b&c=d",
  "https://example.org/path?x=1&y=2#frag",
  "http://shop.tld/p?q=%7Btest%7D"
]
PLACEHOLDERS=["{{COUNT}}","{{PRICE}}","{{APP}}","{{SKU}}"]
WORDS_DE=["Jetzt","sofort","testen","starten","synchronisiert","ohne","Risiko","nur","heute","gültig"]
DASHES=[" — "," – "," - "]
SPACES=[""," ","  "]

TAG_OPEN=re.compile(r'<([a-zA-Z][\w:-]*)(\s[^<>]*?)?>')
TAG_CLOSE=re.compile(r'</([a-zA-Z][\w:-]*)>')
PH_RE=re.compile(r'{{[^{}]+}}')

def build_case():
  w = random.sample(WORDS_DE, k=random.randint(2,4))
  core = " ".join(w)
  # wrap core in random tag
  tag = random.choice(TAGS)
  if tag=="a":
    href=random.choice(HREFS)
    core=f'<a href="{href}">{core}</a>'
  else:
    core=f'<{tag}>{core}</{tag}>'
  # maybe add placeholder(s)
  for _ in range(random.randint(0,2)):
    core += random.choice(DASHES) + random.choice(PLACEHOLDERS)
  # leading/trailing spaces
  core = random.choice(SPACES) + core + random.choice(SPACES)
  return core

def extract_signature(html:str):
  tags = TAG_OPEN.findall(html) + TAG_CLOSE.findall(html)
  # Normalize: OPEN returns tuples; CLOSE returns strings
  sig=[]
  for m in TAG_OPEN.finditer(html):
    sig.append(("O", m.group(1).lower(), (m.group(2) or "").strip()))
  for m in TAG_CLOSE.finditer(html):
    sig.append(("C", m.group(1).lower(), ""))
  # preserve order by re-scan
  seq=[]
  i=0
  while i<len(html):
    mo=TAG_OPEN.search(html,i)
    mc=TAG_CLOSE.search(html,i)
    if mo and (not mc or mo.start()<mc.start()):
      seq.append(("O", mo.group(1).lower(), (mo.group(2) or "").strip()))
      i=mo.end()
    elif mc:
      seq.append(("C", mc.group(1).lower(), ""))
      i=mc.end()
    else:
      break
  phs = sorted(set(PH_RE.findall(html)))
  return seq, phs

def call_guard(txt:str):
  cmd=f"{GUARD} de en {shlex.quote(txt)}"
  out = subprocess.check_output(cmd, shell=True, text=True)
  return json.loads(out)

def check_case(src:str, out_json):
  out = out_json.get("out","")
  seq_in,  ph_in  = extract_signature(src)
  seq_out, ph_out = extract_signature(out)
  ok_tags = seq_in == seq_out
  ok_ph   = ph_in == ph_out
  checks  = out_json.get("checks",{})
  engine_ok = checks.get("html_ok") and checks.get("ph_ok")
  return ok_tags and ok_ph and bool(engine_ok), {
    "src":src,"out":out,"seq_in":seq_in,"seq_out":seq_out,"ph_in":ph_in,"ph_out":ph_out,"checks":checks
  }

def main(n=50, seed=42):
  random.seed(seed)
  fails=[]
  for i in range(1, n+1):
    case = build_case()
    res  = call_guard(case)
    ok, ctx = check_case(case, res)
    if not ok: fails.append(ctx)
    print(f"[{i:03d}] {'OK ' if ok else 'FAIL'}  len_in={len(case)} len_out={len(ctx['out'])}")
  print(f"\nSummary: OK={n-len(fails)} FAIL={len(fails)}")
  if fails:
    print("\n--- First failure detail ---")
    f=fails[0]
    print(json.dumps(f, ensure_ascii=False, indent=2))
    sys.exit(1)
  sys.exit(0)

if __name__=="__main__":
  n=int(sys.argv[1]) if len(sys.argv)>1 else 50
  main(n)
