#!/usr/bin/env python
"""Code Interpreter Sandbox Service.

This service provides a secure sandbox for executing Python code snippets.
It exposes an API that allows the main application to execute code and get results.
"""

import json
import logging
import os
import sys
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join("logs", "code_interpreter.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("code_interpreter")

# Create directories if they don't exist
os.makedirs("logs", exist_ok=True)
os.makedirs("temp", exist_ok=True)
# Use the same environment variable for datasets path
DATASETS_DIR = os.environ.get("ONYX_DATASETS_DIR", os.path.join(os.getcwd(), "datasets"))
os.makedirs(DATASETS_DIR, exist_ok=True)
logger.info(f"DATASETS_DIR set to: {DATASETS_DIR}")

# Create FastAPI app
app = FastAPI(
    title="Code Interpreter Sandbox",
    description="A secure sandbox service for executing Python code",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session state
class CodeInterpreterState:
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset the interpreter state."""
        logger.info("Resetting interpreter state.")
        self.globals = {
            "__builtins__": __builtins__,
            "print": self.capture_print,
            "plt": None,  # Will be initialized on first use
            "pd": None,   # Will be initialized on first use
            "np": None,   # Will be initialized on first use
        }
        self.locals = {}
        self.output = []
        self.figures = []
        self.temp_files = []
        self.is_busy = False
    
    def capture_print(self, *args, **kwargs):
        """Capture print statements and store in output."""
        end = kwargs.get('end', '\n')
        sep = kwargs.get('sep', ' ')
        message = sep.join(str(arg) for arg in args) + end
        self.output.append({"type": "stdout", "data": message})
        logger.info(f"Captured print: {message.strip()}")
        
    def save_figure(self, fig):
        """Save a matplotlib figure to disk and add it to figures list."""
        import matplotlib.pyplot as plt
        
        # Create a unique filename
        filename = f"fig_{uuid.uuid4().hex}.png"
        filepath = os.path.join("temp", filename)
        
        logger.info(f"Attempting to save figure to: {filepath}")
        # Save the figure
        fig.savefig(filepath)
        self.temp_files.append(filepath)
        self.figures.append(filepath)
        
        # Add the figure path to output
        self.output.append({
            "type": "figure", 
            "data": filepath
        })
        
        # Close the figure to free memory
        plt.close(fig)
        logger.info(f"Figure saved and closed: {filepath}")
        
        return filepath

# Initialize interpreter state
interpreter = CodeInterpreterState()
logger.info("CodeInterpreterState initialized.")

# API Models
class CodeExecutionRequest(BaseModel):
    """Request model for code execution."""
    code: str = Field(..., description="Python code to execute")
    session_id: Optional[str] = Field(None, description="Session ID for maintaining state")

class CodeExecutionResponse(BaseModel):
    """Response model for code execution."""
    success: bool = Field(..., description="Whether execution was successful")
    output: List[Dict[str, Any]] = Field(default_factory=list, description="Captured output")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time: float = Field(..., description="Execution time in seconds")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.info(f"Health check requested. Busy status: {interpreter.is_busy}")
    return {"status": "ok", "busy": interpreter.is_busy}

@app.post("/restart", status_code=status.HTTP_200_OK)
async def restart():
    """Restart the interpreter, clearing all state."""
    logger.info("Restart endpoint called.")
    if interpreter.is_busy:
        logger.warning("Restart requested while interpreter is busy.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Interpreter is currently busy executing code"
        )
    
    # Clean up any temporary files
    for filepath in interpreter.temp_files:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Removed temporary file: {filepath}")
        except Exception as e:
            logger.error(f"Error removing temp file {filepath}: {e}")
    
    interpreter.reset()
    logger.info("Interpreter successfully restarted.")
    return {"status": "ok", "message": "Interpreter state has been reset"}

@app.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(request: CodeExecutionRequest):
    """Execute Python code in the sandbox and return the results."""
    logger.info(f"Execute endpoint called. Session ID: {request.session_id}")
    # Log the received code string
    logger.info(f"Code received for execution:\n---\n{request.code}\n---")
    
    if interpreter.is_busy:
        logger.warning("Execute requested while interpreter is busy.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Interpreter is currently busy executing code"
        )
    
    interpreter.is_busy = True
    start_time = datetime.now()
    response_data = None # Initialize response_data
    
    try:
        # Clear previous output
        interpreter.output = []
        interpreter.figures = []
        logger.info("Cleared previous interpreter output and figures.")
        
        # Execute the code
        exec_globals = interpreter.globals.copy()
        
        # Lazy import of popular libraries
        if "plt" in request.code and exec_globals["plt"] is None:
            logger.info("Detected 'plt' in code. Importing matplotlib.pyplot.")
            import matplotlib.pyplot as plt
            plt.switch_backend('agg')  # Non-interactive backend
            plt.rcParams.update({'figure.max_open_warning': 0})
            # Override savefig
            original_savefig = plt.savefig
            
            def custom_savefig(*args, **kwargs):
                logger.info(f"Custom savefig called with args: {args}, kwargs: {kwargs}")
                result = original_savefig(*args, **kwargs)
                if len(args) > 0:
                    filepath = args[0]
                    interpreter.output.append({
                        "type": "figure", 
                        "data": filepath
                    })
                    logger.info(f"Figure path added to output via savefig: {filepath}")
                return result
            
            plt.savefig = custom_savefig
            
            # Override show to save figures instead
            original_show = plt.show
            def custom_show(*args, **kwargs):
                logger.info(f"Custom plt.show() called.")
                fig = plt.gcf()
                interpreter.save_figure(fig)
            
            plt.show = custom_show
            
            exec_globals["plt"] = plt
        
        if "pd" in request.code and exec_globals["pd"] is None:
            logger.info("Detected 'pd' in code. Importing pandas.")
            import pandas as pd
            exec_globals["pd"] = pd
        
        if "np" in request.code and exec_globals["np"] is None:
            logger.info("Detected 'np' in code. Importing numpy.")
            import numpy as np
            exec_globals["np"] = np
        
        # Add additional imports and utilities
        if exec_globals.get("Path") is None:
            exec_globals["Path"] = Path
            logger.info("Added 'Path' to execution globals.")
        
        if exec_globals.get("json") is None:
            exec_globals["json"] = json
            logger.info("Added 'json' to execution globals.")
        
        # Add datasets path
        if exec_globals.get("DATASETS_PATH") is None:
            exec_globals["DATASETS_PATH"] = os.path.abspath(DATASETS_DIR)
            logger.info(f"Added 'DATASETS_PATH' to execution globals: {exec_globals['DATASETS_PATH']}")
        
        logger.info("Executing code...")
        exec(request.code, exec_globals, interpreter.locals)
        logger.info("Code execution finished.")
        
        # Check if a figure was created but not shown
        import matplotlib.pyplot as plt
        if plt.get_fignums():
            logger.info(f"Detected {len(plt.get_fignums())} unshown figures. Saving them.")
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                interpreter.save_figure(fig)
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Code executed successfully in {execution_time:.4f} seconds.")
        
        # Format any pandas DataFrames in the output
        for i, out in enumerate(interpreter.output):
            if out["type"] == "stdout" and isinstance(out["data"], str):
                if "<class 'pandas.core.frame.DataFrame'>" in out["data"]:
                    logger.info(f"Attempting to reformat DataFrame output at index {i}.")
                    for var_name, var_value in interpreter.locals.items():
                        import pandas as pd
                        if isinstance(var_value, pd.DataFrame):
                            df_repr = var_value.to_string()
                            interpreter.output[i]["data"] = f"DataFrame {var_name}:\n{df_repr}\n"
                            logger.info(f"Reformatted DataFrame '{var_name}' output.")
                            break
        
        response_data = CodeExecutionResponse(
            success=True,
            output=interpreter.output,
            execution_time=execution_time
        )
    
    except Exception as e:
        # Get traceback information
        error_message = f"{type(e).__name__}: {str(e)}"
        tb = traceback.format_exc()
        
        logger.error(f"Code execution error: {error_message}\n{tb}")
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        
        response_data = CodeExecutionResponse(
            success=False,
            output=interpreter.output, # Include any partial output before the error
            error=f"{error_message}\n\n{tb}",
            execution_time=execution_time
        )
    
    finally:
        interpreter.is_busy = False
        logger.info("Interpreter busy status set to False.")
        if response_data:
            # Log the execution result (the response object)
            # Using model_dump_json for a cleaner representation if it's a Pydantic model
            try:
                logger.info(f"Execution result being returned:\n---\n{response_data.model_dump_json(indent=2)}\n---")
            except AttributeError: # Fallback for non-Pydantic objects, though it should be
                logger.info(f"Execution result being returned:\n---\n{response_data}\n---")
        else:
            logger.error("Response data was not set before finally block.") # Should not happen

    return response_data # Return the prepared response

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8765))
    logger.info(f"Starting Uvicorn server on port {port}...")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)