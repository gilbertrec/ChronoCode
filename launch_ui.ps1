$ErrorActionPreference = "Stop"

# Define Python command path
$PythonCmd = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonCmd)) {
    Write-Error "Virtual environment not found. Please run install.ps1 first."
    exit 1
}

# Start backend as background job
Write-Host "Starting backend server..."
$BackendJob = Start-Job -ScriptBlock {
    param($py)
    & $py UI\backend\server.py
} -ArgumentList $PythonCmd

try {
    # Start frontend
    Write-Host "Starting frontend server..."
    Set-Location -Path "UI\web"
    npm install
    npm run dev
} finally {
    # Cleanup backend job when frontend stops or script exits
    Write-Host "Stopping backend server..."
    Stop-Job -Job $BackendJob
    Remove-Job -Job $BackendJob
    Set-Location -Path "..\.."
}
