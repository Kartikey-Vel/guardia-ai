"""
Database Connection and Session Management
Modern MongoDB integration with Motor (async) and connection pooling
"""
import asyncio
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from loguru import logger
from ..config.settings import settings

class DatabaseManager:
    """Manages database connections and sessions"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self._is_connected = False
    
    async def connect(self) -> None:
        """Connect to MongoDB database"""
        try:
            # Create MongoDB client with connection pooling
            self.client = AsyncIOMotorClient(
                settings.mongodb_url,
                maxPoolSize=settings.mongodb_max_connections,
                minPoolSize=settings.mongodb_min_connections,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=20000,
                retryWrites=True,
                retryReads=True
            )
            
            # Get database
            self.database = self.client[settings.mongodb_database]
            
            # Test connection
            await self.client.admin.command('ping')
            self._is_connected = True
            
            logger.info(f"✅ Connected to MongoDB: {settings.mongodb_database}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            self._is_connected = False
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self._is_connected = False
            logger.info("📤 Disconnected from MongoDB")
    
    async def is_connected(self) -> bool:
        """Check if database is connected"""
        if not self._is_connected or not self.client:
            return False
        
        try:
            await self.client.admin.command('ping')
            return True
        except Exception:
            self._is_connected = False
            return False
    
    async def get_database(self) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if not self._is_connected:
            await self.connect()
        return self.database
    
    async def create_indexes(self) -> None:
        """Create database indexes for optimal performance"""
        if self.database is None:
            await self.connect()
        
        try:
            # Users collection indexes
            await self.database.users.create_index("username", unique=True)
            await self.database.users.create_index("email", unique=True)
            await self.database.users.create_index("created_at")
            
            # Family members collection indexes
            await self.database.family_members.create_index([("owner_id", 1), ("name", 1)])
            await self.database.family_members.create_index("created_at")
            
            # Alerts collection indexes
            await self.database.alerts.create_index([("user_id", 1), ("created_at", -1)])
            await self.database.alerts.create_index("status")
            await self.database.alerts.create_index("priority")
            await self.database.alerts.create_index("detection_type")
            
            # Surveillance sessions collection indexes
            await self.database.surveillance_sessions.create_index([("user_id", 1), ("start_time", -1)])
            await self.database.surveillance_sessions.create_index("is_active")
            
            # Surveillance frames collection indexes (with TTL for auto-cleanup)
            await self.database.surveillance_frames.create_index("timestamp", expireAfterSeconds=30*24*60*60)  # 30 days
            await self.database.surveillance_frames.create_index("camera_id")
            await self.database.surveillance_frames.create_index("processed")
            
            logger.info("✅ Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create database indexes: {e}")
            raise
    
    async def health_check(self) -> dict:
        """Perform database health check"""
        try:
            if not await self.is_connected():
                return {"status": "unhealthy", "error": "Not connected"}
            
            # Test basic operations
            start_time = asyncio.get_event_loop().time()
            await self.client.admin.command('ping')
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Get database stats
            stats = await self.database.command("dbStats")
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "database_size_mb": round(stats.get("dataSize", 0) / 1024 / 1024, 2),
                "collections": stats.get("collections", 0),
                "indexes": stats.get("indexes", 0)
            }
            
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

# Global database manager instance
db_manager = DatabaseManager()

async def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance"""
    return await db_manager.get_database()

async def init_database() -> None:
    """Initialize database connection and create indexes"""
    await db_manager.connect()
    await db_manager.create_indexes()

async def close_database() -> None:
    """Close database connection"""
    await db_manager.disconnect()

# Database event handlers for FastAPI
async def startup_event():
    """Database startup event handler"""
    await init_database()
    logger.info("🚀 Database initialized")

async def shutdown_event():
    """Database shutdown event handler"""
    await close_database()
    logger.info("🛑 Database connections closed")
