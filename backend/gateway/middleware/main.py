from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, status


from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup logic (e.g., database connections, cache, model loading)
    yield
    # Shutdown logic (e.g., closing connections, cleanup)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
