"""CORS configuration for Next.js + FastAPI integration."""
from fastapi.middleware.cors import CORSMiddleware
import os

# Get environment configuration
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# Base allowed origins for development
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Add production frontend URL if provided
if FRONTEND_URL and FRONTEND_URL not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(FRONTEND_URL)

print(f"[CORS] Configuration:")
print(f"   Environment: {ENVIRONMENT}")
print(f"   Allowed Origins: {ALLOWED_ORIGINS}")


def add_cors_middleware(app):
    """Add CORS middleware to the FastAPI application."""
    # In production, use allow_origin_regex for wildcard support (Vercel deployments)
    if ENVIRONMENT == "production":
        print("[PROD] Using production CORS with Vercel wildcard support")
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"https://.*\.vercel\.app",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        print(f"[DEV] Using development CORS with origins: {ALLOWED_ORIGINS}")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
