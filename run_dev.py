#!/usr/bin/env python3
"""
Development version of the SignAI Backend with detailed logging
"""

import os
import sys
import logging
import traceback
from app import create_app
from datetime import datetime

# Import dotenv at the top level
try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv is not installed. Run 'pip install python-dotenv' to load .env files.")
    load_dotenv = lambda: None  # Define a no-op function

# Configure output directory for logs
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Configure logging to output to both console and file
log_filename = os.path.join(log_dir, f'signai_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename)
    ])
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        print("=" * 80)
        print(f"Starting SignAI Backend in development mode...")
        print(f"Logs will be saved to: {log_filename}")
        print("=" * 80)
        
        # Load environment variables from .env file if it exists
        if os.path.exists('.env'):
            print("Loading environment from .env file")
            load_dotenv()
        
        # Create Flask app
        app = create_app()
        
        # Route static files
        @app.route('/static/<path:path>')
        def send_static(path):
            return app.send_static_file(f'static/{path}')

        # Route HTML files directly from templates folder for frontend
        @app.route('/<path:path>.html')
        def send_html(path):
            from flask import render_template
            try:
                return render_template(f'{path}.html')
            except Exception as e:
                logger.error(f"Error loading template {path}.html: {e}")
                return render_template('index.html')
        
        # Set port
        port = int(os.environ.get('PORT', 5000))
        
        print(f"Starting server on http://localhost:{port}")
        print("API documentation available at: http://localhost:{port}/api_checker")
        print("Press Ctrl+C to stop the server")
        
        # Run the application with debug=True
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        print(f"Error starting application: {e}")
        traceback.print_exc()
        logger.error(f"Application startup failed: {e}", exc_info=True)
        sys.exit(1) 