"""Reference track API routes."""
from fastapi import APIRouter

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("/ping")
async def ping():
    """Health check endpoint for reference API."""
    return {"message": "reference api ok"}

