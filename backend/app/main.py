"""
Main FastAPI application entry point for GoingMerry-Stonks platform.

This module initializes the FastAPI application and configures routing,
middleware, and core application settings.
"""

from typing import Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import options, screener


# Initialize FastAPI application
app = FastAPI(
    title="GoingMerry-Stonks API",
    description="Stock and Options Analysis Platform API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(options.router)
app.include_router(screener.router)


@app.get("/", tags=["Health"])
async def root() -> Dict[str, str]:
    """
    Root endpoint - Health check.

    Returns:
        Dict[str, str]: Welcome message and API status.
    """
    return {
        "message": "Hello World",
        "status": "healthy",
        "api": "GoingMerry-Stonks API",
    }


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Dict[str, str]: API health status.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
