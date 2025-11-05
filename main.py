from http import HTTPStatus
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.database import Base, check_db_connection, engine
from app.models import (
    user,
    user_image,
    pool_image,
    user_choice,
)

# from app.routes.user_route import user_router
import logging
from app.routes import api_v1_router


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Dating AI Engine",
    description="AI-powered dating preference learning system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(HTTPStatus.INTERNAL_SERVER_ERROR)


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

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True, log_level="info")
