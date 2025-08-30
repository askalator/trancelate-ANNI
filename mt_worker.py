import os, torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from functools import lru_cache
from transformers import MarianMTModel, MarianTokenizer

ALIAS={'nb':'no'}
EXT=['de','fr','es','it','pt','nl','sv','da','no','ru','fi','pl','cs','ro','hu','bg','uk','sk','sl','hr','sr','lt','lv','et','el','tr','sq','mk','bs','is']
DIRECT=set()
for l in EXT:
    DIRECT.add(('en',l)); DIRECT.add((l,'en'))

def norm(x): return str(x or '').strip().lower()[:2]
def canon(s,t): s=norm(s); t=ALIAS.get(norm(t),norm(t)); return s,t

@lru_cache(maxsize=256)
def load(s,t):
    mid=f'Helsinki-NLP/opus-mt-{s}-{t}'
    tok=MarianTokenizer.from_pretrained(mid)
    mdl=MarianMTModel.from_pretrained(mid)
    return tok, mdl

def translate_txt(txt,s,t):
    tok,mdl=load(s,t)
    enc=tok([txt], return_tensors='pt')
    with torch.no_grad():
        out=mdl.generate(**enc, max_new_tokens=512)
    return tok.batch_decode(out, skip_special_tokens=True)[0]

app=FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
class Req(BaseModel): text:str; source:str; target:str

@app.post('/translate')
def tr(r:Req):
    s,t=canon(r.source,r.target)
    if (s,t) not in DIRECT:
        return {"error":"pair_not_supported","source":s,"target":t}
    return {"translated_text": translate_txt(r.text,s,t)}

@app.get('/health')
def health(): return {"ok": True, "direct": sorted(list(DIRECT))}
