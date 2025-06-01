import os
import sys
import io
import traceback
# import contextlib # Not used in the latest snippet
import tempfile
# import subprocess # Not used
import logging
from typing import Any, Dict, List, Optional # List, Dict, Any not directly used in signature but good for general typing
from pathlib import Path # Used for path manipulation

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import builtins # To access the original open

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration for Allowed Path ---
# Define the root directory for allowed file operations.
# Get from environment variable or use a default relative to the script.
# IMPORTANT: Ensure this path is properly secured and intended for this purpose.
RAW_ALLOWED_BASE_PATH = os.environ.get("EXEC_ALLOWED_BASE_PATH", "./datasets")
RESOLVED_ALLOWED_BASE_PATH: Optional[Path] = None

try:
    # Ensure the directory exists or can be created
    _temp_path = Path(os.path.expanduser(RAW_ALLOWED_BASE_PATH))
    _temp_path.mkdir(parents=True, exist_ok=True) # Create if not exists
    RESOLVED_ALLOWED_BASE_PATH = _temp_path.resolve(strict=True) # strict=True ensures it exists now
    logger.info(f"Allowed base path for file operations: {RESOLVED_ALLOWED_BASE_PATH}")
except Exception as e:
    logger.error(
        f"Configuration error: EXEC_ALLOWED_BASE_PATH '{RAW_ALLOWED_BASE_PATH}' is invalid, "
        f"not accessible, or could not be created: {e}. File operations will be restricted."
    )
    # If RESOLVED_ALLOWED_BASE_PATH remains None, _is_path_allowed will deny all.

