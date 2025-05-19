import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("/media/owais/HDD/slcccc/test_5/signai-web-app-firebase-adminsdk-fbsvc-ba097b499b.json")
firebase_admin.initialize_app(cred)
print("Firebase Admin SDK initialized successfully!")