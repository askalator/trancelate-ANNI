#!/usr/bin/env python3
"""
TranceCreate v1.2 - FastAPI Service with Pluggable Pipeline
Enhanced version with modular stages, hot-reload, and configurable pipeline
Port: 8095
"""

import json
import time
import re
import requests
import hashlib
import os
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import difflib
from pathlib import Path

# Import pipeline infrastructure
from tc_pipeline import Pipeline, Ctx
from tc_stages import TcCoreStage, ProfileStage, PolicyCheckStage, DegradeStage

# FastAPI App
app = FastAPI(
    title="TranceCreate API",
    version="1.2.0",
    description="Enhanced TranceCreate with modular pipeline, hot-reload, and configurable stages"
)

# Initialize pipeline
pipeline = Pipeline("config/tc_pipeline.json")
pipeline.register_stage(TcCoreStage)
pipeline.register_stage(ProfileStage)
pipeline.register_stage(PolicyCheckStage)
pipeline.register_stage(DegradeStage)

# Reload pipeline after registering stages
pipeline._load_pipeline()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
GUARD_URL = "http://127.0.0.1:8091"
GUARD_API_KEY = "topsecret"
TC_MISTRAL_URL = os.getenv("TC_MISTRAL_URL", "http://127.0.0.1:8092/generate")
TC_USE_MISTRAL = os.getenv("TC_USE_MISTRAL", "true").lower() == "true"
TC_TIMEOUT = int(os.getenv("TC_TIMEOUT", "60"))
CONFIG_DIR = Path("config")

