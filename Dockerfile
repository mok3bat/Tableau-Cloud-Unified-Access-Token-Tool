# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create keys directory
RUN mkdir -p keys

# Create __init__.py files for Python packages
RUN touch auth/__init__.py managers/__init__.py testing/__init__.py utils/__init__.py

# Expose port
EXPOSE 7860

# Run the application
CMD ["python", "app.py"]