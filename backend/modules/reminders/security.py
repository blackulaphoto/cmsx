#!/usr/bin/env python3
"""
Security utilities for authentication
Password hashing, JWT token creation and verification
"""

from datetime import datetime, timedelta
from typing import Optional, Union
import os
import secrets

from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt

from .models import TokenData, User

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        role: str = payload.get("role")
        
        if username is None:
            return None
            
        token_data = TokenData(
            username=username,
            user_id=user_id,
            role=role
        )
        return token_data
        
    except JWTError:
        return None

def create_user_token(user: User) -> dict:
    """Create token payload for user"""
    return {
        "sub": user.username,
        "user_id": user.user_id,
        "role": user.role,
        "email": user.email,
        "full_name": user.full_name
    }

def generate_secure_password(length: int = 12) -> str:
    """Generate a secure random password"""
    import string
    import random
    
    # Ensure password has at least one of each character type
    password = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice("!@#$%^&*")
    ]
    
    # Fill the rest with random characters
    for _ in range(length - 4):
        password.append(random.choice(
            string.ascii_letters + string.digits + "!@#$%^&*"
        ))
    
    # Shuffle the password
    random.shuffle(password)
    return ''.join(password)

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

def mask_sensitive_data(data: dict) -> dict:
    """Mask sensitive data in logs/responses"""
    masked = data.copy()
    sensitive_fields = ['password', 'hashed_password', 'access_token', 'secret']
    
    for field in sensitive_fields:
        if field in masked:
            if isinstance(masked[field], str) and len(masked[field]) > 4:
                masked[field] = masked[field][:2] + "*" * (len(masked[field]) - 4) + masked[field][-2:]
            else:
                masked[field] = "***"
    
    return masked

