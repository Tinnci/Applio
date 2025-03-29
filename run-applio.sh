#!/bin/sh
printf "\033]0;Applio (using .venv)\007"

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment (.venv) not found."
    echo "Please run './run-install.sh' first to set up the environment using UV."
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
. .venv/bin/activate

# Set macOS specific environment variables if on Darwin
if [ "$(uname)" = "Darwin" ]; then
    echo "Setting macOS specific environment variables..."
    export PYTORCH_ENABLE_MPS_FALLBACK=1
    export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
fi

clear
echo "Running Applio..."
python app.py --open

echo ""
echo "Applio has finished or encountered an error."
# No pause needed in shell script, window usually stays open or user runs in existing terminal.
