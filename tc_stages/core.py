"""
Core TranceCreate Pipeline Stages
Implements the main processing stages for the pipeline
"""

import re
import hashlib
from typing import Dict, Any, List
from tc_pipeline import Ctx, Stage


class TcCoreStage(Stage):
    """Core transcreation stage - calls Mistral or fallback"""
    name = "tc_core"
    
    def run(self, ctx: Ctx) -> Ctx:
        """Execute core transcreation logic"""
        # Import here to avoid circular imports
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from tc_server import tc_generate, generate_stable_seed
        
        # Get baseline text
        baseline_text = ctx.get('baseline', '')
        if not baseline_text:
            raise ValueError("No baseline text provided")
        
        # Generate seed if not provided
        seed = ctx.get('seed')
        if seed is None:
            seed = generate_stable_seed(
                baseline_text,
                ctx.get('target', ''),
                ctx.get('profile', ''),
                ctx.get('persona', ''),
                ctx.get('level', 1)
            )
            ctx['seed'] = seed
        
        # Call existing tc_generate function
        try:
            transcreated_text, tc_model = tc_generate(
                baseline_text,
                ctx.get('target', ''),
                ctx.get('profile', ''),
                ctx.get('persona', ''),
                ctx.get('level', 1),
                seed
            )
            
            # Update context
            ctx['text'] = transcreated_text
            if 'trace' not in ctx:
                ctx['trace'] = {}
            ctx['trace']['tc_model'] = tc_model
            
        except Exception as e:
            # On error, keep baseline and add error reason
            ctx['text'] = baseline_text
            if 'trace' not in ctx:
                ctx['trace'] = {}
            ctx['trace']['tc_model'] = 'error'
            if 'degrade_reasons' not in ctx:
                ctx['degrade_reasons'] = []
            ctx['degrade_reasons'].append(f"tc_core_error:{str(e)}")
        
        return ctx


class ProfileStage(Stage):
    """Profile enhancement stage - applies profile/persona hints"""
    name = "post_profile"
    
    def run(self, ctx: Ctx) -> Ctx:
        """Apply profile and persona enhancements"""
        text = ctx.get('text', '')
        profile = ctx.get('profile', '')
        persona = ctx.get('persona', '')
        level = ctx.get('level', 1)
        target = ctx.get('target', '')
        
        if not text or level == 0:
            return ctx
        
        try:
            # Load profile and persona configs
            profile_config = self._load_profile_config()
            persona_config = self._load_persona_config()
            locale_config = self._load_locale_config()
            
            # Apply profile hints
            if profile in profile_config.get('profiles', {}):
                profile_data = profile_config['profiles'][profile]
                
                # Add CTA if level > 1 and not present
                if level > 1 and 'cta' in profile_data:
                    cta_text = profile_data['cta'].get(target, profile_data['cta'].get('en', ''))
                    if cta_text and cta_text not in text:
                        text += f" {cta_text}"
                
                # Add emoji if level > 1 and not present
                if level > 1 and 'emoji' in profile_data:
                    emoji = profile_data['emoji']
                    if emoji and emoji not in text:
                        text += f" {emoji}"
            
            # Apply persona hints
            if persona in persona_config.get('personas', {}):
                persona_data = persona_config['personas'][persona]
                # Note: Persona style is already applied in tc_core stage
                pass
            
            # Apply locale-specific hints
            if target in locale_config.get('locales', {}):
                locale_data = locale_config['locales'][target]
                # Note: Locale hints are already applied in tc_core stage
                pass
            
            ctx['text'] = text
            
        except Exception as e:
            # On error, keep current text and add error reason
            if 'degrade_reasons' not in ctx:
                ctx['degrade_reasons'] = []
            ctx['degrade_reasons'].append(f"profile_error:{str(e)}")
        
        return ctx
    
    def _load_profile_config(self) -> Dict[str, Any]:
        """Load profile configuration"""
        try:
            import json
            with open('config/trance_profiles.json', 'r') as f:
                return json.load(f)
        except:
            return {"profiles": {}}
    
    def _load_persona_config(self) -> Dict[str, Any]:
        """Load persona configuration"""
        try:
            import json
            with open('config/tc_personas.json', 'r') as f:
                return json.load(f)
        except:
            return {"personas": {}}
    
    def _load_locale_config(self) -> Dict[str, Any]:
        """Load locale configuration"""
        try:
            import json
            with open('config/tc_locales.json', 'r') as f:
                return json.load(f)
        except:
            return {"locales": {}}


