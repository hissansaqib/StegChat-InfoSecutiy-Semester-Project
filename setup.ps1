#!powershell
Write-Host "=== StegChat setup ==="
# Check for a suitable Python interpreter (>=3.12). Prefer Python 3.14 if available.
try {
    $verOutput = py -3.14-64 -c "import sys;print('.'.join(map(str, sys.version_info[:3])))" 2>$null
    $ver = $verOutput.Trim()
    if ($ver -match "^(\d+)\.(\d+)\.(\d+)$") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 12)) {
            Write-Host "Using Python interpreter py -3.14-64 (version $ver)"
        } else {
            Write-Error "Suitable Python (>=3.12) not found (found $ver)."
            exit 1
        }
    } else {
        Write-Error "Unable to parse Python version output."
        exit 1
    }
} catch {
    Write-Error "Python interpreter py -3.14-64 not found."
    exit 1
}
# Check Node version (>=18)
$nodeVersion = (node --version 2>$null) -replace "v", ""
if ($nodeVersion -match "^(\d+)\.(\d+)\.(\d+)$") {
    $nMajor = [int]$Matches[1]
    if ($nMajor -lt 18) {
        Write-Error "Node >=18 required (found $nodeVersion)."
        exit 1
    }
} else {
    Write-Error "Node not found."
    exit 1
}
# Install backend dependencies via pip using requirements.txt
Write-Host "Installing backend dependencies..."
py -3.14-64 -m pip install -r "$PSScriptRoot\backend\requirements.txt"
# Verify backend import
Write-Host "Verifying backend import..."
py -3.14-64 -c "import backend.app.main; print('Backend import OK')"
# Install frontend dependencies and build
Set-Location "$PSScriptRoot\frontend"
Write-Host "Installing frontend dependencies..."
npm ci
Write-Host "Building frontend..."
npm run build
Write-Host "Setup completed successfully."
