# app/database.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('DB_env.env')

class Database:
    def __init__(self):
        self.uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.db_name = os.getenv("DB_NAME", "equipment_monitor")
        self.client = None
        self.db = None
        self._connect()

    def _connect(self):
        try:
            self.client = MongoClient(self.uri)
            # Check if connection is successful
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            print("Successfully connected to MongoDB")
        except ConnectionFailure as e:
            print(f"Could not connect to MongoDB: {e}")
            raise

    def close(self):
        if self.client:
            self.client.close()

# Create a global database instance
db_client = Database()