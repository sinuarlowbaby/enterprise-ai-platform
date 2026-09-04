from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, status


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup logic (e.g., database connections, cache, model loading)
    yield
    # Shutdown logic (e.g., closing connections, cleanup)


app = FastAPI(
    title="Enterprise AI Platform - API Gateway",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
