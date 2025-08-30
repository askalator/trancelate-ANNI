import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ctranslate2, sentencepiece as spm

app = FastAPI()
_cache = {}

def path_for(src, tgt):
    base = os.path.expanduser("~/trancelate-onprem/mt-ct2")
    if (src, tgt) == ("de", "en"):
        return os.path.join(base, "de-en")
    if (src, tgt) == ("en", "de"):
        return os.path.join(base, "en-de")
    raise HTTPException(400, f"unsupported pair {src}->{tgt}")

def load_pair(src, tgt):
    key = f"{src}->{tgt}"
    if key in _cache:
        return _cache[key]
    path = path_for(src, tgt)
    need = [os.path.join(path, f) for f in ("model.bin","source.spm","target.spm")]
    miss = [p for p in need if not os.path.isfile(p)]
    if miss:
        raise HTTPException(500, f"CT2 model files missing: {miss}")
    tr = ctranslate2.Translator(path, device="cpu", compute_type="int8")
    sp_src = spm.SentencePieceProcessor(model_file=os.path.join(path, "source.spm"))
    sp_tgt = spm.SentencePieceProcessor(model_file=os.path.join(path, "target.spm"))
    _cache[key] = (tr, sp_src, sp_tgt)
    return _cache[key]

class MTReq(BaseModel):
    source: str
    target: str
    text: str

@app.get("/healthz")
def health(): return {"ok": True}

@app.post("/translate")
def translate(r: MTReq):
    tr, sp_src, sp_tgt = load_pair(r.source, r.target)
    toks = sp_src.encode(r.text, out_type=str)

    res = tr.translate_batch(
        [toks],
        beam_size=1,                 # greedy
        max_decoding_length=12,      # kurze, saubere Outputs
        min_decoding_length=1,
        length_penalty=0.0,
        repetition_penalty=3.0,      # deutlich strenger
        no_repeat_ngram_size=4,      # 4-Gramm nicht wiederholen
        end_token="</s>",
    )

    out = res[0].hypotheses[0]
    # auf EOS kappen
    if "</s>" in out:
        out = out[:out.index("</s>")]
    # einfache Entdoppelung direkt auf Token-Ebene (keine Dreifach-Wiederholungen)
    cleaned = []
    for t in out:
        if len(cleaned) >= 2 and t == cleaned[-1] == cleaned[-2]:
            continue
        cleaned.append(t)

    return {"translated_text": sp_tgt.decode_pieces(cleaned)}
