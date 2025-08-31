# ANNI Quick Reference Guide
*TranceLate.it FlexCo - Version 2.0*

---

## 🚀 Quick Start

### 1. Start Services
```bash
# Start all services
./start_local.sh

# Or individually:
nohup uvicorn mt_guard:app --host 0.0.0.0 --port 8091 >/tmp/guard.log 2>&1 &
nohup uvicorn m2m_worker:app --host 0.0.0.0 --port 8093 >/tmp/worker.log 2>&1 &
nohup uvicorn tc_server:app --host 0.0.0.0 --port 8095 >/tmp/tc_server.log 2>&1 &
nohup uvicorn ts_server:app --host 0.0.0.0 --port 8096 >/tmp/ts_server.log 2>&1 &
python3 -m http.server 8094  # GUI
```

### 2. Verify Installation
```bash
curl http://127.0.0.1:8091/health  # Guard
curl http://127.0.0.1:8093/health  # Worker
curl http://127.0.0.1:8095/health  # TranceCreate
curl http://127.0.0.1:8096/health  # TranceSpell
```

### 3. Basic Translation
```bash
curl -X POST http://127.0.0.1:8091/translate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"source":"en","target":"de","text":"Hello world!"}'
```

---

## 📡 Service Ports

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| **Guard** | 8091 | Translation Gateway | `/health` |
| **Worker** | 8093 | M2M100 Engine | `/health` |
| **GUI** | 8094 | Web Interface | Static HTML |
| **TranceCreate** | 8095 | Content Enhancement | `/health` |
| **TranceSpell** | 8096 | Spell Checking | `/health` |

---

## 🔧 Core Commands

### Service Management
```bash
# Check service status
lsof -i :8091-8096

# Stop specific service
lsof -tiTCP:8091 | xargs kill -9

# View logs
tail -f /tmp/guard.log
tail -f /tmp/worker.log
tail -f /tmp/tc_server.log
tail -f /tmp/ts_server.log
```

### Translation
```bash
# Basic translation
anni en de "Hello world!"

# Multiple targets
anni en -m de,fr,es "Hello world!"

# Long text via file
anni en de < long_text.txt
```

### TranceCreate
```bash
# Content enhancement
curl -X POST http://127.0.0.1:8095/transcreate \
  -H "Content-Type: application/json" \
  -d '{
    "source":"en","target":"de","text":"Hello world!",
    "profile":"marketing","persona":"ogilvy","level":2
  }'
```

### TranceSpell
```bash
# Spell checking
curl -X POST http://127.0.0.1:8096/check \
  -H "Content-Type: application/json" \
  -d '{"lang":"de-DE","text":"<button>Jetz registrieren</button>"}'
```

---

## ⚙️ Configuration

### Environment Variables
```bash
# Core ANNI
export MT_BACKEND=http://127.0.0.1:8093
export ANNI_MAX_NEW_TOKENS=512
export ANNI_CHUNK_CHARS=600
export ANNI_API_KEY=your-secret-key

# TranceCreate
export TC_GUARD_URL=http://127.0.0.1:8091/translate
export TC_API_KEY=your-secret-key
export TC_USE_MISTRAL=true

# TranceSpell
export TS_PORT=8096
```

### Key Configuration Files
- `config/tc_pipeline.json` - TranceCreate pipeline stages
- `config/claim_fit.json` - ClaimGuard settings
- `config/trancespell.json` - Spell checking configuration
- `langs.json` - Supported languages
- `lang_aliases.json` - Language code mappings

---

## 🧪 Testing

### Smoke Tests
```bash
# Basic functionality
python scripts/anni_smoke.py
python scripts/verify_stack.py

# TranceCreate
python scripts/test_tc_pipeline.py
python scripts/test_tc_claim_fit.py

# TranceSpell
python scripts/test_trancespell.py
python scripts/test_trancespell_languages.py
```

### Quality Gates
```bash
# Run quality checks
python scripts/test_invariants.py
python scripts/test_long_text.py
python scripts/test_language_pairs.py
```

---

## 🔍 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check port conflicts
lsof -i :8091
lsof -i :8093
lsof -i :8095
lsof -i :8096

# Kill conflicting processes
kill -9 <PID>
```

#### Translation Errors
```bash
# Check worker health
curl http://127.0.0.1:8093/health

# Verify MT_BACKEND
echo $MT_BACKEND

# Check worker logs
tail -f /tmp/worker.log
```

#### Invariant Violations
```bash
# Test invariant protection
curl -X POST http://127.0.0.1:8091/translate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"source":"en","target":"de","text":"Hello {{COUNT}} world!"}'
```

---

## 📊 Monitoring

### Health Dashboard
```bash
# Create health status file
curl -s http://127.0.0.1:8091/health > guard_status.json
curl -s http://127.0.0.1:8093/health > worker_status.json
curl -s http://127.0.0.1:8095/health > tc_status.json
curl -s http://127.0.0.1:8096/health > ts_status.json
```

### Performance Monitoring
```bash
# Monitor response times
time curl -s http://127.0.0.1:8091/health

# Check resource usage
ps aux | grep -E "(guard|worker|tc|ts)" | grep -v grep

# Monitor logs
tail -f /tmp/*.log | grep -E "(ERROR|WARN|INFO)"
```

---

## 🚀 Advanced Features

### Pipeline Management
```bash
# View current pipeline
curl http://127.0.0.1:8095/pipeline

# Update pipeline
curl -X PUT http://127.0.0.1:8095/pipeline \
  -H "Content-Type: application/json" \
  -d '{"stages": ["tc_core", "claim_guard", "policy_check", "degrade"]}'
```

### Language Management
```bash
# Check available languages
curl http://127.0.0.1:8096/languages

# View language aliases
cat langs.json
cat lang_aliases.json
```

---

## 📚 Useful Commands

### Quick Diagnostics
```bash
# Service status overview
for port in 8091 8093 8095 8096; do
  echo "Port $port:"; curl -s http://127.0.0.1:$port/health | jq '.ok' 2>/dev/null || echo "Not responding"
done

# Port usage summary
lsof -i :8091-8096 | grep LISTEN

# Log file sizes
ls -lh /tmp/*.log
```

### Performance Testing
```bash
# Load test
for i in {1..10}; do
  time curl -s -X POST http://127.0.0.1:8091/translate \
    -H "Content-Type: application/json" \
    -H "X-API-Key: your-key" \
    -d '{"source":"en","target":"de","text":"Test message $i"}' > /dev/null
done
```

---

## 📞 Support

### Documentation
- **Complete Handbook**: `ANNI_Complete_Handbook.md`
- **API Reference**: See handbook sections 6-8
- **Troubleshooting**: See handbook section 9

### Contact
- **Email**: support@trancelate.it
- **Documentation**: https://docs.trancelate.it
- **GitHub**: https://github.com/trancelate/anni

---

*Quick Reference Version: 2.0*  
*Last Updated: 2025-08-30*
