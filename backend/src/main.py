"""Main FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import APP_NAME
from api.routes_reference import router as reference_router

app = FastAPI(title=APP_NAME)

# Configure CORS for localhost frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(reference_router, prefix="/api")


@app.get("/api/health")
async def healthcheck():
    """Health check endpoint."""
    return {"status": "ok"}

