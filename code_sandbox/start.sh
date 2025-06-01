#!/bin/bash

# Start script for Code Execution Service

echo "Starting Code Execution Service..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Set environment variables
export HOST=${HOST:-127.0.0.1}
export PORT=${PORT:-8001}

# Create datasets directory if it doesn't exist
mkdir -p ./datasets

echo "Code Execution Service will be available at http://$HOST:$PORT"
echo "Health check: http://$HOST:$PORT/health"
echo "API docs: http://$HOST:$PORT/docs"

# Start the service
python main.py 