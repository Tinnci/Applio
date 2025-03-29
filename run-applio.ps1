# Get the directory where the script is located and its name
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$folderName = (Get-Item $scriptDir).Name

# Set the console window title
$Host.UI.RawUI.WindowTitle = "$folderName (using .venv)"

# Check if the virtual environment directory exists
$venvPath = Join-Path $scriptDir ".venv"
if (-not (Test-Path -Path $venvPath -PathType Container)) {
    Write-Host "Virtual environment (.venv) not found."
    Write-Host "Please run 'run-install.ps1' first to set up the environment using UV."
    Read-Host -Prompt "Press Enter to exit"
    exit 1
}

Write-Host "Activating virtual environment and starting Applio..."

# Construct the path to the PowerShell activation script
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

# Check if the activation script exists
if (-not (Test-Path -Path $activateScript -PathType Leaf)) {
    Write-Host "Activation script not found: $activateScript"
    Write-Host "Ensure the virtual environment was created correctly."
    Read-Host -Prompt "Press Enter to exit"
    exit 1
}

# Activate the virtual environment
try {
    . $activateScript
    Write-Host "Virtual environment activated."
} catch {
    Write-Host "Failed to activate virtual environment."
    Write-Host $_.Exception.Message
    Read-Host -Prompt "Press Enter to exit"
    exit 1
}

Write-Host "Running Applio..."
# Run the Python application
try {
    python app.py --open
} catch {
    Write-Host "Error running Applio:"
    Write-Host $_.Exception.Message
    # Optional: Keep the window open to see the error
    # Read-Host -Prompt "Press Enter to exit"
    # exit 1 # Decide if you want to exit immediately on error
}

Write-Host "" # Blank line
Write-Host "Applio has finished or encountered an error. Press Enter to close this window."
Read-Host -Prompt "Press Enter to continue"
