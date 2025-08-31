from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
import torch, os
import sys

# Import shared functionality
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from libs.trance_common import app_version

app = FastAPI()
tok=None; mdl=None
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_ID = os.environ.get("M2M_MODEL","facebook/m2m100_418M")

def ensure_loaded():
    global tok, mdl
    if tok is None or mdl is None:
        tok = M2M100Tokenizer.from_pretrained(MODEL_ID)
        mdl = M2M100ForConditionalGeneration.from_pretrained(MODEL_ID)
        mdl.to(device); mdl.eval()

def norm(code:str)->str:
    return (code or "").split("-",1)[0].strip().lower()

class Req(BaseModel):
    source:str
    target:str
    text:str
    max_new_tokens:int|None=None

@app.get("/health")
def health():
    try:
        ensure_loaded()
        resp = {"ok":True,"model":"m2m100_418M","ready":True}
        resp.update(app_version())
        return resp
    except Exception as e:
        resp = {"ok":False,"error":str(e),"ready":False}
        resp.update(app_version())
        return resp

@app.post("/translate")
def translate(r:Req):
    try:
        ensure_loaded()
        src=norm(r.source); tgt=norm(r.target)
        tok.src_lang = src
        enc = tok(r.text, return_tensors="pt")
        enc = {k:v.to(device) for k,v in enc.items()}
        tid = tok.get_lang_id(tgt)
        with torch.no_grad():
            gen = mdl.generate(**enc, forced_bos_token_id=tid, do_sample=False, num_beams=1, max_new_tokens=r.max_new_tokens or 512)
        txt = tok.batch_decode(gen, skip_special_tokens=True)[0]
        return {"translated_text": txt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
