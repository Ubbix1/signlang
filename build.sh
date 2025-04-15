#!/bin/bash
echo "Starting build process..."

# Print environment information
echo "Environment: ${FLASK_ENV:-development}"
echo "Python version:"
python --version

# Ensure pip is up to date
echo "Updating pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Verify NumPy version
echo "Verifying NumPy version..."
python -c "import numpy as np; print(f'NumPy version: {np.__version__}')"

# Check if TensorFlow can be imported
echo "Checking TensorFlow import..."
python -c "import tensorflow as tf; print(f'TensorFlow version: {tf.__version__}')"

# Set port if not already set
if [ -z "$PORT" ]; then
  export PORT=8000
  echo "PORT not set, defaulting to $PORT"
fi

# Check if we need to create the database
if [ ! -f "app/database/database.db" ]; then
  echo "Setting up database..."
  python create_db.py
fi

echo "Build completed successfully! App will run on port $PORT" 