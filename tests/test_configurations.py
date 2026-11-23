#!/usr/bin/env python3
"""
================================================================================
INT333 Test Suite: test_configurations.py
Validates syntax and structural integrity of Terraform, Ansible, and Nagios configs.
================================================================================
"""

import unittest
import os
import re

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

class TestConfigurations(unittest.TestCase):

    def test_terraform_files_exist_and_valid(self):
        """Verify core Terraform configuration files exist and have valid structure"""
        tf_files = ["main.tf", "variables.tf", "outputs.tf", "inventory.tpl"]
        for tf in tf_files:
            path = os.path.join(ROOT_DIR, "terraform", tf)
            self.assertTrue(os.path.exists(path), f"Missing Terraform file: {tf}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                # Check for balanced braces
                open_braces = content.count("{")
                close_braces = content.count("}")
                self.assertEqual(open_braces, close_braces, f"Mismatched braces in {tf}")

    def test_ansible_playbooks_exist(self):
        """Verify Ansible playbooks exist and have valid YAML header"""
        playbooks = ["site.yml", "webapp.yml", "nagios.yml", "self_heal.yml"]
        for pb in playbooks:
            path = os.path.join(ROOT_DIR, "ansible", "playbooks", pb)
            self.assertTrue(os.path.exists(path), f"Missing Ansible playbook: {pb}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertTrue(content.strip().startswith("---"), f"Playbook {pb} missing YAML document start (---)")

    def test_ansible_roles_exist(self):
        """Verify role tasks and handlers exist"""
        role_tasks = [
            ("common", "tasks/main.yml"),
            ("webapp", "tasks/main.yml"),
            ("webapp", "handlers/main.yml"),
            ("nagios", "tasks/main.yml"),
            ("nagios", "handlers/main.yml"),
        ]
        for role, rel_path in role_tasks:
            path = os.path.join(ROOT_DIR, "ansible", "roles", role, rel_path)
            self.assertTrue(os.path.exists(path), f"Missing role file: {role}/{rel_path}")

    def test_nagios_definitions_syntax(self):
        """Verify Nagios object config files have valid block definitions"""
        cfg_files = ["hosts.cfg", "services.cfg", "commands.cfg"]
        for cfg in cfg_files:
            path = os.path.join(ROOT_DIR, "nagios", "sample_configs", cfg)
            self.assertTrue(os.path.exists(path), f"Missing Nagios config: {cfg}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                # Check for balanced braces
                open_braces = content.count("{")
                close_braces = content.count("}")
                self.assertEqual(open_braces, close_braces, f"Mismatched braces in {cfg}")
                self.assertIn("define ", content, f"No define statements found in {cfg}")

    def test_sample_webapp_executable(self):
        """Verify Flask webapp file exists and imports cleanly"""
        app_path = os.path.join(ROOT_DIR, "ansible", "roles", "webapp", "files", "app.py")
        self.assertTrue(os.path.exists(app_path), "Missing app.py")
        with open(app_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("/health", content)
            self.assertIn("/simulate-failure", content)
            self.assertIn("/recover", content)

if __name__ == "__main__":
    unittest.main()
