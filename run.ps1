# PowerShell runner script for StegChat

param(
    [Parameter(Mandatory=$false)][string]$Target = "dev"
)

switch ($Target) {
    "backend" {
        Write-Host "Starting StegChat FastAPI Backend..." -ForegroundColor Cyan
        uvicorn backend.app.main:create_app --reload --host 127.0.0.1 --port 8000
    }
    "frontend" {
        Write-Host "Starting StegChat Vite Frontend..." -ForegroundColor Cyan
        Set-Location frontend
        npm run dev
    }
    "dev" {
        Write-Host "StegChat Full-Stack Startup" -ForegroundColor Green
        Write-Host "1. Starting backend in background..." -ForegroundColor Yellow
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "uvicorn backend.app.main:create_app --reload --host 127.0.0.1 --port 8000"
        Start-Sleep -Seconds 2
        Write-Host "2. Starting frontend in foreground (http://localhost:5173)..." -ForegroundColor Yellow
        Set-Location frontend
        npm run dev
    }
    "install" {
        Write-Host "Installing dependencies..." -ForegroundColor Cyan
        pip install passlib[bcrypt] cryptography pillow pydantic-settings
        Set-Location frontend
        npm install
    }
}

