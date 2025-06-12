#!/usr/bin/env python3
"""
Reliable Code Sandbox Service Runner
Fixes HTTP request handling issues
"""

import os
import logging
from pathlib import Path
import uvicorn

# Import our FastAPI app
from main import app, RESOLVED_ALLOWED_BASE_PATH

def main():
    port = int(os.getenv("PORT", "8856"))
    host = os.getenv("HOST", "127.0.0.1")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting Code Execution Service on {host}:{port}")
    
    if RESOLVED_ALLOWED_BASE_PATH is None:
        logger.critical(
            "CRITICAL: EXEC_ALLOWED_BASE_PATH is not configured correctly. "
            "File operations within executed code will be denied."
        )
    else:
        logger.info(f"Allowed base path: {RESOLVED_ALLOWED_BASE_PATH}")
    
    # Configure uvicorn with better settings
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        reload=False,
        log_level="info",
        access_log=True,
        loop="asyncio",
        http="httptools",
        ws="websockets",
        workers=1,
        backlog=2048,
        limit_concurrency=1000,
        limit_max_requests=1000,
        timeout_keep_alive=5,
        timeout_graceful_shutdown=10
    )
    
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    main() 