# app/database.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        """Establish connection to MongoDB."""
        try:
            # Create MongoDB client with connection options
            self.client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=10000,         # 10 second connection timeout
                maxPoolSize=50,                 # Maximum connections in pool
                retryWrites=True                # Enable retryable writes
            )
            
            # Test the connection
            self.client.admin.command('ping')
            
            # Get database
            self.db = self.client[self.db_name]
            
            logger.info(f"✓ Successfully connected to MongoDB")
            logger.info(f"✓ Database: {self.db_name}")
            logger.info(f"✓ URI: {self.uri}")
            
            # Print server info
            server_info = self.client.server_info()
            logger.info(f"✓ MongoDB version: {server_info['version']}")
            
        except ConnectionFailure as e:
            logger.error(f"✗ Could not connect to MongoDB: {e}")
            raise
        except ServerSelectionTimeoutError as e:
            logger.error(f"✗ MongoDB server selection timeout: {e}")
            logger.error("Make sure MongoDB is running and accessible")
            raise
        except Exception as e:
            logger.error(f"✗ Unexpected database connection error: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = self.db.command("dbStats")
            return {
                "database": stats.get("db"),
                "collections": stats.get("collections", 0),
                "objects": stats.get("objects", 0),
                "data_size": stats.get("dataSize", 0),
                "storage_size": stats.get("storageSize", 0),
                "indexes": stats.get("indexes", 0),
                "index_size": stats.get("indexSize", 0)
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

    def list_collections(self) -> List[str]:
        """List all collections in the database."""
        try:
            return self.db.list_collection_names()
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []

    def drop_database(self):
        """Drop the entire database (use with caution!)."""
        try:
            self.client.drop_database(self.db_name)
            logger.warning(f"Database {self.db_name} dropped!")
        except Exception as e:
            logger.error(f"Error dropping database: {e}")
            raise

    def create_collection(self, collection_name: str, **options):
        """Create a collection with options."""
        try:
            self.db.create_collection(collection_name, **options)
            logger.info(f"Created collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error creating collection {collection_name}: {e}")
            raise

    def backup_collection(self, collection_name: str) -> List[Dict]:
        """Backup a collection to a list of documents."""
        try:
            collection = self.db[collection_name]
            return list(collection.find())
        except Exception as e:
            logger.error(f"Error backing up collection {collection_name}: {e}")
            return []

    def restore_collection(self, collection_name: str, documents: List[Dict]):
        """Restore a collection from a list of documents."""
        try:
            collection = self.db[collection_name]
            if documents:
                collection.insert_many(documents)
                logger.info(f"Restored {len(documents)} documents to {collection_name}")
        except Exception as e:
            logger.error(f"Error restoring collection {collection_name}: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the database."""
        try:
            start_time = datetime.now()
            
            # Test connection
            self.client.admin.command('ping')
            
            # Test database access
            collections = self.list_collections()
            
            # Test write operation
            test_collection = self.db.health_check
            test_doc = {"timestamp": datetime.now(), "test": True}
            result = test_collection.insert_one(test_doc)
            test_collection.delete_one({"_id": result.inserted_id})
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "collections_count": len(collections),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Create a global database instance
try:
    db_client = Database()
except Exception as e:
    logger.error(f"Failed to initialize database client: {e}")
    db_client = None

# Utility functions
def get_db():
    """Get database instance."""
    if db_client is None:
        raise RuntimeError("Database not initialized")
    return db_client.db

def check_connection():
    """Check if database connection is healthy."""
    if db_client is None:
        return False
    try:
        db_client.client.admin.command('ping')
        return True
    except:
        return False

def reconnect():
    """Attempt to reconnect to database."""
    global db_client
    try:
        if db_client:
            db_client.close()
        db_client = Database()
        return True
    except Exception as e:
        logger.error(f"Failed to reconnect to database: {e}")
        return False