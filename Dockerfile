FROM python:3.11-slim

# Install system dependencies (if any)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Create non‑root user
RUN useradd -m appuser
WORKDIR /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Environment variables
ENV PORT=8000
ENV ENV_SEED=42

# Expose ports (FastAPI and optional Gradio UI)
EXPOSE 8000
EXPOSE 7860

# Run the FastAPI app
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]