app = FastAPI(title="Code Execution Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeExecutionRequest(BaseModel):
    code: str
    language: str = "python"
    timeout: int = 30

class CodeExecutionResponse(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    execution_time: Optional[float] = None


def _is_path_allowed(filepath_arg: Any, operation_mode: str = 'r') -> bool:
    """
    Checks if a given filepath is within the RESOLVED_ALLOWED_BASE_PATH.
    Handles strings and Path objects. Allows non-path objects (like URLs for pandas) to pass through.
    """
    if RESOLVED_ALLOWED_BASE_PATH is None:
        logger.warning("File operations are effectively disabled due to unconfigured/invalid EXEC_ALLOWED_BASE_PATH.")
        return False

    if not isinstance(filepath_arg, (str, Path)):
        return True # Not a local filesystem path string/object (e.g., could be a URL for pandas, or a buffer)

    try:
        # Expand user tilde, convert to Path object
        expanded_path = Path(os.path.expanduser(str(filepath_arg)))

        # For read operations, or operations where the file/dir is expected to exist:
        # We resolve to a canonical, absolute path.
        # For write operations to a new file, the file itself won't exist,
        # so .resolve(strict=True) would fail. We check its parent.
        
        final_path_to_check: Path
        if any(m in operation_mode for m in ['w', 'a', 'x', '+']): # Write, append, create
            # If writing, the file might not exist. Resolve its intended parent.
            # If path is 'new_file.txt', parent is '.'. If 'dir/new_file.txt', parent is 'dir'.
            # We need the absolute path of the parent.
            if expanded_path.is_absolute():
                parent_dir_to_resolve = expanded_path.parent
            else:
                # Convert to absolute path first based on CWD, then get parent
                parent_dir_to_resolve = Path(os.getcwd(), expanded_path).parent
            
            # Now resolve the parent directory
            final_path_to_check = parent_dir_to_resolve.resolve(strict=True) # Parent must exist
            # And ensure the final path (file itself) is also under the resolved parent
            # This check ensures we are not writing to `ALLOWED_BASE_PATH` itself if it's a file
            # and path_arg was like `../ALLOWED_BASE_PATH_filename`
            intended_file_abs_path = parent_dir_to_resolve.joinpath(expanded_path.name).resolve(strict=False)
            if not (intended_file_abs_path.parent == final_path_to_check):
                 # This can happen with tricky paths like ../filename that try to escape
                 logger.warning(f"Path traversal attempt detected for write: {filepath_arg}")
                 return False

        else: # Read or other modes assuming path exists
            final_path_to_check = expanded_path.resolve(strict=True) # Path must exist

        # Check if the resolved path is within or is the allowed base path
        # Path.is_relative_to() is Python 3.9+
        # str(final_path_to_check).startswith(str(RESOLVED_ALLOWED_BASE_PATH)) is an alternative
        is_safe = (final_path_to_check == RESOLVED_ALLOWED_BASE_PATH or
                   final_path_to_check.is_relative_to(RESOLVED_ALLOWED_BASE_PATH))
        
        if not is_safe:
            logger.warning(f"Path '{filepath_arg}' (resolved to '{final_path_to_check}') is outside allowed base '{RESOLVED_ALLOWED_BASE_PATH}'.")
        return is_safe

    except FileNotFoundError:
        logger.warning(f"Path resolution failed for '{filepath_arg}' (FileNotFoundError). Operation denied.")
        return False # Path (or its parent for writes) does not exist
    except Exception as e:
        logger.error(f"Error during path validation for '{filepath_arg}': {e}")
        return False


# Store the original open function
_original_open = builtins.open

def safe_custom_open(file: Any, mode: str = 'r', *args, **kwargs):
    """
    A wrapper around the original builtins.open that checks if the file path is allowed.
    """
    if not _is_path_allowed(file, operation_mode=mode):
        raise PermissionError(
            f"File access to '{file}' is restricted. Ensure it is within the allowed project directory: {RESOLVED_ALLOWED_BASE_PATH}"
        )
    return _original_open(file, mode, *args, **kwargs)


def execute_python_code(code: str, timeout: int = 30) -> tuple[bool, str, Optional[str], float]:
    import time
    start_time = time.time()

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        namespace = {
            '__builtins__': __builtins__, # Standard builtins
            'open': safe_custom_open,      # Our SAFE open function
            'pd': None,
            'np': None,
            'plt': None,
            'os': os, # Be cautious exposing 'os'. Users could try os.chdir or other fs ops.
                      # Consider providing a limited 'os' or specific functions.
            'sys': sys, # Similar caution for 'sys'
        }

        # Try to import common libraries and make them available
        # Their file I/O operations (like pd.read_csv) should eventually call our `safe_custom_open`
        # if they operate on local files.
        try:
            import pandas as pd
            namespace['pd'] = pd
        except ImportError:
            pass
        try:
            import numpy as np
            namespace['np'] = np
        except ImportError:
            pass
        try:
            import matplotlib.pyplot as plt
            namespace['plt'] = plt
        except ImportError:
            pass

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
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        return False, stdout_capture.getvalue(), error_msg, execution_time
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


@app.get("/")
async def root():
    return {"message": "Code Execution Service is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "code-execution"}

@app.post("/execute", response_model=CodeExecutionResponse)
async def execute_code_endpoint(request: CodeExecutionRequest):
    try:
        logger.info(f"Executing {request.language} code...")
        logger.debug(f"Code: {request.code[:200]}...") # Log more chars for context

        if request.language.lower() != "python":
            raise HTTPException(
                status_code=400,
                detail=f"Language '{request.language}' is not supported. Only Python is currently supported."
            )
        
        if RESOLVED_ALLOWED_BASE_PATH is None and "open(" in request.code: # Basic check
             logger.warning("Attempt to use file operations while EXEC_ALLOWED_BASE_PATH is not configured.")
             # Depending on policy, you might want to reject earlier or let safe_custom_open handle it.

        success, output, error, execution_time = execute_python_code(
            code=request.code,
            timeout=request.timeout
        )

        logger.info(f"Code execution completed. Success: {success}, Time: {execution_time:.2f}s")
        if error:
            logger.warning(f"Execution error: {error[:200]}...")


        return CodeExecutionResponse(
            success=success,
            output=output,
            error=error,
            execution_time=execution_time
        )

    except Exception as e:
        logger.error(f"Error executing code: {str(e)}")
        logger.exception("Detailed error during code execution endpoint:")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/execute-file")
async def execute_file_endpoint(file_path: str):
    """
    Execute a Python file and return the result.
    The file_path itself MUST be within the RESOLVED_ALLOWED_BASE_PATH.
    """
    try:
        # First, check if the script file itself is allowed to be read
        if not _is_path_allowed(file_path, operation_mode='r'):
            raise HTTPException(status_code=403, detail=f"Access to script file '{file_path}' is not permitted.")

        # Convert to absolute path to be sure, though _is_path_allowed should handle it
        abs_script_path = Path(os.path.expanduser(file_path)).resolve(strict=True)

        if not abs_script_path.exists(): # Should have been caught by _is_path_allowed's resolve(strict=True)
            raise HTTPException(status_code=404, detail=f"File not found: {abs_script_path}")

        with _original_open(abs_script_path, 'r') as f: # Use original open to read the script itself
            code = f.read()

        request_model = CodeExecutionRequest(code=code, language="python")
        return await execute_code_endpoint(request_model)

    except PermissionError as e: # Catch specific permission error from our checks
        logger.error(f"Permission denied for file '{file_path}': {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError:
         raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Error executing file '{file_path}': {str(e)}")
        logger.exception("Detailed error during file execution endpoint:")
        raise HTTPException(status_code=500, detail=f"Error executing file: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    host = os.getenv("HOST", "127.0.0.1")
    
    logger.info(f"Starting Code Execution Service on {host}:{port}")
    # Ensure ALLOWED_BASE_PATH is set, or log a clear warning if not.
    if RESOLVED_ALLOWED_BASE_PATH is None:
        logger.critical(
            f"CRITICAL: EXEC_ALLOWED_BASE_PATH ('{RAW_ALLOWED_BASE_PATH}') is not configured correctly. "
            "File operations within executed code will be denied. Please check the path and permissions."
        )
    
    # Make sure your filename matches "main:app" (e.g. if this file is main.py)
    uvicorn.run(
        "main:app", # Change "main" if your file is named differently
        host=host,
        port=port,
        reload=True, # Be careful with reload in "production" if stateful (RESOLVED_ALLOWED_BASE_PATH is ok)
        log_level="info"
    )