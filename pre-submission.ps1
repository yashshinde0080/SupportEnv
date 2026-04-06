# SupportEnv Pre-submission Validation Script (Windows/PowerShell)
# This script runs the automated checks required for the OpenEnv competition.

$ErrorActionPreference = "Stop"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "   SupportEnv Pre-submission Validation Suite       " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. OpenEnv Specification Validation
Write-Host "`n[1/3] Running 'openenv validate'..." -ForegroundColor Yellow
if (Get-Command "openenv" -ErrorAction SilentlyContinue) {
    try {
        openenv validate
        Write-Host "OpenEnv specification check passed." -ForegroundColor Green
    } catch {
        Write-Host "Error: OpenEnv specification validation failed." -ForegroundColor Red
    }
} else {
    Write-Host "Warning: 'openenv' CLI tool not found. Skipping specification check." -ForegroundColor Gray
    Write-Host "Please ensure 'openenv-core' is installed: pip install openenv-core" -ForegroundColor Gray
}

# 2. Docker Containerization Check
Write-Host "`n[2/3] Building Docker image..." -ForegroundColor Yellow
if (Get-Command "docker" -ErrorAction SilentlyContinue) {
    try {
        docker build -t support-env-validation .
        Write-Host "Docker build successful." -ForegroundColor Green
    } catch {
        Write-Host "Error: Docker build failed. This is mandatory for submission." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Error: 'docker' not found. Docker check is MANDATORY for submission." -ForegroundColor Red
    exit 1
}

# 3. Environment Connectivity & Health Check
Write-Host "`n[3/3] Checking API Connectivity..." -ForegroundColor Yellow
$TEST_PORT = 8081

# Start the server using start-process to keep it separate
Write-Host "Starting test server on port $TEST_PORT..." -ForegroundColor Gray
$process = Start-Process uvicorn -ArgumentList "server.app:app --host 0.0.0.0 --port $TEST_PORT" -PassThru -NoNewWindow
Start-Sleep -Seconds 5

try {
    # Check Health
    $health = Invoke-RestMethod -Uri "http://localhost:$TEST_PORT/health"
    Write-Host "Connectivity check passed: /health is responding." -ForegroundColor Green
    
    # Check OpenEnv Reset
    $reset = Invoke-RestMethod -Uri "http://localhost:$TEST_PORT/reset" -Method Post -Body '{}' -ContentType "application/json"
    if ($reset.ticket_id -or $reset.observation) {
        Write-Host "OpenEnv Reset check passed: /reset is responding with initial observation." -ForegroundColor Green
    } else {
        throw "Reset response did not contain ticket data."
    }
} catch {
    Write-Host "Error: Connectivity checks failed. Details: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    # Clean up the server process
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "`n====================================================" -ForegroundColor Cyan
Write-Host "   Validation SUCCESS: SupportEnv is ready for HF!  " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Press any key to exit..."
$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") | Out-Null
