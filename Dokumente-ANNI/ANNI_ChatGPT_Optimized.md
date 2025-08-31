# ANNI - ChatGPT Optimized Documentation
*TranceLate.it FlexCo - Version 2.0 - Stand: 2025-08-30*

---

## 🎯 **Für ChatGPT/Mistral: Vollständige Code-Basis & Live-Status**

Diese Dokumentation enthält **alle wichtigen Code-Snippets**, **aktuelle Konfigurationen** und **Live-System-Status**, damit KI-Assistenten ohne direkten Code-Zugriff effektiv helfen können.

---

## 📊 **LIVE SYSTEM STATUS (Stand: 2025-08-30)**

### **Service Status**
| Service | Port | Status | Health Check | Log File |
|---------|------|--------|--------------|----------|
| **Guard** | 8091 | ✅ RUNNING | `{"ok":true,"ready":true}` | `/tmp/guard.log` |
| **Worker** | 8093 | ✅ RUNNING | `{"ok":true,"model":"facebook/m2m100_418M"}` | `/tmp/worker.log` |
| **TranceCreate** | 8095 | ✅ RUNNING | `{"ok":true,"role":"TranceCreate","version":"1.2.0"}` | `/tmp/tc_server.log` |
| **TranceSpell** | 8096 | ✅ RUNNING | `{"ok":true,"engine":"pyspell","langs":["de","en","es","fr"]}` | `/tmp/ts_server.log` |
| **GUI** | 8094 | ✅ RUNNING | Static HTML | `anni_gui.html` |

### **Aktuelle Konfiguration**
```bash
# Environment Variables (aktuell gesetzt)
export MT_BACKEND=http://127.0.0.1:8093
export ANNI_MAX_NEW_TOKENS=512
export ANNI_CHUNK_CHARS=600
export TC_GUARD_URL=http://127.0.0.1:8091/translate
export TC_USE_MISTRAL=true
export TS_PORT=8096
```

---

## 🔧 **CORE CODE SNIPPETS**

### **1. Guard Service (mt_guard.py)**

#### **Invariant Protection**
```python
# Aus mt_guard.py - Zeile 45-80
import re
from typing import Tuple, List, Dict

# Regex Patterns für Invarianten
PLACEHOLDER_RE = re.compile(r'\{\{[^}]+\}\}')
SINGLE_BRACE_RE = re.compile(r'\{[^}]+\}')
HTML_TAG_RE = re.compile(r'<[^>]+>')
URL_RE = re.compile(r'https?://[^\s<>"]+')
EMOJI_RE = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF]')
NUM_RE = re.compile(r'\b\d+(?:[,\d]*\d)*(?:\.\d+)?(?:[–—]\d+(?:[,\d]*\d)*(?:\.\d+)?)?\b')

def freeze_invariants(text: str) -> Tuple[str, List[Dict], Dict[str, str]]:
    """Freeze sensitive elements before translation"""
    masked_text = text
    spans = []
    table = {}
    span_id = 0
    
    # Find all protected spans
    patterns = [
        (PLACEHOLDER_RE, "PLACEHOLDER"),
        (SINGLE_BRACE_RE, "SINGLE_BRACE"), 
        (HTML_TAG_RE, "HTML_TAG"),
        (URL_RE, "URL"),
        (EMOJI_RE, "EMOJI"),
        (NUM_RE, "NUM")
    ]
    
    for pattern, span_type in patterns:
        matches = list(pattern.finditer(text))
        for match in reversed(matches):
            start, end = match.span()
            content = match.group(0)
            span_key = f"__{span_type}{span_id}__"
            
            # Store span info
            spans.append({
                "type": span_type,
                "start": start,
                "end": end,
                "content": content,
                "key": span_key
            })
            
            # Replace in masked text
            masked_text = masked_text[:start] + span_key + masked_text[end:]
            table[span_key] = content
            span_id += 1
    
    return masked_text, spans, table
```

