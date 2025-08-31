#!/usr/bin/env python3
"""
Release Gatekeeper for ANNI.
Automated validation before release.
"""

import sys
import json
import subprocess
import urllib.request
import urllib.parse
import os
from pathlib import Path
from typing import Dict, List, Tuple

def check_git_status() -> bool:
    """Check if working tree is clean"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            if result.stdout.strip():
                print(f"❌ Working tree not clean:\n{result.stdout}")
                return False
            else:
                print("✅ Working tree clean")
                return True
        else:
            print(f"❌ Git status failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Git status error: {e}")
        return False

def get_version_info() -> Tuple[str, str]:
    """Get version and commit hash"""
    try:
        # Read VERSION file
        version_file = Path("VERSION")
        if not version_file.exists():
            print("❌ VERSION file not found")
            return None, None
        
        with open(version_file, 'r') as f:
            version = f.read().strip()
        
        # Get git commit
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            commit = result.stdout.strip()
        else:
            commit = "unknown"
        
        print(f"✅ Version: {version}, Commit: {commit}")
        return version, commit
    except Exception as e:
        print(f"❌ Version info error: {e}")
        return None, None

def load_port_config() -> Dict[str, int]:
    """Load port configuration"""
    try:
        config_file = Path("config/ports.json")
        if not config_file.exists():
            print("❌ config/ports.json not found")
            return {}
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        return config
    except Exception as e:
        print(f"❌ Port config error: {e}")
        return {}

def check_service_health(service_name: str, port: int, endpoint: str, expected_fields: List[str]) -> bool:
    """Check service health and version consistency"""
    try:
        url = f"http://127.0.0.1:{port}{endpoint}"
        req = urllib.request.Request(url)
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode())
                
                # Check required fields
                missing_fields = []
                for field in expected_fields:
                    if field not in data:
                        missing_fields.append(field)
                
                if missing_fields:
                    print(f"❌ {service_name} missing fields: {missing_fields}")
                    return False
                
                print(f"✅ {service_name} {endpoint} OK")
                return True
            else:
                print(f"❌ {service_name} {endpoint} HTTP {response.getcode()}")
                return False
    except Exception as e:
        print(f"❌ {service_name} {endpoint} error: {e}")
        return False

def check_services_version_consistency(version: str, commit: str, ports: Dict[str, int]) -> bool:
    """Check all services for version consistency"""
    print("\n🔍 Checking service version consistency...")
    
    service_checks = {
        "guard": ("/meta", ["version", "commit"]),
        "worker": ("/health", ["version", "commit"]),
        "trancecreate": ("/health", ["version", "commit"]),
        "trancespell": ("/health", ["version", "commit"])
    }
    
    results = {}
    all_ok = True
    
    for service_name, (endpoint, expected_fields) in service_checks.items():
        if service_name in ports:
            port = ports[service_name]
            ok = check_service_health(service_name, port, endpoint, expected_fields)
            results[service_name] = ok
            all_ok = all_ok and ok
        else:
            print(f"❌ {service_name} port not configured")
            results[service_name] = False
            all_ok = False
    
    return all_ok, results

def run_smoke_tests() -> Tuple[bool, Dict[str, bool]]:
    """Run all smoke tests"""
    print("\n🧪 Running smoke tests...")
    
    smoke_scripts = [
        ("stack", "scripts/smoke_stack.py"),
        ("claim_guard", "scripts/smoke_tc_claim_guard.py"),
        ("trancespell", "scripts/smoke_trancespell.py")
    ]
    
    results = {}
    all_ok = True
    
    for test_name, script_path in smoke_scripts:
        try:
            if not Path(script_path).exists():
                print(f"❌ Smoke test {test_name} not found: {script_path}")
                results[test_name] = False
                all_ok = False
                continue
            
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"✅ Smoke test {test_name} OK")
                results[test_name] = True
            else:
                print(f"❌ Smoke test {test_name} FAILED:")
                print(f"   stdout: {result.stdout}")
                print(f"   stderr: {result.stderr}")
                results[test_name] = False
                all_ok = False
                
        except subprocess.TimeoutExpired:
            print(f"❌ Smoke test {test_name} TIMEOUT")
            results[test_name] = False
            all_ok = False
        except Exception as e:
            print(f"❌ Smoke test {test_name} error: {e}")
            results[test_name] = False
            all_ok = False
    
    return all_ok, results

def check_large_files() -> bool:
    """Check for files larger than 50MB in git tracking"""
    print("\n📁 Checking for large files...")
    
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ Git ls-files failed: {result.stderr}")
            return False
        
        large_files = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                file_path = Path(line.strip())
                if file_path.exists():
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    if size_mb > 50:
                        large_files.append((line.strip(), size_mb))
        
        if large_files:
            print("❌ Large files found (>50MB):")
            for file_path, size_mb in large_files:
                print(f"   {file_path}: {size_mb:.1f}MB")
            return False
        else:
            print("✅ No large files found")
            return True
            
    except Exception as e:
        print(f"❌ Large files check error: {e}")
        return False

def print_release_notes() -> bool:
    """Print release notes stub from CHANGELOG Unreleased section"""
    print("\n📝 Release Notes Stub:")
    print("=" * 50)
    
    try:
        changelog_file = Path("CHANGELOG.md")
        if not changelog_file.exists():
            print("❌ CHANGELOG.md not found")
            return False
        
        with open(changelog_file, 'r') as f:
            content = f.read()
        
        # Find Unreleased section
        import re
        unreleased_pattern = r'## \[Unreleased\]\n\n(.*?)(?=\n## \[|\Z)'
        match = re.search(unreleased_pattern, content, re.DOTALL)
        
        if match:
            unreleased_content = match.group(1).strip()
            if unreleased_content:
                print(unreleased_content)
                return True
            else:
                print("(No changes in Unreleased section)")
                return True
        else:
            print("❌ Unreleased section not found in CHANGELOG.md")
            return False
            
    except Exception as e:
        print(f"❌ Release notes error: {e}")
        return False

def main():
    """Main release gate function"""
    print("🚪 ANNI Release Gate")
    print("=" * 50)
    
    # Check git status
    if not check_git_status():
        sys.exit(1)
    
    # Get version info
    version, commit = get_version_info()
    if not version or not commit:
        sys.exit(1)
    
    # Load port configuration
    ports = load_port_config()
    if not ports:
        sys.exit(1)
    
    # Check service version consistency
    services_ok, service_results = check_services_version_consistency(version, commit, ports)
    if not services_ok:
        sys.exit(1)
    
    # Run smoke tests
    smokes_ok, smoke_results = run_smoke_tests()
    if not smokes_ok:
        sys.exit(1)
    
    # Check for large files
    if not check_large_files():
        sys.exit(1)
    
    # Print release notes
    print_release_notes()
    
    # Summary
    print("\n" + "=" * 50)
    print("RELEASE-GATE OK")
    print(f"version={version}")
    print(f"commit={commit}")
    
    service_status = []
    for service, ok in service_results.items():
        status = "ok" if ok else "fail"
        service_status.append(f"{service} {status}")
    
    smoke_status = []
    for test, ok in smoke_results.items():
        status = "ok" if ok else "fail"
        smoke_status.append(f"{test} {status}")
    
    print(f"services=[{', '.join(service_status)}]")
    print(f"smokes=[{', '.join(smoke_status)}]")
    
    print("\n🎉 Release gate passed! Ready for release.")

if __name__ == "__main__":
    main()
