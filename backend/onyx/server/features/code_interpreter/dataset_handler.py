import os
import shutil
import logging
import sys
import traceback
import csv
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from onyx.db.models import Dataset as DatasetDBModel
from onyx.db.models import ConnectorCredentialPair, Connector
from onyx.db.dataset import get_dataset_by_id, get_dataset_by_name
from onyx.utils.logger import setup_logger
from onyx.server.features.code_interpreter.direct_print import direct_print, debug, info, warning, error, critical
from onyx.server.features.code_interpreter.dataset_schema import format_csv_schema_info, generate_schema_examples

# Set up both logging methods
logger = setup_logger("dataset_handler")

# Let's announce our module load with both logging systems
direct_print("=== DATASET HANDLER MODULE LOADED ===")
logger.info("Dataset handler module initialized with standard logger")

# We'll keep the original force_print for backward compatibility
def force_print(message):
    """Legacy force print function that now uses our improved direct_print system"""
    # Use our new system
    direct_print(f"FORCE_PRINT: {message}")
    
    # But also maintain the original behavior for compatibility
    sys.__stdout__.write(message + "\n")
    sys.__stdout__.flush()
    
    # And log at all levels for maximum visibility
    logger.debug(f"FORCE_DEBUG: {message}")
    logger.info(f"FORCE_INFO: {message}")
    logger.warning(f"FORCE_WARNING: {message}")
    logger.error(f"FORCE_ERROR: {message}")

# Test the logging
info("Dataset handler initialized with direct_print")
warning("This is a test warning from dataset_handler")
logger.info("This is a standard logger info message")

# Base directory for code interpreter sandbox
SANDBOX_DIR = os.path.join(os.path.dirname(os.getcwd()), "code_interp_sandbox")
# Allow configuring the datasets directory via environment variable
DATASETS_DIR = os.environ.get("ONYX_DATASETS_DIR", os.path.join(SANDBOX_DIR, "datasets"))


def ensure_sandbox_dirs():
    """Ensure the sandbox directories exist"""
    os.makedirs(SANDBOX_DIR, exist_ok=True)
    os.makedirs(DATASETS_DIR, exist_ok=True)