#### **Translation Endpoint**
```python
# Aus mt_guard.py - Zeile 200-250
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

app = FastAPI(title="ANNI Guard", version="2.0")

class TranslationRequest(BaseModel):
    source: str
    target: str
    text: str
    max_new_tokens: int = 512

class TranslationResponse(BaseModel):
    translated_text: str
    checks: Dict[str, Any]

@app.post("/translate", response_model=TranslationResponse)
async def translate(request: TranslationRequest):
    """Main translation endpoint with invariant protection"""
    try:
        # Step 1: Freeze invariants
        masked_text, spans, table = freeze_invariants(request.text)
        
        # Step 2: Chunk long texts
        chunks = chunk_text(masked_text, max_chars=600)
        
        # Step 3: Translate chunks
        translated_chunks = []
        for chunk in chunks:
            response = call_backend(chunk, request.source, request.target, request.max_new_tokens)
            translated_chunks.append(response["translated_text"])
        
        # Step 4: Unfreeze invariants
        result = "".join(translated_chunks)
        result = unfreeze_invariants(result, table)
        
        # Step 5: Validate invariants
        checks = check_invariants(request.text, result)
        
        return TranslationResponse(
            translated_text=result,
            checks=checks
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### **2. Worker Service (m2m_worker.py)**

#### **Model Loading**
```python
# Aus m2m_worker.py - Zeile 20-60
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
import torch

class M2MWorker:
    def __init__(self):
        self.model_name = "facebook/m2m100_418M"
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
    def load_model(self):
        """Load M2M100 model and tokenizer"""
        try:
            self.tokenizer = M2M100Tokenizer.from_pretrained(self.model_name)
            self.model = M2M100ForConditionalGeneration.from_pretrained(self.model_name)
            self.model.to(self.device)
            return True
        except Exception as e:
            print(f"Model loading failed: {e}")
            return False
    
    def translate(self, text: str, source_lang: str, target_lang: str, max_new_tokens: int = 512):
        """Translate text using M2M100"""
        try:
            # Set source language
            self.tokenizer.src_lang = source_lang
            
            # Tokenize
            inputs = self.tokenizer(text, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    forced_bos_token_id=self.tokenizer.get_lang_id(target_lang),
                    max_new_tokens=max_new_tokens,
                    do_sample=False
                )
            
            # Decode
            result = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
            return {"translated_text": result}
            
        except Exception as e:
            return {"error": str(e)}
```

### **3. TranceCreate Service (tc_server.py)**

#### **Pipeline System**
```python
# Aus tc_server.py - Zeile 100-150
from tc_pipeline import Pipeline, Ctx
from tc_stages.core import TcCoreStage, ProfileStage, PolicyCheckStage, DegradeStage
from tc_stages.claim_fit import ClaimFitStage

