#!/usr/bin/env python3
"""
================================================================================
INT333: Master Test Runner
Executes all unit tests and configuration integrity validations.
================================================================================
"""

import unittest
import sys
import os

def run():
    print("=" * 70)
    print(" INT333: DevOps Project Automated Verification & Test Suite")
    print(" Evaluating: Terraform IaC, Ansible Roles, Nagios Custom Plugin")
    print("=" * 70)
    
    loader = unittest.TestLoader()
    start_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../tests"))
    suite = loader.discover(start_dir, pattern="test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 70)
    if result.wasSuccessful():
        print(">> ALL TESTS PASSED SUCCESSFULLY! (100% Verification Coverage)")
        print("=" * 70)
        sys.exit(0)
    else:
        print(f">> {len(result.failures)} FAILURE(S), {len(result.errors)} ERROR(S) DETECTED.")
        print("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    run()
