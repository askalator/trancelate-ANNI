import re
import json
import os
from typing import Dict, Any, List, Tuple

class TerminologyStage:
    name = "terminology"
    
    def __init__(self):
        self.config_path = "config/terminology.json"
        self.last_mtime = 0
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load terminology configuration with hot-reload support"""
        try:
            if os.path.exists(self.config_path):
                current_mtime = os.path.getmtime(self.config_path)
                if current_mtime > self.last_mtime:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        self.config = json.load(f)
                    self.last_mtime = current_mtime
        except Exception:
            self.config = {}
        return self.config
    
    def _get_target_lang(self, target: str) -> str:
        """Extract primary language subtag (e.g., 'de-DE' -> 'de')"""
        return target.split('-')[0].lower()
    
    def _create_masks(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """Mask protected spans and return masked text with mask info"""
        masks = []
        masked_text = text
        
        # Simple masking approach - replace one by one
        # Start with the most specific patterns
        patterns = [
            (r'\{\{[^}]*\}\}', 'PLACEHOLDER'),  # {{...}}
            (r'\{[^}]*\}', 'TOKEN'),            # {token}
            (r'<[^>]+>', 'HTML'),              # HTML tags
            (r'https?://[^\s]+', 'URL'),        # URLs
            (r'[\u2600-\u27BF\uFE0F\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF]', 'EMOJI'),  # Emojis
            (r'\b\d+\b', 'NUMBER')              # Numbers
        ]
        
        mask_id = 0
        for pattern, mask_type in patterns:
            # Find all matches for this pattern
            matches = list(re.finditer(pattern, text))
            # Process matches in reverse order to avoid position shifts
            for match in reversed(matches):
                mask_key = f"__MASK_{mask_type}_{mask_id}__"
                masks.append((mask_key, match.group(0)))
                # Replace in masked_text
                masked_text = masked_text[:match.start()] + mask_key + masked_text[match.end():]
                mask_id += 1
        
        return masked_text, masks
    
    def _restore_masks(self, text: str, masks: List[Tuple[str, str]]) -> str:
        """Restore masked content"""
        for mask_key, original in masks:
            text = text.replace(mask_key, original)
        return text
    
    def _apply_preferred_terms(self, text: str, target_lang: str) -> str:
        """Apply preferred terminology replacements"""
        if not self.config.get('default', {}).get('prefer'):
            return text
        
        prefer_config = self.config['default']['prefer'].get(target_lang, {})
        if not prefer_config:
            return text
        
        enforce_mode = self.config.get('default', {}).get('enforce', 'soft')
        
        for old_term, new_term in prefer_config.items():
            if enforce_mode == 'hard':
                # Hard mode: also match simple plurals
                pattern = rf'\b{re.escape(old_term)}(?:s|es)?\b'
                text = re.sub(pattern, new_term, text, flags=re.IGNORECASE)
            else:
                # Soft mode: exact match only
                pattern = rf'\b{re.escape(old_term)}\b'
                text = re.sub(pattern, new_term, text, flags=re.IGNORECASE)
        
        return text
    
    def _check_forbidden_terms(self, text: str, target_lang: str) -> List[str]:
        """Check for forbidden terms and return reasons"""
        reasons = []
        if not self.config.get('default', {}).get('forbid'):
            return reasons
        
        forbid_list = self.config['default']['forbid'].get(target_lang, [])
        if not forbid_list:
            return reasons
        
        for term in forbid_list:
            if re.search(rf'\b{re.escape(term)}\b', text, re.IGNORECASE):
                reasons.append(f"forbidden_term:{term}")
        
        return reasons
    
    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Run terminology stage"""
        # Hot-reload config
        self._load_config()
        
        source = ctx.get('source', 'en')
        target = ctx.get('target', 'en')
        
        # Use baseline text if available, otherwise use current text
        text = ctx.get('baseline', ctx.get('text', ''))
        
        if not text:
            return ctx
        
        target_lang = self._get_target_lang(target)
        
        # Create masks for protected content
        masked_text, masks = self._create_masks(text)
        
        # Apply preferred terminology
        processed_text = self._apply_preferred_terms(masked_text, target_lang)
        
        # Check for forbidden terms
        forbidden_reasons = self._check_forbidden_terms(processed_text, target_lang)
        
        # Restore masks
        final_text = self._restore_masks(processed_text, masks)
        
        # Update context - store processed text separately
        ctx['terminology_processed'] = final_text
        
        # Also update the main text field for compatibility
        ctx['text'] = final_text
        
        if forbidden_reasons:
            if 'degrade_reasons' not in ctx:
                ctx['degrade_reasons'] = []
            ctx['degrade_reasons'].extend(forbidden_reasons)
        
        return ctx
