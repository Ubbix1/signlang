# SignAI Backend

Backend API for Sign Language Recognition

## Overview

SignAI Backend provides the server-side functionality for the SignAI application, which uses machine learning to recognize sign language gestures. The backend is built with Flask and uses Firebase for authentication and MongoDB for storing application data.

## Features

- User authentication via Firebase
- Gesture recognition using TensorFlow and MediaPipe (optional)
- Prediction history storage and retrieval
- Session management for tracking user activity
- Admin dashboard for system statistics

## Requirements

- Python 3.10
- MongoDB Atlas account
- Firebase project with Authentication enabled

## Setup

### Local Development

1. Clone the repository:
   ```
   git clone https://github.com/Ubbix1/SignAiBackend.git
   cd SignAiBackend
   ```

2. Use the setup script to create a virtual environment and install dependencies:
   ```
   ./setup_env.sh
   ```

3. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```

4. Run the application:
   ```
   python run.py
   ```

The application will be available at http://localhost:5000

### Manual Setup

1. Create a virtual environment:
   ```
   python3.10 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python run.py
   ```

## API Endpoints

To view all available API endpoints, navigate to `/api_checker` after starting the application.

## Database Collections

The application uses the following MongoDB collections:

- `users`: Stores extended user profile data
- `prediction_logs`: Stores gesture prediction history
- `sessions`: Stores user session information
- `error_logs`: Stores application error logs

## Deployment

### Render

The application includes configuration for deployment on Render:

1. Push your changes to GitHub
2. Create a new Web Service in Render
3. Connect to your GitHub repository
4. Use the following settings:
   - Build Command: `bash build.sh`
   - Start Command: `gunicorn run:app --bind=0.0.0.0:$PORT --workers=2 --timeout=120 --log-level=debug`

## License

[MIT](LICENSE)
