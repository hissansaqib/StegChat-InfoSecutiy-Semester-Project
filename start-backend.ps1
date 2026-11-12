#!powershell
Write-Host "Installing backend dependencies..."
# Install required Python packages
py -3.14-64 -m pip install -r "$PSScriptRoot\backend\requirements.txt"

Write-Host "Starting StegChat backend..."
# Run the FastAPI app using Uvicorn
py -3.14-64 -m uvicorn backend.app.main:create_app --host 127.0.0.1 --port 8000 --reload
