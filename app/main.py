from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_tables

# Import API routers
from app.api.ingestion import router as ingestion_router

# Create FastAPI app
app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    description="Prediction Market Arbitrage System"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(ingestion_router)

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    create_tables()

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Prediction Market Arbitrage System API",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "ingestion": "/api/v1/ingestion"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.project_name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
