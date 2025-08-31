"""
TranceSpell® Core - Masking + Spell-Engine + Checker
Detection-only spell checking with invariant-safe masking
"""

import re
import time
import json
import os
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path

# Regex patterns for masking (compatible with Guard/TC)
PLACEHOLDER_RE = re.compile(r'\{\{[^}]+\}\}')
SINGLE_BRACE_RE = re.compile(r'\{[^}]+\}')
HTML_TAG_RE = re.compile(r'<[^>]+>')
URL_RE = re.compile(r'https?://[^\s<>"{}]+')
EMOJI_RE = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF]')
NUM_RE = re.compile(r'(?<!\w)(\d(?:[0-9\u00A0\u202F .,])*?\d(?:[0-9\u00A0\u202F .,]*\d)*(?:\s*[–-]\s*\d(?:[0-9\u00A0\u202F .,])*?\d)*)(?=\D|$)')

class TranceSpellCore:
    """Core spell checking functionality with invariant-safe masking"""
    
    def __init__(self, config_path: str = "config/trancespell.json"):
        self.config = self._load_config(config_path)
        self.spell_engines = {}
        self.hunspell_paths = self._discover_hunspell_dirs()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default configuration
            return {
                "dictionaries": {},
                "hunspell_paths": [
                    "/usr/share/hunspell",
                    "/usr/local/share/hunspell", 
                    "/Library/Spelling"
                ],
                "aliases": {
                    "de-DE": "de", "en-US": "en", "iw": "he", "in": "id", 
                    "pt-BR": "pt", "zh-CN": "zh", "zh-TW": "zh"
                },
                "max_suggestions": 5,
                "timeout_ms": 8000
            }
    
    def lang_normalize(self, lang: str) -> str:
        """Normalize language code using aliases"""
        aliases = self.config.get("aliases", {})
        return aliases.get(lang, lang.split('-')[0] if '-' in lang else lang)
    
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
    
    def _try_hunspell(self, lang: str):
        """Try to load Hunspell dictionary"""
        try:
            import hunspell
            dicts = self.config.get("dictionaries", {})
            if lang in dicts:
                aff_path = dicts[lang].get("aff")
                dic_path = dicts[lang].get("dic")
                if aff_path and dic_path and os.path.exists(aff_path) and os.path.exists(dic_path):
                    return hunspell.HunSpell(dic_path, aff_path)
        except ImportError:
            pass
        return None
    
    def _try_pyspellchecker(self, lang: str):
        """Try to load pyspellchecker for supported languages"""
        try:
            from spellchecker import SpellChecker
            supported_langs = ["en", "de", "es", "fr", "it", "pt", "nl", "pl"]
            if lang in supported_langs:
                return SpellChecker(language=lang)
        except ImportError:
            pass
        return None
    
    def mask(self, text: str) -> Tuple[str, List[Dict], Dict[str, str]]:
        """Mask protected spans (compatible with Guard/TC)"""
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
            for match in reversed(matches):  # Process in reverse to maintain offsets
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
    
    def unmask(self, text: str, table: Dict[str, str]) -> str:
        """Unmask protected spans"""
        if not table:
            return text
        
        for key, content in table.items():
            text = text.replace(key, content)
        
        return text
    
    def check(self, text: str, lang: str) -> Tuple[List[Dict], Dict[str, Any]]:
        """Check spelling and return issues with trace"""
        start_time = time.time()
        
        # Normalize language
        normalized_lang = self.lang_normalize(lang)
        
        # Get spell engine
        engine = self._get_spell_engine(normalized_lang)
        
        if not engine:
            # Language not supported
            elapsed_ms = int((time.time() - start_time) * 1000)
            return [], {
                "lang": normalized_lang,
                "engine": "none",
                "checked_tokens": 0,
                "issues": 0,
                "elapsed_ms": elapsed_ms,
                "note": "lang_not_supported_for_spell"
            }
        
        # Mask protected content
        masked_text, spans, table = self.mask(text)
        
        # Tokenize and check spelling
        issues = []
        checked_tokens = 0
        
        # Simple word tokenization (split on whitespace and punctuation)
        words = re.findall(r'\b\w+\b', masked_text)
        
        for word in words:
            if word.startswith('__') and word.endswith('__'):
                continue  # Skip masked tokens
            
            checked_tokens += 1
            
            # Check spelling
            if hasattr(engine, 'spell'):  # Hunspell
                if not engine.spell(word):
                    suggestions = engine.suggest(word)[:self.config.get("max_suggestions", 5)]
                    # Find word position in original text
                    word_pos = masked_text.find(word)
                    if word_pos != -1:
                        # Calculate original position
                        original_pos = self._calculate_original_position(word_pos, spans)
                        issues.append({
                            "start": original_pos,
                            "end": original_pos + len(word),
                            "token": word,
                            "suggestions": suggestions,
                            "rule": "spell"
                        })
            
            elif hasattr(engine, 'unknown'):  # pyspellchecker
                if word in engine.unknown([word]):
                    suggestions = list(engine.candidates(word))[:self.config.get("max_suggestions", 5)]
                    # Find word position in original text
                    word_pos = masked_text.find(word)
                    if word_pos != -1:
                        # Calculate original position
                        original_pos = self._calculate_original_position(word_pos, spans)
                        issues.append({
                            "start": original_pos,
                            "end": original_pos + len(word),
                            "token": word,
                            "suggestions": suggestions,
                            "rule": "spell"
                        })
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        trace = {
            "lang": normalized_lang,
            "engine": "hunspell" if hasattr(engine, 'spell') else "pyspellchecker",
            "checked_tokens": checked_tokens,
            "issues": len(issues),
            "elapsed_ms": elapsed_ms
        }
        
        return issues, trace
    
    def _calculate_original_position(self, masked_pos: int, spans: List[Dict]) -> int:
        """Calculate original text position from masked position"""
        original_pos = masked_pos
        
        for span in spans:
            if span["start"] <= original_pos < span["end"]:
                # Position is within a span, adjust
                original_pos = span["start"]
                break
            elif span["end"] <= original_pos:
                # Position is after a span, adjust for span length difference
                span_length = span["end"] - span["start"]
                span_key_length = len(span["key"])
                original_pos += span_length - span_key_length
        
        return original_pos
    
    def get_available_languages(self) -> Tuple[List[str], Dict[str, str]]:
        """Get list of available languages and aliases (legacy method)"""
        supported = self.list_supported_langs()
        all_langs = supported["full"] + supported["basic"]
        aliases = self.config.get("aliases", {})
        return all_langs, aliases
    
    def _discover_hunspell_dirs(self) -> List[str]:
        """Discover Hunspell dictionary directories from system paths and config"""
        paths = []
        
        # Add paths from config
        config_paths = self.config.get("hunspell_paths", [])
        paths.extend(config_paths)
        
        # Add common system paths
        common_paths = [
            "/usr/share/hunspell",
            "/usr/local/share/hunspell",
            "/Library/Spelling",
            "/opt/homebrew/share/hunspell"
        ]
        
        for path in common_paths:
            if path not in paths and os.path.exists(path):
                paths.append(path)
        
        return paths
    
    def list_supported_langs(self) -> Dict[str, List[str]]:
        """List languages by support level: full (Hunspell), basic (pyspell), unsupported"""
        full = []      # Hunspell dictionaries found
        basic = []     # pyspellchecker available
        unsupported = []  # neither available
        
        # Check Hunspell dictionaries
        for path in self.hunspell_paths:
            if os.path.exists(path):
                try:
                    for file in os.listdir(path):
                        if file.endswith('.aff'):
                            lang_code = file[:-4]  # Remove .aff
                            dic_file = os.path.join(path, f"{lang_code}.dic")
                            if os.path.exists(dic_file):
                                if lang_code not in full:
                                    full.append(lang_code)
                except (OSError, PermissionError):
                    continue
        
        # Check pyspellchecker languages
        try:
            from spellchecker import SpellChecker
            pyspell_langs = ["en", "de", "es", "fr", "it", "pt", "nl", "pl"]
            for lang in pyspell_langs:
                if lang not in full:  # Don't duplicate
                    basic.append(lang)
        except ImportError:
            pass
        
        # Determine unsupported languages (example: CJK languages)
        cjk_langs = ["ja", "ko", "zh", "th", "vi", "ar", "he"]
        for lang in cjk_langs:
            if lang not in full and lang not in basic:
                unsupported.append(lang)
        
        return {
            "full": sorted(full),
            "basic": sorted(basic),
            "unsupported": sorted(unsupported)
        }
