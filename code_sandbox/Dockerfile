FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create datasets directory
RUN mkdir -p ./datasets

# Expose port
EXPOSE 8856

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV EXEC_ALLOWED_BASE_PATH=./datasets

# Run the application
CMD ["python", "main.py"] 