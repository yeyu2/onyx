#!/usr/bin/env python3
"""
Simple working code execution service
Fixes all HTTP issues by using basic HTTP server
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
import io
import traceback
import os
from pathlib import Path
import time
from urllib.parse import urlparse, parse_qs
import pandas as pd
import numpy as np

# Configure allowed path
RAW_ALLOWED_BASE_PATH = os.environ.get("EXEC_ALLOWED_BASE_PATH", "./datasets")
try:
    _temp_path = Path(os.path.expanduser(RAW_ALLOWED_BASE_PATH))
    _temp_path.mkdir(parents=True, exist_ok=True)
    RESOLVED_ALLOWED_BASE_PATH = _temp_path.resolve(strict=True)
    print(f"Allowed base path: {RESOLVED_ALLOWED_BASE_PATH}")
except Exception as e:
    print(f"Path config error: {e}")
    RESOLVED_ALLOWED_BASE_PATH = None

def execute_python_code(code: str, timeout: int = 30):
    """Execute Python code safely"""
    start_time = time.time()
    
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        namespace = {
            '__builtins__': __builtins__,
            'pd': pd,
            'np': np,
            'os': os,
            'sys': sys,
        }
        
        exec(code, namespace)
        
        output = stdout_capture.getvalue()
        error_output = stderr_capture.getvalue()
        execution_time = time.time() - start_time
        
        if error_output:
            return False, output, error_output, execution_time
        else:
            return True, output, None, execution_time
            
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"{type(e).__name__}: {str(e)}\\n{traceback.format_exc()}"
        return False, stdout_capture.getvalue(), error_msg, execution_time
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

class CodeExecutionHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"status": "healthy", "service": "code-execution"}
            self.wfile.write(json.dumps(response).encode())
            return
        
        self.send_response(404)
        self.end_headers()
    
    def do_POST(self):
        if self.path == "/execute":
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode())
                
                code = request_data.get('code', '')
                timeout = request_data.get('timeout', 30)
                
                print(f"Executing code: {code[:100]}...")
                
                success, output, error, execution_time = execute_python_code(code, timeout)
                
                response = {
                    "success": success,
                    "output": output,
                    "error": error,
                    "execution_time": execution_time
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
                print(f"Execution completed: success={success}, time={execution_time:.3f}s")
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {
                    "success": False,
                    "output": "",
                    "error": f"Server error: {str(e)}",
                    "execution_time": 0
                }
                self.wfile.write(json.dumps(error_response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def main():
    port = int(os.getenv("PORT", "8856"))
    host = os.getenv("HOST", "127.0.0.1")
    
    server = HTTPServer((host, port), CodeExecutionHandler)
    print(f"Starting Simple Code Execution Service on {host}:{port}")
    print(f"Health: http://{host}:{port}/health")
    print(f"Ready to execute code!")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nShutting down...")
        server.shutdown()

if __name__ == "__main__":
    main() 