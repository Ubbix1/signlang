#!/usr/bin/env python3
"""
Test MongoDB Connection
"""

import logging
import sys
import urllib.parse
from datetime import datetime
from pymongo import MongoClient

# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def test_mongodb_connection():
    """Test MongoDB connection"""
    try:
        logger.info("Starting MongoDB connection test...")

        # MongoDB URI
        mongodb_uri = "mongodb+srv://drkgamer194:admin123@signai.uu3gif4.mongodb.net/?retryWrites=true&w=majority&appName=signai"

        # Parse MongoDB URI to ensure a database name is present
        parsed_uri = urllib.parse.urlparse(mongodb_uri)
        logger.debug(f"Parsed URI: {parsed_uri}")

        # If no database specified in URI, add 'signai' as default
        if not parsed_uri.path or parsed_uri.path == '/':
            # Add default database name
            base_uri = mongodb_uri.split('?')[0].rstrip('/')
            query_params = mongodb_uri.split('?', 1)[1] if '?' in mongodb_uri else ''
            mongodb_uri = f"{base_uri}/signai"
            if query_params:
                mongodb_uri = f"{mongodb_uri}?{query_params}"

            logger.debug(f"Added default database name to MongoDB URI: {mongodb_uri}")

        logger.info(f"Connecting to MongoDB: {mongodb_uri}")

        # Connect to MongoDB
        client = MongoClient(mongodb_uri)
        db = client.get_database()

        logger.info(f"Connected to MongoDB database: {db.name}")

        # Check connection by attempting a simple operation
        result = db.command('ping')
        logger.info(f"MongoDB ping result: {result}")

        # Create collections required for the application
        required_collections = [
            'users',             # Store user profiles beyond Firebase Auth
            'prediction_logs',   # Store prediction logs
            'sessions',          # Store user session data
            'error_logs'         # Store error logs
        ]
        
        # Create all required collections
        for collection_name in required_collections:
            if collection_name not in db.list_collection_names():
                # Create collection by inserting a document
                logger.info(f"Creating collection: {collection_name}")
                db[collection_name].insert_one({
                    "name": f"Initial {collection_name} Document",
                    "created_at": datetime.utcnow(),
                    "is_test": True
                })
                logger.info(f"Collection '{collection_name}' created successfully.")
            else:
                logger.info(f"Collection '{collection_name}' already exists.")

        # List collections
        collections = db.list_collection_names()
        logger.info(f"MongoDB collections: {collections}")

        # Create a test prediction log
        prediction_logs = db.prediction_logs
        test_prediction = {
            "user_id": "test_user_123",
            "session_id": "test_session_456",
            "gesture_label": "Hello",
            "confidence": 0.92,
            "timestamp": datetime.utcnow(),
            "is_test": True
        }

        # Insert document
        logger.info("Inserting test prediction log...")
        result = prediction_logs.insert_one(test_prediction)
        logger.info(f"Inserted prediction log ID: {result.inserted_id}")

        # Find document
        logger.info("Retrieving test prediction log...")
        retrieved_doc = prediction_logs.find_one({"_id": result.inserted_id})
        logger.info(f"Retrieved prediction log: {retrieved_doc}")

        # Delete test document
        logger.info("Cleaning up test data...")
        prediction_logs.delete_one({"_id": result.inserted_id})
        
        # Delete all test documents
        for collection_name in required_collections:
            delete_result = db[collection_name].delete_many({"is_test": True})
            logger.info(f"Deleted {delete_result.deleted_count} test documents from {collection_name}")

        logger.info("MongoDB connection test successful!")

    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    test_mongodb_connection()
