"""
User Management Service
Handles user authentication, registration, and profile management
"""
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from loguru import logger
import numpy as np

from ..models.schemas import (
    User, UserCreate, UserUpdate, UserInDB, 
    FamilyMember, FamilyMemberCreate,
    Token, TokenData
)
from ..db.repository import BaseRepository
from ..config.settings import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRepository(BaseRepository[User]):
    """Repository for user operations"""
    
    def __init__(self):
        super().__init__("users", User)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return await self.get_by_field("username", username)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return await self.get_by_field("email", email)
    
    async def update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        await self.update(user_id, {"last_login": datetime.utcnow()})
    
    async def add_face_encoding(self, user_id: str, face_encoding: List[float]):
        """Add face encoding to user"""
        user = await self.get_by_id(user_id)
        if user:
            encodings = user.face_encodings or []
            encodings.append(face_encoding)
            await self.update(user_id, {"face_encodings": encodings})

class FamilyMemberRepository(BaseRepository[FamilyMember]):
    """Repository for family member operations"""
    
    def __init__(self):
        super().__init__("family_members", FamilyMember)
    
    async def get_by_owner(self, owner_id: str) -> List[FamilyMember]:
        """Get all family members for an owner"""
        return await self.find_many({"owner_id": owner_id})
    
    async def get_by_name_and_owner(self, name: str, owner_id: str) -> Optional[FamilyMember]:
        """Get family member by name and owner"""
        results = await self.find_many({"name": name, "owner_id": owner_id})
        return results[0] if results else None
    
    async def add_face_encoding(self, member_id: str, face_encoding: List[float]):
        """Add face encoding to family member"""
        member = await self.get_by_id(member_id)
        if member:
            encodings = member.face_encodings or []
            encodings.append(face_encoding)
            await self.update(member_id, {"face_encodings": encodings})
    
    async def add_photo(self, member_id: str, photo_path: str):
        """Add photo path to family member"""
        member = await self.get_by_id(member_id)
        if member:
            photos = member.photos or []
            photos.append(photo_path)
            await self.update(member_id, {"photos": photos})

