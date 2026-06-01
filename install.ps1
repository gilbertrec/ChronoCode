Write-Host "Installing ChronoCode dependencies..."

# Check if Python is installed
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH."
    exit 1
}

# Create virtual environment
Write-Host "Creating Python virtual environment..."
python -m venv .venv

# Install Python requirements
Write-Host "Installing Python requirements..."
.\.venv\Scripts\pip install -r requirements.txt

# Check if npm is installed
if (-not (Get-Command "npm" -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js/npm is not installed or not in PATH."
    exit 1
}

# Install Frontend requirements
Write-Host "Installing Frontend requirements..."
Set-Location -Path "UI\web"
npm install
Set-Location -Path "..\.."

Write-Host "Installation complete!"
