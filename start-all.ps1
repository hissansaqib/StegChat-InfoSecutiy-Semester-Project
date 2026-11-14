#!powershell
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Launching StegChat backend and frontend..."

# Check ports 8000 and 5173
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Warning "Port 8000 is already in use by PID $($port8000.OwningProcess)."
}
$port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($port5173) {
    Write-Warning "Port 5173 is already in use by PID $($port5173.OwningProcess)."
}

# Start backend in a new PowerShell window
$backendCmd = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptDir\start-backend.ps1`""
$backendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList $backendCmd -PassThru

Start-Sleep -Seconds 2

# Start frontend in a new PowerShell window
$frontendCmd = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptDir\start-frontend.ps1`""
$frontendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList $frontendCmd -PassThru

Write-Host "=========================================="
Write-Host " StegChat Services Launched!"
Write-Host " Backend  : http://127.0.0.1:8000"
Write-Host " API Docs : http://127.0.0.1:8000/docs"
Write-Host " Frontend : http://localhost:5173"
Write-Host "=========================================="


