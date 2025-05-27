#!/usr/bin/env python3
"""
Test script for dataset_handler module
"""

import os
import sys
import traceback

# Add the backend directory to the path so we can import onyx modules
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

try:
    # Import the direct_print function first to test logging
    from onyx.server.features.code_interpreter.direct_print import direct_print
    
    # Print a test message
    direct_print("===== TEST SCRIPT STARTED =====")
    
    # Now try to import the dataset handler
    from onyx.server.features.code_interpreter.dataset_handler import (
        get_dataset_files_by_name,
        prepare_datasets_for_execution,
        format_dataset_instructions,
        print_debug_info
    )
    
    # Import database session
    from onyx.db.engine import get_session_context_manager
    
    # Test with a sample dataset name
    DATASET_NAME = 'test_dataset'
    
    # Main test function
    def test_dataset_handler():
        direct_print(f"\n\nTesting dataset handler with dataset: {DATASET_NAME}")
        
        with get_session_context_manager() as db_session:
            # Test 1: Get dataset files by name
            direct_print("\n--- Test 1: get_dataset_files_by_name ---")
            files = get_dataset_files_by_name(db_session, DATASET_NAME)
            direct_print(f"Found {len(files)} files for dataset {DATASET_NAME}")
            for i, file in enumerate(files):
                direct_print(f"  File {i+1}: {file['name']}")
            
            # Test 2: Prepare datasets for execution
            direct_print("\n--- Test 2: prepare_datasets_for_execution ---")
            datasets_info = prepare_datasets_for_execution(db_session, [DATASET_NAME])
            direct_print("Results from prepare_datasets_for_execution:")
            print_debug_info(datasets_info, simplified=True)
            
            # Test 3: Format dataset instructions
            direct_print("\n--- Test 3: format_dataset_instructions ---")
            instructions = format_dataset_instructions(datasets_info)
            direct_print(f"Generated instructions length: {len(instructions)} characters")
            direct_print("First 500 characters of instructions:")
            direct_print(instructions[:500] + "...")

    # Run the test
    if __name__ == "__main__":
        try:
            test_dataset_handler()
            direct_print("\n===== TEST COMPLETED SUCCESSFULLY =====")
        except Exception as e:
            direct_print(f"\nERROR: {str(e)}")
            traceback.print_exc()
            direct_print("\n===== TEST FAILED =====")
            sys.exit(1)
except Exception as e:
    print(f"Failed to import required modules: {str(e)}")
    traceback.print_exc()
    sys.exit(1) 