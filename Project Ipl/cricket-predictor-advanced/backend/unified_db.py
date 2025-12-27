"""
Unified User Database System
Consolidates all user data into a single SQLite database
Replaces both auth_db.py and users.json
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import os
import uuid
import hashlib

# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "cricket_users.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """Unified User Model"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    
    # Token system for predictions
    tokens = Column(Integer, default=100)
    
    # User metadata
    referral_code = Column(String, unique=True, default=lambda: str(uuid.uuid4())[:8].upper())
    referred_by = Column(String, nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "tokens": self.tokens,
            "referral_code": self.referral_code,
            "referred_by": self.referred_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }


# Create tables
def init_db():
    """Initialize database"""
    Base.metadata.create_all(bind=engine)
    print("[DB] Database initialized")


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str, salt: str = None) -> tuple:
    """Hash password with salt"""
    if not salt:
        salt = str(uuid.uuid4())[:16]
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return password_hash, salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verify password"""
    computed_hash, _ = hash_password(password, salt)
    return computed_hash == password_hash


def create_user(db: Session, username: str, display_name: str, password: str, email: str = None, referral_code: str = None) -> User:
    """Create a new user"""
    # Check if user exists
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise ValueError("Username already exists")
    
    if email:
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise ValueError("Email already registered")
    
    password_hash, salt = hash_password(password)
    
    user = User(
        username=username,
        display_name=display_name,
        email=email or f"{username}@cricket.local",
        password_hash=password_hash,
        salt=salt,
        referral_code=referral_code or str(uuid.uuid4())[:8].upper(),
        tokens=100  # Default 100 tokens for new users
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> User:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, username: str, password: str) -> User:
    """Authenticate user"""
    user = get_user_by_username(db, username)
    if not user:
        return None
    
    if not verify_password(password, user.password_hash, user.salt):
        return None
    
    if not user.is_active:
        return None
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user


def deduct_tokens(db: Session, username: str, tokens: int = 10) -> bool:
    """Deduct tokens from user for predictions"""
    user = get_user_by_username(db, username)
    if not user:
        return False
    
    if user.tokens < tokens:
        return False
    
    user.tokens -= tokens
    db.commit()
    db.refresh(user)
    return True


def add_tokens(db: Session, username: str, tokens: int) -> bool:
    """Add tokens to user"""
    user = get_user_by_username(db, username)
    if not user:
        return False
    
    user.tokens += tokens
    db.commit()
    db.refresh(user)
    return True


def get_all_users(db: Session) -> list:
    """Get all users (for admin/debugging)"""
    return db.query(User).all()
