import asyncio
from app.main import app
from mangum import Mangum

# ASGI handler for Vercel deployment
handler = Mangum(app, lifespan="off")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)