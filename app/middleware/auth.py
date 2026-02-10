"""JWT authentication middleware for FastAPI."""
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel
from typing import Optional
import os

# Load environment
BETTER_AUTH_SECRET = os.environ.get("BETTER_AUTH_SECRET", "0mbJv2O1s7AApOa1TUTKA29VZ376i3zS")  # Default to the value from .env

security = HTTPBearer()


class CurrentUser(BaseModel):
    """User information extracted from JWT."""
    user_id: str
    email: Optional[str] = None


async def get_current_user(
    request: Request
) -> CurrentUser:
    """
    Validate JWT token from Authorization header and extract user information.

    Args:
        request: FastAPI request object to extract Authorization header

    Returns:
        CurrentUser with user_id and email from token

    Raises:
        HTTPException: If token is invalid or expired
    """
    # Skip authentication for OPTIONS requests (preflight CORS requests)
    if request.method == "OPTIONS":
        return CurrentUser(user_id="", email="")
    
    # Extract Authorization header
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]  # Remove "Bearer " prefix

    try:
        payload = jwt.decode(
            token,
            BETTER_AUTH_SECRET,
            algorithms=["HS256"]
        )

        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return CurrentUser(
            user_id=user_id,
            email=payload.get("email")
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_user_access(
    user_id: str,
    request: Request
) -> str:
    """
    Verify that the authenticated user matches the requested user ID.

    Args:
        user_id: The user ID from the request path
        request: FastAPI request object to extract Authorization header

    Returns:
        The verified user ID

    Raises:
        HTTPException: If user ID doesn't match or user is not authenticated
    """
    # Skip verification for OPTIONS requests (preflight CORS requests)
    if request.method == "OPTIONS":
        return user_id
    
    current_user = await get_current_user(request)

    if user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's resources"
        )
    return user_id
