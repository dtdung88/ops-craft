from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.security import decode_token
from app.schemas.user import TokenData

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        if payload is None:
            raise credentials_exception
        
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        token_type: str = payload.get("type", "access")  # Default to access if not present
        
        if username is None or user_id is None:
            raise credentials_exception
        
        # Verify it's an access token, not refresh token (only if type field exists)
        if token_type and token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if user is None:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise credentials_exception


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verify user is active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


class RoleChecker:
    """Dependency to check user role"""
    def __init__(self, required_role: UserRole):
        self.required_role = required_role
    
    def __call__(self, user: User = Depends(get_current_active_user)) -> User:
        if not user.has_permission(self.required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires {self.required_role.value} role or higher"
            )
        return user


# Role permission dependencies
require_admin = RoleChecker(UserRole.ADMIN)
require_operator = RoleChecker(UserRole.OPERATOR)
require_viewer = RoleChecker(UserRole.VIEWER)