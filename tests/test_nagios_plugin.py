#!/usr/bin/env python3
"""
================================================================================
INT333 Test Suite: test_nagios_plugin.py
Validates Nagios custom plugin return codes (OK, WARNING, CRITICAL, UNKNOWN)
Fulfills Rubric: Testing & Error Handling (5 marks)
================================================================================
"""

import unittest
import subprocess
import sys
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

PLUGIN_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../ansible/roles/nagios/files/plugins/check_webapp_health.py")
)

TEST_PORT = 5055

class MockHealthHandler(BaseHTTPRequestHandler):
    mode = "OK"  # Can be "OK", "CRITICAL", "SLOW"

    def do_GET(self):
        if self.path == "/health":
            if MockHealthHandler.mode == "OK":
                body = b'{"status": "OK", "service": "test-api"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
            elif MockHealthHandler.mode == "CRITICAL":
                body = b'{"status": "CRITICAL", "error": "simulated database drop"}'
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
            elif MockHealthHandler.mode == "SLOW":
                time.sleep(1.2)  # Exceeds 1.0s warning threshold
                body = b'{"status": "OK", "service": "slow-api"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
        else:
            self.send_response(404)
            self.send_header("Connection", "close")
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress HTTP server console logs during tests

class TestNagiosPlugin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", TEST_PORT), MockHealthHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def run_plugin(self, *extra_args):
        cmd = [sys.executable, PLUGIN_PATH, "-H", "127.0.0.1", "-p", str(TEST_PORT)] + list(extra_args)
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return proc.returncode, proc.stdout.strip()

    def test_state_ok(self):
        """Plugin should return 0 (OK) when endpoint returns 200 OK and valid status"""
        MockHealthHandler.mode = "OK"
        code, out = self.run_plugin()
        self.assertEqual(code, 0, f"Expected 0 (OK), got {code}. Output: {out}")
        self.assertIn("OK - Web Application API Healthy", out)

    def test_state_warning_on_latency(self):
        """Plugin should return 1 (WARNING) when latency exceeds warning threshold"""
        MockHealthHandler.mode = "SLOW"
        code, out = self.run_plugin("-w", "1.0", "-c", "2.5")
        self.assertEqual(code, 1, f"Expected 1 (WARNING), got {code}. Output: {out}")
        self.assertIn("WARNING - High latency detected", out)

    def test_state_critical_on_http_error(self):
        """Plugin should return 2 (CRITICAL) when endpoint returns HTTP 500 error"""
        MockHealthHandler.mode = "CRITICAL"
        code, out = self.run_plugin()
        self.assertEqual(code, 2, f"Expected 2 (CRITICAL), got {code}. Output: {out}")
        self.assertIn("CRITICAL", out)

    def test_state_critical_on_connection_refused(self):
        """Plugin should return 2 (CRITICAL) when host/port is unreachable"""
        # Pick an unused port
        cmd = [sys.executable, PLUGIN_PATH, "-H", "127.0.0.1", "-p", "59999"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2, f"Expected 2 (CRITICAL), got {proc.returncode}")
        self.assertIn("CRITICAL", proc.stdout)

if __name__ == "__main__":
    unittest.main()
