# PowerShell script to run full project checks
# Backend: lint with ruff and run pytest
# Frontend: lint, run Vitest, and build the production bundle

# Exit on first error
$ErrorActionPreference = "Stop"

Write-Host "Running backend lint (ruff)..."
poetry run ruff backend/app

Write-Host "Running backend tests (pytest)..."
poetry run pytest backend/tests

Write-Host "Running frontend lint..."
cd frontend
npm run lint

Write-Host "Running frontend tests (Vitest)..."
npm run test

Write-Host "Building frontend..."
npm run build

Write-Host "All checks completed successfully."