class UserService:
    """Service class for user management operations"""
    
    def __init__(self):
        self.user_repo = UserRepository()
        self.family_repo = FamilyMemberRepository()
        self.current_user: Optional[User] = None
    
    # Authentication methods
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def _get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)
    
    def _create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user credentials"""
        try:
            user = await self.user_repo.get_by_username(username)
            if not user:
                return None
            
            if not self._verify_password(password, user.hashed_password):
                return None
            
            # Update last login
            await self.user_repo.update_last_login(str(user.id))
            return user
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        try:
            # Check if username or email already exists
            existing_user = await self.user_repo.get_by_username(user_data.username)
            if existing_user:
                raise ValueError("Username already exists")
            
            existing_email = await self.user_repo.get_by_email(user_data.email)
            if existing_email:
                raise ValueError("Email already exists")
            
            # Create user with hashed password
            hashed_password = self._get_password_hash(user_data.password)
            
            user_dict = user_data.dict()
            del user_dict["password"]  # Remove plain password
            user_dict["hashed_password"] = hashed_password
            
            user = User(**user_dict)
            created_user = await self.user_repo.create(user)
            
            logger.info(f"✅ User created: {created_user.username}")
            return created_user
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    async def login(self, username: str, password: str) -> Optional[Token]:
        """Login user and return JWT token"""
        try:
            user = await self.authenticate_user(username, password)
            if not user:
                return None
            
            # Create access token
            access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
            access_token = self._create_access_token(
                data={"sub": user.username}, expires_delta=access_token_expires
            )
            
            # Set current user
            self.current_user = user
            
            logger.info(f"✅ User logged in: {user.username}")
            return Token(access_token=access_token, token_type="bearer")
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return None
    
    async def get_current_user(self, token: str) -> Optional[User]:
        """Get current user from JWT token"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            username: str = payload.get("sub")
            if username is None:
                return None
            
            token_data = TokenData(username=username)
            
        except JWTError:
            return None
        
        user = await self.user_repo.get_by_username(token_data.username)
        return user
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """Update user information"""
        try:
            update_dict = user_data.dict(exclude_unset=True)
            return await self.user_repo.update(user_id, update_dict)
            
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            raise
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user and associated data"""
        try:
            # Delete associated family members
            family_members = await self.family_repo.get_by_owner(user_id)
            for member in family_members:
                await self.family_repo.delete(str(member.id))
            
            # Delete user
            result = await self.user_repo.delete(user_id)
            
            if result:
                logger.info(f"✅ User deleted: {user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            raise
    
    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        return await self.user_repo.get_all(skip=skip, limit=limit)
    
    # Family member management
    async def add_family_member(self, owner_id: str, member_data: FamilyMemberCreate) -> FamilyMember:
        """Add family member"""
        try:
            # Check if family member already exists
            existing = await self.family_repo.get_by_name_and_owner(member_data.name, owner_id)
            if existing:
                raise ValueError("Family member with this name already exists")
            
            # Create family member
            member_dict = member_data.dict()
            member_dict["owner_id"] = owner_id
            
            member = FamilyMember(**member_dict)
            created_member = await self.family_repo.create(member)
            
            logger.info(f"✅ Family member added: {created_member.name}")
            return created_member
            
        except Exception as e:
            logger.error(f"Failed to add family member: {e}")
            raise
    
    async def get_family_members(self, owner_id: str) -> List[FamilyMember]:
        """Get all family members for owner"""
        return await self.family_repo.get_by_owner(owner_id)
    
    async def update_family_member(self, member_id: str, update_data: Dict[str, Any]) -> Optional[FamilyMember]:
        """Update family member information"""
        try:
            return await self.family_repo.update(member_id, update_data)
            
        except Exception as e:
            logger.error(f"Failed to update family member: {e}")
            raise
    
    async def delete_family_member(self, member_id: str) -> bool:
        """Delete family member"""
        try:
            result = await self.family_repo.delete(member_id)
            
            if result:
                logger.info(f"✅ Family member deleted: {member_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete family member: {e}")
            raise
    
    async def add_face_encoding_to_member(self, member_id: str, face_encoding: List[float]) -> bool:
        """Add face encoding to family member"""
        try:
            await self.family_repo.add_face_encoding(member_id, face_encoding)
            logger.info(f"✅ Face encoding added to member: {member_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add face encoding: {e}")
            return False
    
    async def add_photo_to_member(self, member_id: str, photo_path: str) -> bool:
        """Add photo to family member"""
        try:
            await self.family_repo.add_photo(member_id, photo_path)
            logger.info(f"✅ Photo added to member: {member_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add photo: {e}")
            return False
    
    async def get_all_known_faces(self, owner_id: str) -> List[Dict[str, Any]]:
        """Get all known face encodings for recognition"""
        try:
            family_members = await self.get_family_members(owner_id)
            known_faces = []
            
            # Add owner's face encodings
            if self.current_user and str(self.current_user.id) == owner_id:
                for encoding in self.current_user.face_encodings or []:
                    known_faces.append({
                        "name": self.current_user.username,
                        "encoding": encoding,
                        "person_id": str(self.current_user.id),
                        "relation": "owner"
                    })
            
            # Add family members' face encodings
            for member in family_members:
                for encoding in member.face_encodings or []:
                    known_faces.append({
                        "name": member.name,
                        "encoding": encoding,
                        "person_id": str(member.id),
                        "relation": member.relation
                    })
            
            logger.info(f"Retrieved {len(known_faces)} known face encodings")
            return known_faces
            
        except Exception as e:
            logger.error(f"Failed to get known faces: {e}")
            return []
    
    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return {}
            
            family_members = await self.family_repo.get_by_owner(user_id)
            
            # Count face encodings
            total_encodings = len(user.face_encodings or [])
            for member in family_members:
                total_encodings += len(member.face_encodings or [])
            
            stats = {
                "user_id": user_id,
                "username": user.username,
                "family_members_count": len(family_members),
                "total_face_encodings": total_encodings,
                "account_created": user.created_at,
                "last_login": user.last_login,
                "is_active": user.is_active
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get user statistics: {e}")
            return {}
    
    async def logout(self):
        """Logout current user"""
        if self.current_user:
            logger.info(f"✅ User logged out: {self.current_user.username}")
            self.current_user = None
