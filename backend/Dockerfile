# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy backend source code into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -e .

# Run the ingestion script to create the DuckDB database file
RUN python scripts/ingest_all.py

# Expose the FastAPI port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]