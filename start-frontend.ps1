#!powershell
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$ScriptDir\frontend"

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js / npm is not installed or not found in PATH."
    exit 1
}

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..."
    npm ci
}

Write-Host "Starting StegChat frontend on http://localhost:5173..."
npm run dev


