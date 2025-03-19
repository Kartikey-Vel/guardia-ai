from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from src.config.yosemite_config import settings
from src.utils.tasmanian_logger import setup_logger

logger = setup_logger(__name__)

# Global client variable
_client = None

async def get_mongo_client():
    """Get MongoDB client with connection pooling."""
    global _client
    if _client is None:
        try:
            _client = AsyncIOMotorClient(settings.MONGODB_URL)
            # Verify connection is working
            await _client.admin.command("ismaster")
            logger.info("Connected to MongoDB successfully")
        except ConnectionFailure:
            logger.error("MongoDB connection failed")
            raise
    return _client

async def close_mongo_connection():
    """Close MongoDB connection."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed")

async def get_database():
    """Get database connection."""
    client = await get_mongo_client()
    return client[settings.MONGODB_DB]

async def get_collection(collection_name: str):
    """Get a specific collection from the database."""
    db = await get_database()
    return db[collection_name]

async def get_events_collection():
    """Get the security events collection."""
    return await get_collection("security_events")

async def get_users_collection():
    """Get the users collection."""
    return await get_collection("users")

async def create_indexes():
    """Create necessary indexes for collections."""
    # For events collection
    events_collection = await get_events_collection()
    await events_collection.create_index("timestamp")
    await events_collection.create_index("event_type")
    await events_collection.create_index("threat_level.level")

    # For users collection
    users_collection = await get_users_collection()
    await users_collection.create_index("username", unique=True)
    await users_collection.create_index("email", unique=True)
    
    logger.info("Database indexes created successfully")
