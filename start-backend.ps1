#!powershell
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not found in PATH."
    exit 1
}

Write-Host "Starting StegChat backend on http://127.0.0.1:8000..."
py -3.14-64 -m uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload --reload-dir "$ScriptDir\backend\app"

