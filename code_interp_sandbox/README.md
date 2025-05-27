# Code Interpreter Sandbox

This is a standalone service that provides a secure sandbox for executing Python code snippets. It is designed to be used with the Onyx application to provide code interpretation capabilities.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the service:
```bash
python app.py
```

The service will be available at http://localhost:8765.

## API Endpoints

- `GET /health`: Check the health of the service
- `POST /restart`: Reset the interpreter state
- `POST /execute`: Execute Python code and return the results

## API Usage

### Execute Code

```python
import requests
import json

code = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Create a sample dataset
data = {
    'x': np.random.rand(100),
    'y': np.random.rand(100)
}
df = pd.DataFrame(data)

# Create a plot
plt.figure(figsize=(10, 6))
plt.scatter(df['x'], df['y'])
plt.title('Sample Scatter Plot')
plt.xlabel('X')
plt.ylabel('Y')
plt.show()

print(df.describe())
"""

response = requests.post(
    "http://localhost:8765/execute",
    json={"code": code}
)

result = response.json()
print(json.dumps(result, indent=2))
```

### Restart Interpreter

```python
import requests

response = requests.post("http://localhost:8765/restart")
print(response.json())
```

## Security Considerations

This service executes arbitrary Python code, which is inherently risky. In a production environment, you should:

1. Run this service in a isolated container or VM
2. Set up resource limits to prevent DoS attacks
3. Consider using a more secure sandboxing solution like PyPy.js or Pyodide
4. Only allow trusted sources to access this service

## Adding Datasets

You can add datasets to the `datasets` directory, and they will be accessible to the code interpreter via the `DATASETS_PATH` global variable. 