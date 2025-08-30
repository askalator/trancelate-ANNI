#!/usr/bin/env python3
import sys
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

def run(mdl, tok, txt):
    enc = tok([txt], return_tensors="pt")
    out = mdl.generate(**enc, max_new_tokens=64)
    return tok.batch_decode(out, skip_special_tokens=True)[0]

def load(mid):
    tok = AutoTokenizer.from_pretrained(mid)
    mdl = AutoModelForSeq2SeqLM.from_pretrained(mid)
    return tok, mdl

tok_de_en, mdl_de_en = load("Helsinki-NLP/opus-mt-de-en")
MAP = {"sv":"en-sv","da":"en-da","nb":"en-no","no":"en-no","pl":"en-pl","cs":"en-cs","ro":"en-ro","tr":"en-tr","pt":"en-pt","pt-BR":"en-pt"}

def de_to(lang, text):
    if lang not in MAP: raise SystemExit("unsupported_target")
    en = run(mdl_de_en, tok_de_en, text)
    tgt_id = "Helsinki-NLP/opus-mt-"+MAP[lang]
    tok2, mdl2 = load(tgt_id)
    print(run(mdl2, tok2, en))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: pivot_mt.py <target_lang> <text>", file=sys.stderr); sys.exit(2)
    lang = sys.argv[1]; text = " ".join(sys.argv[2:])
    de_to(lang, text)
