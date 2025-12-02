"""
User Management Service for Guardia AI
Comprehensive user profiles with biometric data, family members, access levels, and activity logs
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import select, func, and_, or_
from passlib.context import CryptContext
from jose import JWTError, jwt
import pyotp
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
import redis.asyncio as redis

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics
users_total = Gauge('user_management_users_total', 'Total users', ['role'])
login_attempts = Counter('user_management_login_attempts_total', 'Login attempts', ['result'])
activity_logs = Counter('user_management_activity_logs_total', 'Activity logs', ['action'])

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./users.db")
SECRET_KEY = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Database setup
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# Enums
class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    FAMILY = "family"
    GUEST = "guest"
    OPERATOR = "operator"


class AccessLevel(int, Enum):
    NONE = 0
    VIEW_ONLY = 1
    BASIC = 2
    STANDARD = 3
    ELEVATED = 4
    FULL = 5


class ActivityType(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    FAILED_LOGIN = "failed_login"
    PASSWORD_CHANGE = "password_change"
    PROFILE_UPDATE = "profile_update"
    FACE_ENROLLED = "face_enrolled"
    FACE_REMOVED = "face_removed"
    MEMBER_ADDED = "member_added"
    MEMBER_REMOVED = "member_removed"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    SETTINGS_CHANGED = "settings_changed"
    EMERGENCY_TRIGGERED = "emergency_triggered"


# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    avatar_url = Column(String(500))
    
    # Role and access
    role = Column(String(20), default=UserRole.GUEST.value)
    access_level = Column(Integer, default=AccessLevel.BASIC.value)
    
    # Biometric data references
    face_id = Column(String(36))  # Reference to enrolled face
    
    # Security
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(32))
    
    # Preferences
    preferences = Column(JSON, default=dict)
    notification_settings = Column(JSON, default=dict)
    
    # Emergency contacts
    emergency_contacts = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    family_members = relationship("FamilyMember", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")


class FamilyMember(Base):
    __tablename__ = "family_members"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Member info
    name = Column(String(200), nullable=False)
    relationship = Column(String(50))  # spouse, child, parent, etc.
    
    # Access
    access_level = Column(Integer, default=AccessLevel.BASIC.value)
    can_arm_disarm = Column(Boolean, default=False)
    can_view_cameras = Column(Boolean, default=True)
    can_receive_alerts = Column(Boolean, default=True)
    
    # Biometric
    face_id = Column(String(36))
    
    # Contact
    phone = Column(String(20))
    email = Column(String(255))
    
    # Schedule-based access
    access_schedule = Column(JSON)  # {"mon": {"start": "08:00", "end": "22:00"}, ...}
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="family_members")


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    activity_type = Column(String(50), nullable=False)
    description = Column(Text)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    metadata = Column(JSON)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="activity_logs")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    name = Column(String(200), nullable=False)
    relationship = Column(String(50))
    phone = Column(String(20), nullable=False)
    email = Column(String(255))
    priority = Column(Integer, default=1)  # 1 = highest priority
    
    # Auto-contact settings
    auto_contact_on_critical = Column(Boolean, default=True)
    auto_contact_on_high = Column(Boolean, default=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = UserRole.GUEST


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[Dict] = None
    notification_settings: Optional[Dict] = None


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    avatar_url: Optional[str]
    role: str
    access_level: int
    is_active: bool
    is_verified: bool
    two_factor_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class FamilyMemberCreate(BaseModel):
    name: str
    relationship: Optional[str] = None
    access_level: int = AccessLevel.BASIC.value
    can_arm_disarm: bool = False
    can_view_cameras: bool = True
    can_receive_alerts: bool = True
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    access_schedule: Optional[Dict] = None


class FamilyMemberResponse(BaseModel):
    id: str
    name: str
    relationship: Optional[str]
    access_level: int
    can_arm_disarm: bool
    can_view_cameras: bool
    can_receive_alerts: bool
    phone: Optional[str]
    email: Optional[str]
    face_id: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class EmergencyContactCreate(BaseModel):
    name: str
    relationship: Optional[str] = None
    phone: str
    email: Optional[EmailStr] = None
    priority: int = 1
    auto_contact_on_critical: bool = True
    auto_contact_on_high: bool = False


class EmergencyContactResponse(BaseModel):
    id: str
    name: str
    relationship: Optional[str]
    phone: str
    email: Optional[str]
    priority: int
    auto_contact_on_critical: bool
    auto_contact_on_high: bool
    is_active: bool
    
    class Config:
        from_attributes = True


class ActivityLogResponse(BaseModel):
    id: int
    activity_type: str
    description: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime
    metadata: Optional[Dict]
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class TwoFactorSetup(BaseModel):
    code: str


# Helper Functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_db():
    async with async_session() as session:
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if username is None or token_type != "access":
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


async def log_activity(
    db: AsyncSession,
    user_id: str,
    activity_type: ActivityType,
    description: str = None,
    ip_address: str = None,
    user_agent: str = None,
    metadata: Dict = None
):
    """Log user activity"""
    log = ActivityLog(
        user_id=user_id,
        activity_type=activity_type.value,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata
    )
    db.add(log)
    await db.commit()
    activity_logs.labels(action=activity_type.value).inc()


# FastAPI Application
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("User management service started")
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Guardia User Management",
    description="Comprehensive user management with profiles, family members, and activity logs",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health and Metrics
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "user-management"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Authentication
@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    # Check if email or username exists
    result = await db.execute(
        select(User).where(or_(User.email == user_data.email, User.username == user_data.username))
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email or username already registered")
    
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        role=user_data.role.value
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    await log_activity(
        db, user.id, ActivityType.LOGIN,
        "User registered",
        ip_address=request.client.host
    )
    
    logger.info(f"User registered: {user.email}")
    return user


@app.post("/auth/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login and get tokens"""
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        login_attempts.labels(result="failed").inc()
        if user:
            await log_activity(
                db, user.id, ActivityType.FAILED_LOGIN,
                "Failed login attempt",
                ip_address=request.client.host
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is disabled")
    
    # Update last login
    user.last_login = datetime.utcnow()
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    # Store refresh token
    refresh_token_obj = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(refresh_token_obj)
    await db.commit()
    
    await log_activity(
        db, user.id, ActivityType.LOGIN,
        "User logged in",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    login_attempts.labels(result="success").inc()
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@app.post("/auth/refresh", response_model=Token)
async def refresh_token(token_data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Refresh access token"""
    try:
        payload = jwt.decode(token_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        token_type = payload.get("type")
        
        if not username or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
            
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Check if token is revoked
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == token_data.refresh_token,
            RefreshToken.revoked == False
        )
    )
    token_obj = result.scalar_one_or_none()
    
    if not token_obj or token_obj.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    # Get user
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    # Create new tokens
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    new_refresh_token = create_refresh_token(data={"sub": user.username})
    
    # Revoke old refresh token and create new one
    token_obj.revoked = True
    new_token_obj = RefreshToken(
        user_id=user.id,
        token=new_refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(new_token_obj)
    await db.commit()
    
    return Token(access_token=access_token, refresh_token=new_refresh_token)


@app.post("/auth/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout and revoke tokens"""
    # Revoke all refresh tokens for user
    await db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.user_id == current_user.id)
        .values(revoked=True)
    )
    await db.commit()
    
    await log_activity(
        db, current_user.id, ActivityType.LOGOUT,
        "User logged out",
        ip_address=request.client.host
    )
    
    return {"status": "logged out"}


# User Profile
@app.get("/users/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@app.put("/users/me", response_model=UserResponse)
async def update_me(
    update_data: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile"""
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    await log_activity(
        db, current_user.id, ActivityType.PROFILE_UPDATE,
        "Profile updated",
        ip_address=request.client.host
    )
    
    return current_user


@app.post("/users/me/password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change password"""
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    
    await log_activity(
        db, current_user.id, ActivityType.PASSWORD_CHANGE,
        "Password changed",
        ip_address=request.client.host
    )
    
    return {"status": "password changed"}


# Two-Factor Authentication
@app.post("/users/me/2fa/setup")
async def setup_2fa(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Setup two-factor authentication"""
    if current_user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="2FA already enabled")
    
    secret = pyotp.random_base32()
    current_user.two_factor_secret = secret
    await db.commit()
    
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(current_user.email, issuer_name="Guardia AI")
    
    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri
    }


@app.post("/users/me/2fa/verify")
async def verify_2fa(
    setup_data: TwoFactorSetup,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify and enable 2FA"""
    if not current_user.two_factor_secret:
        raise HTTPException(status_code=400, detail="2FA not set up")
    
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(setup_data.code):
        raise HTTPException(status_code=400, detail="Invalid code")
    
    current_user.two_factor_enabled = True
    await db.commit()
    
    await log_activity(
        db, current_user.id, ActivityType.SETTINGS_CHANGED,
        "2FA enabled",
        ip_address=request.client.host
    )
    
    return {"status": "2FA enabled"}


@app.delete("/users/me/2fa")
async def disable_2fa(
    code: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disable 2FA"""
    if not current_user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="2FA not enabled")
    
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(code):
        raise HTTPException(status_code=400, detail="Invalid code")
    
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    await db.commit()
    
    await log_activity(
        db, current_user.id, ActivityType.SETTINGS_CHANGED,
        "2FA disabled",
        ip_address=request.client.host
    )
    
    return {"status": "2FA disabled"}


# Family Members
@app.get("/family-members", response_model=List[FamilyMemberResponse])
async def list_family_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List family members"""
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == current_user.id)
    )
    return result.scalars().all()


@app.post("/family-members", response_model=FamilyMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_family_member(
    member_data: FamilyMemberCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a family member"""
    member = FamilyMember(
        user_id=current_user.id,
        **member_data.model_dump()
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    
    await log_activity(
        db, current_user.id, ActivityType.MEMBER_ADDED,
        f"Added family member: {member.name}",
        ip_address=request.client.host
    )
    
    return member


@app.get("/family-members/{member_id}", response_model=FamilyMemberResponse)
async def get_family_member(
    member_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get family member"""
    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.user_id == current_user.id
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")
    
    return member


@app.put("/family-members/{member_id}", response_model=FamilyMemberResponse)
async def update_family_member(
    member_id: str,
    member_data: FamilyMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update family member"""
    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.user_id == current_user.id
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")
    
    for field, value in member_data.model_dump().items():
        setattr(member, field, value)
    
    await db.commit()
    await db.refresh(member)
    
    return member


@app.delete("/family-members/{member_id}")
async def delete_family_member(
    member_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete family member"""
    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.user_id == current_user.id
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")
    
    name = member.name
    await db.delete(member)
    await db.commit()
    
    await log_activity(
        db, current_user.id, ActivityType.MEMBER_REMOVED,
        f"Removed family member: {name}",
        ip_address=request.client.host
    )
    
    return {"status": "deleted"}


# Emergency Contacts
@app.get("/emergency-contacts", response_model=List[EmergencyContactResponse])
async def list_emergency_contacts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List emergency contacts"""
    result = await db.execute(
        select(EmergencyContact)
        .where(EmergencyContact.user_id == current_user.id)
        .order_by(EmergencyContact.priority)
    )
    return result.scalars().all()


@app.post("/emergency-contacts", response_model=EmergencyContactResponse, status_code=status.HTTP_201_CREATED)
async def add_emergency_contact(
    contact_data: EmergencyContactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add emergency contact"""
    contact = EmergencyContact(
        user_id=current_user.id,
        **contact_data.model_dump()
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    
    return contact


@app.delete("/emergency-contacts/{contact_id}")
async def delete_emergency_contact(
    contact_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete emergency contact"""
    result = await db.execute(
        select(EmergencyContact).where(
            EmergencyContact.id == contact_id,
            EmergencyContact.user_id == current_user.id
        )
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Emergency contact not found")
    
    await db.delete(contact)
    await db.commit()
    
    return {"status": "deleted"}


# Activity Logs
@app.get("/activity-logs", response_model=List[ActivityLogResponse])
async def get_activity_logs(
    activity_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get activity logs"""
    query = select(ActivityLog).where(ActivityLog.user_id == current_user.id)
    
    if activity_type:
        query = query.where(ActivityLog.activity_type == activity_type)
    
    if start_date:
        query = query.where(ActivityLog.timestamp >= start_date)
    
    if end_date:
        query = query.where(ActivityLog.timestamp <= end_date)
    
    query = query.order_by(ActivityLog.timestamp.desc()).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


# Admin Endpoints
@app.get("/admin/users", response_model=List[UserResponse])
async def list_users(
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)"""
    if current_user.role not in [UserRole.OWNER.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = select(User)
    
    if role:
        query = query.where(User.role == role)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@app.put("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: UserRole,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user role (owner only)"""
    if current_user.role != UserRole.OWNER.value:
        raise HTTPException(status_code=403, detail="Owner access required")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.role = role.value
    await db.commit()
    
    await log_activity(
        db, current_user.id, ActivityType.SETTINGS_CHANGED,
        f"Changed role for user {user.username} to {role.value}",
        ip_address=request.client.host
    )
    
    return {"status": "role updated"}


@app.put("/admin/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate user (admin only)"""
    if current_user.role not in [UserRole.OWNER.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role == UserRole.OWNER.value:
        raise HTTPException(status_code=400, detail="Cannot deactivate owner")
    
    user.is_active = False
    await db.commit()
    
    await log_activity(
        db, current_user.id, ActivityType.SETTINGS_CHANGED,
        f"Deactivated user: {user.username}",
        ip_address=request.client.host
    )
    
    return {"status": "user deactivated"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("USER_MANAGEMENT_PORT", "8013"))
    uvicorn.run(app, host="0.0.0.0", port=port)
