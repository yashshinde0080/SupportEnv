FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security (UID 1000 for HF Spaces compatibility)
RUN useradd -m -u 1000 appuser

# Set working directory and change ownership
WORKDIR /app
COPY --chown=appuser:appuser . /app

# Ensure we have the ML cache dir writable
RUN mkdir -p /.cache && chmod -R 777 /.cache

# Switch to non-root user
USER appuser

# Set environment variables
ENV PORT=8000
ENV ENV_SEED=42
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Expose ports
EXPOSE 8000
EXPOSE 7860

# Run the FastAPI app
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]