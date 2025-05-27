#!/usr/bin/env python3
import sys
from onyx.server.features.code_interpreter.direct_print import (
    direct_print, debug, info, warning, error, critical
)
from onyx.utils.logger import setup_logger

# Set up standard logger
logger = setup_logger("test_direct_print")

def test_direct_print():
    """Test direct print functions"""
    
    # Test standard logger
    logger.info("Standard logger test")
    
    # Test direct print functions
    info("Direct print test")
    warning("Warning test")
    error("Error test")
    
    # Success message
    direct_print("Test complete")

if __name__ == "__main__":
    test_direct_print() 