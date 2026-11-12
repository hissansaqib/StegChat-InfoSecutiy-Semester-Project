#!powershell
Write-Host "Starting StegChat frontend..."
# Change to the frontend directory
Set-Location "$PSScriptRoot\frontend"
# Ensure dependencies are installed
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..."
    npm ci
}
# Start Vite development server
npm run dev

