"""
Authentication Routes
User authentication, registration, and token management
"""
from typing import Optional
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ...models.schemas import (
    UserCreate, User, Token, APIResponse,
    UserRole
)
from ...services.user_service import UserService
from ...config.settings import settings

router = APIRouter()
security = HTTPBearer()
user_service = UserService()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Dependency to get current authenticated user"""
    try:
        user = await user_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/register", response_model=APIResponse)
async def register(user_data: UserCreate):
    """Register a new user"""
    try:
        # First user becomes owner, others become family members
        existing_users = await user_service.get_all_users(limit=1)
        if not existing_users:
            user_data.role = UserRole.OWNER
        
        user = await user_service.create_user(user_data)
        
        return APIResponse(
            success=True,
            message="User registered successfully",
            data={
                "user_id": str(user.id),
                "username": user.username,
                "role": user.role
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=APIResponse)
async def login(username: str, password: str):
    """Login user and return access token"""
    try:
        token = await user_service.login(username, password)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return APIResponse(
            success=True,
            message="Login successful",
            data={
                "access_token": token.access_token,
                "token_type": token.token_type,
                "expires_in": settings.access_token_expire_minutes * 60
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/logout", response_model=APIResponse)
async def logout(current_user: User = Depends(get_current_user)):
    """Logout current user"""
    try:
        await user_service.logout()
        
        return APIResponse(
            success=True,
            message="Logout successful"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/me", response_model=APIResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    try:
        # Get user statistics
        stats = await user_service.get_user_statistics(str(current_user.id))
        
        return APIResponse(
            success=True,
            message="User information retrieved",
            data={
                "user_id": str(current_user.id),
                "username": current_user.username,
                "email": current_user.email,
                "full_name": current_user.full_name,
                "role": current_user.role,
                "is_active": current_user.is_active,
                "created_at": current_user.created_at,
                "last_login": current_user.last_login,
                "statistics": stats
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )

@router.post("/refresh", response_model=APIResponse)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token"""
    try:
        # Create new token for the current user
        token = await user_service.login(current_user.username, "")  # Password not needed for refresh
        
        return APIResponse(
            success=True,
            message="Token refreshed successfully",
            data={
                "access_token": token.access_token,
                "token_type": token.token_type,
                "expires_in": settings.access_token_expire_minutes * 60
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/change-password", response_model=APIResponse)
async def change_password(old_password: str, new_password: str, 
                         current_user: User = Depends(get_current_user)):
    """Change user password"""
    try:
        # Verify old password
        authenticated_user = await user_service.authenticate_user(
            current_user.username, old_password
        )
        
        if not authenticated_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        hashed_password = user_service._get_password_hash(new_password)
        await user_service.update_user(str(current_user.id), {"hashed_password": hashed_password})
        
        return APIResponse(
            success=True,
            message="Password changed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )
