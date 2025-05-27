import sys
import logging
from io import TextIOWrapper

# Store the original stdout
original_stdout = sys.stdout
original_stderr = sys.stderr

# Create a custom stdout/stderr handler that writes to both file and console
class TeeOutput(TextIOWrapper):
    def __init__(self, original_stream, *args, **kwargs):
        self.original_stream = original_stream
        super().__init__(*args, **kwargs)
    
    def write(self, data):
        # Force write to the original stdout (usually the console)
        self.original_stream.write(data)
        self.original_stream.flush()
        # Also let the normal logging system handle it
        return super().write(data)

# Example usage
def enable_direct_prints():
    """Call this at the start of your script to force print statements to show"""
    # Create temporary files for redirection
    temp_stdout = open('/tmp/stdout_debug.log', 'w')
    temp_stderr = open('/tmp/stderr_debug.log', 'w')
    
    # Replace stdout with our custom handler
    sys.stdout = TeeOutput(original_stdout, temp_stdout)
    sys.stderr = TeeOutput(original_stderr, temp_stderr)
    
    # Disable other handlers from root logger to prevent duplication
    root = logging.getLogger()
    root.handlers = []
    
    # Add a stream handler to stdout for logging
    handler = logging.StreamHandler(original_stdout)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)
    
    print("DEBUG MODE: Direct print statements enabled")

if __name__ == "__main__":
    enable_direct_prints()
    print("This should show in the console regardless of logging configuration") 