"""
Database Repository Pattern Implementation
CRUD operations with proper error handling and validation
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Type, Generic, TypeVar
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError, PyMongoError
from loguru import logger

from ..models.schemas import BaseMongoModel
from .connection import get_database

T = TypeVar('T', bound=BaseMongoModel)

class BaseRepository(ABC, Generic[T]):
    """Base repository class with common CRUD operations"""
    
    def __init__(self, collection_name: str, model_class: Type[T]):
        self.collection_name = collection_name
        self.model_class = model_class
        self._collection: Optional[AsyncIOMotorCollection] = None
    
    async def get_collection(self) -> AsyncIOMotorCollection:
        """Get MongoDB collection"""
        if self._collection is None:
            database = await get_database()
            self._collection = database[self.collection_name]
        return self._collection
    
    async def create(self, obj: T) -> T:
        """Create a new document"""
        try:
            collection = await self.get_collection()
            
            # Convert to dict and handle ObjectId
            doc_dict = obj.dict(by_alias=True, exclude_unset=True)
            if '_id' not in doc_dict:
                doc_dict['_id'] = ObjectId()
            
            result = await collection.insert_one(doc_dict)
            
            # Fetch the created document
            created_doc = await collection.find_one({"_id": result.inserted_id})
            return self.model_class(**created_doc)
            
        except DuplicateKeyError as e:
            logger.error(f"Duplicate key error in {self.collection_name}: {e}")
            raise ValueError("Document with this key already exists")
        except PyMongoError as e:
            logger.error(f"Database error in {self.collection_name}.create: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {self.collection_name}.create: {e}")
            raise
    
    async def get_by_id(self, obj_id: str) -> Optional[T]:
        """Get document by ID"""
        try:
            collection = await self.get_collection()
            
            if not ObjectId.is_valid(obj_id):
                return None
            
            document = await collection.find_one({"_id": ObjectId(obj_id)})
            
            if document:
                return self.model_class(**document)
            return None
            
        except PyMongoError as e:
            logger.error(f"Database error in {self.collection_name}.get_by_id: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {self.collection_name}.get_by_id: {e}")
            raise
    
    async def get_by_field(self, field: str, value: Any) -> Optional[T]:
        """Get document by specific field"""
        try:
            collection = await self.get_collection()
            document = await collection.find_one({field: value})
            
            if document:
                return self.model_class(**document)
            return None
            
        except PyMongoError as e:
            logger.error(f"Database error in {self.collection_name}.get_by_field: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {self.collection_name}.get_by_field: {e}")
            raise
    
    async def get_all(self, skip: int = 0, limit: int = 100, sort_by: str = "_id", sort_order: int = -1) -> List[T]:
        """Get all documents with pagination"""
        try:
            collection = await self.get_collection()
            
            cursor = collection.find().sort(sort_by, sort_order).skip(skip).limit(limit)
            documents = await cursor.to_list(length=limit)
            
            return [self.model_class(**doc) for doc in documents]
            
        except PyMongoError as e:
            logger.error(f"Database error in {self.collection_name}.get_all: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {self.collection_name}.get_all: {e}")
            raise
    
    async def update(self, obj_id: str, update_data: Dict[str, Any]) -> Optional[T]:
        """Update document by ID"""
        try:
            collection = await self.get_collection()
            
            if not ObjectId.is_valid(obj_id):
                return None
            
            # Add updated_at timestamp
            from datetime import datetime
            update_data["updated_at"] = datetime.utcnow()
            
            result = await collection.find_one_and_update(
                {"_id": ObjectId(obj_id)},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                return self.model_class(**result)
            return None
            
        except PyMongoError as e:
            logger.error(f"Database error in {self.collection_name}.update: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {self.collection_name}.update: {e}")
            raise
    
    async def delete(self, obj_id: str) -> bool:
        """Delete document by ID"""
        try:
            collection = await self.get_collection()
            
            if not ObjectId.is_valid(obj_id):
                return False
            
            result = await collection.delete_one({"_id": ObjectId(obj_id)})
            return result.deleted_count > 0
            
        except PyMongoError as e:
            logger.error(f"Database error in {self.collection_name}.delete: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {self.collection_name}.delete: {e}")
            raise
    
    async def count(self, filter_dict: Dict[str, Any] = None) -> int:
        """Count documents matching filter"""
        try:
            collection = await self.get_collection()
            return await collection.count_documents(filter_dict or {})
            
        except PyMongoError as e:
            logger.error(f"Database error in {self.collection_name}.count: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {self.collection_name}.count: {e}")
            raise
    
    async def find_many(self, filter_dict: Dict[str, Any], skip: int = 0, limit: int = 100, sort_by: str = "_id", sort_order: int = -1) -> List[T]:
        """Find documents matching filter"""
        try:
            collection = await self.get_collection()
            
            cursor = collection.find(filter_dict).sort(sort_by, sort_order).skip(skip).limit(limit)
            documents = await cursor.to_list(length=limit)
            
            return [self.model_class(**doc) for doc in documents]
            
        except PyMongoError as e:
            logger.error(f"Database error in {self.collection_name}.find_many: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {self.collection_name}.find_many: {e}")
            raise
