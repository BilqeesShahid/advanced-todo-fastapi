"""Authentication router for Phase V Advanced Task Management."""
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timedelta
import os
import uuid
import jwt

from app.schemas.auth import SignUpRequest, SignInRequest, TokenResponse
from app.db.config import get_session
from app.models.user import User
from sqlmodel import Session, select

router = APIRouter(tags=["Authentication"])  # No prefix since main.py adds /api prefix

BETTER_AUTH_SECRET = os.environ.get("BETTER_AUTH_SECRET", "0mbJv2O1s7AApOa1TUTKA29VZ376i3zS")


def create_jwt_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, BETTER_AUTH_SECRET, algorithm="HS256")


@router.post("/sign-up", response_model=TokenResponse)
async def sign_up(request: SignUpRequest, session: Session = Depends(get_session)):
    try:
        # Check if user already exists
        existing_statement = select(User).where(User.email == request.email)
        existing = session.exec(existing_statement).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        user = User(
            id=str(uuid.uuid4()),
            email=request.email,
            name=request.name,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        token = create_jwt_token(user.id, user.email)
        return TokenResponse(
            token=token,
            user_id=user.id,
            email=user.email
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.post("/sign-in", response_model=TokenResponse)
async def sign_in(request: SignInRequest, session: Session = Depends(get_session)):
    try:
        # Find user by email
        statement = select(User).where(User.email == request.email)
        user = session.exec(statement).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        token = create_jwt_token(user.id, user.email)
        return TokenResponse(
            token=token,
            user_id=user.id,
            email=user.email
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sign in failed: {str(e)}"
        )
