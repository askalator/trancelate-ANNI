# TranceCreation v1

**TranceCreation v1** ist ein separater FastAPI-Service, der Guard-Baseline-Übersetzungen zu Copy-Writer-Qualität veredelt.

## 🎯 Übersicht

TranceCreation veredelt die Guard-Baseline-Übersetzungen mit:
- **Profiles**: Verschiedene Stil-Profile (Marketing, Social, Technical, Creative)
- **Personas**: Copy-Writer-Personas (Ogilvy, Halbert, etc.)
- **Levels**: Verschiedene Intensitätsstufen (0-3)
- **Policies**: Sicherheitsrichtlinien und Invarianten-Schutz

## 🏗️ Architektur

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client        │    │  TranceCreation │    │     Guard       │
│                 │───▶│   (Port 8095)   │───▶│   (Port 8091)   │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │     Mistral     │
                       │   (Port 8092)   │
                       │                 │
                       └─────────────────┘
```

## 🚀 Installation & Start

### 1. Abhängigkeiten installieren
```bash
pip install fastapi uvicorn requests pydantic
```

### 2. Service starten
```bash
./start_trance_creation.sh
```

### 3. Service testen
```bash
python scripts/test_trance_creation.py
```

## 📚 API Dokumentation

### Health Check
```bash
curl http://127.0.0.1:8095/health
```

### Profile abrufen
```bash
curl http://127.0.0.1:8095/profiles
```

### Transcreation
```bash
curl -X POST http://127.0.0.1:8095/transcreate \
  -H "Content-Type: application/json" \
  -d '{
    "source": "en",
    "target": "ja",
    "text": "Discover our amazing products!",
    "profile": "marketing",
    "persona": "ogilvy",
    "level": 2
  }'
```

## 🎨 Profile

### Marketing Profile
- **Stil**: Persuasive, benefit-focused, action-oriented
- **CTA**: Locale-spezifische Call-to-Actions
- **Emoji**: ✨

### Social Profile
- **Stil**: Casual, engaging, shareable
- **CTA**: Social Media optimiert
- **Emoji**: 🔥

### Technical Profile
- **Stil**: Precise, detailed, professional
- **Emoji**: ⚙️

### Creative Profile
- **Stil**: Imaginative, expressive, artistic
- **Emoji**: 🎨

## 👤 Personas

### David Ogilvy
- **Stil**: Clear, precise, elegant, subtle, benefit-focused
- **Beschreibung**: Klare, präzise, elegante Copy, die sich auf Vorteile konzentriert

### Gary Halbert
- **Stil**: Bold, direct-response, urgency, proof, compelling
- **Beschreibung**: Mutige, direkte Response-Copy mit Dringlichkeit und Beweisen

### Direct-Response
- **Stil**: Urgent, action-oriented, benefit-driven, compelling
- **Beschreibung**: Direkte Response-Marketing-Stil

### Brand-Warm
- **Stil**: Friendly, approachable, trustworthy, conversational
- **Beschreibung**: Warme, markenfreundliche Stil

### Luxury
- **Stil**: Sophisticated, exclusive, premium, refined
- **Beschreibung**: Luxus-Marken-Stil

### Casual
- **Stil**: Relaxed, informal, friendly, conversational
- **Beschreibung**: Entspannte, informelle Stil

### Authoritative
- **Stil**: Confident, expert, trustworthy, commanding
- **Beschreibung**: Autoritativer, Experten-Stil

## 📊 Levels

### Level 0: Minimal
- **Beschreibung**: Minimal changes, very conservative
- **Verwendung**: Für rechtliche Texte, technische Dokumentation

### Level 1: Light
- **Beschreibung**: Light improvements, subtle enhancements
- **Verwendung**: Für professionelle Kommunikation

### Level 2: Moderate
- **Beschreibung**: Moderate changes, noticeable improvements
- **Verwendung**: Für Marketing-Material

### Level 3: Significant
- **Beschreibung**: Significant changes, bold enhancements
- **Verwendung**: Für kreative Kampagnen, Social Media

## 🔒 Policies

### Preserve Elements
Standardmäßig werden folgende Elemente 1:1 erhalten:
- `{{placeholders}}` - Platzhalter
- `{single_brace}` - Einzelne Klammern
- `<html>` - HTML-Tags
- `numbers` - Zahlen und Preise
- `urls` - URLs
- `emojis` - Emojis

### Max Change Ratio
- **Standard**: 0.25 (25% Änderung erlaubt)
- **Bereich**: 0.0 - 1.0
- **Fail-closed**: Bei Überschreitung wird Baseline zurückgegeben

### Forbidden Terms
- **Standard**: Leere Liste
- **Fail-closed**: Bei Vorkommen wird Baseline zurückgegeben
- **Beispiel**: `["guarantee", "free shipping", "limited time"]`

### Domains Off
- **Standard**: `["legal", "privacy", "tos", "gdpr"]`
- **Beschreibung**: Domains, die von Transcreation ausgeschlossen sind

## 🔄 Fail-Closed Verhalten

TranceCreation implementiert **Fail-Closed** Verhalten:

1. **Guard nicht erreichbar**: HTTP 502, Baseline zurückgegeben
2. **Mistral nicht erreichbar**: Baseline zurückgegeben, `degraded=true`
3. **Policy verletzt**: Baseline zurückgegeben, `degraded=true`
4. **Invarianten verletzt**: Baseline zurückgegeben, `degraded=true`

## 📝 Beispiele

### Beispiel 1: Marketing + Ogilvy
```python
import requests

