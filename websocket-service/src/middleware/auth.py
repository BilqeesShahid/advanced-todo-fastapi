"""
Authentication Middleware.

Provides JWT-based authentication for WebSocket and HTTP endpoints.
"""

import jwt
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from jose import JWTError
from functools import wraps

logger = logging.getLogger(__name__)

# Configuration - in production, these would come from environment variables
SECRET_KEY = "your-secret-key-here"  # This should be loaded from environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class AuthMiddleware:
    """Authentication middleware for validating JWT tokens."""

    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode JWT token and return payload.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload or None if invalid
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith("Bearer "):
                token = token[7:]

            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload

        except JWTError as e:
            logger.error(f"JWT decode error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error decoding token: {str(e)}")
            return None

    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        """
        Verify JWT token and return user ID.

        Args:
            token: JWT token string

        Returns:
            User ID string or None if invalid
        """
        payload = AuthMiddleware.decode_token(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                # Check if token is expired
                exp = payload.get("exp")
                if exp and datetime.utcnow().timestamp() > exp:
                    logger.warning("Token expired")
                    return None
                return user_id

        return None

    @staticmethod
    async def authenticate_request(request: Request) -> Optional[str]:
        """
        Authenticate incoming request and return user ID.

        Args:
            request: FastAPI request object

        Returns:
            User ID string or None if authentication failed
        """
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("No Authorization header found")
            return None

        # Verify token format
        if not auth_header.startswith("Bearer "):
            logger.warning("Invalid Authorization header format")
            return None

        token = auth_header[7:]  # Remove "Bearer " prefix
        user_id = AuthMiddleware.verify_token(token)

        if user_id:
            logger.info(f"Authenticated user: {user_id}")
            # Store user_id in request state for later use
            request.state.user_id = user_id
        else:
            logger.warning("Token verification failed")

        return user_id

    @staticmethod
    async def authenticate_websocket_connection(query_params: Dict[str, str]) -> Optional[str]:
        """
        Authenticate WebSocket connection using query parameters.

        Args:
            query_params: Dictionary of query parameters

        Returns:
            User ID string or None if authentication failed
        """
        token = query_params.get("token")
        if not token:
            logger.warning("No token provided in WebSocket connection")
            return None

        user_id = AuthMiddleware.verify_token(token)
        if user_id:
            logger.info(f"WebSocket authenticated user: {user_id}")
        else:
            logger.warning("WebSocket token verification failed")

        return user_id


def require_auth(handler):
    """Decorator to require authentication for handlers."""
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        # This would check for authentication before calling the handler
        # Implementation depends on the specific handler type
        request = kwargs.get('request') or (args[0] if args else None)

        if request and hasattr(request, 'headers'):
            user_id = await AuthMiddleware.authenticate_request(request)
            if not user_id:
                raise HTTPException(status_code=401, detail="Authentication required")
            return await handler(*args, **kwargs)
        else:
            # For other types of handlers (e.g., WebSocket), authentication
            # would need to be handled differently
            return await handler(*args, **kwargs)

    return wrapper


# Example usage in FastAPI
def add_auth_middleware(app):
    """Add authentication middleware to FastAPI app."""
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        # Skip authentication for public endpoints
        if request.url.path in ["/", "/health", "/docs", "/redoc"]:
            return await call_next(request)

        user_id = await AuthMiddleware.authenticate_request(request)
        if not user_id and request.method != "OPTIONS":
            # Don't require auth for OPTIONS requests (preflight)
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"}
            )

        response = await call_next(request)
        return response