#!/usr/bin/env python3
import re, json, sys, requests
from urllib.parse import urlparse, urlunparse
from lxml import html as LH, etree

MIN_LEN=10
MAX_CHARS=800
UA='TranceLate-Fetch/1.0 (+self-host)'

def norm(s): return re.sub(r'\s+',' ', s or '').strip()
def tag_name(n): 
    t=getattr(n,'tag',''); return t.lower() if isinstance(t,str) else ''
def ident_text(el):
    cid = norm(el.get('id'))
    cls = el.get('class'); 
    if isinstance(cls,(list,tuple)): cls=' '.join(cls)
    cls = norm(cls)
    return f"{cid} {cls}".strip().lower()
def chunk(text):
    if len(text)<=MAX_CHARS: return [text]
    parts=re.split(r'(?<=[.!?:])\s+', text); out=[]; buf=''
    for p in parts:
        if not p: continue
        n=(buf+' '+p).strip() if buf else p
        if len(n)<=MAX_CHARS: buf=n
        else:
            if buf: out.append(buf)
            buf=p
    if buf: out.append(buf)
    return out
def pick_main(tree):
    cands=[]
    for el in tree.xpath('//main | //*[@id or @class][self::div or self::section]'):
        ident=ident_text(el)
        if re.search(r'(content|main|homepage|primary|page|container|wrapper)', ident):
            txt=' '.join(el.itertext())
            cands.append((len(norm(txt)), el))
    if cands:
        cands.sort(reverse=True, key=lambda x: x[0])
        return cands[0][1]
    b=tree.xpath('//body'); return b[0] if b else tree
def is_nav_list(el):
    ident=ident_text(el)
    return any(k in ident for k in ['nav','menu','breadcrumb','footer','social'])
def fetch(url):
    r=requests.get(url, headers={'User-Agent':UA}, timeout=25)
    r.raise_for_status()
    return r.text
def extract(url, html):
    tree=LH.fromstring(html)
    etree.strip_elements(tree, 'script','style','noscript','template', with_tail=False)
    main=pick_main(tree)
    segs=[]; order=0
    title = norm(main.xpath('string(.//h1)') or tree.xpath('string(//title)'))
    if title: segs.append({"order":order,"type":"title","text":title}); order+=1
    for el in main.iter():
        tag=tag_name(el)
        if tag in {'h1','h2','h3'}:
            txt=norm(' '.join(el.itertext()))
            if txt and len(txt)>=MIN_LEN:
                segs.append({"order":order,"type":tag,"text":txt}); order+=1
        elif tag=='p':
            txt=norm(' '.join(el.itertext()))
            if txt and len(txt)>=MIN_LEN:
                for ch in chunk(txt):
                    segs.append({"order":order,"type":"p","text":ch}); order+=1
        elif tag=='li':
            parent=el.getparent()
            if parent is not None and tag_name(parent) in ('ul','ol') and not is_nav_list(parent):
                txt=norm(' '.join(el.itertext()))
                if txt and len(txt)>=MIN_LEN:
                    segs.append({"order":order,"type":"li","text":txt}); order+=1
    # dedupe by normalized text
    seen=set(); dedup=[]
    for s in segs:
        key=norm(s["text"]).lower()
        if key in seen: continue
        seen.add(key); dedup.append(s)
    return dedup

def main():
    if len(sys.argv)<3:
        print("usage: crawl_fetch_clean.py <urls.txt> <out.jsonl>", file=sys.stderr); sys.exit(2)
    inlist, outp = sys.argv[1], sys.argv[2]
    urls=[u.strip() for u in open(inlist,encoding='utf-8') if u.strip()]
    total=0
    with open(outp,'w',encoding='utf-8') as out:
        for u in urls:
            try:
                html=fetch(u)
                segs=extract(u, html)
            except Exception as e:
                print(f"ERROR {u}: {e}", file=sys.stderr); continue
            meta={"_meta":{"source_url":u,"host":urlparse(u).netloc,"count":len(segs)}}
            out.write(json.dumps(meta, ensure_ascii=False)+'\n')
            for s in segs: out.write(json.dumps(s, ensure_ascii=False)+'\n')
            total += len(segs)
    print(f"✅ wrote {total} segments from {len(urls)} URLs to {outp}")
if __name__=='main__': pass
if __name__=='__main__': main()
