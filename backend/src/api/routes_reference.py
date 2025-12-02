"""Reference track API routes."""
import os
import shutil
import uuid
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

from models.store import REFERENCE_BUNDLES, REFERENCE_REGIONS
from models.region import Region
from stem_ingest.ingest_service import load_reference_bundle
from analysis.region_detector.region_detector import detect_regions
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/reference", tags=["reference"])

# Temporary directory for uploaded files
TEMP_DIR = Path("tmp/reference")


@router.get("/ping")
async def ping():
    """Health check endpoint for reference API."""
    return {"message": "reference api ok"}


@router.post("/upload")
async def upload_reference(
    drums: UploadFile = File(...),
    bass: UploadFile = File(...),
    vocals: UploadFile = File(...),
    instruments: UploadFile = File(...),
    full_mix: UploadFile = File(...)
):
    """
    Upload reference track stems and full mix.
    
    Accepts 5 audio files (drums, bass, vocals, instruments, full_mix)
    and creates a ReferenceBundle.
    
    Returns:
        JSON with referenceId for the uploaded bundle
    """
    reference_id = str(uuid.uuid4())
    logger.info(f"Starting upload for reference_id: {reference_id}")
    
    # Create temporary directory for this reference
    ref_dir = TEMP_DIR / reference_id
    ref_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Map of roles to file paths
        file_paths: Dict[str, Path] = {}
        
        # Save uploaded files
        uploads = {
            "drums": drums,
            "bass": bass,
            "vocals": vocals,
            "instruments": instruments,
            "full_mix": full_mix
        }
        
        for role, upload_file in uploads.items():
            # Get file extension from original filename or content type
            original_filename = upload_file.filename or f"{role}.wav"
            file_ext = Path(original_filename).suffix or ".wav"
            
            # Save to temporary directory
            file_path = ref_dir / f"{role}{file_ext}"
            
            logger.info(f"Saving {role} to {file_path}")
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(upload_file.file, f)
            
            file_paths[role] = file_path
        
        # Load reference bundle
        logger.info(f"Loading reference bundle from {ref_dir}")
        bundle = load_reference_bundle(file_paths)
        
        # Store in memory
        REFERENCE_BUNDLES[reference_id] = bundle
        logger.info(f"Stored reference bundle {reference_id}: {bundle}")
        
        return {
            "referenceId": reference_id,
            "bpm": bundle.bpm,
            "duration": bundle.full_mix.duration,
            "key": bundle.key
        }
    
    except Exception as e:
        logger.error(f"Error uploading reference {reference_id}: {e}", exc_info=True)
        # Clean up on error
        if ref_dir.exists():
            shutil.rmtree(ref_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to upload and process reference: {str(e)}"
        )


@router.post("/{reference_id}/analyze")
async def analyze_reference(reference_id: str):
    """
    Analyze a reference bundle to detect regions.
    
    Args:
        reference_id: ID of the reference bundle to analyze
    
    Returns:
        JSON with analysis status and region count
    """
    logger.info(f"Starting analysis for reference_id: {reference_id}")
    
    # Look up reference bundle
    if reference_id not in REFERENCE_BUNDLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference bundle {reference_id} not found"
        )
    
    bundle = REFERENCE_BUNDLES[reference_id]
    
    try:
        # Detect regions
        logger.info(f"Detecting regions for bundle: {bundle}")
        regions = detect_regions(bundle)
        
        # Store regions
        REFERENCE_REGIONS[reference_id] = regions
        logger.info(f"Detected {len(regions)} regions for reference {reference_id}")
        
        return {
            "referenceId": reference_id,
            "regionCount": len(regions),
            "status": "ok"
        }
    
    except Exception as e:
        logger.error(f"Error analyzing reference {reference_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze reference: {str(e)}"
        )


@router.get("/{reference_id}/regions")
async def get_regions(reference_id: str):
    """
    Get detected regions for a reference bundle.
    
    Args:
        reference_id: ID of the reference bundle
    
    Returns:
        JSON list of regions
    """
    logger.info(f"Getting regions for reference_id: {reference_id}")
    
    # Check if reference exists
    if reference_id not in REFERENCE_BUNDLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference bundle {reference_id} not found"
        )
    
    # Check if regions have been detected
    if reference_id not in REFERENCE_REGIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regions not found for reference {reference_id}. Run /analyze first."
        )
    
    regions = REFERENCE_REGIONS[reference_id]
    
    # Convert Region dataclasses to dictionaries for JSON serialization
    regions_dict = []
    for region in regions:
        regions_dict.append({
            "id": region.id,
            "name": region.name,
            "type": region.type,
            "start": region.start,
            "end": region.end,
            "duration": region.duration,
            "motifs": region.motifs,
            "fills": region.fills,
            "callResponse": region.callResponse
        })
    
    return {
        "referenceId": reference_id,
        "regions": regions_dict,
        "count": len(regions_dict)
    }
