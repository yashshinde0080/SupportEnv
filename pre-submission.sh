#!/bin/bash
# SupportEnv Pre-submission Validation Script
# This script runs the three automated checks required for the OpenEnv competition.

set -e

# Configuration
REPO_DIR=$(pwd)
DOCKER_IMAGE="support-env-validation"
HEALTH_CHECK_URL="http://localhost:8000/health"

echo "===================================================="
echo "   SupportEnv Pre-submission Validation Suite       "
echo "===================================================="

# 1. OpenEnv Specification Validation
echo -e "\n[1/3] Running 'openenv validate'..."
if command -v openenv &> /dev/null; then
    openenv validate
else
    echo "Warning: 'openenv' CLI tool not found. Skipping specification check."
    echo "Please ensure 'openenv-core' is installed: pip install openenv-core"
fi

# 2. Docker Containerization Check
echo -e "\n[2/3] Building Docker image..."
if command -v docker &> /dev/null; then
    docker build -t $DOCKER_IMAGE .
    echo "Docker build successful."
else
    echo "Error: 'docker' not found. Docker check is MANDATORY for submission."
    exit 1
fi

# 3. Environment Connectivity & Health Check
echo -e "\n[3/3] Checking API Connectivity..."
# Start the server in the background for a quick check
# Use a non-standard port to avoid conflicts if already running
TEST_PORT=8081
uvicorn server.app:app --host 0.0.0.0 --port $TEST_PORT &
SERVER_PID=$!

# Wait for server to start
sleep 5

# Ping health endpoint
HEALTH=$(curl -s http://localhost:$TEST_PORT/health || echo "FAILED")
if [[ "$HEALTH" == *"OK"* || "$HEALTH" == *"status"* ]]; then
    echo "Connectivity check passed: /health is responding."
else
    echo "Error: Connectivity check failed. Ensure uvicorn is available and the server starts safely."
    kill $SERVER_PID
    exit 1
fi

# Ping reset endpoint (Must work for OpenEnv crawler)
RESET=$(curl -s -X POST http://localhost:$TEST_PORT/reset -d '{}' || echo "FAILED")
if [[ "$RESET" == *"ticket"* || "$RESET" == *"observation"* ]]; then
    echo "OpenEnv Reset check passed: /reset is responding with initial observation."
else
    echo "Error: OpenEnv Reset check failed. Validator will not be able to start episodes."
    kill $SERVER_PID
    exit 1
fi

# Kill the test server
kill $SERVER_PID
echo "API checks complete."

echo -e "\n===================================================="
echo "   Validation SUCCESS: SupportEnv is ready for HF!  "
echo "===================================================="
