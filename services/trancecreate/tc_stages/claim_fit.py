import re
import json
import os
from typing import Dict, Any, List, Tuple, Optional
from tc_pipeline import Ctx, Stage

class ClaimFitStage(Stage):
    """Claim fit stage - automatically shortens UI text to match source length"""
    name = "claim_fit"
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load claim fit configuration"""
        try:
            with open('config/claim_fit.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                "default": {
                    "units": "graphemes",
                    "fit_to_source": True,
                    "ratio": 1.0,
                    "ellipsis": False,
                    "max_iterations": 3,
                    "breakpoints": ["\\s+", "\\u2009", "\\u200A", "-", "–", "—", "/", "·", ":", ";", ","],
                    "drop_parentheticals": True,
                    "drop_trailing_fragments": True
                }
            }
    
    def _detect_ui_elements(self, text: str) -> List[Dict[str, Any]]:
        """Detect UI elements in text"""
        elements = []
        
        # Button elements
        button_pattern = r'<button[^>]*>(.*?)</button>'
        for match in re.finditer(button_pattern, text, re.DOTALL):
            elements.append({
                "type": "button",
                "start": match.start(),
                "end": match.end(),
                "content": match.group(1),
                "full_match": match.group(0)
            })
        
        # CTA links
        cta_pattern = r'<a[^>]*(?:role="button"|class="[^"]*(?:btn|button|cta)[^"]*")[^>]*>(.*?)</a>'
        for match in re.finditer(cta_pattern, text, re.DOTALL):
            elements.append({
                "type": "cta",
                "start": match.start(),
                "end": match.end(),
                "content": match.group(1),
                "full_match": match.group(0)
            })
        
        # Input values
        input_pattern = r'<input[^>]*type="(?:submit|button)"[^>]*\bvalue="([^"]*)"'
        for match in re.finditer(input_pattern, text):
            elements.append({
                "type": "input_value",
                "start": match.start(),
                "end": match.end(),
                "content": match.group(1),
                "full_match": match.group(0)
            })
        
        # Placeholders
        placeholder_pattern = r'\bplaceholder="([^"]*)"'
        for match in re.finditer(placeholder_pattern, text):
            elements.append({
                "type": "placeholder",
                "start": match.start(),
                "end": match.end(),
                "content": match.group(1),
                "full_match": match.group(0)
            })
        
        # Aria labels
        aria_pattern = r'\baria-label="([^"]*)"'
        for match in re.finditer(aria_pattern, text):
            elements.append({
                "type": "aria_label",
                "start": match.start(),
                "end": match.end(),
                "content": match.group(1),
                "full_match": match.group(0)
            })
        
        # Labels
        label_pattern = r'<label[^>]*>(.*?)</label>'
        for match in re.finditer(label_pattern, text, re.DOTALL):
            elements.append({
                "type": "label",
                "start": match.start(),
                "end": match.end(),
                "content": match.group(1),
                "full_match": match.group(0)
            })
        
        return elements
    
    def _create_masks(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """Mask protected spans"""
        masks = []
        masked_text = text
        
        # Simple masking approach - replace one by one
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
            matches = list(re.finditer(pattern, text))
            for match in reversed(matches):  # Process matches in reverse order to avoid position shifts
                mask_key = f"__MASK_{mask_type}_{mask_id}__"
                masks.append((mask_key, match.group(0)))
                masked_text = masked_text[:match.start()] + mask_key + masked_text[match.end():]
                mask_id += 1
        
        return masked_text, masks
    
    def _restore_masks(self, text: str, masks: List[Tuple[str, str]]) -> str:
        """Restore masked content"""
        for mask_key, original in masks:
            text = text.replace(mask_key, original)
        return text
    
    def _measure_visible_length(self, text: str, units: str = "graphemes") -> int:
        """Measure visible length of text"""
        if units == "graphemes":
            try:
                # Use regex to find graphemes
                graphemes = re.findall(r'\X', text)
                return len(graphemes)
            except:
                # Fallback to NFC length
                import unicodedata
                return len(unicodedata.normalize('NFC', text))
        else:
            return len(text)
    
    def _shorten_text(self, text: str, budget: int, config: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Shorten text to fit budget"""
        steps = []
        current_text = text
        max_iterations = config.get("max_iterations", 3)
        
        for iteration in range(max_iterations):
            current_len = self._measure_visible_length(current_text, config.get("units", "graphemes"))
            if current_len <= budget:
                break
            
            steps.append(f"iteration_{iteration+1}: {current_len} -> target {budget}")
            
            # Step 1: Whitespace squeeze
            if current_len > budget:
                old_text = current_text
                current_text = re.sub(r'\s+', ' ', current_text)
                if current_text != old_text:
                    steps.append("whitespace_squeeze")
            
            current_len = self._measure_visible_length(current_text, config.get("units", "graphemes"))
            if current_len <= budget:
                break
            
            # Step 2: Drop parentheticals (right to left)
            if config.get("drop_parentheticals", True) and current_len > budget:
                old_text = current_text
                # Remove (...), [...], {...} content
                current_text = re.sub(r'\([^)]*\)', '', current_text)
                current_text = re.sub(r'\[[^\]]*\]', '', current_text)
                current_text = re.sub(r'\{[^}]*\}', '', current_text)
                if current_text != old_text:
                    steps.append("drop_parentheticals")
            
            current_len = self._measure_visible_length(current_text, config.get("units", "graphemes"))
            if current_len <= budget:
                break
            
            # Step 3: Drop trailing fragments
            if config.get("drop_trailing_fragments", True) and current_len > budget:
                old_text = current_text
                # Find last strong separator
                strong_separators = ["—", "–", ":", ";"]
                for sep in strong_separators:
                    if sep in current_text:
                        parts = current_text.split(sep)
                        if len(parts) > 1:
                            current_text = sep.join(parts[:-1]) + sep
                            break
                if current_text != old_text:
                    steps.append("drop_trailing_fragments")
            
            current_len = self._measure_visible_length(current_text, config.get("units", "graphemes"))
            if current_len <= budget:
                break
            
            # Step 4: Cut to budget at breakpoints
            if current_len > budget:
                old_text = current_text
                breakpoints = config.get("breakpoints", ["\\s+", "-", "–", "—", "/", "·", ":", ";", ","])
                
                # Find the best breakpoint
                best_cut = budget
                for bp in breakpoints:
                    if bp == "\\s+":
                        # Find last space before budget
                        for i in range(min(budget, len(current_text))):
                            if current_text[budget - i - 1].isspace():
                                best_cut = budget - i
                                break
                    else:
                        # Find last occurrence of breakpoint before budget
                        pos = current_text.rfind(bp, 0, budget)
                        if pos > 0:
                            best_cut = pos
                
                if best_cut < len(current_text):
                    current_text = current_text[:best_cut]
                    steps.append(f"cut_at_breakpoint:{best_cut}")
            
            current_len = self._measure_visible_length(current_text, config.get("units", "graphemes"))
            if current_len <= budget:
                break
        
        # Final hard cut if still too long
        if self._measure_visible_length(current_text, config.get("units", "graphemes")) > budget:
            if config.get("units", "graphemes") == "graphemes":
                graphemes = re.findall(r'\X', current_text)
                current_text = ''.join(graphemes[:budget])
            else:
                current_text = current_text[:budget]
            steps.append("hard_cut")
        
        return current_text, steps
    
    def run(self, ctx: Ctx) -> Ctx:
        """Run claim fit stage"""
        src_html = ctx.get("original_text") or ""
        # prefer the true candidate; fall back to current text
        tgt_html_in = ctx.get("tc_candidate_text") or ctx.get("text") or ""
        
        if not src_html or not tgt_html_in:
            return ctx
        
        config = self.config.get("default", {})
        
        # Detect UI elements in source and target
        source_elements = self._detect_ui_elements(src_html)
        target_elements = self._detect_ui_elements(tgt_html_in)
        
        # Initialize trace
        ctx.setdefault("trace", {}).setdefault("claim_fit", [])
        
        # Process each target element
        for i, target_elem in enumerate(target_elements):
            # Find corresponding source element
            source_elem = None
            for src_elem in source_elements:
                if src_elem["type"] == target_elem["type"]:
                    source_elem = src_elem
                    break
            
            if not source_elem:
                # No corresponding source element - add trace entry with modified=false
                entry = {
                    "type": target_elem["type"], "index": i,
                    "src_len": 0, "tgt_len_before": 0,
                    "tgt_len_after": 0, "budget": 0,
                    "units": config.get("units", "graphemes"), "steps": [], "modified": False
                }
                ctx["trace"]["claim_fit"].append(entry)
                continue
            
            # Mask protected content
            masked_source_content, source_masks = self._create_masks(source_elem["content"])
            masked_target_content, target_masks = self._create_masks(target_elem["content"])
            
            # Measure visible lengths
            src_len = self._measure_visible_length(masked_source_content, config.get("units", "graphemes"))
            tb = self._measure_visible_length(masked_target_content, config.get("units", "graphemes"))
            
            # Calculate budget
            ratio = config.get("ratio", 1.0)
            budget = int(src_len * ratio)
            
            # Shorten target content if needed
            if tb > budget:
                shortened_masked, steps = self._shorten_text(masked_target_content, budget, config)
                shortened_content = self._restore_masks(shortened_masked, target_masks)
                
                # Replace in target text
                tgt_html_in = tgt_html_in[:target_elem["start"]] + target_elem["full_match"].replace(target_elem["content"], shortened_content) + tgt_html_in[target_elem["end"]:]
                
                # Update trace
                ta = self._measure_visible_length(shortened_masked, config.get("units", "graphemes"))
            else:
                steps = []
                ta = tb
            
            # Trace always fill (even if no shortening occurred)
            entry = {
                "type": target_elem["type"], "index": i,
                "src_len": src_len, "tgt_len_before": tb,
                "tgt_len_after": ta, "budget": budget,
                "units": config.get("units", "graphemes"), "steps": steps, "modified": (ta != tb)
            }
            ctx.setdefault("trace", {}).setdefault("claim_fit", []).append(entry)
        
        # Update context
        ctx["text"] = tgt_html_in
        
        # Änderungsrate gegen Original erfassen (für spätere Policies/Diagnose)
        from tc_pipeline import compute_char_ratio
        ratio = compute_char_ratio(ctx.get("original_text",""), ctx.get("text",""))
        ctx.setdefault("trace", {})["claim_fit_ratio_vs_original"] = ratio
        
        return ctx