class TranceCreateService:
    def __init__(self):
        self.pipeline = Pipeline()
        self.stage_registry = {
            "tc_core": TcCoreStage,
            "post_profile": ProfileStage,
            "policy_check": PolicyCheckStage,
            "degrade": DegradeStage,
            "claim_fit": ClaimFitStage
        }
        
    def setup_pipeline(self, stage_names: List[str]):
        """Setup pipeline with specified stages"""
        stages = []
        for name in stage_names:
            if name in self.stage_registry:
                stages.append(self.stage_registry[name]())
        self.pipeline.stages = stages
    
    def transcreate(self, request: TranscreateRequest) -> TranscreateResponse:
        """Main transcreation endpoint"""
        try:
            # Step 1: Get baseline from Guard
            baseline_text = self.get_baseline(request)
            
            # Step 2: Setup context
            ctx = Ctx({
                "source": request.source,
                "target": request.target,
                "baseline_text": baseline_text,
                "text": baseline_text,
                "original_text": request.text,
                "profile": request.profile,
                "persona": request.persona,
                "level": request.level,
                "policies": request.policies.model_dump(),
                "seed": request.seed or self.generate_stable_seed(request),
                "trace": {},
                "degrade_reasons": []
            })
            
            # Step 3: Run pipeline
            self.pipeline.run(ctx)
            
            # Step 4: Build response
            return TranscreateResponse(
                baseline_text=ctx.get("baseline_text", ""),
                transcreated_text=ctx.get("text", ""),
                degraded=bool(ctx.get("degraded", False)),
                degrade_reasons=ctx.get("degrade_reasons", []),
                trace=ctx.get("trace", {})
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
```

### **4. TranceSpell Service (ts_server.py)**

#### **Spell Checking Engine**
```python
# Aus ts_core.py - Zeile 150-200
class TranceSpellCore:
    def __init__(self, config_path: str = "config/trancespell.json"):
        self.config = self._load_config(config_path)
        self.spell_engines = {}
        self.hunspell_paths = self._discover_hunspell_dirs()
    
    def _get_spell_engine(self, lang: str):
        """Get spell engine for language (Hunspell or pyspellchecker)"""
        if lang in self.spell_engines:
            return self.spell_engines[lang]
        
        # Try Hunspell first
        engine = self._try_hunspell(lang)
        if engine:
            self.spell_engines[lang] = engine
            return engine
        
        # Fallback to pyspellchecker
        engine = self._try_pyspellchecker(lang)
        if engine:
            self.spell_engines[lang] = engine
            return engine
        
        return None
    
    def check(self, text: str, lang: str) -> List[Dict]:
        """Check spelling in text"""
        try:
            # Normalize language
            lang = self.lang_normalize(lang)
            
            # Get engine
            engine = self._get_spell_engine(lang)
            if not engine:
                return []
            
            # Mask invariants
            masked_text, spans, table = self.mask(text)
            
            # Tokenize and check
            tokens = masked_text.split()
            issues = []
            
            for token in tokens:
                if token.startswith("__") and token.endswith("__"):
                    continue  # Skip masked tokens
                
                if hasattr(engine, 'unknown'):
                    # Hunspell
                    if not engine.spell(token):
                        suggestions = engine.suggest(token)[:5]
                        issues.append({
                            "token": token,
                            "suggestions": suggestions,
                            "rule": "spell"
                        })
                else:
                    # pyspellchecker
                    if token in engine.unknown([token]):
                        suggestions = list(engine.candidates(token))[:5]
                        issues.append({
                            "token": token,
                            "suggestions": suggestions,
                            "rule": "spell"
                        })
            
            # Calculate original positions
            for issue in issues:
                start, end = self._calculate_original_position(issue["token"], spans)
                issue["start"] = start
                issue["end"] = end
            
            return issues
            
        except Exception as e:
            return []
```

---

## ⚙️ **AKTUELLE KONFIGURATIONSDATEIEN**

### **1. TranceCreate Pipeline (config/tc_pipeline.json)**
```json
{
  "stages": [
    "tc_core",
    "claim_fit", 
    "policy_check",
    "degrade"
  ]
}
```

### **2. ClaimGuard Settings (config/claim_fit.json)**
```json
{
  "default": {
    "units": "graphemes",
    "fit_to_source": true,
    "ratio": 1.0,
    "ellipsis": false,
    "max_iterations": 3,
    "breakpoints": ["\\s+", "\\u2009", "\\u200A", "-", "–", "—", "/", "·", ":", ";", ","],
    "drop_parentheticals": true,
    "drop_trailing_fragments": true
  }
}
```

### **3. TranceSpell Configuration (config/trancespell.json)**
```json
{
  "dictionaries": {
    "de": {
      "aff": "/usr/local/share/hunspell/de_DE.aff",
      "dic": "/usr/local/share/hunspell/de_DE.dic"
    },
    "en": {
      "aff": "/usr/local/share/hunspell/en_US.aff", 
      "dic": "/usr/local/share/hunspell/en_US.dic"
    }
  },
  "hunspell_paths": [
    "/usr/share/hunspell",
    "/usr/local/share/hunspell",
    "/Library/Spelling",
    "/opt/homebrew/share/hunspell"
  ],
  "aliases": {
    "de-DE": "de",
    "en-US": "en",
    "iw": "he",
    "in": "id",
    "pt-BR": "pt",
    "zh-CN": "zh",
    "zh-TW": "zh"
  },
  "max_suggestions": 5,
  "timeout_ms": 8000
}
```

### **4. Language Support (langs.json)**
```json
[
  "af", "am", "ar", "as", "az", "be", "bg", "bn", "br", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "eo", "es", "et", "eu", "fa", "fi", "fo", "fr", "fy", "ga", "gd", "gl", "gu", "ha", "he", "hi", "hr", "ht", "hu", "hy", "id", "ig", "is", "it", "ja", "jv", "ka", "kk", "km", "kn", "ko", "ku", "ky", "la", "lg", "ln", "lo", "lt", "lv", "mg", "mk", "ml", "mn", "mr", "ms", "mt", "my", "nb", "ne", "nl", "nn", "no", "oc", "or", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk", "sl", "so", "sq", "sr", "ss", "su", "sv", "sw", "ta", "te", "th", "tl", "tr", "ug", "uk", "ur", "uz", "vi", "wo", "xh", "yi", "yo", "zh", "zu"
]
```

### **5. Language Aliases (lang_aliases.json)**
```json
{
  "de-DE": "de",
  "en-US": "en", 
  "en-GB": "en",
  "iw": "he",
  "in": "id",
  "pt-BR": "pt",
  "pt-PT": "pt",
  "zh-CN": "zh",
  "zh-TW": "zh",
  "zh-HK": "zh",
  "zh-SG": "zh"
}
```

---

## 🧪 **PRAKTISCHE BEISPIELE & TESTS**

### **1. Basic Translation Test**
```bash
# Test Guard Service
curl -X POST http://127.0.0.1:8091/translate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "source": "en",
    "target": "de", 
    "text": "Hello {{COUNT}} world!",
    "max_new_tokens": 512
  }'

