"""
Version helper for TranceLate services.
Reads VERSION file and git commit hash.
"""

import os
import subprocess
from pathlib import Path

def read_version() -> str:
    """
    Read version from root VERSION file.
    
    Returns:
        Version string (trimmed)
    """
    try:
        # Find root directory (where VERSION file is located)
        current_dir = Path(__file__).parent
        root_dir = current_dir.parent.parent  # libs/trance_common -> libs -> root
        version_file = root_dir / "VERSION"
        
        if version_file.exists():
            with open(version_file, 'r') as f:
                return f.read().strip()
        else:
            return "0.0.0"
    except Exception:
        return "0.0.0"

def git_commit_short() -> str:
    """
    Get short git commit hash.
    
    Returns:
        Short commit hash or "unknown" on error
    """
    try:
        # Find root directory
        current_dir = Path(__file__).parent
        root_dir = current_dir.parent.parent
        
        # Run git command
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return "unknown"
    except Exception:
        return "unknown"

def app_version() -> dict:
    """
    Get application version information.
    
    Returns:
        Dict with "version" and "commit" keys
    """
    return {
        "version": read_version(),
        "commit": git_commit_short()
    }
