# PowerShell script to run full project checks across backend and frontend
# Exit immediately on any error
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

Set-Location $RepoRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  StegChat Comprehensive Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "`n[1/5] Running Backend Ruff Lint..." -ForegroundColor Yellow
python -m ruff check backend/app --config backend/pyproject.toml
if ($LASTEXITCODE -ne 0) { Write-Error "Backend linting failed"; exit 1 }

Write-Host "`n[2/5] Running Backend Pytest Suite..." -ForegroundColor Yellow
python -m pytest backend/tests -ra
if ($LASTEXITCODE -ne 0) { Write-Error "Backend test suite failed"; exit 1 }

Write-Host "`n[3/5] Running Frontend TypeScript Typecheck..." -ForegroundColor Yellow
Set-Location "$RepoRoot\frontend"
npx tsc --noEmit
if ($LASTEXITCODE -ne 0) { Write-Error "Frontend TypeScript validation failed"; exit 1 }

Write-Host "`n[4/5] Running Frontend ESLint and Vitest Suite..." -ForegroundColor Yellow
npm run lint
if ($LASTEXITCODE -ne 0) { Write-Error "Frontend ESLint failed"; exit 1 }

npm test
if ($LASTEXITCODE -ne 0) { Write-Error "Frontend Vitest suite failed"; exit 1 }

Write-Host "`n[5/5] Building Frontend Production Bundle..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) { Write-Error "Frontend production build failed"; exit 1 }

Set-Location $RepoRoot
Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "  ALL CHECKS PASSED WITH ZERO ERRORS!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
