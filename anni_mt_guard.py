#!/usr/bin/env python3
import os, sys, json, re, urllib.request, urllib.error, time

URL = os.environ.get("ANNI_MT_URL","http://127.0.0.1:8091/translate")
API = os.environ.get("ANNI_API_KEY","topsecret")
HDR = {"Content-Type":"application/json","X-API-Key":API}

DAYX      = re.compile(r'\bDAYX\d+\b', re.IGNORECASE)
URL_RE    = re.compile(r'(?i)\b((?:https?|ftps?)://[^\s"<>\')]+)')
EMAIL_RE  = re.compile(r'(?i)\b([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})')
TAG_RE    = re.compile(r'</?[A-Za-z][\w:-]*(\s[^<>]*?)?>')

TOKEN_RE  = re.compile(r'\{\{\s*TLT_TAG_(\d+)\s*\}\}')

def _freeze_specials(s:str):
    url_map=[]; email_map=[]
    def u_sub(m):
        i=len(url_map); url_map.append(m.group(1)); return f"{{{{U{i}}}}}"
    def e_sub(m):
        i=len(email_map); email_map.append(m.group(1)); return f"{{{{E{i}}}}}"
    s = URL_RE.sub(u_sub, s)
    s = EMAIL_RE.sub(e_sub, s)
    return s, url_map, email_map

def _thaw_specials(s:str, url_map, email_map):
    for i,v in enumerate(url_map):
        s = s.replace(f"{{{{U{i}}}}}", v)
    for i,v in enumerate(email_map):
        s = s.replace(f"{{{{E{i}}}}}", v)
    return s

def _freeze_tags(s:str):
    tags=[]
    def repl(m):
        i=len(tags); tags.append(m.group(0)); return f"{{{{TLT_TAG_{i}}}}}"
    return TAG_RE.sub(repl, s), tags

def _thaw_tags(s:str, tags):
    def repl(m):
        idx=int(m.group(1))
        return tags[idx] if 0 <= idx < len(tags) else m.group(0)
    return TOKEN_RE.sub(repl, s)

def call_mt(src, tgt, text, retry=3, backoff=0.25):
    # 1) URLs/Emails einfrieren
    pre1, umap, emap = _freeze_specials(text)
    # 2) HTML-Tags als Platzhalter markieren
    pre2, tagmap = _freeze_tags(pre1)
    body={"source":src,"target":tgt,"text":pre2}
    data=json.dumps(body).encode()

    for i in range(retry):
        try:
            req=urllib.request.Request(URL,method="POST",headers=HDR)
            with urllib.request.urlopen(req,data, timeout=30) as r:
                res=json.load(r)
            raw = res.get("translated_text","")
            raw = DAYX.sub('', raw)
            # 3) Tags zurücksetzen
            out = _thaw_tags(raw, tagmap)
            # 4) URLs/Emails zurücksetzen
            out = _thaw_specials(out, umap, emap)
            return {"ok":True,"out":out,"checks":res.get("checks",{})}
        except urllib.error.HTTPError as e:
            if i==retry-1: return {"ok":False,"err":f"HTTP {e.code}"}
        except Exception as e:
            if i==retry-1: return {"ok":False,"err":str(e)}
        time.sleep(backoff*(2**i))
    return {"ok":False,"err":"unknown"}

def main():
    if len(sys.argv)<3:
        print("usage: anni_mt_guard.py <source> <target> [text... or stdin]", file=sys.stderr); sys.exit(2)
    src,tgt=sys.argv[1],sys.argv[2]
    text=" ".join(sys.argv[3:]).strip() if len(sys.argv)>3 else sys.stdin.read()
    res=call_mt(src,tgt,text)
    print(json.dumps(res, ensure_ascii=False))
if __name__=="__main__": main()
