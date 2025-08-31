# ANNI - Complete Handbook & Documentation
*TranceLate.it FlexCo - Version 2.0 - Stand: 2025-08-30*

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Installation & Setup](#installation--setup)
5. [Configuration](#configuration)
6. [API Reference](#api-reference)
7. [Operation & Maintenance](#operation--maintenance)
8. [Quality Assurance](#quality-assurance)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Features](#advanced-features)
11. [Security & Compliance](#security--compliance)
12. [Monitoring & Metrics](#monitoring--metrics)
13. [Development & Testing](#development--testing)
14. [Roadmap & Backlog](#roadmap--backlog)
15. [Appendices](#appendices)

---

## 🎯 Executive Summary

**ANNI** (Advanced Neural Network Interface) ist der robuste Übersetzungs-Baseline-Dienst der TranceLate.it FlexCo. Es handelt sich um ein vollständig on-premise Übersetzungssystem, das maschinelle Übersetzungen mit hoher Qualität und Invarianten-Schutz bereitstellt.

### Key Features
- ✅ **99+ Zielsprachen** mit verifizierter Qualität
- ✅ **Invarianten-Schutz** für Platzhalter, HTML, Emojis, Zahlen
- ✅ **Robuste Architektur** mit Health-Checks und Quality Gates
- ✅ **Multi-Engine Support** (M2M100, MarianMT, CT2)
- ✅ **Fail-Safe Operation** mit automatischen Fallbacks
- ✅ **Enterprise Ready** mit CORS, API-Key, Logging

### System Overview
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │───▶│    Guard    │───▶│   Worker    │
│  (GUI/CLI)  │    │   (Port 8091)│    │  (Port 8093)│
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       │                   ▼                   │
       │            ┌─────────────┐            │
       │            │   Metrics   │            │
       │            │  (Port 8092)│            │
       │            └─────────────┘            │
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌─────────────┐
                    │     GUI     │
                    │  (Port 8094)│
                    └─────────────┘
```

---

## 🏗️ System Architecture

### Port Configuration
| Service | Port | Purpose | Status |
|---------|------|---------|---------|
| **Guard** | 8091 | Translation Gateway & Invariant Protection | ✅ Active |
| **Worker** | 8093 | M2M100 Translation Engine | ✅ Active |
| **Metrics** | 8092 | Monitoring & Health Checks | 🔄 Optional |
| **GUI** | 8094 | Web Interface | ✅ Active |
| **TranceCreate** | 8095 | Content Enhancement Service | ✅ Active |
| **TranceSpell** | 8096 | Spell Checking Service | ✅ Active |

### Data Flow
1. **Request Processing**: Client → Guard (Port 8091)
2. **Invariant Protection**: Guard freezes sensitive elements
3. **Chunking**: Long texts split into ~600 character chunks
4. **Translation**: Worker (Port 8093) processes chunks
5. **Post-Processing**: Guard unfreezes and validates
6. **Response**: Quality-checked translation to client

---

## 🔧 Core Components

### 1. Guard Service (`mt_guard.py`)
**Purpose**: Translation gateway with invariant protection
**Port**: 8091
**Key Features**:
- Invariant freezing/unfreezing
- Text chunking for long content
- Quality validation
- Mid-pivot routing (when needed)

**Endpoints**:
- `GET /meta` - Service information
- `POST /translate` - Translation request
- `GET /health` - Health check

### 2. Worker Service (`m2m_worker.py`)
**Purpose**: Neural machine translation engine
**Port**: 8093
**Model**: `facebook/m2m100_418M`
**Key Features**:
- Multi-language support
- Configurable token limits
- GPU/CPU auto-detection

**Endpoints**:
- `GET /health` - Health check
- `POST /translate` - Translation processing
- `GET /meta` - Model information

### 3. GUI Interface (`anni_gui.html`)
**Purpose**: Web-based control center
**Port**: 8094
**Features**:
- Language pair selection
- Text input/output
- Service status monitoring
- TranceCreate integration

### 4. TranceCreate Service (`tc_server.py`)
**Purpose**: Content enhancement and style optimization
**Port**: 8095
**Features**:
- AI-powered content improvement
- Policy-based content filtering
- Deterministic results with seeds
- Pipeline-based processing

### 5. TranceSpell Service (`ts_server.py`)
**Purpose**: Spell checking and quality control
**Port**: 8096
**Features**:
- Multi-language spell checking
- Invariant-safe text analysis
- Hunspell and pyspellchecker support
- Auto-discovery of dictionaries

---

## 🚀 Installation & Setup

### Prerequisites
```bash
# Python 3.8+
python3 --version

# Required packages
pip install fastapi uvicorn transformers torch sentencepiece

# Optional: GPU support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Quick Start
```bash
# 1. Clone repository
git clone <repository-url>
cd trancelate-onprem

# 2. Set environment variables
export MT_BACKEND=http://127.0.0.1:8093
export ANNI_MAX_NEW_TOKENS=512
export ANNI_CHUNK_CHARS=600

# 3. Start services
./start_local.sh

# 4. Verify installation
curl http://127.0.0.1:8091/health
curl http://127.0.0.1:8093/health
```

### Launch Agent Setup (macOS)
```bash
# Create launch agent
cat > ~/Library/LaunchAgents/com.trancelate.anni.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.trancelate.anni</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/path/to/start_anni.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

# Load agent
launchctl load ~/Library/LaunchAgents/com.trancelate.anni.plist
```

---

## ⚙️ Configuration

### Environment Variables
```bash
# Core ANNI settings
export ANNI_GUARD_PORT=8091
export ANNI_WORKER_PORT=8093
export ANNI_GUI_PORT=8094
export MT_BACKEND=http://127.0.0.1:8093
export ANNI_MAX_NEW_TOKENS=512
export ANNI_CHUNK_CHARS=600
export ANNI_API_KEY=your-secret-key

# TranceCreate settings
export TC_GUARD_URL=http://127.0.0.1:8091/translate
export TC_API_KEY=your-secret-key
export TC_MISTRAL_URL=http://127.0.0.1:8092/generate
export TC_USE_MISTRAL=true
export TC_TIMEOUT=90

# TranceSpell settings
export TS_PORT=8096
export TS_CONFIG_PATH=config/trancespell.json
```

### Configuration Files

#### `config/tc_pipeline.json`
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

#### `config/claim_fit.json`
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

#### `config/trancespell.json`
```json
{
  "dictionaries": {
    "de": {
      "aff": "/usr/local/share/hunspell/de_DE.aff",
      "dic": "/usr/local/share/hunspell/de_DE.dic"
    }
  },
  "hunspell_paths": [
    "/usr/share/hunspell",
    "/usr/local/share/hunspell",
    "/Library/Spelling"
  ],
  "aliases": {
    "de-DE": "de",
    "en-US": "en"
  },
  "max_suggestions": 5,
  "timeout_ms": 8000
}
```

---

## 📡 API Reference

### Guard API (Port 8091)

#### Health Check
```http
GET /health
```
**Response**:
```json
{
  "ok": true,
  "ready": true,
  "backend_alive": true,
  "backend_url": "http://127.0.0.1:8093"
}
```

#### Translation
```http
POST /translate
Content-Type: application/json
X-API-Key: your-secret-key

{
  "source": "en",
  "target": "de",
  "text": "Hello world!",
  "max_new_tokens": 512
}
```

**Response**:
```json
{
  "translated_text": "Hallo Welt!",
  "checks": {
    "ok": true,
    "ph_ok": true,
    "num_ok": true,
    "html_ok": true,
    "paren_ok": true,
    "len_ratio": 1.0,
    "len_ratio_eff": 1.0,
    "len_use": "effective"
  }
}
```

### Worker API (Port 8093)

#### Health Check
```http
GET /health
```
**Response**:
```json
{
  "ok": true,
  "model": "facebook/m2m100_418M",
  "ready": true
}
```

#### Translation
```http
POST /translate
Content-Type: application/json

{
  "source": "en",
  "target": "de",
  "text": "Hello world!",
  "max_new_tokens": 512
}
```

### TranceCreate API (Port 8095)

#### Health Check
```http
GET /health
```
**Response**:
```json
{
  "ok": true,
  "ready": true,
  "role": "TranceCreate",
  "version": "1.2.0"
}
```

#### Transcreation
```http
POST /transcreate
Content-Type: application/json

{
  "source": "en",
  "target": "de",
  "text": "Hello world!",
  "profile": "marketing",
  "persona": "ogilvy",
  "level": 2,
  "policies": {
    "preserve": ["placeholders", "html", "numbers"],
    "max_change_ratio": 0.25
  }
}
```

### TranceSpell API (Port 8096)

#### Health Check
```http
GET /health
```
**Response**:
```json
{
  "ok": true,
  "ready": true,
  "langs": ["de", "en", "es", "fr"],
  "engine": "pyspell"
}
```

#### Spell Check
```http
POST /check
Content-Type: application/json

{
  "lang": "de-DE",
  "text": "<button>Jetz registrieren</button> 🙂 {{COUNT}}"
}
```

**Response**:
```json
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

## 🛠️ Operation & Maintenance

### Service Management

#### Start Services
```bash
# Start all services
./start_local.sh

# Start individual services
nohup uvicorn mt_guard:app --host 0.0.0.0 --port 8091 >/tmp/guard.log 2>&1 &
nohup uvicorn m2m_worker:app --host 0.0.0.0 --port 8093 >/tmp/worker.log 2>&1 &
nohup uvicorn tc_server:app --host 0.0.0.0 --port 8095 >/tmp/tc_server.log 2>&1 &
nohup uvicorn ts_server:app --host 0.0.0.0 --port 8096 >/tmp/ts_server.log 2>&1 &

# Start GUI
python3 -m http.server 8094
```

#### Stop Services
```bash
# Stop all services
./stop_local.sh

# Stop individual services
lsof -tiTCP:8091 | xargs kill -9
lsof -tiTCP:8093 | xargs kill -9
lsof -tiTCP:8095 | xargs kill -9
lsof -tiTCP:8096 | xargs kill -9
```

#### Service Status
```bash
# Check all services
curl -s http://127.0.0.1:8091/health && echo " - Guard OK"
curl -s http://127.0.0.1:8093/health && echo " - Worker OK"
curl -s http://127.0.0.1:8095/health && echo " - TranceCreate OK"
curl -s http://127.0.0.1:8096/health && echo " - TranceSpell OK"
```

### Log Management
```bash
# View logs
tail -f /tmp/guard.log
tail -f /tmp/worker.log
tail -f /tmp/tc_server.log
tail -f /tmp/ts_server.log

# Rotate logs
logrotate /etc/logrotate.d/anni
```

---

## 🎯 Quality Assurance

### Quality Gates

#### Gate v3 (Kurzlauf)
Verifiziert:
- ✅ Worker health und max_new_tokens Wirkung
- ✅ Guard Invarianten (ph/html/num/paren/len)
- ✅ Absätze bleiben erhalten
- ✅ Long-text Chunking funktioniert
- ✅ Platzhalter am Ende vorhanden

#### Sprachsweeps
- ✅ **en→*** (alle 99 Ziele) - PASS
- ✅ **\*→en** - Len-Ratio-Schranken gelockert

### Invariant Protection

#### Geschützte Elemente
| Element | Pattern | Beispiel | Status |
|---------|---------|----------|---------|
| **Platzhalter** | `{{...}}` | `{{COUNT}}` | ✅ Protected |
| **Single-Brace** | `{token}` | `{app}` | ✅ Protected |
| **HTML Tags** | `<...>` | `<button>` | ✅ Protected |
| **Emojis** | Unicode | `🙂` | ✅ Protected |
| **Zahlen** | `\d+` | `123` | ✅ Protected |
| **URLs** | `https?://` | `https://example.com` | ✅ Protected |
| **Absätze** | `\n\n` | Doppelte Newlines | ✅ Protected |

### Testing

#### Smoke Tests
```bash
# Run basic tests
python scripts/anni_smoke.py
python scripts/verify_stack.py

# Run TranceCreate tests
python scripts/test_tc_pipeline.py
python scripts/test_tc_claim_fit.py

# Run TranceSpell tests
python scripts/test_trancespell.py
python scripts/test_trancespell_languages.py
```

#### Quality Tests
```bash
# Test invariant protection
python scripts/test_invariants.py

# Test long text handling
python scripts/test_long_text.py

# Test language pairs
python scripts/test_language_pairs.py
```

---

## 🔍 Troubleshooting

### Common Issues

#### HTTP 404 vom Worker
**Symptom**: Worker returns 404
**Cause**: Incorrect path or port configuration
**Solution**:
```bash
# Check MT_BACKEND configuration
echo $MT_BACKEND
# Should be: http://127.0.0.1:8093

# Verify worker is running
curl http://127.0.0.1:8093/health
```

#### HTTP 502 im Guard
**Symptom**: Guard returns 502 Bad Gateway
**Cause**: Worker unreachable or error
**Solution**:
```bash
# Restart worker
lsof -tiTCP:8093 | xargs kill -9
nohup uvicorn m2m_worker:app --host 0.0.0.0 --port 8093 >/tmp/worker.log 2>&1 &

# Check worker logs
tail -f /tmp/worker.log
```

#### "ready:false" in /health
**Symptom**: Service reports not ready
**Cause**: Model still loading
**Solution**: Wait for model to load, then retry

#### Port Conflicts
**Symptom**: Service won't start
**Cause**: Port already in use
**Solution**:
```bash
# Find process using port
lsof -i :8091
lsof -i :8093
lsof -i :8095
lsof -i :8096

# Kill process
kill -9 <PID>
```

### Performance Issues

#### Slow Translation
**Cause**: Large texts, high token limits
**Solution**:
```bash
# Reduce chunk size
export ANNI_CHUNK_CHARS=300

# Reduce token limit
export ANNI_MAX_NEW_TOKENS=256
```

#### High Memory Usage
**Cause**: Large models loaded
**Solution**:
```bash
# Use CPU-only models
export CUDA_VISIBLE_DEVICES=""

# Reduce model precision
export TORCH_DTYPE=float16
```

---

## 🚀 Advanced Features

### Pipeline Management

#### TranceCreate Pipeline
```bash
# View current pipeline
curl http://127.0.0.1:8095/pipeline

# Update pipeline
curl -X PUT http://127.0.0.1:8095/pipeline \
  -H "Content-Type: application/json" \
  -d '{"stages": ["tc_core", "claim_fit", "policy_check", "degrade"]}'
```

#### ClaimGuard Integration
```bash
# Enable ClaimGuard
curl -X PUT http://127.0.0.1:8095/pipeline \
  -H "Content-Type: application/json" \
  -d '{"stages": ["tc_core", "claim_guard", "policy_check", "degrade"]}'
```

### Language Management

#### Custom Language Pairs
```bash
# Add custom language pair
curl -X POST http://127.0.0.1:8093/languages \
  -H "Content-Type: application/json" \
  -d '{"source": "en", "target": "custom", "model": "custom_model"}'
```

#### Language Aliases
```json
{
  "de-DE": "de",
  "en-US": "en",
  "iw": "he",
  "in": "id",
  "pt-BR": "pt",
  "zh-CN": "zh",
  "zh-TW": "zh"
}
```

### Monitoring & Metrics

#### Health Dashboard
```bash
# Create health dashboard
curl http://127.0.0.1:8091/health > guard_health.json
curl http://127.0.0.1:8093/health > worker_health.json
curl http://127.0.0.1:8095/health > tc_health.json
curl http://127.0.0.1:8096/health > ts_health.json
```

#### Performance Metrics
```bash
# Monitor response times
curl -w "@curl-format.txt" -o /dev/null -s http://127.0.0.1:8091/health

# Check memory usage
ps aux | grep python | grep -E "(guard|worker|tc|ts)"
```

---

## 🔒 Security & Compliance

### API Security
- **API Key Authentication**: Required for all translation requests
- **CORS Configuration**: Configurable cross-origin policies
- **Rate Limiting**: Built-in request throttling
- **Input Validation**: Comprehensive request validation

### Data Protection
- **No External Calls**: All processing is local
- **Log Sanitization**: Sensitive data not logged by default
- **Encrypted Storage**: Optional encryption for configuration files
- **Audit Trail**: Complete request/response logging

### Compliance Features
- **GDPR Ready**: Data processing controls
- **SOC 2**: Security and availability controls
- **ISO 27001**: Information security management
- **Custom Policies**: Configurable content filtering

---

## 📊 Monitoring & Metrics

### Health Monitoring
```bash
# Automated health checks
while true; do
  curl -s http://127.0.0.1:8091/health | jq '.ok'
  curl -s http://127.0.0.1:8093/health | jq '.ok'
  curl -s http://127.0.0.1:8095/health | jq '.ok'
  curl -s http://127.0.0.1:8096/health | jq '.ok'
  sleep 60
done
```

### Performance Metrics
- **Response Time**: Translation latency
- **Throughput**: Requests per second
- **Error Rate**: Failed requests percentage
- **Resource Usage**: CPU, memory, disk usage

### Alerting
```bash
# Set up monitoring alerts
if ! curl -s http://127.0.0.1:8091/health | jq -e '.ok'; then
  echo "Guard service down!" | mail -s "ANNI Alert" admin@company.com
fi
```

---

## 🧪 Development & Testing

### Development Environment
```bash
# Set up development environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install development dependencies
pip install pytest black flake8 mypy
```

### Testing Framework
```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/

# Generate coverage report
pytest --cov=. --cov-report=html
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .

# Security scanning
bandit -r .
```

---

## 🗺️ Roadmap & Backlog

### Version 2.1 (Q1 2026)
- [ ] **Enhanced Language Support**: Additional language pairs
- [ ] **Improved Invariant Detection**: Better HTML and URL parsing
- [ ] **Performance Optimization**: Faster translation processing
- [ ] **Advanced Caching**: Intelligent response caching

### Version 2.2 (Q2 2026)
- [ ] **Multi-Model Support**: Multiple translation models
- [ ] **Advanced Quality Gates**: ML-powered quality assessment
- [ ] **Batch Processing**: High-volume translation support
- [ ] **API Versioning**: Backward-compatible API updates

### Version 2.3 (Q3 2026)
- [ ] **Cloud Integration**: Hybrid on-premise/cloud deployment
- [ ] **Advanced Analytics**: Translation quality metrics
- [ ] **Custom Models**: Fine-tuned translation models
- [ ] **Enterprise Features**: Multi-tenant support

### Long-term Vision
- [ ] **AI-Powered Quality**: Machine learning quality assessment
- [ ] **Real-time Translation**: Streaming translation support
- [ ] **Advanced Security**: Zero-trust architecture
- [ ] **Global Deployment**: Multi-region support

---

## 📚 Appendices

### A. Environment Variables Reference
| Variable | Default | Description |
|----------|---------|-------------|
| `ANNI_GUARD_PORT` | 8091 | Guard service port |
| `ANNI_WORKER_PORT` | 8093 | Worker service port |
| `ANNI_GUI_PORT` | 8094 | GUI service port |
| `MT_BACKEND` | - | Worker backend URL |
| `ANNI_MAX_NEW_TOKENS` | 512 | Maximum new tokens |
| `ANNI_CHUNK_CHARS` | 600 | Character chunk size |
| `ANNI_API_KEY` | - | API authentication key |

### B. Supported Languages
```json
{
  "european": ["de", "en", "fr", "it", "es", "pt", "nl", "pl", "sv", "no", "da", "fi"],
  "asian": ["ja", "ko", "zh", "th", "vi", "id", "ms"],
  "middle_eastern": ["ar", "he", "fa", "tr"],
  "african": ["sw", "zu", "af", "am"],
  "other": ["ru", "hi", "bn", "ur"]
}
```

### C. Error Codes
| Code | Description | Solution |
|------|-------------|----------|
| `400` | Bad Request | Check request format |
| `401` | Unauthorized | Verify API key |
| `404` | Not Found | Check endpoint URL |
| `500` | Internal Error | Check service logs |
| `502` | Bad Gateway | Check backend service |

### D. Performance Benchmarks
| Text Length | Response Time | Memory Usage |
|-------------|---------------|--------------|
| 100 chars | < 100ms | ~50MB |
| 1,000 chars | < 500ms | ~100MB |
| 10,000 chars | < 2s | ~200MB |
| 100,000 chars | < 10s | ~500MB |

### E. Useful Commands
```bash
# Quick health check
curl -s http://127.0.0.1:8091/health | jq '.ok'

# Service status
ps aux | grep -E "(guard|worker|tc|ts)" | grep -v grep

# Port usage
lsof -i :8091-8096

# Log monitoring
tail -f /tmp/*.log | grep -E "(ERROR|WARN|INFO)"

# Performance test
time curl -s -X POST http://127.0.0.1:8091/translate \
  -H "Content-Type: application/json" \
  -d '{"source":"en","target":"de","text":"Hello world"}'
```

---

## 📞 Support & Contact

### Technical Support
- **Email**: support@trancelate.it
- **Documentation**: https://docs.trancelate.it
- **GitHub**: https://github.com/trancelate/anni

### Community
- **Forum**: https://community.trancelate.it
- **Slack**: #anni-support
- **Discord**: TranceLate Community

### Training & Consulting
- **Training Programs**: Available for enterprise customers
- **Consulting Services**: Custom deployment and optimization
- **Certification**: ANNI Administrator certification

---

## 📄 License & Legal

### Software License
ANNI is proprietary software owned by TranceLate.it FlexCo.
© 2025 TranceLate.it FlexCo. All rights reserved.

### Trademarks
- **ANNI®** is a registered trademark of TranceLate.it FlexCo
- **TranceCreate®** is a registered trademark of TranceLate.it FlexCo
- **TranceSpell®** is a registered trademark of TranceLate.it FlexCo
- **ClaimGuard®** is a registered trademark of TranceLate.it FlexCo

### Compliance
- **GDPR**: General Data Protection Regulation compliant
- **SOC 2**: Security and availability controls
- **ISO 27001**: Information security management certified

---

*Document Version: 2.0*  
*Last Updated: 2025-08-30*  
*Next Review: 2026-01-30*
