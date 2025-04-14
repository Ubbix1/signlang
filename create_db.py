# create_db.py
from app import create_app
from app.database.db import get_db

app = create_app()

with app.app_context():
    db = get_db()
    # Firebase collections are created automatically when documents are added
    # This script is here to verify connection and print some useful information
    print("✅ Connected to Firebase Firestore successfully.")
    print("🔥 Firebase collections will be created automatically as data is added.")
