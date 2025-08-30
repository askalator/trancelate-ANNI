"""
TranceCreate Pipeline Infrastructure
Modular, configurable pipeline system with hot-reload capability
"""

from typing import Dict, Any, List, Protocol, Tuple
import json
import os
import time
from pathlib import Path


class Ctx(Dict[str, Any]):
    """Pipeline context - holds all data passed between stages"""
    pass


class Stage(Protocol):
    """Stage protocol - all stages must implement this interface"""
    name: str
    
    def run(self, ctx: Ctx) -> Ctx:
        """Execute stage logic and return updated context"""
        ...


class Pipeline:
    """Pipeline manager with hot-reload capability"""
    
    def __init__(self, config_path: str = "config/tc_pipeline.json"):
        self.config_path = config_path
        self.stages: List[Stage] = []
        self.last_mtime = 0
        self.stage_registry: Dict[str, type] = {}
        self._load_pipeline()
    
    def register_stage(self, stage_class: type):
        """Register a stage class in the registry"""
        if hasattr(stage_class, 'name'):
            self.stage_registry[stage_class.name] = stage_class
    
    def _load_pipeline(self):
        """Load pipeline configuration from JSON file"""
        try:
            if os.path.exists(self.config_path):
                mtime = os.path.getmtime(self.config_path)
                if mtime > self.last_mtime:
                    with open(self.config_path, 'r') as f:
                        config = json.load(f)
                    self.last_mtime = mtime
                    self._build_pipeline(config.get('stages', []))
            else:
                # Default pipeline if file doesn't exist
                default_stages = ["tc_core", "post_profile", "policy_check", "degrade"]
                self._build_pipeline(default_stages)
        except Exception as e:
            print(f"Warning: Failed to load pipeline config: {e}")
            # Fallback to default
            default_stages = ["tc_core", "post_profile", "policy_check", "degrade"]
            self._build_pipeline(default_stages)
    
    def _build_pipeline(self, stage_names: List[str]):
        """Build pipeline from stage names"""
        self.stages = []
        for name in stage_names:
            if name in self.stage_registry:
                stage_class = self.stage_registry[name]
                self.stages.append(stage_class())
            else:
                print(f"Warning: Unknown stage '{name}' - skipping")
    
    def check_reload(self):
        """Check if pipeline config has changed and reload if needed"""
        try:
            if os.path.exists(self.config_path):
                mtime = os.path.getmtime(self.config_path)
                if mtime > self.last_mtime:
                    print(f"Pipeline config changed, reloading...")
                    self._load_pipeline()
                    return True
        except Exception as e:
            print(f"Error checking pipeline reload: {e}")
        return False
    
    def run(self, ctx: Ctx) -> Ctx:
        """Execute pipeline with given context"""
        # Check for hot-reload before running
        self.check_reload()
        
        # Run each stage in sequence
        for stage in self.stages:
            try:
                ctx = stage.run(ctx)
            except Exception as e:
                print(f"Error in stage {stage.name}: {e}")
                # Add error to degrade reasons
                if 'degrade_reasons' not in ctx:
                    ctx['degrade_reasons'] = []
                ctx['degrade_reasons'].append(f"stage_error:{stage.name}:{str(e)}")
        
        return ctx
    
    def get_config(self) -> Dict[str, Any]:
        """Get current pipeline configuration"""
        return {
            "stages": [{"name": stage.name} for stage in self.stages],
            "mtime": int(self.last_mtime)
        }
    
    def update_config(self, stages: List[str]) -> bool:
        """Update pipeline configuration"""
        try:
            # Validate stage names
            unknown_stages = [s for s in stages if s not in self.stage_registry]
            if unknown_stages:
                raise ValueError(f"Unknown stages: {unknown_stages}")
            
            # Save to file
            config = {"stages": stages}
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Reload pipeline
            self._load_pipeline()
            return True
        except Exception as e:
            print(f"Error updating pipeline config: {e}")
            return False