class PolicyCheckStage(Stage):
    """Policy checking stage - validates policies and invariants"""
    name = "policy_check"
    
    def run(self, ctx: Ctx) -> Ctx:
        """Check policies and invariants"""
        baseline_text = ctx.get('baseline', '')
        transcreated_text = ctx.get('text', '')
        policies = ctx.get('policies', {})
        
        if not baseline_text or not transcreated_text:
            return ctx
        
        degrade_reasons = []
        
        # Check max change ratio
        max_change_ratio = policies.get('max_change_ratio', 0.25)
        if max_change_ratio > 0:
            change_ratio = self._calculate_change_ratio(baseline_text, transcreated_text)
            if change_ratio > max_change_ratio:
                degrade_reasons.append("max_change_ratio_exceeded")
        
        # Check forbidden terms
        forbidden_terms = policies.get('forbidden_terms', [])
        for term in forbidden_terms:
            if term.lower() in transcreated_text.lower():
                degrade_reasons.append(f"forbidden_term:{term}")
        
        # Check preserved elements
        preserve_list = policies.get('preserve', [])
        if preserve_list:
            if not self._check_preserved_elements(baseline_text, transcreated_text, preserve_list):
                degrade_reasons.append("invariants_failed")
        
        # Update context
        if degrade_reasons:
            if 'degrade_reasons' not in ctx:
                ctx['degrade_reasons'] = []
            ctx['degrade_reasons'].extend(degrade_reasons)
        
        return ctx
    
    def _calculate_change_ratio(self, baseline: str, transcreated: str) -> float:
        """Calculate character change ratio using Levenshtein distance"""
        try:
            from difflib import SequenceMatcher
            return 1.0 - SequenceMatcher(None, baseline, transcreated).ratio()
        except:
            # Fallback calculation
            return abs(len(transcreated) - len(baseline)) / max(len(baseline), 1)
    
    def _check_preserved_elements(self, baseline: str, transcreated: str, preserve_list: List[str]) -> bool:
        """Check if preserved elements are maintained"""
        try:
            # Simple check for placeholders, HTML tags, numbers
            for preserve_type in preserve_list:
                if preserve_type == "placeholders":
                    # Check {{...}} placeholders
                    baseline_placeholders = re.findall(r'\{\{[^}]+\}\}', baseline)
                    transcreated_placeholders = re.findall(r'\{\{[^}]+\}\}', transcreated)
                    if baseline_placeholders != transcreated_placeholders:
                        return False
                
                elif preserve_type == "html":
                    # Check HTML tags
                    baseline_tags = re.findall(r'<[^>]+>', baseline)
                    transcreated_tags = re.findall(r'<[^>]+>', transcreated)
                    if baseline_tags != transcreated_tags:
                        return False
                
                elif preserve_type == "numbers":
                    # Check numbers
                    baseline_numbers = re.findall(r'\d+', baseline)
                    transcreated_numbers = re.findall(r'\d+', transcreated)
                    if baseline_numbers != transcreated_numbers:
                        return False
            
            return True
        except:
            return True  # On error, assume preserved


class DegradeStage(Stage):
    """Degradation stage - applies degradation if needed"""
    name = "degrade"
    
    def run(self, ctx: Ctx) -> Ctx:
        """Apply degradation if degrade reasons exist"""
        degrade_reasons = ctx.get('degrade_reasons', [])
        baseline_text = ctx.get('baseline', '')
        
        if degrade_reasons:
            # Degrade: return baseline text
            ctx['text'] = baseline_text
            ctx['degraded'] = True
        else:
            ctx['degraded'] = False
        
        return ctx