response = requests.post("http://127.0.0.1:8095/transcreate", json={
    "source": "en",
    "target": "ja",
    "text": "Discover our amazing products with {{COUNT}} items available.",
    "profile": "marketing",
    "persona": "ogilvy",
    "level": 2
})

data = response.json()
print(f"Baseline: {data['baseline_text']}")
print(f"Transcreated: {data['transcreated_text']}")
print(f"Char Ratio: {data['diffs']['char_ratio']:.3f}")
print(f"Degraded: {data['degraded']}")
```

### Beispiel 2: Mit Baseline-Text
```python
response = requests.post("http://127.0.0.1:8095/transcreate", json={
    "target": "ja",
    "baseline_text": "素晴らしい製品を発見してください。{{COUNT}}個のアイテムが利用可能です。",
    "profile": "social",
    "persona": "halbert",
    "level": 1
})
```

### Beispiel 3: Mit Policies
```python
response = requests.post("http://127.0.0.1:8095/transcreate", json={
    "target": "en",
    "baseline_text": "This is a test message about our products.",
    "profile": "marketing",
    "persona": "halbert",
    "level": 2,
    "policies": {
        "forbidden_terms": ["guarantee", "free shipping"],
        "max_change_ratio": 0.15
    }
})
```

## 🧪 Tests

### Alle Tests ausführen
```bash
python scripts/test_trance_creation.py
```

### Beispiele ausführen
```bash
python scripts/example_trance_creation.py
```

### Einzelne Tests
```bash
# Health Check
curl http://127.0.0.1:8095/health

# Profile abrufen
curl http://127.0.0.1:8095/profiles

# Transcreation testen
curl -X POST http://127.0.0.1:8095/transcreate \
  -H "Content-Type: application/json" \
  -d '{"target":"en","baseline_text":"Test","profile":"marketing","persona":"ogilvy","level":1}'
```

## 📁 Dateistruktur

```
trancelate-onprem/
├── trance_creation.py              # Hauptservice
├── start_trance_creation.sh        # Start-Script
├── config/
│   ├── trance_profiles.json        # Profile-Konfiguration
│   ├── tc_personas.json           # Persona-Konfiguration
│   └── tc_locales.json            # Locale-Konfiguration
├── scripts/
│   ├── test_trance_creation.py     # Self-Tests
│   └── example_trance_creation.py  # Beispiele
└── README_trance_creation.md       # Diese Datei
```

## 🔧 Konfiguration

### Profile anpassen
Bearbeiten Sie `config/trance_profiles.json`:
```json
{
  "profiles": {
    "custom": {
      "cta": {
        "de": "Jetzt kaufen",
        "en": "Buy now"
      },
      "emoji": "🚀",
      "style": "custom style description"
    }
  }
}
```

### Personas anpassen
Bearbeiten Sie `config/tc_personas.json`:
```json
{
  "personas": {
    "custom": {
      "style": "custom, professional, engaging",
      "description": "Custom persona description"
    }
  }
}
```

## 🚨 Troubleshooting

### Service startet nicht
1. Prüfen Sie die Abhängigkeiten: `pip install fastapi uvicorn requests pydantic`
2. Prüfen Sie die Konfigurationsdateien in `config/`
3. Prüfen Sie die Ports: 8095 sollte frei sein

### Guard nicht erreichbar
- Prüfen Sie, ob Guard auf Port 8091 läuft
- TranceCreation wird fail-closed und gibt Baseline zurück

### Mistral nicht erreichbar
- Prüfen Sie, ob Mistral auf Port 8092 läuft
- TranceCreation wird fail-closed und gibt Baseline zurück

### Policy-Fehler
- Prüfen Sie die `max_change_ratio` (Standard: 0.25)
- Prüfen Sie die `forbidden_terms` Liste
- Bei Policy-Verletzung wird Baseline zurückgegeben

## 📈 Monitoring

### Health Check
```bash
curl http://127.0.0.1:8095/health
```

### Response-Metriken
Jede Transcreation-Response enthält:
- `trace.guard_latency_ms`: Guard-Latenz
- `trace.tc_latency_ms`: TranceCreation-Latenz
- `diffs.char_ratio`: Änderungsverhältnis
- `degraded`: Fail-closed Status

## 🔄 Integration

### Mit ANNI GUI
TranceCreation kann in die ANNI GUI integriert werden:
- Neuer Tab "Transcreation"
- Profile/Persona-Auswahl
- Level-Slider
- Policy-Konfiguration

### Mit bestehenden Services
- **Guard**: Ruft Guard für Baseline auf
- **Mistral**: Verwendet Mistral für Transcreation
- **Keine Änderungen** an bestehenden Services erforderlich

## 📄 Lizenz

TranceCreation v1 ist Teil des ANNI-Ökosystems und folgt den gleichen Lizenzbedingungen.

---

**TranceCreation v1** - Veredelt Guard-Baseline-Übersetzungen zu Copy-Writer-Qualität 🎨
