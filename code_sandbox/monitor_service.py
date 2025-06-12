#!/usr/bin/env python3
"""
Code Sandbox Service Monitor
Helps debug connection issues by continuously monitoring the service
"""

import requests
import time
import json
from datetime import datetime

def check_service_health():
    """Check if the service is responding to health checks"""
    try:
        response = requests.get("http://127.0.0.1:8856/health", timeout=5)
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

def test_simple_execution():
    """Test simple code execution"""
    try:
        payload = {
            "code": "print('Service test:', 42)",
            "language": "python",
            "timeout": 10
        }
        response = requests.post(
            "http://127.0.0.1:8856/execute",
            json=payload,
            timeout=15
        )
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

def test_pandas_execution():
    """Test pandas code execution (the problematic case)"""
    try:
        payload = {
            "code": "import pandas as pd; print('Pandas version:', pd.__version__)",
            "language": "python",
            "timeout": 30
        }
        response = requests.post(
            "http://127.0.0.1:8856/execute",
            json=payload,
            timeout=35
        )
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

def monitor_service(duration_minutes=5):
    """Monitor the service for a specified duration"""
    print(f"Monitoring Code Sandbox Service for {duration_minutes} minutes...")
    print("=" * 60)
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    while time.time() < end_time:
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Health check
        health_ok, health_msg = check_service_health()
        
        # Simple execution test
        simple_ok, simple_msg = test_simple_execution()
        
        # Pandas execution test
        pandas_ok, pandas_msg = test_pandas_execution()
        
        status = "✅ OK" if all([health_ok, simple_ok, pandas_ok]) else "❌ FAIL"
        
        print(f"[{timestamp}] {status} | Health: {health_ok} | Simple: {simple_ok} | Pandas: {pandas_ok}")
        
        if not health_ok:
            print(f"  Health Error: {health_msg}")
        if not simple_ok:
            print(f"  Simple Error: {simple_msg}")
        if not pandas_ok:
            print(f"  Pandas Error: {pandas_msg}")
        
        time.sleep(10)  # Check every 10 seconds
    
    print("Monitoring completed.")

if __name__ == "__main__":
    import sys
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    monitor_service(duration) 