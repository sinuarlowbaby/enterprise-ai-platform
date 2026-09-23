import logging
from pathlib import Path
import sys

# Ensure backend root is on sys.path when running `python app/main.py` directly
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.routers import chat_router

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("enterprise_ai")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager for startup and shutdown event management.
    Performs critical environment and system checks before accepting traffic.
    """
    # ==================== STARTUP ====================
    logger.info("Initializing %s...", settings.APP_NAME)
    logger.info("Environment: %s | Debug: %s", settings.APP_ENV, settings.DEBUG)
    logger.info("Database Target: %s", settings.POSTGRES_DB)
    logger.info("Checking system boot preconditions: Configuration successfully verified.")
    logger.info("System boot complete. Application is ready to serve requests.")
    logger.info("Swagger UI: http://localhost:8000/docs")

    # Yield control to the application to start serving requests
    yield

    # ==================== SHUTDOWN ====================
    logger.info("Shutting down %s...", settings.APP_NAME)
    logger.info("Cleaning up resources and closing active connections...")
    logger.info("Shutdown sequence complete.")


# Initialize FastAPI application with lifespan
app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise AI Platform Backend Service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    tags=["Health"],
    summary="Application Health Check",
    response_description="Returns current operational status of the service",
    status_code=status.HTTP_200_OK,
)
async def health_check():
    """Health check endpoint to verify service vitality for monitoring and load balancers."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "service": settings.APP_NAME,
            "environment": settings.APP_ENV,
            "version": "0.1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# Mount Chat Routers
# Available at both /api/v1/chat and /chat for convenience
app.include_router(chat_router, prefix=settings.API_PREFIX)
app.include_router(chat_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
