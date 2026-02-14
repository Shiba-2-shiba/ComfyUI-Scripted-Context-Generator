# -*- coding: utf-8 -*-
"""
runner.py — PromptBuilder Verification Runner

Unified interface to run all verification scripts in the assets/ directory.
Supports running Unit Tests (unittest based) and Integrity Checks (script based).

Usage:
    python assets/runner.py [mode]

Modes:
    all       : Run ALL tests and checks (default)
    unit      : Run only Unit Tests (test_*.py)
    integrity : Run only Integrity Checks (verify_*.py)
"""

import sys
import os
import unittest
import subprocess
import time
import argparse
from typing import List, Tuple

# Ensure we can import modules from root
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

def run_unit_tests() -> bool:
    """Discover and run all test_*.py scripts using unittest."""
    print("\n" + "="*60)
    print("  Running Unit Tests (test_*.py)")
    print("="*60)
    
    loader = unittest.TestLoader()
    suite = loader.discover(CURRENT_DIR, pattern="test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_integrity_checks() -> bool:
    """Find and run all verify_*.py scripts as subprocesses."""
    print("\n" + "="*60)
    print("  Running Integrity Checks (verify_*.py)")
    print("="*60)
    
    scripts = [f for f in os.listdir(CURRENT_DIR) if f.startswith("verify_") and f.endswith(".py")]
    scripts.sort()
    
    results = []
    
    for script in scripts:
        print(f"\n[Running {script}]...")
        path = os.path.join(CURRENT_DIR, script)
        
        start_time = time.time()
        # Run process, capture output to preserve it but check return code
        # We allow stdout to flow through to console for visibility
        proc = subprocess.run([sys.executable, path], cwd=ROOT_DIR)
        duration = time.time() - start_time
        
        status = "PASS" if proc.returncode == 0 else "FAIL"
        results.append((script, status, duration))
        
        if proc.returncode != 0:
            print(f"  -> {script} FAILED (Exit Code: {proc.returncode})")
    
    # Summary
    print("\n" + "-"*60)
    print("  Integrity Check Summary")
    print("-"*60)
    all_passed = True
    for script, status, duration in results:
        print(f"  {script:<30} : {status:<4} ({duration:.2f}s)")
        if status == "FAIL":
            all_passed = False
            
    return all_passed

def main():
    parser = argparse.ArgumentParser(description="PromptBuilder Verification Runner")
    parser.add_argument("mode", nargs="?", choices=["all", "unit", "integrity"], default="all", help="Execution mode")
    args = parser.parse_args()
    
    success_unit = True
    success_integrity = True
    
    start_global = time.time()
    
    if args.mode in ["all", "unit"]:
        success_unit = run_unit_tests()
        
    if args.mode in ["all", "integrity"]:
        success_integrity = run_integrity_checks()
        
    duration_global = time.time() - start_global
    
    print("\n" + "="*60)
    print(f"  Final Verification Result ({duration_global:.2f}s)")
    print("="*60)
    
    if args.mode == "all":
        print(f"  Unit Tests      : {'PASS' if success_unit else 'FAIL'}")
        print(f"  Integrity Checks: {'PASS' if success_integrity else 'FAIL'}")
    elif args.mode == "unit":
        print(f"  Unit Tests      : {'PASS' if success_unit else 'FAIL'}")
    elif args.mode == "integrity":
        print(f"  Integrity Checks: {'PASS' if success_integrity else 'FAIL'}")
        
    if success_unit and success_integrity:
        print("\n  [SUCCESS] All checks passed.")
        sys.exit(0)
    else:
        print("\n  [FAILURE] Some checks failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
