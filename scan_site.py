import argparse, os, re, json, sqlite3
from urllib.parse import urljoin, urlparse, urldefrag
import httpx
from bs4 import BeautifulSoup
import trafilatura
from sentence_transformers import SentenceTransformer

def canon(u): u=urldefrag(u)[0]; return u[:-1] if u.endswith('/') else u
def same_host(a,b): return urlparse(a).netloc==urlparse(b).netloc

def extract_text(html):
    txt = trafilatura.extract(html, include_comments=False, favor_recall=True)
    if not txt:
        s=BeautifulSoup(html,'lxml'); [x.decompose() for x in s(['script','style','noscript'])]
        txt=re.sub(r'\s+',' ',s.get_text('\n')).strip()
    title=None
    try: title=(BeautifulSoup(html,'lxml').title.string or '').strip()
    except: pass
    return title or '', txt or ''

def chunk(text, max_chars=900):
    parts,buf=[],[]
    for para in re.split(r'\n{2,}', text):
        if not para.strip(): continue
        if sum(map(len,buf))+len(para)<=max_chars: buf.append(para)
        else: parts.append('\n'.join(buf)); buf=[para]
    if buf: parts.append('\n'.join(buf))
    return parts[:64]

def ensure_db(outdir):
    os.makedirs(outdir, exist_ok=True)
    db=os.path.join(outdir,'kb.sqlite')
    con=sqlite3.connect(db); con.execute('pragma journal_mode=WAL;')
    con.execute('create table if not exists pages(id integer primary key, url text unique, title text)')
    con.execute('create table if not exists chunks(id integer primary key, page_id integer, idx integer, text text)')
    con.commit(); return con

async def crawl(seed, max_pages):
    out,seen,queue=[],set(),[seed]
    async with httpx.AsyncClient(follow_redirects=True, headers={'User-Agent':'TranceLate-Scanner/0.1'}) as c:
        while queue and len(out)<max_pages:
            url=canon(queue.pop(0))
            if url in seen: continue
            seen.add(url)
            try:
                r=await c.get(url, timeout=20)
                if 'text/html' not in r.headers.get('content-type',''): continue
                title, text = extract_text(r.text)
                if text: out.append((url,title,text))
                s=BeautifulSoup(r.text,'lxml')
                for a in s.find_all('a',href=True):
                    href=canon(urljoin(url,a['href']))
                    if same_host(seed,href) and href not in seen and len(queue)<max_pages*3:
                        queue.append(href)
            except: pass
    return out

def build_orgcard(seed, pages):
    host=urlparse(seed).netloc
    desc=' '.join((pages[0][2] if pages else '') .split()[:60])
    return {'brand':host,'summary':desc,'title':pages[0][1] if pages and pages[0][1] else host,'source':seed}

def collect_glossary(seed):
    brand=re.sub(r'^www\.','',urlparse(seed).netloc).split('.')[0]
    return sorted({brand, brand.capitalize(), brand.upper()})

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('url'); ap.add_argument('--out',default='tenants/demo'); ap.add_argument('--max-pages',type=int,default=12)
    ap.add_argument('--emb','--emb-model',dest='emb',default='intfloat/e5-small')
    args=ap.parse_args()

    import asyncio
    pages=asyncio.run(crawl(args.url,args.max_pages))
    if not pages: print('Keine Seiten gefunden.'); return

    # Artefakte
    os.makedirs(args.out,exist_ok=True)
    with open(os.path.join(args.out,'orgcard.json'),'w') as f: json.dump(build_orgcard(args.url,pages),f,ensure_ascii=False,indent=2)
    with open(os.path.join(args.out,'glossary.json'),'w') as f: json.dump({'never_translate':collect_glossary(args.url)},f,ensure_ascii=False,indent=2)

    # Embeddings-Index (nur Texte speichern; Embeddings macht das Gateway)
    con=ensure_db(args.out); cur=con.cursor()
    kept=0
    for url,title,text in pages:
        if len(text)<120: continue
        cur.execute('insert or ignore into pages(url,title) values(?,?)',(url,title))
        pid=cur.execute('select id from pages where url=?',(url,)).fetchone()[0]
        for i,ck in enumerate(chunk(text)): cur.execute('insert into chunks(page_id,idx,text) values(?,?,?)',(pid,i,ck)); kept+=1
    con.commit(); con.close()
    print(f'OK: {len(pages)} Seiten, {kept} Chunks → {args.out}')
if __name__=='__main__': main()