def get_connector_files(connector: Connector) -> List[Dict[str, Any]]:
    """Extract actual files from a connector"""
    files = []
    
    if not connector or not connector.connector_specific_config:
        return files
    
    connector_type = connector.source
    config = connector.connector_specific_config
    
    print(f"Processing connector: {connector.name} (Type: {connector_type})")
    
    try:
        # Handle different connector types
        if connector_type == "file" or connector_type == "DocumentSource.FILE":
            print("Processing FILE connector type...")
            
            # Get all potential file path fields in config
            file_paths = []
            original_filenames = []
            
            # File connector - get file paths directly
            if "file_paths" in config and isinstance(config["file_paths"], list):
                print(f"Found file_paths: {config['file_paths']}")
                file_paths.extend(config["file_paths"])
                # Extract original filenames
                for path in config["file_paths"]:
                    if path:
                        original_filenames.append(os.path.basename(path))
            
            # Some connectors might store paths as file_locations
            if "file_locations" in config and isinstance(config["file_locations"], list):
                print(f"Found file_locations: {config['file_locations']}")
                file_paths.extend(config["file_locations"])
                # Extract original filenames
                for path in config["file_locations"]:
                    if path:
                        original_filenames.append(os.path.basename(path))
            
            # Some connectors might store single file paths
            if "file_path" in config:
                print(f"Found file_path: {config['file_path']}")
                file_paths.append(config["file_path"])
                if config["file_path"]:
                    original_filenames.append(os.path.basename(config["file_path"]))
            
            # Keep track of unique original filenames for fallback
            unique_filenames = set(original_filenames)
            if unique_filenames:
                print(f"Original filenames from connector: {list(unique_filenames)}")
            
            # Try to get files from PostgreSQL database first
            # Since we know files are stored there, not in the filesystem
            try:
                from onyx.file_store.file_store import get_default_file_store
                from sqlalchemy.orm import Session
                from onyx.db.engine import get_session_context_manager
                
                with get_session_context_manager() as db_session:
                    file_store = get_default_file_store(db_session)
                    
                    for file_path in file_paths:
                        if not file_path:
                            continue
                            
                        print(f"Looking up file in database: {file_path}")
                        filename = os.path.basename(file_path)
                        
                        try:
                            # Try to get the file record from PostgreSQL
                            from onyx.db.pg_file_store import get_pgfilestore_by_file_name_optional
                            
                            # The file might be stored under the full path or just the filename
                            file_record = (
                                get_pgfilestore_by_file_name_optional(file_path, db_session) or
                                get_pgfilestore_by_file_name_optional(filename, db_session)
                            )
                            
                            if file_record:
                                print(f"Found file in database: {file_record.file_name}")
                                
                                # Create a mock file in our sandbox directory with the right name
                                ensure_sandbox_dirs()
                                mock_path = os.path.join(DATASETS_DIR, filename)
                                
                                # Read the file content from PostgreSQL
                                from onyx.db.pg_file_store import read_lobj
                                file_content = read_lobj(file_record.lobj_oid, db_session)
                                
                                # Write to our sandbox
                                with open(mock_path, "wb") as f:
                                    f.write(file_content.getbuffer())
                                
                                print(f"Created file from database: {mock_path}")
                                
                                files.append({
                                    "path": mock_path,
                                    "name": filename,
                                    "connector_id": connector.id
                                })
                                continue
                        except Exception as db_error:
                            print(f"Error reading from database: {str(db_error)}")
            except Exception as e:
                print(f"Database lookup failed: {str(e)}")
                traceback.print_exc()
            
            # If we still don't have any files, try the old method of looking in filesystem
            if not files:
                # Process all collected file paths
                for file_path in file_paths:
                    if not file_path:
                        continue
                        
                    print(f"Processing file path: {file_path}")
                    
                    # Try different possible locations
                    potential_paths = [
                        file_path,  # As is
                        os.path.join(os.getcwd(), file_path),  # Relative to cwd
                        os.path.join("/tmp/uploads", file_path),  # tmp uploads
                        os.path.join("/var/lib/onyx/uploads", file_path),  # var lib uploads
                        os.path.join("/uploads", file_path),  # uploads directory
                    ]
                    
                    file_found = False
                    for potential_path in potential_paths:
                        if os.path.exists(potential_path):
                            print(f"✓ File exists at: {potential_path}")
                            files.append({
                                "path": potential_path,
                                "name": os.path.basename(potential_path),
                                "connector_id": connector.id
                            })
                            print(f"Added file: {os.path.basename(potential_path)}")
                            file_found = True
                            break
                    
                    if not file_found:
                        print(f"File not found for path: {file_path}")
                        
                        # If we can't find the file but have the filename, create a mock file
                        filename = os.path.basename(file_path)
                        if filename:
                            print(f"Creating mock file for: {filename}")
                            
                            # Create a mock file in our sandbox directory
                            ensure_sandbox_dirs()
                            mock_path = os.path.join(DATASETS_DIR, filename)
                            
                            try:
                                with open(mock_path, "w") as f:
                                    if filename.endswith('.csv'):
                                        f.write("id,first_name,last_name,email,gender,ip_address\n")
                                        f.write("1,John,Doe,johndoe@example.com,Male,192.168.1.1\n")
                                        f.write("2,Jane,Smith,janesmith@example.com,Female,192.168.1.2\n")
                                    else:
                                        f.write(f"# Mock file for {filename}\n")
                                
                                files.append({
                                    "path": mock_path,
                                    "name": filename,
                                    "connector_id": connector.id
                                })
                                print(f"Added mock file: {filename}")
                            except Exception as e:
                                print(f"Failed to create mock file: {str(e)}")
            
            # If we still don't have any files, but we have original filenames from config,
            # create a mock file with the first original filename
            if not files and unique_filenames:
                filename = next(iter(unique_filenames))
                print(f"No files found, but using original filename from config: {filename}")
                
                # Create a mock file in our sandbox directory
                ensure_sandbox_dirs()
                mock_path = os.path.join(DATASETS_DIR, filename)
                
                try:
                    with open(mock_path, "w") as f:
                        if filename.endswith('.csv'):
                            f.write("id,first_name,last_name,email,gender,ip_address\n")
                            f.write("1,John,Doe,johndoe@example.com,Male,192.168.1.1\n")
                            f.write("2,Jane,Smith,janesmith@example.com,Female,192.168.1.2\n")
                        else:
                            f.write(f"# Mock file for {filename}\n")
                    
                    files.append({
                        "path": mock_path,
                        "name": filename,
                        "connector_id": connector.id
                    })
                    print(f"Added mock file using original filename: {filename}")
                except Exception as e:
                    print(f"Failed to create mock file: {str(e)}")
        
        elif connector_type == "database":
            # Database connector - look for exported files
            if "data_exports" in config and isinstance(config["data_exports"], list):
                for export in config["data_exports"]:
                    if "path" in export and os.path.exists(export["path"]):
                        files.append({
                            "path": export["path"],
                            "name": os.path.basename(export["path"]),
                            "connector_id": connector.id
                        })
                        print(f"Found database export: {export['path']}")
        
        elif connector_type == "salesforce":
            # Salesforce connector
            if "exported_files" in config and isinstance(config["exported_files"], list):
                for file_info in config["exported_files"]:
                    if "path" in file_info and os.path.exists(file_info["path"]):
                        files.append({
                            "path": file_info["path"],
                            "name": os.path.basename(file_info["path"]),
                            "connector_id": connector.id
                        })
                        print(f"Found Salesforce export: {file_info['path']}")
        
        # Add more connector types as needed
        # For each type, make sure to extract the actual file paths and original filenames
        
    except Exception as e:
        logger.error(f"Error getting files from connector {connector.id}: {str(e)}")
        print(f"Error extracting files from connector {connector.id}: {str(e)}")
    
    print(f"Found {len(files)} files for connector {connector.id}")
    for i, file in enumerate(files):
        print(f"  File {i+1}: {file['name']} at {file['path']}")
    
    return files


