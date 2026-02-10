"""Main FastAPI application for Phase II Todo Backend."""
from fastapi import FastAPI,Request
from app.middleware.cors import add_cors_middleware
from app.db.init import init_db

# Create FastAPI application
app = FastAPI(
    title="Evolution of Task by Chatbot API",
    description="REST API for Phase V Full-Stack Advanced Features of Todo Application",
    version="1.0.0",
    contact={
        "name": "Phase v Development Team",
    },
)

# Add CORS middleware
add_cors_middleware(app)


@app.on_event("startup")
async def startup_event():
    """Initialize database and MCP server on startup."""
    try:
        init_db()
        print("[SUCCESS] Database tables initialized successfully.")
    except Exception as e:
        print(f"[WARNING] Database initialization failed: {str(e)}")
        print("[WARNING] Server will continue but database operations may fail.")
        print("[WARNING] Please check your DATABASE_URL and network connection.")

    # Initialize MCP server with tools
    from app.mcp.server import get_mcp_server
    from app.mcp.tools.add_task import register_add_task_tool
    from app.mcp.tools.list_tasks import register_list_tasks_tool
    from app.mcp.tools.update_task import register_update_task_tool
    from app.mcp.tools.complete_task import register_complete_task_tool
    from app.mcp.tools.delete_task import register_delete_task_tool
    from app.mcp.tools.view_task import register_view_task_tool
    from app.db.config import get_session

    mcp_server = get_mcp_server()

    # Register tools with a database session
    # Note: Each tool invocation will use its own session via dependency injection
    # This is just for registration
    try:
        db = next(get_session())
        try:
            register_add_task_tool(mcp_server, db)
            register_list_tasks_tool(mcp_server, db)
            register_view_task_tool(mcp_server, db)
            register_update_task_tool(mcp_server, db)
            register_complete_task_tool(mcp_server, db)
            register_delete_task_tool(mcp_server, db)
            print(f"[SUCCESS] MCP Server initialized with tools: {mcp_server.list_tools()}")
        finally:
            db.close()
    except Exception as e:
        print(f"[WARNING] MCP tool registration failed: {str(e)}")
        print("[WARNING] Chat functionality may not work until database is accessible.")

    print("[SUCCESS] Application startup complete.")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint - API welcome message."""
    return {
        "message": "Phase3: Welcome to Evolution of Todo API",
        "title": "Evolution of Todo API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# Import and include routers
from app.routers import auth, tasks, chat
app.include_router(auth.router, prefix="/auth")  # Auth endpoints: /auth/sign-up, /auth/sign-in
app.include_router(tasks.router, prefix="/api")  # Task endpoints: /api/{user_id}/tasks
app.include_router(chat.router, prefix="/api")  # Chat endpoints: /api/{user_id}/chat

# Kafka/Dapr subscription endpoints
import httpx
from typing import Dict, Any, List

@app.get("/dapr/subscribe")
def subscribe():
    """Dapr subscription endpoint for Kafka topics."""
    return [{
        "pubsubname": "kafka-pubsub",
        "topic": "task-events",
        "route": "events"
    }]

@app.post("/events")
async def handle_event(request: Request):
    try:
        # Read raw body
        body_bytes = await request.body()

        # If body is empty, return immediately
        if not body_bytes:
            print("[DAPR] Empty request received")
            return {"status": "empty request"}

        # Parse JSON safely
        event = await request.json()
        print(f"[DAPR] Received event: {event}")

        # Process event here (your logic)
        return {"status": "processed", "event": event}

    except Exception as e:
        print(f"[DAPR] Error processing event: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/publish")
async def publish():
    """Test endpoint to publish a message to Kafka."""
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:3500/v1.0/publish/kafka-pubsub/task-events",
            json={"msg": "Hello from Dapr Kafka"}
        )
    return {"status": "sent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
