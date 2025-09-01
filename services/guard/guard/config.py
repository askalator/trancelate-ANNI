import os

class Settings:
    def __init__(self):
        self.MT_BACKEND: str = "http://127.0.0.1:8093"
        self.MT_TIMEOUT: int = int(os.environ.get("MT_TIMEOUT", "60"))
        self.MAX_WORKERS_GUARD: int = int(os.environ.get("MAX_WORKERS_GUARD", "3") or "3")
        self.WORKER_TIMEOUT_S: float = float(os.environ.get("WORKER_TIMEOUT_S", "60") or "60")
        self.ENABLE_WORKER_BATCH: bool = os.environ.get("ENABLE_WORKER_BATCH", "1") not in ("0","","false","False")

        # locales/public
        self.LOCALES_PUBLIC_PATH: str | None = os.environ.get("LOCALES_PUBLIC_PATH")
        self.LOCALES_EXTRA: str = os.environ.get("LOCALES_EXTRA","")
        self.LOCALES_DISABLE: str = os.environ.get("LOCALES_DISABLE","")
        self.PUBLIC_DIR: str | None = os.environ.get("PUBLIC_DIR")

        # style filter
        self.ENABLE_STYLE_FILTER: bool = os.environ.get("ENABLE_STYLE_FILTER","1") not in ("0","false","False","")
        self.STYLE_LANGS: str = os.environ.get("STYLE_LANGS","de")
        self.STYLE_DEFAULT_ADDRESS: str = os.environ.get("STYLE_DEFAULT_ADDRESS","auto")
        self.STYLE_DEFAULT_GENDER: str = os.environ.get("STYLE_DEFAULT_GENDER","none")
        self.STYLE_KEEP_TERMS: str = os.environ.get("STYLE_KEEP_TERMS","TranceLate")
        
        # circuit breaker
        self.CB_ENABLE: bool = (os.environ.get("CB_ENABLE","1") not in ("0","","false","False"))
        self.CB_MAX_RETRIES: int = int(os.environ.get("CB_MAX_RETRIES","0") or "0")
        
        # cache
        self.CACHE_ENABLE: bool = (os.environ.get("CACHE_ENABLE","1") not in ("0","","false","False"))
        self.CACHE_MAX: int = int(os.environ.get("CACHE_MAX","5000") or "5000")
        self.CACHE_TTL: int = int(os.environ.get("CACHE_TTL","86400") or "86400")
        
        # glossary
        self.GLOSSARY_ENABLE: bool = (os.environ.get("GLOSSARY_ENABLE","0") not in ("0","","false","False"))
        self.GLOSSARY_PATH: str = os.environ.get("GLOSSARY_PATH","")
        self.GLOSSARY_TERMS: str = os.environ.get("GLOSSARY_TERMS","")  # CSV
        
        # --- SAFE MODE / FORCE SPANS-ONLY ---
        # Comma-separated BCP47 list, e.g. "zh-CN,zh-TW,ja-JP,ko-KR,he-IL,ar-SA,fa-IR,ur-PK,ps-AF,ru-RU,bg-BG,uk-UA,el-GR"
        def _csv_set(env_key: str) -> set[str]:
            v = os.environ.get(env_key, "") or ""
            return set([s.strip() for s in v.split(",") if s.strip()])
        self.SPANS_ONLY_FORCE_BCP47: set[str] = _csv_set("SPANS_ONLY_FORCE")
        # Comma-separated engine list, e.g. "zh,ja,ko,th,vi,km,lo,my,he,ar,fa,ur,ps,ru,bg,uk,sr,el,ka,hy"
        self.SPANS_ONLY_FORCE_ENGINES: set[str] = _csv_set("SPANS_ONLY_FORCE_ENGINES")

settings = Settings()
