#!/usr/bin/env python3
import sys, re, json
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from lxml import html as LH

MAX_URLS = int(sys.argv[3]) if len(sys.argv) > 3 else 20

def normalize(u: str) -> str:
    pu = urlparse(u)
    # nur http/https, Fragmente + Query raus
    if pu.scheme not in ("http","https"): return ""
    pu = pu._replace(fragment="", query="")
    # doppelte Slashes normalisieren
    path = re.sub(r"/{2,}", "/", pu.path or "/")
    return urlunparse((pu.scheme, pu.netloc, path, "", "", ""))

def same_host(a: str, b: str) -> bool:
    return urlparse(a).netloc.lower() == urlparse(b).netloc.lower()

def main():
    if len(sys.argv) < 2:
        print("usage: list_urls.py <start_url> [out.txt] [max=20]", file=sys.stderr)
        sys.exit(2)
    start = sys.argv[1]
    outp = sys.argv[2] if len(sys.argv) > 2 else "urls.txt"

    r = requests.get(start, headers={"User-Agent":"TranceLate-Crawler/1.0"}, timeout=20)
    r.raise_for_status()
    tree = LH.fromstring(r.text)

    base = normalize(start)
    host = urlparse(base).netloc

    urls = []
    for a in tree.xpath("//a[@href]"):
        href = a.get("href","").strip()
        if not href or href.startswith(("mailto:","tel:","javascript:","#")): 
            continue
        absu = urljoin(base, href)
        absu = normalize(absu)
        if not absu: 
            continue
        if not same_host(base, absu): 
            continue
        # einfache Ausschlüsse (Auth, Suche, RSS etc.)
        if re.search(r"/(login|signup|account|search|rss|feed)/?", absu, re.I):
            continue
        urls.append(absu)

    # dedupe, prioritär längere/“contentigere” Pfade
    seen=set(); dedup=[]
    for u in urls:
        if u in seen: continue
        seen.add(u); dedup.append(u)

    # kleine Heuristik: sortiere nach Pfadlänge, dann alphabetisch
    dedup.sort(key=lambda u: (len(urlparse(u).path), u))
    dedup = dedup[:MAX_URLS]

    with open(outp,"w",encoding="utf-8") as f:
        for u in dedup:
            f.write(u+"\n")

    print(f"✅ wrote {len(dedup)} URLs for {host} to {outp}")

if __name__ == "__main__":
    main()
