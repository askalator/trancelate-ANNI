#!/usr/bin/env python3
"""
Version bump script for ANNI.
Bumps major|minor|patch version and updates CHANGELOG.md.
"""

import sys
import re
from datetime import datetime
from pathlib import Path

def read_version() -> str:
    """Read current version from VERSION file"""
    version_file = Path("VERSION")
    if version_file.exists():
        with open(version_file, 'r') as f:
            return f.read().strip()
    else:
        return "0.0.0"

def write_version(version: str):
    """Write version to VERSION file"""
    version_file = Path("VERSION")
    with open(version_file, 'w') as f:
        f.write(version + '\n')

def bump_version(current_version: str, bump_type: str) -> str:
    """Bump version according to semantic versioning"""
    parts = current_version.split('.')
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {current_version}")
    
    major, minor, patch = map(int, parts)
    
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")
    
    return f"{major}.{minor}.{patch}"

def update_changelog(new_version: str, description: str):
    """Update CHANGELOG.md with new version"""
    changelog_file = Path("CHANGELOG.md")
    
    if not changelog_file.exists():
        print("Warning: CHANGELOG.md not found, creating new file")
        return
    
    with open(changelog_file, 'r') as f:
        content = f.read()
    
    # Get current date in ISO format
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Find the [Unreleased] section
    unreleased_pattern = r'## \[Unreleased\]\n\n(.*?)(?=\n## \[|\Z)'
    match = re.search(unreleased_pattern, content, re.DOTALL)
    
    if match:
        unreleased_content = match.group(1).strip()
        
        # Create new version section
        new_section = f"## [{new_version}] - {today}\n\n{unreleased_content}\n\n"
        
        # Replace [Unreleased] with new version section
        new_content = re.sub(
            r'## \[Unreleased\]\n\n.*?(?=\n## \[|\Z)',
            f"## [Unreleased]\n\n### Added\n- \n\n### Changed\n- \n\n### Fixed\n- \n\n{new_section}",
            content,
            flags=re.DOTALL
        )
        
        # Write updated content
        with open(changelog_file, 'w') as f:
            f.write(new_content)
    else:
        print("Warning: Could not find [Unreleased] section in CHANGELOG.md")

def main():
    """Main function"""
    if len(sys.argv) != 3:
        print("Usage: python scripts/bump_version.py <major|minor|patch> \"description\"")
        sys.exit(1)
    
    bump_type = sys.argv[1]
    description = sys.argv[2]
    
    if bump_type not in ["major", "minor", "patch"]:
        print("Error: bump_type must be major, minor, or patch")
        sys.exit(1)
    
    try:
        # Read current version
        current_version = read_version()
        print(f"Current version: {current_version}")
        
        # Bump version
        new_version = bump_version(current_version, bump_type)
        print(f"New version: {new_version}")
        
        # Write new version
        write_version(new_version)
        print(f"Updated VERSION file")
        
        # Update changelog
        update_changelog(new_version, description)
        print(f"Updated CHANGELOG.md")
        
        print(f"✅ Version bumped from {current_version} to {new_version}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
