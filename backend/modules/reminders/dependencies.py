#!/usr/bin/env python3
"""
Authentication Dependencies for FastAPI
Middleware for JWT token validation and role-based access control
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
import logging

from .models import User, UserRole, TokenData
from .security import verify_token
from .database import AuthDatabase

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Database instance
auth_db = AuthDatabase()

class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

class AuthorizationError(HTTPException):
    """Custom authorization error"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get current authenticated user from JWT token
    This is the main authentication dependency
    """
    try:
        # Verify token
        token_data = verify_token(credentials.credentials)
        if token_data is None:
            raise AuthenticationError("Invalid token")
        
        # Get user from database
        user = auth_db.get_user_by_id(token_data.user_id)
        if user is None:
            raise AuthenticationError("User not found")
        
        if not user.is_active:
            raise AuthenticationError("User account is inactive")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise AuthenticationError()

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (additional check for user status)
    """
    if not current_user.is_active:
        raise AuthenticationError("User account is inactive")
    
    return current_user

def require_role(allowed_roles: List[UserRole]):
    """
    Dependency factory for role-based access control
    Usage: @app.get("/admin", dependencies=[Depends(require_role([UserRole.ADMIN]))])
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AuthorizationError(
                f"Access denied. Required roles: {[role.value for role in allowed_roles]}"
            )
        return current_user
    
    return role_checker

def require_supervisor():
    """Dependency for supervisor-only access"""
    async def supervisor_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in [UserRole.SUPERVISOR, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Supervisor or admin access required"
            )
        return current_user
    return supervisor_dependency

def require_admin():
    """Dependency for admin-only access"""
    async def admin_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return current_user
    return admin_dependency

def require_case_manager():
    """Dependency for case manager access (includes supervisors and admins)"""
    async def case_manager_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in [UserRole.CASE_MANAGER, UserRole.SUPERVISOR, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Case manager access required"
            )
        return current_user
    return case_manager_dependency

async def get_optional_user(
    request: Request
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise
    Useful for endpoints that work with or without authentication
    """
    try:
        # Try to get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        token_data = verify_token(token)
        
        if token_data is None:
            return None
        
        user = auth_db.get_user_by_id(token_data.user_id)
        if user and user.is_active:
            return user
        
        return None
        
    except Exception:
        return None

class TeamAccessChecker:
    """Check if user can access team member data"""
    
    def __init__(self, allow_self: bool = True):
        self.allow_self = allow_self
    
    async def __call__(
        self,
        target_user_id: str,
        current_user: User = Depends(get_current_active_user)
    ) -> bool:
        """Check if current user can access target user's data"""
        
        # Admins can access everything
        if current_user.role == UserRole.ADMIN:
            return True
        
        # Users can access their own data
        if self.allow_self and current_user.user_id == target_user_id:
            return True
        
        # Supervisors can access their team members' data
        if current_user.role == UserRole.SUPERVISOR:
            team_members = auth_db.get_team_members(current_user.user_id)
            team_member_ids = [member.user_id for member in team_members]
            
            if target_user_id in team_member_ids:
                return True
        
        raise AuthorizationError("Access denied to user data")

# Instances for common use cases
check_team_access = TeamAccessChecker(allow_self=True)
check_team_access_no_self = TeamAccessChecker(allow_self=False)

def get_user_permissions(current_user: User = Depends(get_current_active_user)):
    """Get user permissions based on role"""
    from .models import get_role_permissions
    return get_role_permissions(current_user.role)

async def validate_supervisor_access(
    target_user_id: str,
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Validate that supervisor can access team member data"""
    
    if current_user.role == UserRole.ADMIN:
        return current_user
    
    if current_user.role == UserRole.SUPERVISOR:
        team_members = auth_db.get_team_members(current_user.user_id)
        team_member_ids = [member.user_id for member in team_members]
        
        if target_user_id in team_member_ids or target_user_id == current_user.user_id:
            return current_user
    
    if current_user.user_id == target_user_id:
        return current_user
    
    raise AuthorizationError("Access denied to user data")

# Middleware function for protecting routes
def protect_route(allowed_roles: Optional[List[UserRole]] = None):
    """
    Route protection decorator
    Usage: @protect_route([UserRole.ADMIN])
    """
    def decorator(func):
        if allowed_roles:
            return Depends(require_role(allowed_roles))(func)
        else:
            return Depends(get_current_active_user)(func)
    return decorator

