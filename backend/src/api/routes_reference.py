"""Reference track API routes."""
import os
import shutil
import uuid
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query
from fastapi.responses import JSONResponse

from models.store import REFERENCE_BUNDLES, REFERENCE_REGIONS, REFERENCE_MOTIFS, REFERENCE_CALL_RESPONSE, REFERENCE_FILLS
from models.region import Region
from stem_ingest.ingest_service import load_reference_bundle
from analysis.region_detector.region_detector import detect_regions
from analysis.motif_detector.motif_detector import detect_motifs
from analysis.call_response_detector.call_response_detector import detect_call_response, CallResponseConfig
from analysis.fill_detector.fill_detector import detect_fills, FillConfig
from config import (
    DEFAULT_MOTIF_SENSITIVITY,
    DEFAULT_CALL_RESPONSE_MIN_OFFSET_BARS,
    DEFAULT_CALL_RESPONSE_MAX_OFFSET_BARS,
    DEFAULT_CALL_RESPONSE_MIN_SIMILARITY,
    DEFAULT_CALL_RESPONSE_MIN_CONFIDENCE,
    DEFAULT_FILL_PRE_BOUNDARY_WINDOW_BARS,
    DEFAULT_FILL_TRANSIENT_DENSITY_THRESHOLD_MULTIPLIER,
    DEFAULT_FILL_MIN_TRANSIENT_DENSITY
)
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
async def analyze_reference(
    reference_id: str,
    motif_sensitivity: float = Query(DEFAULT_MOTIF_SENSITIVITY, ge=0.0, le=1.0, description="Motif clustering sensitivity (0.0 = strict, 1.0 = loose)")
):
    """
    Analyze a reference bundle to detect regions and motifs.
    
    Args:
        reference_id: ID of the reference bundle to analyze
        motif_sensitivity: Motif clustering sensitivity (0.0 = strict, 1.0 = loose)
    
    Returns:
        JSON with analysis status, region count, and motif counts
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
        
        # Detect motifs
        logger.info(f"Detecting motifs for bundle: {bundle} with sensitivity={motif_sensitivity}")
        instances, groups = detect_motifs(bundle, regions, sensitivity=motif_sensitivity)
        
        # Store motifs
        REFERENCE_MOTIFS[reference_id] = (instances, groups)
        logger.info(f"Detected {len(instances)} motif instances in {len(groups)} groups for reference {reference_id}")
        
        # Detect call-response relationships
        logger.info(f"Detecting call-response relationships for reference {reference_id}")
        call_response_config = CallResponseConfig(
            min_offset_bars=DEFAULT_CALL_RESPONSE_MIN_OFFSET_BARS,
            max_offset_bars=DEFAULT_CALL_RESPONSE_MAX_OFFSET_BARS,
            min_similarity=DEFAULT_CALL_RESPONSE_MIN_SIMILARITY,
            min_confidence=DEFAULT_CALL_RESPONSE_MIN_CONFIDENCE
        )
        call_response_pairs = detect_call_response(instances, regions, bundle.bpm, config=call_response_config)
        
        # Store call-response pairs
        REFERENCE_CALL_RESPONSE[reference_id] = call_response_pairs
        logger.info(f"Detected {len(call_response_pairs)} call-response pairs for reference {reference_id}")
        
        # Detect fills
        logger.info(f"Detecting fills for reference {reference_id}")
        fill_config = FillConfig(
            pre_boundary_window_bars=DEFAULT_FILL_PRE_BOUNDARY_WINDOW_BARS,
            transient_density_threshold_multiplier=DEFAULT_FILL_TRANSIENT_DENSITY_THRESHOLD_MULTIPLIER,
            min_transient_density=DEFAULT_FILL_MIN_TRANSIENT_DENSITY
        )
        fills = detect_fills(bundle, regions, config=fill_config)
        
        # Store fills
        REFERENCE_FILLS[reference_id] = fills
        logger.info(f"Detected {len(fills)} fills for reference {reference_id}")
        
        return {
            "referenceId": reference_id,
            "regionCount": len(regions),
            "motifInstanceCount": len(instances),
            "motifGroupCount": len(groups),
            "callResponseCount": len(call_response_pairs),
            "fillCount": len(fills),
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


@router.get("/{reference_id}/motifs")
async def get_motifs(reference_id: str):
    """
    Get detected motifs for a reference bundle.
    
    Args:
        reference_id: ID of the reference bundle
    
    Returns:
        JSON with motif instances and groups
    """
    logger.info(f"Getting motifs for reference_id: {reference_id}")
    
    # Check if reference exists
    if reference_id not in REFERENCE_BUNDLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference bundle {reference_id} not found"
        )
    
    # Check if motifs have been detected
    if reference_id not in REFERENCE_MOTIFS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Motifs not found for reference {reference_id}. Run /analyze first."
        )
    
    instances, groups = REFERENCE_MOTIFS[reference_id]
    
    # Convert MotifInstance dataclasses to dictionaries for JSON serialization
    instances_dict = []
    for inst in instances:
        instances_dict.append({
            "id": inst.id,
            "stemRole": inst.stem_role,
            "startTime": inst.start_time,
            "endTime": inst.end_time,
            "duration": inst.duration,
            "groupId": inst.group_id,
            "isVariation": inst.is_variation,
            "regionIds": inst.region_ids
        })
    
    # Convert MotifGroup dataclasses to dictionaries
    groups_dict = []
    for group in groups:
        groups_dict.append({
            "id": group.id,
            "label": group.label,
            "memberIds": [m.id for m in group.members],
            "memberCount": len(group.members),
            "variationCount": len(group.variations)
        })
    
    return {
        "referenceId": reference_id,
        "instances": instances_dict,
        "groups": groups_dict,
        "instanceCount": len(instances_dict),
        "groupCount": len(groups_dict)
    }


@router.get("/{reference_id}/call-response")
async def get_call_response(reference_id: str):
    """
    Get detected call-response pairs for a reference bundle.
    
    Args:
        reference_id: ID of the reference bundle
    
    Returns:
        JSON with call-response pairs
    """
    logger.info(f"Getting call-response pairs for reference_id: {reference_id}")
    
    # Check if reference exists
    if reference_id not in REFERENCE_BUNDLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference bundle {reference_id} not found"
        )
    
    # Check if call-response pairs have been detected
    if reference_id not in REFERENCE_CALL_RESPONSE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call-response pairs not found for reference {reference_id}. Run /analyze first."
        )
    
    pairs = REFERENCE_CALL_RESPONSE[reference_id]
    
    # Convert CallResponsePair dataclasses to dictionaries for JSON serialization
    pairs_dict = []
    for pair in pairs:
        pairs_dict.append({
            "id": pair.id,
            "fromMotifId": pair.from_motif_id,
            "toMotifId": pair.to_motif_id,
            "fromStemRole": pair.from_stem_role,
            "toStemRole": pair.to_stem_role,
            "fromTime": pair.from_time,
            "toTime": pair.to_time,
            "timeOffset": pair.time_offset,
            "confidence": pair.confidence,
            "regionId": pair.region_id,
            "isInterStem": pair.is_inter_stem,
            "isIntraStem": pair.is_intra_stem
        })
    
    return {
        "referenceId": reference_id,
        "pairs": pairs_dict,
        "count": len(pairs_dict)
    }


@router.get("/{reference_id}/fills")
async def get_fills(reference_id: str):
    """
    Get detected fills for a reference bundle.
    
    Args:
        reference_id: ID of the reference bundle
    
    Returns:
        JSON with fill objects
    """
    logger.info(f"Getting fills for reference_id: {reference_id}")
    
    # Check if reference exists
    if reference_id not in REFERENCE_BUNDLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference bundle {reference_id} not found"
        )
    
    # Check if fills have been detected
    if reference_id not in REFERENCE_FILLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fills not found for reference {reference_id}. Run /analyze first."
        )
    
    fills = REFERENCE_FILLS[reference_id]
    
    # Convert Fill dataclasses to dictionaries for JSON serialization
    fills_dict = []
    for fill in fills:
        fills_dict.append({
            "id": fill.id,
            "time": fill.time,
            "stemRoles": fill.stem_roles,
            "regionId": fill.region_id,
            "confidence": fill.confidence,
            "fillType": fill.fill_type
        })
    
    return {
        "referenceId": reference_id,
        "fills": fills_dict,
        "count": len(fills_dict)
    }
