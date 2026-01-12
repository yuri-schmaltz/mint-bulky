#!/usr/bin/env python3
"""
Bulky Diagnostic Tool
Captures baseline metrics and system information for performance analysis.
"""

import sys
import os
import subprocess
import platform
import json
from pathlib import Path
from datetime import datetime

def run_cmd(cmd, shell=True):
    """Run command and return stdout."""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def get_python_info():
    """Get Python version and environment."""
    return {
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "python_implementation": platform.python_implementation(),
    }

def get_system_info():
    """Get system information."""
    return {
        "os": platform.system(),
        "os_version": platform.release(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
    }

def get_dependencies():
    """Check for required and optional dependencies."""
    deps = {}
    required = ["gi", "unidecode", "setproctitle"]
    optional = ["pytest", "pylint"]
    
    for pkg in required:
        try:
            mod = __import__(pkg)
            deps[f"{pkg} (required)"] = getattr(mod, '__version__', 'installed')
        except ImportError:
            deps[f"{pkg} (required)"] = "MISSING"
    
    for pkg in optional:
        try:
            mod = __import__(pkg)
            deps[f"{pkg} (optional)"] = getattr(mod, '__version__', 'installed')
        except ImportError:
            deps[f"{pkg} (optional)"] = "not installed"
    
    return deps

def get_filesystem_info():
    """Get filesystem and cache information."""
    cwd = Path(".")
    
    info = {
        "project_size_mb": round(sum(f.stat().st_size for f in cwd.rglob("*") if f.is_file()) / 1024 / 1024, 2),
        "python_files": len(list(cwd.rglob("*.py"))),
        "test_files": len(list(cwd.rglob("test_*.py"))),
    }
    
    # Check for build artifacts
    pycache_size = sum(f.stat().st_size for f in cwd.rglob("__pycache__/*") if f.is_file())
    info["pycache_size_kb"] = round(pycache_size / 1024, 2)
    
    # Check git status
    git_status = run_cmd("git status --short")
    info["git_status"] = "clean" if not git_status else "dirty"
    info["git_commit"] = run_cmd("git rev-parse --short HEAD")
    
    return info

def check_syntax():
    """Check Python syntax."""
    result = run_cmd("python3 -m py_compile usr/lib/bulky/bulky.py")
    return "✓ OK" if not result else f"✗ Error: {result}"

def run_unit_tests():
    """Run unit tests."""
    result = run_cmd("python3 -m unittest discover -s tests -p 'test_*.py' -v 2>&1")
    # Count results
    if "OK" in result or "Ran" in result:
        lines = result.split('\n')
        for line in lines:
            if "Ran" in line:
                return line
    return "⚠ Tests not available"

def check_makefile():
    """Verify Makefile targets."""
    targets = ["test-syntax", "test", "lint", "clean"]
    available = []
    
    makefile = Path("Makefile")
    if makefile.exists():
        content = makefile.read_text()
        for target in targets:
            if f"{target}:" in content:
                available.append(target)
    
    return {"available_targets": available, "total": len(available)}

def main():
    """Run diagnostics and output report."""
    print("=" * 70)
    print("BULKY DIAGNOSTIC REPORT")
    print(f"Generated: {datetime.now().isoformat()}")
    print("=" * 70)
    print()
    
    # System Info
    print("### SYSTEM INFORMATION ###")
    sys_info = get_system_info()
    for key, value in sys_info.items():
        print(f"  {key:.<20} {value}")
    print()
    
    # Python Info
    print("### PYTHON ENVIRONMENT ###")
    py_info = get_python_info()
    for key, value in py_info.items():
        print(f"  {key:.<20} {value}")
    print()
    
    # Dependencies
    print("### DEPENDENCIES ###")
    deps = get_dependencies()
    for key, value in deps.items():
        status = "✓" if "MISSING" not in value else "✗"
        print(f"  {status} {key:.<35} {value}")
    print()
    
    # Filesystem
    print("### PROJECT STRUCTURE ###")
    fs_info = get_filesystem_info()
    for key, value in fs_info.items():
        print(f"  {key:.<30} {value}")
    print()
    
    # Code Quality
    print("### CODE QUALITY ###")
    print(f"  Syntax check:  {check_syntax()}")
    print(f"  Unit tests:    {run_unit_tests()}")
    makefile_info = check_makefile()
    print(f"  Makefile:      {makefile_info['total']}/{len(['test-syntax', 'test', 'lint', 'clean'])} targets available")
    print()
    
    # Performance Baseline (estimate)
    print("### PERFORMANCE BASELINE (ESTIMATED) ###")
    print(f"  Startup time:          ~1-2 seconds (GTK dependent)")
    print(f"  File addition (1 file): ~50-100ms (filesystem dependent)")
    print(f"  Idle memory:           ~50-80 MB (GTK loaded)")
    print(f"  Regex cache size:      32 patterns (functools.lru_cache)")
    print()
    
    # Recommendations
    print("### RECOMMENDATIONS ###")
    if fs_info["pycache_size_kb"] > 50:
        print(f"  ⚠ Large __pycache__ ({fs_info['pycache_size_kb']} KB) - run 'make clean'")
    
    if fs_info["git_status"] == "dirty":
        print("  ℹ Git status dirty - consider committing changes")
    
    if check_syntax() != "✓ OK":
        print("  ✗ Syntax errors found - fix before testing")
    
    deps_missing = [k for k, v in deps.items() if "MISSING" in v]
    if deps_missing:
        print(f"  ✗ Missing dependencies: {', '.join(deps_missing)}")
    
    print()
    print("=" * 70)
    print("END OF DIAGNOSTIC REPORT")
    print("=" * 70)

if __name__ == "__main__":
    main()