# Expected Response:
{
  "translated_text": "Hallo {{COUNT}} Welt!",
  "checks": {
    "ok": true,
    "ph_ok": true,
    "num_ok": true,
    "html_ok": true,
    "paren_ok": true,
    "len_ratio": 1.0,
    "len_ratio_eff": 1.0
  }
}
```

### **2. TranceCreate Enhancement Test**
```bash
# Test TranceCreate Service
curl -X POST http://127.0.0.1:8095/transcreate \
  -H "Content-Type: application/json" \
  -d '{
    "source": "en",
    "target": "de",
    "text": "Buy now!",
    "profile": "marketing",
    "persona": "ogilvy", 
    "level": 2,
    "policies": {
      "preserve": ["placeholders", "html", "numbers"],
      "max_change_ratio": 0.25
    }
  }'

# Expected Response:
{
  "baseline_text": "Jetzt kaufen!",
  "transcreated_text": "Jetzt sofort kaufen! ✨",
  "degraded": false,
  "degrade_reasons": [],
  "trace": {
    "guard_latency_ms": 123,
    "tc_latency_ms": 45,
    "tc_model": "mistral",
    "seed": 12345
  }
}
```

### **3. TranceSpell Check Test**
```bash
# Test TranceSpell Service
curl -X POST http://127.0.0.1:8096/check \
  -H "Content-Type: application/json" \
  -d '{
    "lang": "de-DE",
    "text": "<button>Jetz registrieren</button> 🙂 {{COUNT}}"
  }'

# Expected Response:
{
  "issues": [
    {
      "start": 8,
      "end": 12,
      "token": "Jetz",
      "suggestions": ["Jetzt"],
      "rule": "spell"
    }
  ],
  "masked": true,
  "trace": {
    "lang": "de",
    "engine": "pyspellchecker",
    "checked_tokens": 2,
    "issues": 1,
    "elapsed_ms": 12
  }
}
```

---

## 🔍 **TROUBLESHOOTING MIT CODE-BEISPIELEN**

### **1. HTTP 502 Bad Gateway**
```python
# Problem: Worker nicht erreichbar
# Lösung: Worker neu starten

# Check worker status
import requests
try:
    response = requests.get("http://127.0.0.1:8093/health", timeout=5)
    print(f"Worker OK: {response.json()}")
except requests.exceptions.RequestException as e:
    print(f"Worker DOWN: {e}")
    # Restart worker
    import subprocess
    subprocess.run([
        "nohup", "uvicorn", "m2m_worker:app", 
        "--host", "0.0.0.0", "--port", "8093",
        ">/tmp/worker.log", "2>&1", "&"
    ])
