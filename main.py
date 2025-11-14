"""
Updated main.py with HTTP client lifecycle management
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.container import container
from app.core.database import Base, check_db_connection, engine
from app.core.logging_config import get_logger, setup_logging
from app.middleware.error_middleware import ErrorHandlingMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.routes import api_v1_router
from app.utils.http_client import close_http_client

from fastapi.staticfiles import StaticFiles

Base.metadata.create_all(bind=engine)

setup_logging(level="INFO", json_format=True)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info(
        "Application starting",
        extra={"version": "1.0.0", "environment": "development"}
    )

    if not check_db_connection():
        logger.error("Failed to connect to database on startup")
    else:
        logger.info("Database connection established")

    logger.info("HTTP client initialized with connection pooling")

    yield

    # Shutdown
    logger.info("Application shutting down...")
    
    # Close HTTP client and release connections
    await close_http_client()
    logger.info("HTTP client closed")


app = FastAPI(
    title="Dating AI Engine",
    description="AI-powered dating preference learning system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

container.wire(
    modules=[
        "app.routes.sync_route",
        "app.routes.user_route",
    ]
)

app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = check_db_connection()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "version": "1.0.0",
    }


app.include_router(api_v1_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True, log_level="info")