#!powershell
Write-Host "Launching StegChat backend and frontend..."
# Start backend in a new PowerShell window
$backendCmd = "-NoProfile -ExecutionPolicy Bypass -File \"$PSScriptRoot\\start-backend.ps1\""
$backendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList $backendCmd -PassThru
# Small delay to let backend start
Start-Sleep -Seconds 3
# Start frontend in a new PowerShell window
$frontendCmd = "-NoProfile -ExecutionPolicy Bypass -File \"$PSScriptRoot\\start-frontend.ps1\""
$frontendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList $frontendCmd -PassThru
Write-Host "Backend URL: http://127.0.0.1:8000"
Write-Host "Frontend URL: http://localhost:5173"
# Wait for both processes to exit (optional)
$backendProcess.WaitForExit()
$frontendProcess.WaitForExit()