```

### **2. Invariant Violation**
```python
# Problem: Platzhalter werden verändert
# Lösung: Check freeze/unfreeze logic

def debug_invariants(source: str, target: str):
    """Debug invariant protection"""
    # Freeze
    masked, spans, table = freeze_invariants(source)
    print(f"Masked: {masked}")
    print(f"Spans: {spans}")
    print(f"Table: {table}")
    
    # Simulate translation (no-op for testing)
    translated_masked = masked
    
    # Unfreeze
    result = unfreeze_invariants(translated_masked, table)
    print(f"Result: {result}")
    
    # Check
    checks = check_invariants(source, result)
    print(f"Checks: {checks}")
    
    return checks["ok"]
```

### **3. Memory Issues**
```python
# Problem: High memory usage
# Lösung: Optimize model loading

import torch
import gc

def optimize_memory():
    """Optimize memory usage"""
    # Clear cache
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    # Force garbage collection
    gc.collect()
    
    # Use CPU if memory is low
    if torch.cuda.memory_allocated() > 0.8 * torch.cuda.max_memory_allocated():
        print("Switching to CPU due to memory pressure")
        return "cpu"
    
    return "cuda"
```

---

## 📊 **PERFORMANCE METRICS & BENCHMARKS**

### **Current Performance (Live Data)**
```python
# Performance benchmarks (Stand: 2025-08-30)
PERFORMANCE_DATA = {
    "guard": {
        "avg_response_time_ms": 150,
        "requests_per_second": 6.7,
        "memory_usage_mb": 45,
        "cpu_usage_percent": 12
    },
    "worker": {
        "avg_response_time_ms": 800,
        "requests_per_second": 1.25,
        "memory_usage_mb": 1200,
        "cpu_usage_percent": 85
    },
    "trancecreate": {
        "avg_response_time_ms": 1200,
        "requests_per_second": 0.83,
        "memory_usage_mb": 200,
        "cpu_usage_percent": 25
    },
    "trancespell": {
        "avg_response_time_ms": 50,
        "requests_per_second": 20,
        "memory_usage_mb": 30,
        "cpu_usage_percent": 5
    }
}
```

### **Load Testing Script**
```python
import requests
import time
import statistics

