#!/usr/bin/env python3
"""
Debug version of run.py with more verbose output
"""

import os
import sys
import logging
import traceback
from app import create_app

# Configure logging to output to console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ])
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        print("Starting SignAI application in debug mode...")
        
        # Create Flask app
        app = create_app()
        
        # Set port
        port = int(os.environ.get('PORT', 5000))
        
        print(f"Starting server on http://localhost:{port}")
        print("Press Ctrl+C to stop the server")
        
        # Run the application with debug=True
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        print(f"Error starting application: {e}")
        traceback.print_exc()
        sys.exit(1) 