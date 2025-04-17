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

# Test MongoDB connection
echo "Testing MongoDB connection..."
python test_mongodb.py || echo "MongoDB connection test failed, but continuing build..."

# Set port if not already set
if [ -z "$PORT" ]; then
  export PORT=8000
  echo "PORT not set, defaulting to $PORT"
fi

echo "Build completed successfully! App will run on port $PORT" 