# Load configuration files
def load_config():
    """Load profiles, personas, and locales configuration"""
    config = {
        "profiles": {},
        "personas": {},
        "locales": {}
    }
    
    # Load profiles
    profiles_file = CONFIG_DIR / "trance_profiles.json"
    if profiles_file.exists():
        with open(profiles_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            config["profiles"] = data.get("profiles", {})
    
    # Load personas
    personas_file = CONFIG_DIR / "tc_personas.json"
    if personas_file.exists():
        with open(personas_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            config["personas"] = data.get("personas", {})
    
    # Load locales
    locales_file = CONFIG_DIR / "tc_locales.json"
    if locales_file.exists():
        with open(locales_file, 'r', encoding='utf-8') as f:
            config["locales"] = json.load(f)
    
    return config

# Load config on startup
CONFIG = load_config()

# Pydantic Models
class Policies(BaseModel):
    preserve: List[str] = Field(
        default=["placeholders", "single_brace", "html", "numbers", "urls", "emojis"],
        description="Elements to preserve exactly"
    )
    max_change_ratio: float = Field(default=0.25, ge=0.0, le=1.0)
    forbidden_terms: List[str] = Field(default=[])
    domains_off: List[str] = Field(default=["legal", "privacy", "tos", "gdpr"])

class TranscreateRequest(BaseModel):
    source: Optional[str] = None
    target: str
    text: Optional[str] = None
    baseline_text: Optional[str] = None
    profile: str = "marketing"
    persona: str = "default"
    level: int = Field(default=1, ge=0, le=3)
    seed: Optional[int] = None
    policies: Policies = Field(default_factory=Policies)
    
    @validator('level')
    def validate_level(cls, v):
        if v not in [0, 1, 2, 3]:
            raise ValueError('Level must be 0, 1, 2, or 3')
        return v

class TranscreateResponse(BaseModel):
    baseline_text: str
    transcreated_text: str
    diffs: Dict[str, Any]
    checks: Dict[str, Any]
    degraded: bool
    degrade_reasons: List[str]
    applied: Dict[str, Any]
    trace: Dict[str, Any]

# Utility Functions
def freeze_elements(text: str) -> tuple[str, Dict[str, List[str]]]:
    """Freeze placeholders, HTML, emojis, etc. like Guard does"""
    frozen = {}
    
    # Placeholders {{...}}
    placeholder_pattern = r'\{\{[^}]+\}\}'
    placeholders = re.findall(placeholder_pattern, text)
    for i, ph in enumerate(placeholders):
        placeholder_id = f"__PLACEHOLDER_{i}__"
        text = text.replace(ph, placeholder_id)
        frozen[placeholder_id] = [ph, "placeholder"]
    
    # Single brace {token}
    single_brace_pattern = r'\{[^}]+\}'
    single_braces = re.findall(single_brace_pattern, text)
    for i, sb in enumerate(single_braces):
        if sb not in [ph[0] for ph in frozen.values()]:  # Skip already frozen placeholders
            brace_id = f"__SINGLE_BRACE_{i}__"
            text = text.replace(sb, brace_id)
            frozen[brace_id] = [sb, "single_brace"]
    
    # HTML tags
    html_pattern = r'<[^>]+>'
    html_tags = re.findall(html_pattern, text)
    for i, tag in enumerate(html_tags):
        html_id = f"__HTML_{i}__"
        text = text.replace(tag, html_id)
        frozen[html_id] = [tag, "html"]
    
    # URLs
    url_pattern = r'https?://[^\s<>"]+'
    urls = re.findall(url_pattern, text)
    for i, url in enumerate(urls):
        url_id = f"__URL_{i}__"
        text = text.replace(url, url_id)
        frozen[url_id] = [url, "url"]
    
    # Numbers (including prices)
    number_pattern = r'\b\d+(?:\.\d+)?(?:%|€|\$|¥|£)?\b'
    numbers = re.findall(number_pattern, text)
    for i, num in enumerate(numbers):
        num_id = f"__NUMBER_{i}__"
        text = text.replace(num, num_id, 1)  # Replace only first occurrence
        frozen[num_id] = [num, "number"]
    
    # Emojis
    emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF]'
    emojis = re.findall(emoji_pattern, text)
    for i, emoji in enumerate(emojis):
        emoji_id = f"__EMOJI_{i}__"
        text = text.replace(emoji, emoji_id, 1)
        frozen[emoji_id] = [emoji, "emoji"]
    
    return text, frozen

def unfreeze_elements(text: str, frozen: Dict[str, List[str]]) -> str:
    """Restore frozen elements"""
    for frozen_id, (original, _) in frozen.items():
        text = text.replace(frozen_id, original)
    return text

def get_baseline(source: str, target: str, text: str) -> tuple[str, Dict[str, Any], float]:
    """Get baseline translation from Guard"""
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{GUARD_URL}/translate",
            headers={"X-API-Key": GUARD_API_KEY, "Content-Type": "application/json"},
            json={"source": source, "target": target, "text": text},
            timeout=30
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Guard service error: {response.status_code}")
        
        data = response.json()
        guard_latency = (time.time() - start_time) * 1000
        
        return data.get("translated_text", ""), data.get("checks", {}), guard_latency
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Guard service unreachable: {str(e)}")

def build_prompt(baseline_text: str, profile: str, persona: str, level: int, target: str) -> tuple[str, str]:
    """Build system and user prompts for Mistral"""
    
    # Get profile and persona info
    profile_info = CONFIG["profiles"].get(profile, {})
    persona_info = CONFIG["personas"].get(persona, {})
    
    # Build profile hints
    profile_hints = []
    if "cta" in profile_info and target in profile_info["cta"]:
        profile_hints.append(f"CTA: {profile_info['cta'][target]}")
    if "emoji" in profile_info:
        profile_hints.append(f"Emoji: {profile_info['emoji']}")
    
    persona_style = persona_info.get("style", "clear, professional")
    
    # Level descriptions
    level_descriptions = {
        0: "minimal changes, very conservative",
        1: "light improvements, subtle enhancements",
        2: "moderate changes, noticeable improvements",
        3: "significant changes, bold enhancements"
    }
    
    system_prompt = f"""You are TranceCreate, a copy editor over a correct translation baseline.
Goal: improve persuasion and style for {target} market using persona {persona} and profile {profile}.
Do not change placeholders {{...}}, {{app}} tokens, HTML tags, numbers, prices, or URLs.
Keep meaning faithful; adjust tone only within level {level} ({level_descriptions[level]})."""

    user_prompt = f"""BASELINE:
---
{baseline_text}
---
Requirements:
- Tone & style: {persona_style}; profile hints: {', '.join(profile_hints) if profile_hints else 'none'}
- Keep invariants exactly; do not add claims.
Output ONLY the final text, no explanations."""

    return system_prompt, user_prompt

def mistral_alive() -> bool:
    """Check if Mistral service is alive with 1s timeout"""
    try:
        response = requests.head(TC_MISTRAL_URL, timeout=1)
        return response.status_code == 200
    except:
        return False

def tc_generate_with_mistral(baseline: str, target: str, profile: str, persona: str, level: int, seed: Optional[int]) -> str:
    """Generate transcreation using Mistral"""
    system_prompt, user_prompt = build_prompt(baseline, profile, persona, level, target)
    
    payload = {
        "system": system_prompt,
        "prompt": user_prompt
    }
    
    if seed is not None:
        payload["seed"] = seed
    
    try:
        response = requests.post(
            TC_MISTRAL_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=TC_TIMEOUT
        )
        
        if response.status_code != 200:
            raise Exception(f"Mistral API error: {response.status_code}")
        
        data = response.json()
        return data.get("text", "").strip()
        
    except Exception as e:
        raise Exception(f"Mistral service error: {str(e)}")

def tc_generate_fallback(baseline: str, target: str, profile: str, persona: str, level: int) -> str:
    """Heuristic fallback generation"""
    result = baseline
    
    # Only apply changes if level > 0
    if level == 0:
        return result
    
    # Get profile info for CTA/emoji
    profile_info = CONFIG["profiles"].get(profile, {})
    
    # Light text cleaning (remove double spaces, fix punctuation)
    result = re.sub(r'\s+', ' ', result)  # Remove multiple spaces
    result = re.sub(r'\s+([.,;!?])', r'\1', result)  # Fix spacing before punctuation
    result = result.strip()
    
    # Add CTA if level > 1 and not present
    if level > 1 and "cta" in profile_info and target in profile_info["cta"]:
        cta = profile_info["cta"][target]
        if cta not in result:
            result += f" {cta}"
    
    # Add emoji if level > 1 and not present
    if level > 1 and "emoji" in profile_info:
        emoji = profile_info["emoji"]
        if emoji not in result:
            result += f" {emoji}"
    
    return result

def tc_generate(baseline: str, target: str, profile: str, persona: str, level: int, seed: Optional[int]) -> tuple[str, str]:
    """Generate transcreation with fallback logic"""
    if TC_USE_MISTRAL and mistral_alive():
        try:
            result = tc_generate_with_mistral(baseline, target, profile, persona, level, seed)
            return result, "mistral"
        except Exception as e:
            # Fallback on Mistral error
            result = tc_generate_fallback(baseline, target, profile, persona, level)
            return result, "fallback"
    else:
        result = tc_generate_fallback(baseline, target, profile, persona, level)
        return result, "fallback"

# Make functions available for stages
def tc_generate_for_stages(baseline: str, target: str, profile: str, persona: str, level: int, seed: Optional[int]) -> tuple[str, str]:
    """Wrapper for tc_generate to be used by stages"""
    return tc_generate(baseline, target, profile, persona, level, seed)

def generate_stable_seed(baseline: str, target: str, profile: str, persona: str, level: int) -> int:
    """Generate stable seed from input parameters"""
    seed_string = f"{baseline}{target}{profile}{persona}{level}"
    hash_object = hashlib.md5(seed_string.encode())
    hash_hex = hash_object.hexdigest()
    return int(hash_hex[:8], 16) % (2**31)

def check_policies(baseline: str, transcreated: str, policies: Policies) -> tuple[bool, List[str]]:
    """Check if transcreated text meets policy requirements"""
    degrade_reasons = []
    
    # Check max_change_ratio
    matcher = difflib.SequenceMatcher(None, baseline, transcreated)
    char_ratio = 1 - matcher.ratio()
    
    if char_ratio > policies.max_change_ratio:
        degrade_reasons.append("max_change_ratio_exceeded")
    
    # Check forbidden terms
    for term in policies.forbidden_terms:
        if term.lower() in transcreated.lower():
            degrade_reasons.append(f"forbidden_term:{term}")
    
    # Check preserved elements (simplified - in real implementation would check frozen elements)
    # For now, we assume preserve_ok is True
    
    # Overall policy check
    policy_ok = len(degrade_reasons) == 0
    
    return policy_ok, degrade_reasons

def calculate_diffs(baseline: str, transcreated: str) -> Dict[str, Any]:
    """Calculate differences between baseline and transcreated text"""
    matcher = difflib.SequenceMatcher(None, baseline, transcreated)
    char_ratio = 1 - matcher.ratio()
    
    # Simple diff operations
    ops = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != 'equal':
            ops.append({
                "op": tag,
                "src": [i1, i2],
                "dst": [j1, j2],
                "text": transcreated[j1:j2] if tag in ['replace', 'insert'] else baseline[i1:i2]
            })
    
    return {
        "char_ratio": char_ratio,
        "ops": ops
    }

# API Routes
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"ok": True, "service": "TranceCreate", "version": "1.2.0"}

