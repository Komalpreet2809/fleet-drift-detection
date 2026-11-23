#!/usr/bin/env python3
"""
================================================================================
INT333: DevOps Advance Configuration Management
Custom Nagios Monitoring Plugin: check_webapp_health.py
Fulfills Unit III Practical 8: "Create Custom Nagios Plugins" & Rubric Innovation.

Nagios Return Codes:
  0 = OK
  1 = WARNING
  2 = CRITICAL
  3 = UNKNOWN
================================================================================
"""

import sys
import argparse
import time
import json
import urllib.request
import urllib.error

# Nagios Exit Codes
STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3

def parse_args():
    parser = argparse.ArgumentParser(description="Custom Nagios Plugin to check Web Application Health and Latency.")
    parser.add_argument("-H", "--host", default="127.0.0.1", help="Target hostname or IP (default: 127.0.0.1)")
    parser.add_argument("-p", "--port", type=int, default=5000, help="Target application port (default: 5000)")
    parser.add_argument("-u", "--uri", default="/health", help="Health check endpoint URI (default: /health)")
    parser.add_argument("-w", "--warning", type=float, default=1.0, help="Warning threshold in seconds for response latency (default: 1.0s)")
    parser.add_argument("-c", "--critical", type=float, default=2.5, help="Critical threshold in seconds for response latency (default: 2.5s)")
    return parser.parse_args()

def main():
    args = parse_args()
    url = f"http://{args.host}:{args.port}{args.uri}"
    
    start_time = time.time()
    try:
        # Avoid local monitoring requests from being misrouted through corporate/system HTTP proxies
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        req = urllib.request.Request(url, headers={'User-Agent': 'Nagios-Custom-HealthCheck/1.0'})
        with opener.open(req, timeout=5) as response:
            latency = time.time() - start_time
            status_code = response.getcode()
            body = response.read().decode('utf-8')
            
            # Parse JSON response body
            try:
                payload = json.loads(body)
                service_status = payload.get("status", "").upper()
            except json.JSONDecodeError:
                service_status = "UNKNOWN_FORMAT"
                payload = {}

    except urllib.error.HTTPError as e:
        latency = time.time() - start_time
        print(f"CRITICAL - HTTP Error {e.code}: {e.reason} for {url} | time={latency:.4f}s;;;0;")
        sys.exit(STATE_CRITICAL)

    except urllib.error.URLError as e:
        latency = time.time() - start_time
        print(f"CRITICAL - Connection Refused/Unreachable: {e.reason} for {url} | time={latency:.4f}s;;;0;")
        sys.exit(STATE_CRITICAL)

    except Exception as e:
        print(f"UNKNOWN - Unexpected inspection failure: {str(e)}")
        sys.exit(STATE_UNKNOWN)

    # Evaluate Service Health Condition
    perf_data = f"| time={latency:.4f}s;{args.warning};{args.critical};0;5"

    if status_code != 200 or service_status != "OK":
        print(f"CRITICAL - Service reported unhealthy state [HTTP {status_code}, Status: {service_status}] {perf_data}")
        sys.exit(STATE_CRITICAL)

    if latency >= args.critical:
        print(f"CRITICAL - Latency exceeded threshold ({latency:.3f}s >= {args.critical}s) {perf_data}")
        sys.exit(STATE_CRITICAL)

    if latency >= args.warning:
        print(f"WARNING - High latency detected ({latency:.3f}s >= {args.warning}s) {perf_data}")
        sys.exit(STATE_WARNING)

    # All checks passed
    print(f"OK - Web Application API Healthy (Response: {latency:.3f}s, Status: {service_status}) {perf_data}")
    sys.exit(STATE_OK)

if __name__ == "__main__":
    main()
