import os
import shutil
import time
from pathlib import Path
from typing import IO

from onyx.file_store.file_store import get_default_file_store
from onyx.utils.logger import setup_logger
from sqlalchemy.orm import Session

logger = setup_logger()

# Default dataset directory path (relative to sandbox)
DEFAULT_DATASET_DIR = "../code_sandbox/datasets"


def get_dataset_directory_path(dataset_dir: str = DEFAULT_DATASET_DIR) -> str:
    """
    Get the absolute path to the dataset directory.
    Create the directory if it doesn't exist.
    """
    # Convert to absolute path
    dataset_path = Path(dataset_dir).resolve()
    
    # Create directory if it doesn't exist
    dataset_path.mkdir(parents=True, exist_ok=True)
    
    return str(dataset_path)


def copy_file_to_sandbox(
    file_id: str,
    file_name: str,
    db_session: Session,
    dataset_dir: str = DEFAULT_DATASET_DIR,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> str:
    """
    Copy a file from the file store to the sandbox dataset directory.
    
    Args:
        file_id: The file ID in the file store
        file_name: The desired file name in the dataset directory
        db_session: Database session
        dataset_dir: Path to dataset directory (default: "./datasets")
        max_retries: Maximum number of retry attempts for large files
        retry_delay: Delay between retries in seconds
    
    Returns:
        str: The full path where the file was copied
        
    Raises:
        Exception: If file copying fails after all retries
    """
    logger.notice(f"[DATASET_COPY_DEBUG] copy_file_to_sandbox called for {file_name} (ID: {file_id})")
    logger.notice(f"[DATASET_COPY_DEBUG] Dataset directory: {dataset_dir}")
    
    dataset_path = get_dataset_directory_path(dataset_dir)
    destination_file_path = os.path.join(dataset_path, file_name)
    
    logger.notice(f"[DATASET_COPY_DEBUG] Dataset path resolved to: {dataset_path}")
    logger.notice(f"[DATASET_COPY_DEBUG] Destination file path: {destination_file_path}")
    
    # Get file store instance
    file_store = get_default_file_store(db_session)
    logger.notice(f"[DATASET_COPY_DEBUG] Got file store instance: {type(file_store)}")
    
    logger.notice(f"[DATASET_COPY_DEBUG] Starting copy of dataset file {file_name} (ID: {file_id}) to {destination_file_path}")
    
    for attempt in range(max_retries):
        logger.notice(f"[DATASET_COPY_DEBUG] Attempt {attempt + 1}/{max_retries}")
        try:
            # Read file from file store
            logger.notice(f"[DATASET_COPY_DEBUG] Reading file {file_id} from file store...")
            file_io: IO = file_store.read_file(file_id, mode="b")
            logger.notice(f"[DATASET_COPY_DEBUG] File read successfully from file store")
            
            # Write to destination with buffered copy for large files
            logger.notice(f"[DATASET_COPY_DEBUG] Writing to destination file: {destination_file_path}")
            with open(destination_file_path, "wb") as dest_file:
                # Copy in chunks to handle large files efficiently
                chunk_size = 64 * 1024  # 64KB chunks
                bytes_copied = 0
                
                while True:
                    chunk = file_io.read(chunk_size)
                    if not chunk:
                        break
                    dest_file.write(chunk)
                    bytes_copied += len(chunk)
                
                # Ensure all data is written to disk
                dest_file.flush()
                os.fsync(dest_file.fileno())
            
            logger.notice(f"[DATASET_COPY_DEBUG] Wrote {bytes_copied} bytes to destination")
            
            # Verify file was copied successfully
            if os.path.exists(destination_file_path):
                file_size = os.path.getsize(destination_file_path)
                logger.notice(f"[DATASET_COPY_DEBUG] Successfully copied dataset file {file_name} ({file_size} bytes) to sandbox on attempt {attempt + 1}")
                return destination_file_path
            else:
                raise Exception(f"File {destination_file_path} does not exist after copy")
                
        except Exception as e:
            error_msg = f"Attempt {attempt + 1}/{max_retries} failed to copy {file_name}: {str(e)}"
            
            if attempt < max_retries - 1:
                logger.warning(f"[DATASET_COPY_DEBUG] {error_msg}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                # Increase delay for next retry (exponential backoff)
                retry_delay *= 1.5
            else:
                logger.error(f"[DATASET_COPY_DEBUG] {error_msg}. No more retries.")
                # Clean up partial file if it exists
                if os.path.exists(destination_file_path):
                    try:
                        os.remove(destination_file_path)
                        logger.notice(f"[DATASET_COPY_DEBUG] Cleaned up partial file {destination_file_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"[DATASET_COPY_DEBUG] Failed to clean up partial file {destination_file_path}: {cleanup_error}")
                raise Exception(f"Failed to copy dataset file {file_name} after {max_retries} attempts: {str(e)}")
    
    # This should never be reached, but just in case
    raise Exception(f"Unexpected error: Failed to copy dataset file {file_name}")


def copy_multiple_files_to_sandbox(
    file_mappings: list[tuple[str, str]],
    db_session: Session,
    dataset_dir: str = DEFAULT_DATASET_DIR
) -> list[str]:
    """
    Copy multiple files to the sandbox dataset directory.
    
    Args:
        file_mappings: List of (file_id, file_name) tuples
        db_session: Database session
        dataset_dir: Path to dataset directory
    
    Returns:
        list[str]: List of destination file paths for successfully copied files
        
    Raises:
        Exception: If any file copying fails
    """
    logger.notice(f"[DATASET_COPY_DEBUG] copy_multiple_files_to_sandbox called with {len(file_mappings)} files")
    logger.notice(f"[DATASET_COPY_DEBUG] Dataset directory: {dataset_dir}")
    logger.notice(f"[DATASET_COPY_DEBUG] File mappings: {file_mappings}")
    
    copied_files = []
    failed_files = []
    
    for file_id, file_name in file_mappings:
        logger.notice(f"[DATASET_COPY_DEBUG] Processing file: {file_name} (ID: {file_id})")
        try:
            destination_path = copy_file_to_sandbox(file_id, file_name, db_session, dataset_dir)
            copied_files.append(destination_path)
            logger.notice(f"[DATASET_COPY_DEBUG] Successfully copied {file_name} to {destination_path}")
        except Exception as e:
            failed_files.append((file_name, str(e)))
            logger.error(f"[DATASET_COPY_DEBUG] Failed to copy dataset file {file_name}: {str(e)}")
    
    if failed_files:
        # Clean up successfully copied files if any failed
        for copied_file in copied_files:
            try:
                if os.path.exists(copied_file):
                    os.remove(copied_file)
                    logger.notice(f"[DATASET_COPY_DEBUG] Cleaned up {copied_file} due to overall failure")
            except Exception as cleanup_error:
                logger.warning(f"[DATASET_COPY_DEBUG] Failed to clean up {copied_file}: {cleanup_error}")
        
        failed_names = [name for name, _ in failed_files]
        raise Exception(f"Failed to copy dataset files: {', '.join(failed_names)}")
    
    logger.notice(f"[DATASET_COPY_DEBUG] Successfully copied {len(copied_files)} dataset files to sandbox")
    return copied_files


def remove_dataset_file(file_name: str, dataset_dir: str = DEFAULT_DATASET_DIR) -> bool:
    """
    Remove a dataset file from the sandbox directory.
    
    Args:
        file_name: Name of the file to remove
        dataset_dir: Path to dataset directory
    
    Returns:
        bool: True if file was removed successfully, False otherwise
    """
    dataset_path = get_dataset_directory_path(dataset_dir)
    file_path = os.path.join(dataset_path, file_name)
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.notice(f"Removed dataset file {file_name} from sandbox")
            return True
        else:
            logger.warning(f"Dataset file {file_name} not found in sandbox")
            return False
    except Exception as e:
        logger.error(f"Failed to remove dataset file {file_name}: {str(e)}")
        return False


def cleanup_dataset_directory(dataset_dir: str = DEFAULT_DATASET_DIR) -> int:
    """
    Clean up all files in the dataset directory.
    
    Args:
        dataset_dir: Path to dataset directory
    
    Returns:
        int: Number of files removed
    """
    dataset_path = get_dataset_directory_path(dataset_dir)
    removed_count = 0
    
    try:
        for file_name in os.listdir(dataset_path):
            file_path = os.path.join(dataset_path, file_name)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove {file_path}: {str(e)}")
        
        logger.notice(f"Cleaned up {removed_count} files from dataset directory")
        return removed_count
    except Exception as e:
        logger.error(f"Failed to cleanup dataset directory: {str(e)}")
        return removed_count 