@app.get("/profiles")
async def get_profiles():
    """Get available profiles and personas"""
    return {
        "profiles": CONFIG["profiles"],
        "personas": CONFIG["personas"],
        "locales": CONFIG["locales"]
    }

@app.get("/pipeline")
async def get_pipeline():
    """Get current pipeline configuration"""
    return pipeline.get_config()

@app.put("/pipeline")
async def update_pipeline(request: Dict[str, Any]):
    """Update pipeline configuration"""
    stages = request.get("stages", [])
    
    if not isinstance(stages, list):
        raise HTTPException(status_code=400, detail="stages must be a list")
    
    # Validate stage names
    known_stages = ["tc_core", "post_profile", "policy_check", "degrade"]
    unknown_stages = [s for s in stages if s not in known_stages]
    if unknown_stages:
        raise HTTPException(status_code=400, detail=f"Unknown stages: {unknown_stages}")
    
    # Update pipeline
    success = pipeline.update_config(stages)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update pipeline configuration")
    
    return pipeline.get_config()

@app.post("/transcreate", response_model=TranscreateResponse)
async def transcreate(request: TranscreateRequest):
    """Create transcreated variant using configurable pipeline"""
    
    tc_start_time = time.time()
    
    # Step 1: Get baseline
    if request.baseline_text:
        baseline_text = request.baseline_text
        guard_latency = 0
        guard_checks = {}
    else:
        if not request.source or not request.text:
            raise HTTPException(status_code=400, detail="source and text required when baseline_text not provided")
        
        baseline_text, guard_checks, guard_latency = get_baseline(
            request.source, request.target, request.text
        )
    
    # Step 2: Generate stable seed if not provided
    if request.seed is None:
        seed = generate_stable_seed(baseline_text, request.target, request.profile, request.persona, request.level)
    else:
        seed = request.seed
    
    # Step 3: Create pipeline context
    ctx = Ctx({
        "source": request.source,
        "target": request.target,
        "baseline": baseline_text,
        "text": baseline_text,  # Start with baseline
        "profile": request.profile,
        "persona": request.persona,
        "level": request.level,
        "policies": request.policies.model_dump(),
        "seed": seed,
        "trace": {},
        "degrade_reasons": []
    })
    
    # Step 4: Run pipeline
    try:
        ctx = pipeline.run(ctx)
        tc_latency = (time.time() - tc_start_time) * 1000
    except Exception as e:
        # Fail-closed: return baseline if pipeline fails
        tc_latency = (time.time() - tc_start_time) * 1000
        return TranscreateResponse(
            baseline_text=baseline_text,
            transcreated_text=baseline_text,
            diffs={"char_ratio": 0.0, "ops": []},
            checks=guard_checks,
            degraded=True,
            degrade_reasons=["pipeline_error"],
            applied={
                "profile": request.profile,
                "persona": request.persona,
                "level": request.level,
                "policies": request.policies.model_dump()
            },
            trace={
                "guard_latency_ms": int(guard_latency),
                "tc_latency_ms": int(tc_latency),
                "tc_model": "error",
                "seed": seed,
                "error": str(e)
            }
        )
    
    # Step 5: Extract results from context
    transcreated_text = ctx.get("text", baseline_text)
    degrade_reasons = ctx.get("degrade_reasons", [])
    degraded = ctx.get("degraded", False)
    trace = ctx.get("trace", {})
    
    # Step 6: Calculate diffs
    diffs = calculate_diffs(baseline_text, transcreated_text)
    
    return TranscreateResponse(
        baseline_text=baseline_text,
        transcreated_text=transcreated_text,
        diffs=diffs,
        checks=guard_checks,
        degraded=degraded,
        degrade_reasons=degrade_reasons,
        applied={
            "profile": request.profile,
            "persona": request.persona,
            "level": request.level,
            "policies": request.policies.model_dump()
        },
        trace={
            "guard_latency_ms": int(guard_latency),
            "tc_latency_ms": int(tc_latency),
            "tc_model": trace.get("tc_model", ""),
            "seed": seed
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8095)