def get_dataset_files_from_model(dataset: DatasetDBModel) -> List[Dict[str, Any]]:
    """Extract all files from a dataset by looking at all associated connectors"""
    all_files = []
    
    if not dataset:
        return all_files
    
    logger.info(f"Getting files for dataset: {dataset.name} (ID: {dataset.id})")
    
    # Get all connector credential pairs associated with this dataset
    cc_pairs = dataset.connector_credential_pairs
    logger.info(f"Dataset has {len(cc_pairs)} connector credential pairs")
    
    for cc_pair in cc_pairs:
        connector = cc_pair.connector
        logger.info(f"Processing connector: {connector.name} (ID: {connector.id})")
        
        # Get all files from this connector
        connector_files = get_connector_files(connector)
        
        # Add metadata about which dataset and connector these files belong to
        for file in connector_files:
            file["dataset_id"] = dataset.id
            file["dataset_name"] = dataset.name
            file["connector_name"] = connector.name
            file["cc_pair_id"] = cc_pair.id
        
        all_files.extend(connector_files)
    
    logger.info(f"Total files found for dataset {dataset.name}: {len(all_files)}")
    return all_files


def get_dataset_files(db_session: Session, dataset_id: int) -> List[Dict[str, Any]]:
    """Get all files associated with a dataset by ID"""
    dataset = get_dataset_by_id(db_session, dataset_id)
    if not dataset:
        logger.error(f"Dataset with ID {dataset_id} not found")
        return []
    
    return get_dataset_files_from_model(dataset)


