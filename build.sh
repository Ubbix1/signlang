#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if we need to create the database
if [ ! -f "app/database/database.db" ]; then
  echo "Setting up database..."
  python create_db.py
fi

echo "Build completed successfully!" 