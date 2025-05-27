#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from datetime import datetime
import signal
import threading

# Define log files to monitor
LOG_FILES = [
    "/var/log/supervisord.log",
    "/var/log/celery_worker_primary.log",
    "/var/log/celery_worker_light.log",
    "/var/log/celery_worker_heavy.log",
    "/tmp/force_print.log",
    "/tmp/stdout_debug.log",
    "/tmp/stderr_debug.log",
    "/tmp/dataset_stdout_debug.log",
    "/tmp/dataset_stderr_debug.log",
    "/tmp/stdout_backup.log",
    "./log/onyx_debug.log",
    "./log/onyx_info.log",
    "./log/onyx_notice.log"
]

# ANSI color codes
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

def timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def monitor_log_file(file_path, color, tag, stop_event):
    """Monitor a log file and print new lines with color and tag"""
    if not os.path.exists(file_path):
        print(f"{Colors.YELLOW}[{timestamp()}] Warning: Log file {file_path} does not exist{Colors.RESET}")
        # Create empty file to tail
        try:
            open(file_path, 'a').close()
            print(f"{Colors.GREEN}[{timestamp()}] Created empty file: {file_path}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}[{timestamp()}] Failed to create {file_path}: {str(e)}{Colors.RESET}")
            return
    
    try:
        process = subprocess.Popen(
            ["tail", "-f", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        while not stop_event.is_set():
            line = process.stdout.readline()
            if not line:
                break
            print(f"{color}[{timestamp()}] [{tag}] {line.rstrip()}{Colors.RESET}")
            
        process.terminate()
        process.wait(timeout=1)
        
    except Exception as e:
        print(f"{Colors.RED}[{timestamp()}] Error monitoring {file_path}: {str(e)}{Colors.RESET}")

def main():
    print(f"{Colors.GREEN}[{timestamp()}] Starting log monitor...{Colors.RESET}")
    
    # Create a stop event for clean termination
    stop_event = threading.Event()
    
    # Start threads for each log file
    threads = []
    colors = [Colors.CYAN, Colors.YELLOW, Colors.GREEN, Colors.BLUE, 
              Colors.MAGENTA, Colors.WHITE, Colors.RED]
    
    for i, log_file in enumerate(LOG_FILES):
        color = colors[i % len(colors)]
        tag = os.path.basename(log_file)
        thread = threading.Thread(
            target=monitor_log_file,
            args=(log_file, color, tag, stop_event)
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)
        print(f"{Colors.BLUE}[{timestamp()}] Monitoring: {log_file}{Colors.RESET}")
    
    # Also monitor Python print statements from this process itself
    def log_python_print():
        """Watch system standard output/error to catch any Python print statements"""
        original_stdout = sys.stdout
        
        class PrintLogger:
            def write(self, message):
                if message.strip():  # Only print non-empty messages
                    original_stdout.write(f"{Colors.MAGENTA}[{timestamp()}] [Python] {message}{Colors.RESET}")
                return original_stdout.write(message)
            
            def flush(self):
                return original_stdout.flush()
        
        sys.stdout = PrintLogger()
        
        while not stop_event.is_set():
            time.sleep(0.1)
    
    print_thread = threading.Thread(target=log_python_print)
    print_thread.daemon = True
    print_thread.start()
    threads.append(print_thread)
    
    # Capture Ctrl+C for clean exit
    def signal_handler(sig, frame):
        print(f"\n{Colors.YELLOW}[{timestamp()}] Stopping log monitor...{Colors.RESET}")
        stop_event.set()
        # Allow time for threads to clean up
        time.sleep(1)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        for thread in threads:
            thread.join(timeout=1)

if __name__ == "__main__":
    main() 