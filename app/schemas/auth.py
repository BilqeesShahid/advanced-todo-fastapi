"""Authentication schemas for Phase II Todo Application."""
from pydantic import BaseModel, EmailStr


class TokenResponse(BaseModel):
    """Response containing JWT token after sign in."""
    token: str
    user_id: str
    email: str


class SignUpRequest(BaseModel):
    """Sign up request body."""
    email: EmailStr
    password: str
    name: str | None = None


class SignInRequest(BaseModel):
    """Sign in request body."""
    email: EmailStr
    password: str
