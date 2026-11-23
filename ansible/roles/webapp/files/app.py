#!/usr/bin/env python3
"""
INT333 DevOps Project: Sample Web Application
Provides real-time endpoints for service monitoring and live demo failure injection.
"""

from flask import Flask, jsonify, render_template_string, request
import os
import platform
import time
import socket

app = Flask(__name__)
START_TIME = time.time()
HEALTH_STATE = {"is_healthy": True, "failure_reason": None}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>INT333 DevOps Portal</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }
        .card { background: #1e293b; border-radius: 12px; padding: 24px; max-width: 600px; margin: 0 auto; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5); }
        h1 { margin-top: 0; color: #38bdf8; font-size: 24px; }
        .status-badge { display: inline-block; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 14px; }
        .ok { background: #22c55e; color: #000; }
        .fail { background: #ef4444; color: #fff; }
        .info-grid { display: grid; grid-template-columns: 140px 1fr; gap: 8px; margin: 20px 0; font-size: 14px; }
        .label { color: #94a3b8; }
        .value { color: #f1f5f9; font-family: monospace; }
        .btn { border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-weight: bold; margin-right: 10px; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-success { background: #22c55e; color: black; }
    </style>
</head>
<body>
    <div class="card">
        <h1>INT333 DevOps Monitoring Portal</h1>
        <p>Managed via <strong>Terraform & Ansible</strong> | Monitored by <strong>Nagios Core</strong></p>
        
        <p>Current Service Health: 
            <span class="status-badge {{ 'ok' if is_healthy else 'fail' }}">
                {{ 'HEALTHY (200 OK)' if is_healthy else 'CRITICAL (500 ERROR)' }}
            </span>
        </p>

        <div class="info-grid">
            <span class="label">Host Name:</span><span class="value">{{ hostname }}</span>
            <span class="label">Platform OS:</span><span class="value">{{ os_name }}</span>
            <span class="label">Uptime:</span><span class="value">{{ uptime }} seconds</span>
            <span class="label">Health API:</span><span class="value"><a href="/health" style="color: #38bdf8;">/health</a></span>
        </div>

        <hr style="border: 0; border-top: 1px solid #334155; margin: 20px 0;">
        <h3>Live Demo Control:</h3>
        <form action="/simulate-failure" method="POST" style="display:inline;">
            <button type="submit" class="btn btn-danger">Simulate Service Failure</button>
        </form>
        <form action="/recover" method="POST" style="display:inline;">
            <button type="submit" class="btn btn-success">Restore Normal State</button>
        </form>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    uptime = int(time.time() - START_TIME)
    return render_template_string(
        HTML_TEMPLATE,
        is_healthy=HEALTH_STATE["is_healthy"],
        hostname=socket.gethostname(),
        os_name=f"{platform.system()} {platform.release()}",
        uptime=uptime
    )

@app.route('/health', methods=['GET'])
def health():
    if not HEALTH_STATE["is_healthy"]:
        return jsonify({
            "status": "CRITICAL",
            "service": "devops-portal-api",
            "error": HEALTH_STATE["failure_reason"] or "Internal service dependency failure",
            "timestamp": time.time()
        }), 500

    return jsonify({
        "status": "OK",
        "service": "devops-portal-api",
        "timestamp": time.time(),
        "database": "connected",
        "memory_status": "optimal",
        "version": "1.0.0"
    }), 200

@app.route('/simulate-failure', methods=['POST'])
def simulate_failure():
    HEALTH_STATE["is_healthy"] = False
    HEALTH_STATE["failure_reason"] = "Database connection timed out (Simulated for Live Demo)"
    return jsonify({"action": "Failure triggered", "current_status": "CRITICAL"}), 500

@app.route('/recover', methods=['POST'])
def recover():
    HEALTH_STATE["is_healthy"] = True
    HEALTH_STATE["failure_reason"] = None
    return jsonify({"action": "Service restored", "current_status": "OK"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
