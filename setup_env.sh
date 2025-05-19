#!/bin/bash
echo "Setting up Python environment for SignAI Backend..."

# Check if Python 3.10 is installed
if command -v python3.10 &> /dev/null; then
    echo "Python 3.10 is available"
    PYTHON_CMD=python3.10
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "Using Python $PYTHON_VERSION"
    PYTHON_CMD=python3
else
    echo "Python 3 not found. Please install Python 3.10"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
$PYTHON_CMD -m venv venv
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Environment setup complete. Activate it with: source venv/bin/activate"
echo "Then run the application with: python run.py" 