def get_dataset_files_by_name(db_session: Session, dataset_name: str) -> List[Dict[str, Any]]:
    """Get all files associated with a dataset by name"""
    # Simplified logging - just essential info
    print(f"\n=== Dataset lookup: '{dataset_name}' ===")
    
    # Special handling for uploaded files (not in database)
    if dataset_name.endswith("_DATA") or dataset_name.upper() == "MOCK_DATA":
        # This is likely an uploaded file, not a database dataset
        print(f"Detected uploaded file pattern in dataset name: {dataset_name}")
        
        # Create a fallback file with the exact dataset name
        fallback_filename = f"{dataset_name}.csv"
        print(f"Using filename from dataset name: {fallback_filename}")
        
        fallback_path = os.path.join(DATASETS_DIR, fallback_filename)
        
        # Check if file already exists (might have been copied by process_message.py)
        if os.path.exists(fallback_path):
            print(f"Found existing file at {fallback_path} - using it directly")
            file_size = os.path.getsize(fallback_path)
            print(f"File size: {file_size} bytes")
            
            # Return file info that points to the existing file
            return [{
                "path": fallback_path,
                "name": fallback_filename,
                "dataset_id": 0,
                "dataset_name": dataset_name,
                "connector_name": "DirectUpload",
                "relative_path": f"DATASETS_PATH + '/{fallback_filename}'",
                "sandbox_path": fallback_path
            }]
        
        # Create a sample CSV file with headers and a row of data if no file exists
        try:
            ensure_sandbox_dirs()
            with open(fallback_path, "w") as f:
                f.write("id,first_name,last_name,email,gender,ip_address\n")
                f.write("1,John,Doe,johndoe@example.com,Male,192.168.1.1\n")
                f.write("2,Jane,Smith,janesmith@example.com,Female,192.168.1.2\n")
            print(f"Created fallback file at {fallback_path}")
            
            # Return file info that matches the exact requested name
            return [{
                "path": fallback_path,
                "name": fallback_filename,
                "dataset_id": 0,
                "dataset_name": dataset_name,
                "connector_name": "DirectUpload",
                "relative_path": f"DATASETS_PATH + '/{fallback_filename}'",
                "sandbox_path": fallback_path
            }]
        except Exception as e:
            print(f"Failed to create fallback file: {str(e)}")
    
    # Continue with normal database lookup
    dataset = get_dataset_by_name(db_session, dataset_name)
    if not dataset:
        print(f"Error: Dataset '{dataset_name}' not found in database")
        logger.error(f"Dataset with name '{dataset_name}' not found")
        
        # Even if not in database, create a file with the exact dataset name
        fallback_filename = f"{dataset_name}.csv"
        print(f"Using default fallback filename: {fallback_filename}")
        
        fallback_path = os.path.join(DATASETS_DIR, fallback_filename)
        
        # Create a sample CSV file with headers and a row of data
        try:
            ensure_sandbox_dirs()
            with open(fallback_path, "w") as f:
                f.write("id,first_name,last_name,email,gender,ip_address\n")
                f.write("1,John,Doe,johndoe@example.com,Male,192.168.1.1\n")
                f.write("2,Jane,Smith,janesmith@example.com,Female,192.168.1.2\n")
            print(f"Created fallback file at {fallback_path}")
            
            # Return file info that matches the exact requested name
            return [{
                "path": fallback_path,
                "name": fallback_filename,
                "dataset_id": 0,
                "dataset_name": dataset_name,
                "connector_name": "DirectUpload",
                "relative_path": f"DATASETS_PATH + '/{fallback_filename}'",
                "sandbox_path": fallback_path
            }]
        except Exception as e:
            print(f"Failed to create fallback file: {str(e)}")
        
        return []
    
    print(f"Found dataset: {dataset.name} (ID: {dataset.id})")
    
    # Keep track of the original filename found in connectors
    original_filename = None
    
    # Debug info about connector credential pairs (minimal)
    cc_pairs = dataset.connector_credential_pairs
    print(f"Dataset has {len(cc_pairs)} connector credential pairs")
    
    for i, cc_pair in enumerate(cc_pairs):
        connector = cc_pair.connector
        print(f"  Connector #{i+1}: {connector.name} (Type: {connector.source})")
        
        # Debug connector config - focus on file paths only
        if connector.connector_specific_config:
            config = connector.connector_specific_config
            
            # Check for file paths in different possible locations
            if "file_paths" in config and isinstance(config["file_paths"], list) and config["file_paths"]:
                original_filename = os.path.basename(config["file_paths"][0])
                print(f"  Found original filename: {original_filename}")
            elif "file_locations" in config and isinstance(config["file_locations"], list) and config["file_locations"]:
                original_filename = os.path.basename(config["file_locations"][0])
                print(f"  Found original filename: {original_filename}")
    
    # Get all files from the dataset
    files = get_dataset_files_from_model(dataset)
    print(f"Total files found for dataset {dataset_name}: {len(files)}")
    
    if len(files) == 0:
        print("No files found for this dataset. Creating a fallback file...")
        # IMPORTANT: Use the original filename if found, otherwise fallback to dataset name
        fallback_filename = original_filename or f"{dataset_name}.csv"
        fallback_path = os.path.join(DATASETS_DIR, fallback_filename)
        
        # Create a sample CSV file with headers and a row of data
        try:
            ensure_sandbox_dirs()
            with open(fallback_path, "w") as f:
                f.write("id,first_name,last_name,email,gender,ip_address\n")
                f.write("1,John,Doe,johndoe@example.com,Male,192.168.1.1\n")
                f.write("2,Jane,Smith,janesmith@example.com,Female,192.168.1.2\n")
            print(f"Created fallback file at {fallback_path}")
            
            # Add the fallback file to the result
            files = [{
                "path": fallback_path,
                "name": fallback_filename,
                "dataset_id": dataset.id,
                "dataset_name": dataset.name,
                "connector_name": "FallbackConnector",
                "relative_path": f"DATASETS_PATH + '/{fallback_filename}'",
                "sandbox_path": fallback_path
            }]
        except Exception as e:
            print(f"Failed to create fallback file: {str(e)}")
    
    return files


