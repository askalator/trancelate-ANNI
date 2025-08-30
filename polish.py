#!/usr/bin/env python3
import os, sys, json, re, requests

LLM_URL = os.environ.get("LLM_URL", "http://127.0.0.1:8000/v1/chat/completions")
ORIG = sys.stdin.read().strip() if not sys.argv[1:] else " ".join(sys.argv[1:])

DU_FIX_ENABLED = os.getenv("DU_FIX","off").lower() == "on"

# ---- OrgCard (optional) ---------------------------------------------------
voice = {"principles": [], "do": [], "dont": []}
anrede = None
try:
    if os.path.exists("orgcard.json"):
        oc = json.load(open("orgcard.json"))
        v = oc.get("voice", {})
        voice["principles"] = v.get("principles", []) or []
        voice["do"] = v.get("do", []) or []
        voice["dont"] = v.get("dont", []) or []
        sf = oc.get("style_fingerprint", {})
        if sf.get("du_sie") in ("du","sie"):
            anrede = sf["du_sie"]
except Exception:
    pass

# ---- Platzhalter-Schutz ---------------------------------------------------
PH_RE = re.compile(r"(\{\{[^}]+\}\}|%[sd]|{[A-Za-z0-9_]+})")
phs = PH_RE.findall(ORIG)
tmp = ORIG
for i, ph in enumerate(phs):
    tmp = tmp.replace(ph, f"__PH{i}__")

# ---- System-Prompt --------------------------------------------------------
lines=[]
if voice["principles"]: lines.append("Prinzipien: " + "; ".join(voice["principles"]))
if voice["do"]:         lines.append("Do: " + "; ".join(voice["do"]))
if voice["dont"]:       lines.append("Don't: " + "; ".join(voice["dont"]))
style_block="\n".join(lines) if lines else "Stil: klar, freundlich, präzise, kurze Sätze."
anrede_rule = "Behalte die Anrede des Eingabetextes exakt bei."
if anrede=="du": anrede_rule='Verwende konsequent die Anrede "du".'
if anrede=="sie": anrede_rule='Verwende konsequent die Anrede "Sie".'

system_msg = (
    "Aufgabe: Polishe NUR Ton & Lesbarkeit. Bedeutung & Reihenfolge bleiben identisch. "
    "Zahlen/Platzhalter/Tags unverändert. Keine Erklärungen, keine Klammern.\n"
    f"{anrede_rule}\n" + style_block
)

payload = {
    "model":"mistral","temperature":0,"stop":[" (","("],
    "messages":[{"role":"system","content":system_msg},{"role":"user","content":tmp}]
}

def restore(text):
    for i, ph in enumerate(phs):
        text = text.replace(f"__PH{i}__", ph)
    # keine Anführungszeichen direkt um Platzhalter
    return re.sub(r'([\"“”])(\{\{[^}]+\}\})([\"“”])', r'\2', text).strip()

def is_english(s:str)->bool:
    return bool(re.search(r"\b(the|and|you|we|in|on|with|pages?|price|incl|vat|now|send|save|synchronized)\b", s, re.IGNORECASE))

def fix_sentence_case_en(t:str)->str:
    # senkt EIN Title-Case-Wort nach Placeholder/Tag/En-Dash/Zahl
    patterns = [
        r'(\{\{[^}]+\}\}\s+)([A-Z][a-z]+\b)',
        r'(</[^>]+>\s+)([A-Z][a-z]+\b)',
        r'(–\s+)([A-Z][a-z]+\b)',
        r'(\d+\s+)([A-Z][a-z]+\b)'
    ]
    prev=None
    while prev!=t:
        prev=t
        for pat in patterns:
            t = re.sub(pat, lambda m: m.group(1) + m.group(2).lower(), t)
    return t

def drifted(out, orig):
    if "(" in out or ")" in out: return True
    if len(out) > len(orig) * 1.15: return True
    return False

# ---- LLM-Call -------------------------------------------------------------
try:
    r = requests.post(LLM_URL, json=payload, timeout=60)
    r.raise_for_status()
    out = r.json()["choices"][0]["message"]["content"]
except Exception as e:
    print(f"ERROR calling LLM: {e}", file=sys.stderr); sys.exit(1)

out = restore(out)
if is_english(out):
    out = fix_sentence_case_en(out)

print(ORIG if drifted(out, ORIG) else out)
