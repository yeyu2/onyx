# Code Execution Service

A FastAPI-based service for executing Python code safely in a controlled environment. This service is designed to work with the Onyx dataset chat feature to provide code interpretation capabilities.

## Features

- **Safe Code Execution**: Executes Python code in a controlled environment with output capture
- **Data Science Libraries**: Pre-loaded with common libraries (pandas, numpy, matplotlib, etc.)
- **Dataset Integration**: Supports working directory configuration for dataset file access
- **REST API**: Simple HTTP API for code execution requests
- **Error Handling**: Comprehensive error catching and reporting
- **Timeout Support**: Configurable execution timeouts for safety

## API Endpoints

### POST /execute

Execute Python code and return the result.

**Request Body:**
```json
{
  "code": "print('Hello, World!')",
  "language": "python",
  "timeout": 30,
  "working_dir": "~/datasets/"
}
```

**Response:**
```json
{
  "success": true,
  "output": "Hello, World!\n",
  "error": null,
  "execution_time": 0.001
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "code-execution"
}
```

### POST /execute-file

Execute a Python file and return the result.

**Request Body:**
```json
{
  "file_path": "/path/to/script.py",
  "working_dir": "~/datasets/"
}
```

## Installation

1. Navigate to the service directory:
   ```bash
   cd code_sandbox/datasets
   ```

2. Make the start script executable:
   ```bash
   chmod +x start.sh
   ```

3. Run the service:
   ```bash
   ./start.sh
   ```

Or manually:

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the service:
   ```bash
   python main.py
   ```

## Configuration

Environment variables:
- `HOST`: Service host (default: 127.0.0.1)
- `PORT`: Service port (default: 8001)

## Usage Example

```bash
# Test the service
curl -X POST "http://127.0.0.1:8001/execute" \
     -H "Content-Type: application/json" \
     -d '{
       "code": "import pandas as pd\nprint(pd.__version__)",
       "language": "python"
     }'
```

## Security Notes

⚠️ **WARNING**: This service executes arbitrary code. In production:

1. Run in a sandboxed environment (Docker container, VM, etc.)
2. Implement proper authentication and authorization
3. Restrict network access
4. Monitor resource usage
5. Implement rate limiting
6. Restrict file system access

## Supported Libraries

The service comes pre-loaded with common data science libraries:
- pandas
- numpy
- matplotlib
- seaborn
- scikit-learn
- requests

Additional libraries can be added to `requirements.txt` as needed.

## Development

To add new features:

1. Modify `main.py` to add new endpoints or functionality
2. Update `requirements.txt` if new dependencies are needed
3. Test the changes with the provided examples
4. Update this README with new documentation

## Integration with Onyx

This service is designed to work with Onyx's dataset chat feature. The main backend will send code execution requests to this service and receive the results for display to users.

The service supports the `~/datasets/` working directory path that matches the default dataset configuration in Onyx. 