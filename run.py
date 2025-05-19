#!/usr/bin/env python3
"""
SignAI Backend Launcher
Starts the Flask application for the SignAI sign language recognition system.
"""

import os
import logging
from app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create app - this is the application instance that Gunicorn will use
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

# Note: Health check endpoint is now defined in app/__init__.py

if __name__ == '__main__':
    # Get port from environment variable with fallback to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Only use debug mode when running directly, not through Gunicorn
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    
    # Run the application
    logger.info(f"Starting SignAI backend on port {port} (debug={debug_mode})")
    app.run(host='0.0.0.0', port=port, debug=debug_mode) 
    print("Starting SignAI backend on port 5000 (debug=True)")