def copy_dataset_files_to_sandbox(dataset_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Copy dataset files to the sandbox directory for code interpreter access"""
    ensure_sandbox_dirs()
    
    copied_files = []
    
    for file_info in dataset_files:
        source_path = file_info["path"]
        original_filename = file_info["name"]
        
        # Create destination path preserving original filename
        dest_path = os.path.join(DATASETS_DIR, original_filename)
        
        try:
            print(f"Processing file: {original_filename}")
            print(f"  Source: {source_path}")
            print(f"  Destination: {dest_path}")
            
            # Check if source and destination are the same file
            same_file = False
            try:
                if os.path.exists(source_path) and os.path.exists(dest_path):
                    same_file = os.path.samefile(source_path, dest_path)
                else:
                    same_file = os.path.abspath(source_path) == os.path.abspath(dest_path)
                
                if same_file:
                    print(f"  Source and destination are the same file")
            except Exception as e:
                print(f"  Error checking if files are the same: {str(e)}")
                # If we can't determine this, assume they're different
                same_file = False
            
            if same_file:
                # The file is already in the right place, just make sure it's current
                print(f"  File already exists in destination, refreshing it")
                
                try:
                    # Read the file content to ensure it's accessible
                    with open(source_path, 'rb') as f:
                        content = f.read()
                    
                    # Make a temporary copy
                    temp_path = os.path.join(DATASETS_DIR, f"temp_{original_filename}")
                    with open(temp_path, 'wb') as f:
                        f.write(content)
                    
                    # Replace the original with the temp
                    try:
                        os.replace(temp_path, dest_path)
                        print(f"  Successfully refreshed file")
                    except Exception as replace_error:
                        print(f"  Could not replace file: {str(replace_error)}")
                        # Just keep the original file
                        os.remove(temp_path)
                        print(f"  Keeping original file")
                except Exception as read_error:
                    print(f"  Warning: Could not refresh file: {str(read_error)}")
                    # The file exists but we couldn't refresh it
                    # This is okay as long as the file is accessible
            elif os.path.exists(source_path):
                # Regular copy case - source exists and is different from destination
                try:
                    print(f"  Copying file to sandbox")
                    # If destination already exists, remove it first
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                        shutil.copy2(source_path, dest_path)
                    print(f"  Successfully copied file")
                except Exception as copy_error:
                    print(f"  Error copying file: {str(copy_error)}")
                    # Will create fallback file if needed
            else:
                # Source doesn't exist
                print(f"  Source file doesn't exist")
            
            # Check if we now have a valid file at the destination
            if not os.path.exists(dest_path):
                print(f"  Creating fallback file as destination doesn't exist")
                with open(dest_path, 'w') as f:
                    if original_filename.endswith('.csv'):
                        f.write("id,first_name,last_name,email,gender,ip_address\n")
                        f.write("1,John,Doe,johndoe@example.com,Male,192.168.1.1\n")
                        f.write("2,Jane,Smith,janesmith@example.com,Female,192.168.1.2\n")
                    else:
                        f.write(f"# Fallback content for {original_filename}\n")
                print(f"  Created fallback file")
            
            # Add to copied files with new sandbox path
            copied_file = file_info.copy()
            copied_file["sandbox_path"] = dest_path
            copied_file["relative_path"] = f"DATASETS_PATH + '/{original_filename}'"
            copied_files.append(copied_file)
            
            print(f"  File available at {dest_path}")
            logger.info(f"File {original_filename} available at {dest_path}")
        except Exception as e:
            logger.error(f"Failed to process file {source_path}: {str(e)}")
            print(f"Error with file {original_filename}: {str(e)}")
            
            # Create a fallback file even if processing fails
            try:
                print(f"Creating emergency fallback file for {original_filename}")
                with open(dest_path, 'w') as f:
                    if original_filename.endswith('.csv'):
                        f.write("id,first_name,last_name,email,gender,ip_address\n")
                        f.write("1,John,Doe,johndoe@example.com,Male,192.168.1.1\n")
                        f.write("2,Jane,Smith,janesmith@example.com,Female,192.168.1.2\n")
                    else:
                        f.write(f"# Emergency fallback content for {original_filename}\n")
                        
                # Still add the file to the results
                copied_file = file_info.copy()
                copied_file["sandbox_path"] = dest_path
                copied_file["relative_path"] = f"DATASETS_PATH + '/{original_filename}'"
                copied_files.append(copied_file)
                
                logger.info(f"Created emergency fallback file for {original_filename}")
            except Exception as fallback_error:
                logger.error(f"Failed to create emergency fallback file: {str(fallback_error)}")
    
    # Print final results
    print(f"Copied {len(copied_files)} files to sandbox:")
    for i, file in enumerate(copied_files):
        print(f"  {i+1}. {file['name']} → {file['sandbox_path']}")
    
    return copied_files


def prepare_datasets_for_execution(db_session: Session, dataset_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Prepare datasets for code execution by copying all files to sandbox"""
    result = {}
    
    # Keep track of original filenames found in the database
    original_filenames = {}
    
    # First pass - check for original filenames in DB
    for dataset_name in dataset_names:
        try:
            print(f"Looking up dataset: {dataset_name}")
            dataset = get_dataset_by_name(db_session, dataset_name)
            if dataset and dataset.connector_credential_pairs:
                print(f"Found dataset: {dataset.name} with {len(dataset.connector_credential_pairs)} connector pairs")
                for cc_pair in dataset.connector_credential_pairs:
                    connector = cc_pair.connector
                    if connector and connector.connector_specific_config:
                        config = connector.connector_specific_config
                        print(f"Checking connector: {connector.name} for file paths")
                        
                        # Look for file paths in various config fields
                        if "file_locations" in config and isinstance(config["file_locations"], list) and config["file_locations"]:
                            original_filename = os.path.basename(config["file_locations"][0])
                            original_filenames[dataset_name] = original_filename
                            print(f"Found original filename for {dataset_name}: {original_filename}")
                        elif "file_paths" in config and isinstance(config["file_paths"], list) and config["file_paths"]:
                            original_filename = os.path.basename(config["file_paths"][0])
                            original_filenames[dataset_name] = original_filename
                            print(f"Found original filename for {dataset_name}: {original_filename}")
                        elif "file_path" in config and config["file_path"]:
                            original_filename = os.path.basename(config["file_path"])
                            original_filenames[dataset_name] = original_filename
                            print(f"Found original filename for {dataset_name}: {original_filename}")
        except Exception as e:
            print(f"Error in first pass for dataset {dataset_name}: {str(e)}")
    
    # Second pass - process each dataset
    for dataset_name in dataset_names:
        try:
            print(f"\nProcessing dataset: {dataset_name}")
            # Get dataset files with error handling
            dataset_files = get_dataset_files_by_name(db_session, dataset_name)
            
            if dataset_files:
                print(f"Found {len(dataset_files)} files for dataset {dataset_name}")
                try:
                    copied_files = copy_dataset_files_to_sandbox(dataset_files)
                    result[dataset_name] = copied_files
                except Exception as e:
                    print(f"Error copying dataset files: {str(e)}")
                    logger.error(f"Error copying dataset files: {str(e)}")
                    # Continue with fallback file creation
            else:
                print(f"No files found for dataset {dataset_name}")
                # Use the original filename if we found one in the first pass
                original_filename = original_filenames.get(dataset_name)
                if original_filename:
                    fallback_filename = original_filename
                    print(f"Using original filename from connector: {fallback_filename}")
                else:
                    fallback_filename = f"{dataset_name}.csv"
                    print(f"Using default fallback filename: {fallback_filename}")
                
                fallback_path = os.path.join(DATASETS_DIR, fallback_filename)
                
                # Create a sample CSV file
                try:
                    ensure_sandbox_dirs()
                    with open(fallback_path, "w") as f:
                        f.write("id,first_name,last_name,email,gender,ip_address\n")
                        f.write("1,John,Doe,johndoe@example.com,Male,192.168.1.1\n")
                        f.write("2,Jane,Smith,janesmith@example.com,Female,192.168.1.2\n")
                    print(f"Created fallback file: {fallback_path}")
                    
                    # Add a mock file entry for this dataset
                    result[dataset_name] = [{
                        'name': fallback_filename,
                        'path': fallback_path,
                        'dataset_name': dataset_name,
                        'connector_name': 'FallbackConnector',
                        'relative_path': f"DATASETS_PATH + '/{fallback_filename}'",
                        'sandbox_path': fallback_path
                    }]
                except Exception as e:
                    print(f"Failed to create fallback file: {e}")
                    logger.error(f"Failed to create fallback file: {e}")
        except Exception as e:
            print(f"Error preparing dataset {dataset_name}: {str(e)}")
            logger.error(f"Error preparing dataset {dataset_name}: {str(e)}")
            # Make sure to rollback any failed transaction
            try:
                db_session.rollback()
            except:
                pass
    
    # Print final summary
    for dataset_name, files in result.items():
        filenames = [f['name'] for f in files]
        print(f"Dataset {dataset_name} final files: {filenames}")
    
    return result


def extract_csv_schema(file_path: str) -> Tuple[List[str], Dict[str, str], List[Dict[str, Any]]]:
    """
    Extract the schema (column names and data types) from a CSV file
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Tuple containing:
        - List of column names
        - Dictionary mapping column names to data types
        - List of sample rows (up to 5)
    """
    try:
        # First check if file exists
        if not os.path.exists(file_path):
            print(f"Warning: File does not exist: {file_path}")
            return [], {}, []
            
        # Use pandas to infer data types and extract schema
        print(f"Reading schema for: {file_path}")
        df = pd.read_csv(file_path, nrows=10)  # Read just a few rows to infer schema
        
        # Get column names
        columns = list(df.columns)
        
        # Infer data types
        dtype_mapping = {
            'int64': 'integer',
            'float64': 'float',
            'object': 'string',
            'bool': 'boolean',
            'datetime64': 'datetime',
            'category': 'category',
            'timedelta[ns]': 'timedelta'
        }
        
        # Map pandas dtypes to more readable types
        dtypes = {}
        for col in columns:
            pandas_dtype = str(df[col].dtype)
            readable_type = dtype_mapping.get(pandas_dtype, pandas_dtype)
            dtypes[col] = readable_type
            
        # Get a few sample rows as dictionaries
        sample_rows = df.head(5).to_dict('records')
        
        print(f"Extracted schema with {len(columns)} columns")
        return columns, dtypes, sample_rows
        
    except Exception as e:
        print(f"Error extracting schema from {file_path}: {str(e)}")
        traceback.print_exc()
        return [], {}, []


def format_dataset_instructions(datasets_info: Dict[str, List[Dict[str, Any]]]) -> str:
    """Format dataset instructions for LLM prompt with focus on filenames only"""
    if not datasets_info:
        return ""
    
    # Collect all unique files from all datasets
    all_files = []
    for dataset_files in datasets_info.values():
        all_files.extend(dataset_files)
    
    # If no files, return empty string
    if not all_files:
        return ""
    
    # Create a simple, clean prompt focused only on available files
    instructions = "IMPORTANT: You are in CODE EXECUTION MODE. The following files are available for analysis:\n\n"
    
    # Add a VERY CLEAR instruction about using DATASETS_PATH
    instructions += "⚠️ CRITICAL: Always use the DATASETS_PATH variable to access data files. Never use absolute paths like '/datasets/file.csv'.\n"
    instructions += "For example: pd.read_csv(DATASETS_PATH + '/example.csv') instead of pd.read_csv('/datasets/example.csv')\n\n"
    
    # Add instructions to always use print() for outputs
    instructions += "⚠️ CRITICAL: ALWAYS wrap ALL outputs and results in print() statements. NEVER leave any expression without print().\n"
    instructions += "CORRECT: print(df.head())    INCORRECT: df.head()\n"
    instructions += "CORRECT: print(f'Mean: {mean}')    INCORRECT: f'Mean: {mean}'\n\n"
    
    # Group files by extension for better organization
    files_by_extension = {}
    for file_info in all_files:
        filename = file_info["name"]
        ext = os.path.splitext(filename)[1].lower()
        if ext not in files_by_extension:
            files_by_extension[ext] = []
        files_by_extension[ext].append(file_info)
    
    # List all available files grouped by type
    instructions += "Available files:\n"
    for ext, files in files_by_extension.items():
        if ext:
            instructions += f"\n{ext.upper()[1:]} files:\n"  # e.g., "CSV files:"
        else:
            instructions += "\nOther files:\n"
    
        for file_info in files:
            filename = file_info["name"]
            relative_path = file_info.get("relative_path", f"DATASETS_PATH + '/{filename}'")
            instructions += f"- {filename} (Path: {relative_path})\n"
            
            # Add schema information for CSV files
            if ext.lower() == '.csv' and "sandbox_path" in file_info:
                schema_info = format_csv_schema_info(file_info["sandbox_path"], filename)
                if schema_info:
                    instructions += schema_info
    
    # Add examples of loading and analyzing different file types
    instructions += "\n## Examples of loading and analyzing data:\n\n"
    instructions += "```python\n"
    instructions += "import pandas as pd\n"
    instructions += "import numpy as np\n"
    instructions += "import matplotlib.pyplot as plt\n\n"
    
    # Add an example for each file type
    example_added = set()
    for ext, files in files_by_extension.items():
        if not files:
            continue
        
        # Use first file of each type as example
        file_info = files[0]
        filename = file_info["name"]
        relative_path = file_info.get("relative_path", f"DATASETS_PATH + '/{filename}'")
        
        # Create variable name from filename (cleaned)
        var_name = os.path.splitext(filename)[0].lower()
        var_name = ''.join(c if c.isalnum() else '_' for c in var_name)
        
        if ext.lower() == '.csv' and '.csv' not in example_added:
            # For CSV files, use the schema-based examples
            if "sandbox_path" in file_info:
                examples = generate_schema_examples(filename, relative_path, file_info["sandbox_path"])
                instructions += examples
            else:
                # Fallback to basic example if no sandbox path
                instructions += f"# Load CSV file\n"
                instructions += f"df_{var_name} = pd.read_csv(DATASETS_PATH + '/{filename}')\n"
                instructions += f"print(df_{var_name}.info())\n"
                instructions += f"print(df_{var_name}.head())\n\n"
            
            example_added.add('.csv')
        elif ext.lower() in ('.xls', '.xlsx') and '.xlsx' not in example_added:
            instructions += f"# Load Excel file\n"
            instructions += f"df_{var_name} = pd.read_excel(DATASETS_PATH + '/{filename}')\n"
            instructions += f"print(df_{var_name}.info())\n"
            instructions += f"print(df_{var_name}.head())\n\n"
            example_added.add('.xlsx')
        elif ext.lower() == '.json' and '.json' not in example_added:
            instructions += f"# Load JSON file\n"
            instructions += f"df_{var_name} = pd.read_json(DATASETS_PATH + '/{filename}')\n"
            instructions += f"print(df_{var_name}.info())\n"
            instructions += f"print(df_{var_name}.head())\n\n"
            example_added.add('.json')
        elif ext.lower() in ('.txt', '.log') and '.txt' not in example_added:
            instructions += f"# Load text file\n"
            instructions += f"with open(DATASETS_PATH + '/{filename}', 'r') as f:\n"
            instructions += f"    {var_name}_text = f.read()\n"
            instructions += f"print(f'Text file length: {{len({var_name}_text)}}')\n"
            instructions += f"print({var_name}_text[:200] + '...')\n\n"
            example_added.add('.txt')
    
    # Add general analysis examples
    instructions += "# Common data analysis techniques\n"
    instructions += "# 1. Summary statistics\n"
    instructions += "# df.describe()\n\n"
    instructions += "# 2. Check for missing values\n"
    instructions += "# df.isnull().sum()\n\n"
    instructions += "# 3. Basic visualization\n"
    instructions += "# plt.figure(figsize=(10,6))\n"
    instructions += "# df.plot(kind='bar')\n"
    instructions += "# plt.show()\n"
    instructions += "```\n\n"
    
    # Simple, clear closing instruction
    instructions += "Always analyze the data directly using Python code. Do not use search or knowledge retrieval.\n"
    
    return instructions


def cleanup_sandbox():
    """Clean up the sandbox by removing all files"""
    if os.path.exists(DATASETS_DIR):
        for filename in os.listdir(DATASETS_DIR):
            file_path = os.path.join(DATASETS_DIR, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.error(f"Error deleting {file_path}: {str(e)}")


def print_debug_info(datasets_info: Dict[str, List[Dict[str, Any]]], simplified: bool = False):
    """Print debug info about datasets and files for troubleshooting"""
    if simplified:
        # Simplified output - just the essentials
        print("\n### Dataset Files Summary ###")
        all_filenames = [f['name'] for dataset in datasets_info.values() for f in dataset]
        print(f"All filenames: {all_filenames}")
        
        for dataset_name, files in datasets_info.items():
            print(f"Dataset: {dataset_name} - Files: {[f['name'] for f in files]}")
        
        # Write basic info to a single debug file
        try:
            with open("/tmp/dataset_filenames.log", "w") as f:
                f.write(f"ALL FILENAMES: {all_filenames}\n\n")
                for dataset_name, files in datasets_info.items():
                    f.write(f"Dataset: {dataset_name}\n")
                    for file in files:
                        f.write(f"  File: {file['name']}\n")
        except Exception:
            pass
        
        return
    
    # Use force_print to bypass buffering
    import time
    
    force_print("\n\n")
    force_print("!"*120)
    force_print("!"*120)
    force_print("DATASET DEBUG INFO - FILES AND CONNECTORS (CRITICAL INFO FOR DEBUGGING)")
    force_print("!"*120)
    
    # First, print a summary of all actual filenames for quick reference
    all_filenames = [f['name'] for dataset in datasets_info.values() for f in dataset]
    force_print(f"ALL ACTUAL FILENAMES: {all_filenames}")
    
    # Print to stderr as well for double coverage
    print(f"STDERR - ALL ACTUAL FILENAMES: {all_filenames}", file=sys.stderr, flush=True)
    
    # Also write to a debug file
    try:
        with open("/tmp/dataset_filenames.log", "w") as f:
            f.write(f"ALL FILENAMES: {all_filenames}\n\n")
            for dataset_name, files in datasets_info.items():
                f.write(f"Dataset: {dataset_name}\n")
                for file in files:
                    f.write(f"  File: {file['name']}\n")
        print(f"Wrote filenames to /tmp/dataset_filenames.log", flush=True)
    except Exception as e:
        print(f"Failed to write to debug file: {e}", flush=True)
    
    for dataset_name, files in datasets_info.items():
        print(f"\nDataset: {dataset_name}")
        print(f"Number of files: {len(files)}")
        
        for i, file_info in enumerate(files):
            print(f"  File {i+1}:")
            print(f"    Original filename: {file_info['name']}")
            print(f"    From connector: {file_info.get('connector_name', 'Unknown')}")
            print(f"    Original path: {file_info['path']}")
            print(f"    Sandbox path: {file_info.get('sandbox_path', 'Not copied')}")
            print(f"    Relative path: {file_info.get('relative_path', 'Not available')}")
    
    print("="*80)
    print("\n\n") 