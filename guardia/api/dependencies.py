"""
API dependencies for Guardia AI Enhanced System

This module provides dependency injection functions for FastAPI endpoints including:
- User authentication and authorization
- Service layer dependency injection
- Database connection management
- Request validation and security
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime

from ..config.settings import get_settings
from ..services.user_service import UserService
from ..services.surveillance_service import SurveillanceService
from ..services.alert_service import AlertService
from ..services.notification_service import NotificationService
from ..db.connection import get_database
from ..db.repository import Repository

# Security scheme for JWT tokens
security = HTTPBearer()
settings = get_settings()

async def get_database_dependency():
    """Get database connection for dependency injection"""
    return await get_database()

async def get_repository(db = Depends(get_database_dependency)) -> Repository:
    """Get repository instance for dependency injection"""
    return Repository(db)

async def get_user_service(repository: Repository = Depends(get_repository)) -> UserService:
    """Get user service instance for dependency injection"""
    return UserService(repository)

async def get_surveillance_service(repository: Repository = Depends(get_repository)) -> SurveillanceService:
    """Get surveillance service instance for dependency injection"""
    return SurveillanceService(repository)

async def get_alert_service(repository: Repository = Depends(get_repository)) -> AlertService:
    """Get alert service instance for dependency injection"""
    return AlertService(repository)

async def get_notification_service(repository: Repository = Depends(get_repository)) -> NotificationService:
    """Get notification service instance for dependency injection"""
    return NotificationService(repository)

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify JWT token and extract user information
    
    Returns:
        dict: User information from token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract user information
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "username": payload.get("username"),
            "role": payload.get("role", "user"),
            "permissions": payload.get("permissions", [])
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    user_data: dict = Depends(verify_token),
    user_service: UserService = Depends(get_user_service)
) -> dict:
    """
    Get current authenticated user with full profile information
    
    Returns:
        dict: Complete user profile information
        
    Raises:
        HTTPException: If user not found or inactive
    """
    try:
        # Get full user profile from database
        user = await user_service.get_user_by_id(user_data["user_id"])
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Combine token data with user profile
        return {
            **user_data,
            "profile": user.dict(),
            "is_admin": user_data.get("role") == "admin",
            "full_name": f"{user.first_name} {user.last_name}".strip()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user profile: {str(e)}"
        )

async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Get current active user (alias for get_current_user for compatibility)
    """
    return current_user

async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Get current user and verify admin privileges
    
    Returns:
        dict: User information for admin user
        
    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user

def require_permissions(required_permissions: list):
    """
    Dependency factory for permission-based access control
    
    Args:
        required_permissions: List of required permissions
        
    Returns:
        Dependency function that checks user permissions
    """
    async def check_permissions(current_user: dict = Depends(get_current_user)) -> dict:
        user_permissions = current_user.get("permissions", [])
        
        # Admin users have all permissions
        if current_user.get("is_admin"):
            return current_user
        
        # Check if user has all required permissions
        missing_permissions = [
            perm for perm in required_permissions 
            if perm not in user_permissions
        ]
        
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing_permissions)}"
            )
        
        return current_user
    
    return check_permissions

async def validate_session_access(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    surveillance_service: SurveillanceService = Depends(get_surveillance_service)
) -> dict:
    """
    Validate user access to specific surveillance session
    
    Args:
        session_id: ID of surveillance session
        current_user: Current authenticated user
        surveillance_service: Surveillance service instance
        
    Returns:
        dict: User information if access is valid
        
    Raises:
        HTTPException: If user doesn't have access to session
    """
    try:
        session = await surveillance_service.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surveillance session not found"
            )
        
        # Check if user owns the session or is admin
        if session.user_id != current_user["user_id"] and not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this surveillance session"
            )
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate session access: {str(e)}"
        )

async def validate_camera_access(
    camera_id: str,
    current_user: dict = Depends(get_current_user),
    surveillance_service: SurveillanceService = Depends(get_surveillance_service)
) -> dict:
    """
    Validate user access to specific camera
    
    Args:
        camera_id: ID of camera
        current_user: Current authenticated user
        surveillance_service: Surveillance service instance
        
    Returns:
        dict: User information if access is valid
        
    Raises:
        HTTPException: If user doesn't have access to camera
    """
    try:
        has_access = await surveillance_service.verify_camera_access(
            user_id=current_user["user_id"],
            camera_id=camera_id
        )
        
        # Admin users have access to all cameras
        if not has_access and not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this camera"
            )
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate camera access: {str(e)}"
        )

# Optional dependencies for request context
async def get_user_agent(request) -> Optional[str]:
    """Extract User-Agent header from request"""
    return request.headers.get("user-agent")

async def get_client_ip(request) -> Optional[str]:
    """Extract client IP address from request"""
    # Check for forwarded headers first (behind proxy/load balancer)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection IP
    return getattr(request.client, "host", None)
