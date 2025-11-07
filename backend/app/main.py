"""
Main FastAPI application entry point for GoingMerry-Stonks platform.

This module initializes the FastAPI application and configures routing,
middleware, and core application settings.
"""

from typing import Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import options, screener, technical_analysis


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
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://goingmerry-stonks.web.app",  # Firebase Hosting
        "https://goingmerry-stonks.firebaseapp.com",  # Firebase Hosting (alternative domain)
        "https://api.goingmerry-stonks.com",  # Custom domain (once DNS configured)
        "http://34.8.254.23",  # Load Balancer IP
        "https://34.8.254.23",  # Load Balancer IP (HTTPS)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /api prefix for load balancer routing
app.include_router(options.router, prefix="/api")
app.include_router(screener.router, prefix="/api")
app.include_router(technical_analysis.router, prefix="/api")


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
        host="0.0.0.0",  # nosec B104 - Required for Cloud Run containers
        port=8000,
        reload=True,
    )
