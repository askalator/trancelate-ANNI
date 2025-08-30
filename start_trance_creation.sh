#!/bin/bash
# TranceCreation v1 Startup Script
# Starts TranceCreation service on port 8095

set -e

echo "🚀 Starting TranceCreation v1..."

# Check if config directory exists
if [ ! -d "config" ]; then
    echo "❌ Config directory not found. Please ensure config/ directory exists with required JSON files."
    exit 1
fi

# Check if required config files exist
required_files=("config/trance_profiles.json" "config/tc_personas.json" "config/tc_locales.json")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Required config file not found: $file"
        exit 1
    fi
done

echo "✅ Config files found"

# Check if Python dependencies are available
python3 -c "import fastapi, uvicorn, requests, pydantic" 2>/dev/null || {
    echo "❌ Required Python packages not found. Please install:"
    echo "   pip install fastapi uvicorn requests pydantic"
    exit 1
}

echo "✅ Dependencies available"

# Check if Guard service is running (optional check)
if curl -s http://127.0.0.1:8091/health >/dev/null 2>&1; then
    echo "✅ Guard service is running"
else
    echo "⚠️  Guard service not detected (will fail-closed if needed)"
fi

# Check if Mistral service is running (optional check)
if curl -s http://127.0.0.1:8092/v1/models >/dev/null 2>&1; then
    echo "✅ Mistral service is running"
else
    echo "⚠️  Mistral service not detected (will fail-closed if needed)"
fi

# Start TranceCreation service
echo "🚀 Starting TranceCreation on port 8095..."
echo "   Health: http://127.0.0.1:8095/health"
echo "   Profiles: http://127.0.0.1:8095/profiles"
echo "   Transcreate: POST http://127.0.0.1:8095/transcreate"

# Run the service
python3 trance_creation.py
