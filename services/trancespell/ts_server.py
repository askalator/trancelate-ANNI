"""
TranceSpell® v1.0 FastAPI Server
Detection-only spell checking service with invariant-safe masking
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import time
import sys
import os

# Import shared functionality
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from libs.trance_common import mask, unmask, normalize, json_get, json_post, check_invariants, t, push, app_version

from ts_core import TranceSpellCore

# Initialize FastAPI app
app = FastAPI(
    title="TranceSpell® API v1.0",
    description="Detection-only spell checking with invariant-safe masking",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize TranceSpell core
ts_core = TranceSpellCore()

# Pydantic models
class SpellCheckRequest(BaseModel):
    lang: str = Field(..., description="Language code (e.g., 'de-DE', 'en-US')")
    text: str = Field(..., description="Text to check for spelling errors")

class SpellIssue(BaseModel):
    start: int = Field(..., description="Start position in original text")
    end: int = Field(..., description="End position in original text")
    token: str = Field(..., description="Misspelled token")
    suggestions: List[str] = Field(..., description="Suggested corrections")
    rule: str = Field(..., description="Rule type (always 'spell')")

class SpellCheckResponse(BaseModel):
    issues: List[SpellIssue] = Field(..., description="List of spelling issues found")
    masked: bool = Field(True, description="Whether text was masked for invariant protection")
    trace: Dict[str, Any] = Field(..., description="Trace information and metrics")

class HealthResponse(BaseModel):
    ok: bool = Field(..., description="Service health status")
    ready: bool = Field(..., description="Service readiness status")
    langs: List[str] = Field(..., description="Available languages")
    engine: str = Field(..., description="Primary spell engine (hunspell|pyspell)")

class LanguagesResponse(BaseModel):
    langs: Dict[str, List[str]] = Field(..., description="Languages by support level: full, basic, unsupported")
    aliases: Dict[str, str] = Field(..., description="Language code aliases")
    paths: Dict[str, List[str]] = Field(..., description="Hunspell dictionary paths")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        supported = ts_core.list_supported_langs()
        langs, aliases = ts_core.get_available_languages()
        
        # Determine primary engine
        engine = "hunspell" if supported["full"] else "pyspell"
        
        return HealthResponse(
            ok=True,
            ready=True,
            langs=langs,
            engine=engine,
            **app_version()
        )
    except Exception as e:
        return HealthResponse(
            ok=False,
            ready=False,
            langs=[],
            engine="error",
            **app_version()
        )

@app.get("/languages", response_model=LanguagesResponse)
async def get_languages():
    """Get available languages and aliases"""
    try:
        supported = ts_core.list_supported_langs()
        langs, aliases = ts_core.get_available_languages()
        return LanguagesResponse(
            langs=supported,
            aliases=aliases,
            paths={"hunspell": ts_core.hunspell_paths}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get languages: {str(e)}")

@app.post("/check", response_model=SpellCheckResponse)
async def check_spelling(request: SpellCheckRequest):
    """Check text for spelling errors"""
    try:
        # Perform spell check
        issues, trace = ts_core.check(request.text, request.lang)
        
        return SpellCheckResponse(
            issues=issues,
            masked=True,
            trace=trace
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spell check failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8096)
