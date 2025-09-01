import time, hashlib
from collections import OrderedDict
from typing import Any, Dict, List

class LRUCache:
    def __init__(self, maxsize: int = 5000, ttl: int = 86400):
        self.maxsize = maxsize
        self.ttl = ttl
        self._d: "OrderedDict[str, tuple[float, Dict[str,Any]]]" = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: str):
        now = time.time()
        v = self._d.get(key)
        if not v:
            self.misses += 1
            return None
        ts, data = v
        if now - ts > self.ttl:
            try: del self._d[key]
            except KeyError: pass
            self.misses += 1
            return None
        self._d.move_to_end(key, last=True)
        self.hits += 1
        return data

    def set(self, key: str, value: Dict[str,Any]):
        now = time.time()
        self._d[key] = (now, value)
        self._d.move_to_end(key, last=True)
        if len(self._d) > self.maxsize:
            self._d.popitem(last=False)
            self.evictions += 1

    def stats(self) -> Dict[str,int]:
        return {"size": len(self._d), "hits": self.hits, "misses": self.misses, "evictions": self.evictions}

def style_signature(address: str | None, gender: str | None) -> str:
    a = (address or "auto").lower()
    g = (gender or "none").lower()
    return f"a={a};g={g}"

def glossary_signature(terms: List[Dict[str,str]] | None) -> str:
    if not terms:
        return "gl=none"
    # nur Canonicals/Terms, stabil sortiert
    payload = "|".join(sorted([(t.get("canonical") or t.get("term","")).strip() for t in terms]))
    h = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:8]
    return f"gl={h}"

def build_key(src_engine: str, tgt_engine: str, freeze_text_std: str, sig: str) -> str:
    h = hashlib.sha1(freeze_text_std.encode("utf-8")).hexdigest()[:16]
    return f"{src_engine}->{tgt_engine}|{sig}|{h}"

# singleton; wird in mt_guard mit Settings parametriert
cache: LRUCache | None = None
