import sys
import os
import traceback
import logging
from datetime import datetime

# Make a backup of the original stdout and stderr
original_stdout = sys.__stdout__
original_stderr = sys.__stderr__

# Dedicated log files for direct print
DIRECT_PRINT_LOG = "/tmp/direct_print.log"
DEBUG_LOG = "/tmp/onyx_debug.log"

def timestamp():
    """Get a formatted timestamp for logs"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def direct_print(message, level="INFO"):
    """Print directly to multiple outputs to ensure visibility
    
    This bypasses all Python logging infrastructure to force output to be visible.
    """
    # Format with timestamp and level
    formatted_msg = f"[{timestamp()}] [{level}] {message}"
    
    try:
        # 1. Write directly to the original stdout
        original_stdout.write(formatted_msg + "\n")
        original_stdout.flush()
        
        # 2. Write to system stderr as well for redundancy
        original_stderr.write(formatted_msg + "\n")
        original_stderr.flush()
        
        # 3. Write to multiple log files
        log_files = [DIRECT_PRINT_LOG, DEBUG_LOG]
        for log_file in log_files:
            try:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                with open(log_file, "a") as f:
                    f.write(formatted_msg + "\n")
            except Exception as log_err:
                # If we can't write to the log file, write to stderr
                error_msg = f"Error writing to {log_file}: {str(log_err)}"
                original_stderr.write(error_msg + "\n")
                original_stderr.flush()
    
    except Exception as e:
        # Last resort error handling
        error_msg = f"CRITICAL ERROR in direct_print: {str(e)}\n{traceback.format_exc()}"
        try:
            original_stderr.write(error_msg + "\n")
            original_stderr.flush()
        except:
            pass  # Nothing more we can do

def debug(message):
    """Debug level direct print"""
    direct_print(message, "DEBUG")

def info(message):
    """Info level direct print"""
    direct_print(message, "INFO")

def warning(message):
    """Warning level direct print"""
    direct_print(message, "WARNING")

def error(message):
    """Error level direct print"""
    direct_print(message, "ERROR")

def critical(message):
    """Critical level direct print"""
    direct_print(message, "CRITICAL")

# Enable direct printing as soon as this module is imported
direct_print("=== DIRECT PRINT MODULE INITIALIZED ===") 