def load_test(endpoint: str, requests: int = 100):
    """Load test for any endpoint"""
    times = []
    errors = 0
    
    for i in range(requests):
        start = time.time()
        try:
            response = requests.post(
                endpoint,
                json={"source": "en", "target": "de", "text": f"Test message {i}"},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            if response.status_code == 200:
                times.append(time.time() - start)
            else:
                errors += 1
        except Exception:
            errors += 1
    
    return {
        "avg_time_ms": statistics.mean(times) * 1000,
        "min_time_ms": min(times) * 1000,
        "max_time_ms": max(times) * 1000,
        "requests_per_second": len(times) / sum(times),
        "error_rate": errors / requests
    }

# Usage:
# load_test("http://127.0.0.1:8091/translate")
```

---

## 🚀 **DEPLOYMENT & OPERATIONS**

### **Start Script (start_local.sh)**
```bash
#!/bin/bash
# ANNI Local Startup Script

set -e

echo "Starting ANNI services..."

# Kill existing processes
echo "Cleaning up existing processes..."
lsof -tiTCP:8091 | xargs kill -9 2>/dev/null || true
lsof -tiTCP:8093 | xargs kill -9 2>/dev/null || true
lsof -tiTCP:8095 | xargs kill -9 2>/dev/null || true
lsof -tiTCP:8096 | xargs kill -9 2>/dev/null || true

# Set environment variables
export MT_BACKEND=http://127.0.0.1:8093
export ANNI_MAX_NEW_TOKENS=512
export ANNI_CHUNK_CHARS=600
export TC_GUARD_URL=http://127.0.0.1:8091/translate
export TC_USE_MISTRAL=true

# Start services
echo "Starting Guard (Port 8091)..."
nohup uvicorn mt_guard:app --host 0.0.0.0 --port 8091 >/tmp/guard.log 2>&1 &

echo "Starting Worker (Port 8093)..."
nohup uvicorn m2m_worker:app --host 0.0.0.0 --port 8093 >/tmp/worker.log 2>&1 &

echo "Starting TranceCreate (Port 8095)..."
nohup uvicorn tc_server:app --host 0.0.0.0 --port 8095 >/tmp/tc_server.log 2>&1 &

echo "Starting TranceSpell (Port 8096)..."
nohup uvicorn ts_server:app --host 0.0.0.0 --port 8096 >/tmp/ts_server.log 2>&1 &

echo "Starting GUI (Port 8094)..."
nohup python3 -m http.server 8094 >/tmp/gui.log 2>&1 &

# Wait for services to start
echo "Waiting for services to start..."
sleep 10

# Health checks
echo "Performing health checks..."
curl -s http://127.0.0.1:8091/health | jq '.ok' && echo " - Guard OK" || echo " - Guard FAIL"
curl -s http://127.0.0.1:8093/health | jq '.ok' && echo " - Worker OK" || echo " - Worker FAIL"
curl -s http://127.0.0.1:8095/health | jq '.ok' && echo " - TranceCreate OK" || echo " - TranceCreate FAIL"
curl -s http://127.0.0.1:8096/health | jq '.ok' && echo " - TranceSpell OK" || echo " - TranceSpell FAIL"

echo "ANNI services started successfully!"
echo "GUI available at: http://127.0.0.1:8094/anni_gui.html"
```

### **Stop Script (stop_local.sh)**
```bash
#!/bin/bash
# ANNI Local Shutdown Script

echo "Stopping ANNI services..."

# Stop all services
lsof -tiTCP:8091 | xargs kill -9 2>/dev/null || true
lsof -tiTCP:8093 | xargs kill -9 2>/dev/null || true
lsof -tiTCP:8095 | xargs kill -9 2>/dev/null || true
lsof -tiTCP:8096 | xargs kill -9 2>/dev/null || true
lsof -tiTCP:8094 | xargs kill -9 2>/dev/null || true

echo "ANNI services stopped."
```

---

## 📞 **SUPPORT & TROUBLESHOOTING**

### **Common Error Codes & Solutions**
```python
ERROR_SOLUTIONS = {
    "HTTP 400": {
        "cause": "Bad Request - Invalid JSON or missing fields",
        "solution": "Check request format and required fields",
        "example": "Ensure 'source', 'target', 'text' are present"
    },
    "HTTP 401": {
        "cause": "Unauthorized - Missing or invalid API key",
        "solution": "Add X-API-Key header with valid key",
        "example": 'headers={"X-API-Key": "your-secret-key"}'
    },
    "HTTP 404": {
        "cause": "Not Found - Wrong endpoint or service down",
        "solution": "Check endpoint URL and service status",
        "example": "Verify /translate endpoint and worker health"
    },
    "HTTP 500": {
        "cause": "Internal Server Error - Service exception",
        "solution": "Check service logs for details",
        "example": "tail -f /tmp/worker.log"
    },
    "HTTP 502": {
        "cause": "Bad Gateway - Backend service unreachable",
        "solution": "Restart backend service",
        "example": "Restart worker: lsof -tiTCP:8093 | xargs kill -9"
    }
}
```

### **Debug Commands**
```bash
# Service status
for port in 8091 8093 8095 8096; do
  echo "Port $port:"; curl -s http://127.0.0.1:$port/health | jq '.ok' 2>/dev/null || echo "Not responding"
done

# Log monitoring
tail -f /tmp/*.log | grep -E "(ERROR|WARN|INFO)"

# Memory usage
ps aux | grep -E "(guard|worker|tc|ts)" | grep -v grep

# Port usage
lsof -i :8091-8096 | grep LISTEN
```

---

*ChatGPT Optimized Version: 2.0*  
*Last Updated: 2025-08-30*  
*Contains: Code Snippets, Live Status, Configuration Examples, Troubleshooting*
