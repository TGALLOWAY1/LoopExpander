"""Reference track API routes."""
import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from models.store import (
    REFERENCE_BUNDLES, REFERENCE_REGIONS, REFERENCE_MOTIFS, 
    REFERENCE_CALL_RESPONSE, REFERENCE_FILLS, REFERENCE_MOTIF_INSTANCES_RAW,
    REFERENCE_SUBREGIONS, REFERENCE_ANNOTATIONS
)
from models.region import Region
from stem_ingest.ingest_service import load_reference_bundle
from analysis.region_detector.region_detector import detect_regions
from analysis.motif_detector.motif_detector import (
    detect_motifs, MotifInstance, _cluster_motifs, _align_motifs_with_regions
)
from analysis.motif_detector.config import (
    MotifSensitivityConfig,
    DEFAULT_MOTIF_SENSITIVITY,
    normalize_sensitivity_config,
    clamp_sensitivity
)
from analysis.call_response_detector.call_response_detector import detect_call_response, CallResponseConfig
from analysis.call_response_detector.lanes_service import build_call_response_lanes
from analysis.call_response_detector.lanes_models import CallResponseByStemResponse
from analysis.fill_detector.fill_detector import detect_fills, FillConfig
from analysis.subregions.service import compute_region_subregions, DensityCurves
from analysis.subregions.models import RegionSubRegionsDTO
from models.annotations import ReferenceAnnotations, RegionAnnotations
from config import DEFAULT_SUBREGION_BARS_PER_CHUNK, DEFAULT_SUBREGION_SILENCE_INTENSITY_THRESHOLD
from config import (
    DEFAULT_MOTIF_SENSITIVITY,
    DEFAULT_CALL_RESPONSE_MIN_OFFSET_BARS,
    DEFAULT_CALL_RESPONSE_MAX_OFFSET_BARS,
    DEFAULT_CALL_RESPONSE_MIN_SIMILARITY,
    DEFAULT_CALL_RESPONSE_MIN_CONFIDENCE,
    DEFAULT_FILL_PRE_BOUNDARY_WINDOW_BARS,
    DEFAULT_FILL_TRANSIENT_DENSITY_THRESHOLD_MULTIPLIER,
    DEFAULT_FILL_MIN_TRANSIENT_DENSITY,
    USE_FULL_MIX_FOR_LANE_VIEW,
    VISUAL_COMPOSER_ENABLED
)
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/reference", tags=["reference"])

# Temporary directory for uploaded files
TEMP_DIR = Path("tmp/reference")


def _get_project_root() -> Path:
    """Get the project root directory (3 levels up from this file: api -> src -> backend -> root)."""
    return Path(__file__).resolve().parents[3]


def _get_gallium_test_paths() -> Dict[str, Path]:
    """Get file paths for Gallium test stems."""
    root = _get_project_root() / "2. Test Data" / "Song-1-Gallium-MakeEmWatch-130BPM"
    return {
        "drums": root / "DRUMS.wav",
        "bass": root / "BASS.wav",
        "vocals": root / "VOCALS.wav",
        "instruments": root / "INSTRUMENTS.wav",
        "full_mix": root / "FULL.wav",
    }


@router.get("/ping")
async def ping():
    """Health check endpoint for reference API."""
    return {"message": "reference api ok"}


@router.post("/dev/gallium")
async def create_gallium_dev_reference():
    """
    Dev-only endpoint to load Gallium test stems from disk.
    
    This endpoint loads the test audio files from the test data directory
    and processes them through the same upload/analysis pipeline as the
    normal upload endpoint.
    
    Returns:
        JSON with referenceId, bpm, duration, and key (same format as /upload)
    """
    logger.info("Loading Gallium test stems from disk")
    
    # Get test file paths
    paths = _get_gallium_test_paths()
    
    # Validate all files exist
    for role, path in paths.items():
        if not path.exists():
            logger.error(f"Missing Gallium test file for {role}: {path}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Missing Gallium test file for {role}: {path}"
            )
    
    # Generate reference ID
    reference_id = str(uuid.uuid4())
    logger.info(f"Creating dev reference with ID: {reference_id}")
    
    try:
        # Load reference bundle directly from file paths
        logger.info(f"Loading reference bundle from test files")
        bundle = load_reference_bundle(paths)
        
        # Store in memory (same as normal upload)
        REFERENCE_BUNDLES[reference_id] = bundle
        logger.info(f"Stored reference bundle {reference_id}: {bundle}")
        
        return {
            "referenceId": reference_id,
            "bpm": bundle.bpm,
            "duration": bundle.full_mix.duration,
            "key": bundle.key
        }
    
    except Exception as e:
        logger.error(f"Error loading Gallium test reference {reference_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load Gallium test reference: {str(e)}"
        )


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
        
        # Detect motifs using stored sensitivity config
        # The query parameter is kept for backward compatibility but we prefer stored config
        # If query param differs from default, it overrides stored config
        # NOTE: For the Region Map stem lanes, we use stem-only motif analysis (no full-mix motifs).
        # Each motif instance is explicitly tagged with its stem_role for per-stem lane visualization.
        if motif_sensitivity != DEFAULT_MOTIF_SENSITIVITY:
            # Query parameter provided and differs from default, use it for all stems
            logger.info(f"Detecting motifs for bundle: {bundle} with sensitivity={motif_sensitivity} (from query param, overriding stored config)")
            instances, groups = detect_motifs(bundle, regions, sensitivity=motif_sensitivity, exclude_full_mix=True)
        else:
            # Use stored per-stem sensitivity config
            logger.info(f"Detecting motifs for bundle: {bundle} with sensitivity_config={bundle.motif_sensitivity_config}")
            instances, groups = detect_motifs(bundle, regions, sensitivity_config=bundle.motif_sensitivity_config, exclude_full_mix=True)
        
        # Store raw instances (before clustering) for re-clustering with different sensitivity
        # Create deep copies to avoid modifying the clustered instances
        raw_instances = []
        for inst in instances:
            raw_inst = MotifInstance(
                id=inst.id,
                stem_role=inst.stem_role,
                start_time=inst.start_time,
                end_time=inst.end_time,
                features=inst.features.copy(),  # Copy numpy array
                group_id=None,  # Reset clustering
                is_variation=False,  # Reset variation flag
                region_ids=inst.region_ids.copy()  # Keep region alignment
            )
            raw_instances.append(raw_inst)
        REFERENCE_MOTIF_INSTANCES_RAW[reference_id] = raw_instances
        
        # Store motifs
        REFERENCE_MOTIFS[reference_id] = (instances, groups)
        logger.info(f"Detected {len(instances)} motif instances in {len(groups)} groups for reference {reference_id}")
        
        # Detect call-response relationships
        # The Region Map's 5-layer view is stem-centric; we intentionally ignore full-mix motifs here.
        logger.info(f"Detecting call-response relationships for reference {reference_id}")
        call_response_config = CallResponseConfig(
            min_offset_bars=DEFAULT_CALL_RESPONSE_MIN_OFFSET_BARS,
            max_offset_bars=DEFAULT_CALL_RESPONSE_MAX_OFFSET_BARS,
            min_similarity=DEFAULT_CALL_RESPONSE_MIN_SIMILARITY,
            min_confidence=DEFAULT_CALL_RESPONSE_MIN_CONFIDENCE,
            use_full_mix=False  # Stem-only mode for 5-layer Region Map view
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
async def get_motifs(
    reference_id: str,
    sensitivity: Optional[float] = Query(None, ge=0.0, le=1.0, description="Optional: Re-cluster motifs with different sensitivity (0.0 = strict, 1.0 = loose)")
):
    """
    Get detected motifs for a reference bundle.
    
    Args:
        reference_id: ID of the reference bundle
        sensitivity: Optional sensitivity parameter to re-cluster motifs with different threshold
    
    Returns:
        JSON with motif instances and groups
    """
    logger.info(f"Getting motifs for reference_id: {reference_id}, sensitivity={sensitivity}")
    
    # Check if reference exists
    if reference_id not in REFERENCE_BUNDLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference bundle {reference_id} not found"
        )
    
    # Check if motifs have been detected
    if reference_id not in REFERENCE_MOTIF_INSTANCES_RAW:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Motifs not found for reference {reference_id}. Run /analyze first."
        )
    
    # Get regions for re-alignment
    if reference_id not in REFERENCE_REGIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regions not found for reference {reference_id}. Run /analyze first."
        )
    
    regions = REFERENCE_REGIONS[reference_id]
    raw_instances = REFERENCE_MOTIF_INSTANCES_RAW[reference_id]
    
    # If sensitivity is provided and different from stored, re-cluster
    if sensitivity is not None:
        logger.info(f"Re-clustering motifs with sensitivity={sensitivity}")
        # Create fresh copies of instances for re-clustering
        instances_to_cluster = []
        for raw_inst in raw_instances:
            fresh_inst = MotifInstance(
                id=raw_inst.id,
                stem_role=raw_inst.stem_role,
                start_time=raw_inst.start_time,
                end_time=raw_inst.end_time,
                features=raw_inst.features.copy(),
                group_id=None,
                is_variation=False,
                region_ids=[]
            )
            instances_to_cluster.append(fresh_inst)
        
        # Re-cluster with new sensitivity
        instances, groups = _cluster_motifs(instances_to_cluster, sensitivity)
        
        # Re-align with regions
        _align_motifs_with_regions(instances, regions)
    else:
        # Use stored clustering
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


class MotifSensitivityUpdate(BaseModel):
    """Update model for motif sensitivity configuration."""
    drums: Optional[float] = Field(None, ge=0.0, le=1.0, description="Drums sensitivity (0.0 = strict, 1.0 = loose)")
    bass: Optional[float] = Field(None, ge=0.0, le=1.0, description="Bass sensitivity (0.0 = strict, 1.0 = loose)")
    vocals: Optional[float] = Field(None, ge=0.0, le=1.0, description="Vocals sensitivity (0.0 = strict, 1.0 = loose)")
    instruments: Optional[float] = Field(None, ge=0.0, le=1.0, description="Instruments sensitivity (0.0 = strict, 1.0 = loose)")


@router.get("/{reference_id}/motif-sensitivity")
async def get_motif_sensitivity(reference_id: str):
    """
    Get motif sensitivity configuration for a reference bundle.
    
    Args:
        reference_id: ID of the reference bundle
    
    Returns:
        JSON with motif sensitivity configuration
    """
    logger.info(f"Getting motif sensitivity for reference_id: {reference_id}")
    
    # Check if reference exists
    if reference_id not in REFERENCE_BUNDLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference bundle {reference_id} not found"
        )
    
    bundle = REFERENCE_BUNDLES[reference_id]
    
    return {
        "referenceId": reference_id,
        "motifSensitivityConfig": bundle.motif_sensitivity_config
    }


@router.patch("/{reference_id}/motif-sensitivity")
async def update_motif_sensitivity(
    reference_id: str,
    update: MotifSensitivityUpdate = Body(...)
):
    """
    Update motif sensitivity configuration for a reference bundle.
    
    Args:
        reference_id: ID of the reference bundle
        update: Partial update with sensitivity values (only provided keys are updated)
    
    Returns:
        JSON with updated motif sensitivity configuration
    """
    logger.info(f"Updating motif sensitivity for reference_id: {reference_id}, update={update}")
    
    # Check if reference exists
    if reference_id not in REFERENCE_BUNDLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference bundle {reference_id} not found"
        )
    
    bundle = REFERENCE_BUNDLES[reference_id]
    
    # Validate and merge provided values
    update_dict = update.model_dump(exclude_unset=True)
    
    # Clamp values to safe range [0.05, 0.95] even if they're in valid [0.0, 1.0] range
    # This prevents extreme values that could lead to no motifs being detected
    clamped_dict = {}
    for key, value in update_dict.items():
        if value is not None:
            # Validate value is in range [0.0, 1.0] (Pydantic Field already does this, but double-check)
            if value < 0.0 or value > 1.0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid sensitivity value for {key}: {value}. Must be between 0.0 and 1.0"
                )
            # Clamp to safe range [0.05, 0.95]
            clamped_value = clamp_sensitivity(value)
            if clamped_value != value:
                logger.info(
                    f"[MotifSensitivity] Clamped {key} sensitivity from {value} to {clamped_value} "
                    "(extreme values can prevent motif detection)"
                )
            clamped_dict[key] = clamped_value
    
    # Merge provided keys into existing config
    bundle.motif_sensitivity_config.update(clamped_dict)
    
    # Normalize the entire config to ensure all values are in safe range
    bundle.motif_sensitivity_config = normalize_sensitivity_config(bundle.motif_sensitivity_config)
    
    logger.info(f"Updated motif sensitivity config for {reference_id}: {bundle.motif_sensitivity_config}")
    
    return {
        "referenceId": reference_id,
        "motifSensitivityConfig": bundle.motif_sensitivity_config
    }


@router.post("/{reference_id}/reanalyze-motifs")
async def reanalyze_motifs(reference_id: str):
    """
    Re-run motif detection for a reference bundle using stored sensitivity configuration.
    
    This endpoint re-detects motifs using the current motif_sensitivity_config stored
    on the reference bundle. Regions must already be detected (via /analyze).
    
    Args:
        reference_id: ID of the reference bundle
    
    Returns:
        JSON with analysis status and motif counts
    """
    logger.info(f"Re-analyzing motifs for reference_id: {reference_id}")
    
    # Check if reference exists
    if reference_id not in REFERENCE_BUNDLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference bundle {reference_id} not found"
        )
    
    bundle = REFERENCE_BUNDLES[reference_id]
    
    # Check if regions have been detected
    if reference_id not in REFERENCE_REGIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regions not found for reference {reference_id}. Run /analyze first."
        )
    
    regions = REFERENCE_REGIONS[reference_id]
    
    try:
        # Detect motifs using stored sensitivity config
        logger.info(f"Re-detecting motifs for bundle: {bundle} with sensitivity_config={bundle.motif_sensitivity_config}")
        # NOTE: For the Region Map stem lanes, we use stem-only motif analysis (no full-mix motifs).
        instances, groups = detect_motifs(bundle, regions, sensitivity_config=bundle.motif_sensitivity_config, exclude_full_mix=True)
        
        # Store raw instances (before clustering) for re-clustering with different sensitivity
        raw_instances = []
        for inst in instances:
            raw_inst = MotifInstance(
                id=inst.id,
                stem_role=inst.stem_role,
                start_time=inst.start_time,
                end_time=inst.end_time,
                features=inst.features.copy(),  # Copy numpy array
                group_id=None,  # Reset clustering
                is_variation=False,  # Reset variation flag
                region_ids=inst.region_ids.copy()  # Keep region alignment
            )
            raw_instances.append(raw_inst)
        REFERENCE_MOTIF_INSTANCES_RAW[reference_id] = raw_instances
        
        # Store motifs
        REFERENCE_MOTIFS[reference_id] = (instances, groups)
        logger.info(f"Re-detected {len(instances)} motif instances in {len(groups)} groups for reference {reference_id}")
        
        return {
            "referenceId": reference_id,
            "motifInstanceCount": len(instances),
            "motifGroupCount": len(groups),
            "status": "ok"
        }
    
    except Exception as e:
        logger.error(f"Error re-analyzing motifs for reference {reference_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-analyze motifs: {str(e)}"
        )


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


@router.get("/{reference_id}/call-response-by-stem", response_model=CallResponseByStemResponse)
async def get_call_response_by_stem(reference_id: str):
    """
    Get call-response patterns organized by stem lanes.
    
    This endpoint returns call/response events organized per stem category,
    excluding full-mix motifs. Events are converted to bar-based coordinates
    for timeline visualization.
    
    Args:
        reference_id: ID of the reference bundle
    
    Returns:
        CallResponseByStemResponse with lanes organized by stem
    """
    logger.info(f"Getting call-response by stem for reference_id: {reference_id}")
    
    # Check if reference exists
    if reference_id not in REFERENCE_BUNDLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference bundle {reference_id} not found"
        )
    
    bundle = REFERENCE_BUNDLES[reference_id]
    
    # Check if regions have been detected
    if reference_id not in REFERENCE_REGIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regions not found for reference {reference_id}. Run /analyze first."
        )
    
    regions = REFERENCE_REGIONS[reference_id]
    
    # Check if call-response pairs have been detected
    if reference_id not in REFERENCE_CALL_RESPONSE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call-response pairs not found for reference {reference_id}. Run /analyze first."
        )
    
    call_response_pairs = REFERENCE_CALL_RESPONSE[reference_id]
    
    # NOTE: The Region Map stem lanes are intended to be per-stem only; full-mix motifs are ignored here by design.
    # Filter out any pairs involving full_mix unless explicitly enabled
    if not USE_FULL_MIX_FOR_LANE_VIEW:
        stem_only_pairs = [
            pair for pair in call_response_pairs
            if pair.from_stem_role != "full_mix" and pair.to_stem_role != "full_mix"
        ]
        filtered_count = len(call_response_pairs) - len(stem_only_pairs)
        if filtered_count > 0:
            logger.info(
                f"[CallResponseLanes] Filtered out {filtered_count} full-mix pairs (USE_FULL_MIX_FOR_LANE_VIEW=False)"
            )
        call_response_pairs = stem_only_pairs
    else:
        logger.warning(
            "[CallResponseLanes] USE_FULL_MIX_FOR_LANE_VIEW=True - full-mix motifs will be included (not recommended for stem lanes)"
        )
    
    # Get motif instances if available (for getting end times)
    # Filter to only per-stem motifs (exclude full_mix)
    motif_instances = None
    if reference_id in REFERENCE_MOTIF_INSTANCES_RAW:
        raw_instances = REFERENCE_MOTIF_INSTANCES_RAW[reference_id]
        if not USE_FULL_MIX_FOR_LANE_VIEW:
            # Filter out full_mix motif instances
            stem_only_instances = [
                inst for inst in raw_instances
                if inst.stem_role != "full_mix"
            ]
            filtered_motif_count = len(raw_instances) - len(stem_only_instances)
            if filtered_motif_count > 0:
                logger.info(
                    f"[CallResponseLanes] Filtered out {filtered_motif_count} full-mix motif instances (USE_FULL_MIX_FOR_LANE_VIEW=False)"
                )
            motif_instances = stem_only_instances
        else:
            motif_instances = raw_instances
    
    # Log summary of per-stem motifs being used
    per_stem_motif_count = len(motif_instances) if motif_instances else 0
    logger.info(
        f"[CallResponseLanes] Using {per_stem_motif_count} per-stem motifs; full-mix motifs disabled (USE_FULL_MIX_FOR_LANE_VIEW=False)"
    )
    
    # Build lanes
    try:
        lanes_response = build_call_response_lanes(
            reference_id=reference_id,
            regions=regions,
            call_response_pairs=call_response_pairs,
            bpm=bundle.bpm,
            motif_instances=motif_instances
        )
        
        return lanes_response
    except Exception as e:
        logger.error(f"Error building call-response lanes for reference {reference_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build call-response lanes: {str(e)}"
        )


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


@router.get("/{reference_id}/subregions")
async def get_subregions(reference_id: str):
    """
    Get computed subregion patterns for a reference bundle.
    
    This endpoint provides DNA-style segmentation of regions into subregions
    per stem category, capturing patterns, variations, silence, and intensity.
    
    Args:
        reference_id: ID of the reference bundle
    
    Returns:
        JSON with subregion data organized by region and stem category (lanes)
    
    Example response:
        {
            "reference_id": "abc123",
            "regions": [
                {
                    "regionId": "region_01",
                    "lanes": {
                        "drums": [
                            {
                                "id": "subregion_region_01_drums_1",
                                "regionId": "region_01",
                                "stemCategory": "drums",
                                "startBar": 0.0,
                                "endBar": 8.0,
                                "label": null,
                                "motifGroupId": null,
                                "isVariation": false,
                                "isSilence": false,
                                "intensity": 0.5
                            }
                        ],
                        "bass": [...],
                        "vocals": [...],
                        "instruments": [...]
                    }
                }
            ]
        }
    """
    logger.info(f"Getting subregions for reference_id: {reference_id}")
    
    # Check if reference exists
    if reference_id not in REFERENCE_BUNDLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference bundle {reference_id} not found"
        )
    
    bundle = REFERENCE_BUNDLES[reference_id]
    
    # Check if regions have been detected
    if reference_id not in REFERENCE_REGIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regions not found for reference {reference_id}. Run /analyze first."
        )
    
    regions = REFERENCE_REGIONS[reference_id]
    
    # Check if motifs have been detected (needed for subregion computation)
    if reference_id not in REFERENCE_MOTIFS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Motifs not found for reference {reference_id}. Run /analyze first."
        )
    
    # Get motifs
    motif_instances, motif_groups = REFERENCE_MOTIFS[reference_id]
    
    # Check if subregions are already computed and cached
    if reference_id in REFERENCE_SUBREGIONS:
        logger.info(f"Returning cached subregions for reference {reference_id}")
        subregions = REFERENCE_SUBREGIONS[reference_id]
    else:
        # Compute subregions using real analysis data
        logger.info(f"Computing subregions for reference {reference_id}")
        
        # Create density curves from bundle (computes RMS envelopes per stem)
        density_curves = DensityCurves(bundle)
        
        # Compute subregions
        subregions = compute_region_subregions(
            regions=regions,
            motifs=motif_instances,
            motif_groups=motif_groups,
            density_curves=density_curves,
            bpm=bundle.bpm,
            bars_per_chunk=DEFAULT_SUBREGION_BARS_PER_CHUNK,
            silence_threshold=DEFAULT_SUBREGION_SILENCE_INTENSITY_THRESHOLD
        )
        
        # Cache the result
        REFERENCE_SUBREGIONS[reference_id] = subregions
        logger.info(f"Cached subregions for reference {reference_id}")
    
    # Convert to DTOs for JSON serialization
    regions_dto = []
    for region_subregions in subregions:
        region_dto = RegionSubRegionsDTO.model_validate(region_subregions)
        regions_dto.append(region_dto)
    
    return {
        "referenceId": reference_id,
        "regions": [r.model_dump(by_alias=True) for r in regions_dto]
    }


@router.get("/{reference_id}/annotations")
async def get_annotations(reference_id: str):
    """
    Get Visual Composer annotations for a reference bundle.
    
    Args:
        reference_id: ID of the reference bundle
    
    Returns:
        JSON with annotations data, or empty structure if none exist
    
    Raises:
        404 if Visual Composer feature is disabled
        404 if reference bundle not found
    """
    # Check feature flag
    if not VISUAL_COMPOSER_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visual Composer annotations feature is disabled"
        )
    
    logger.info(f"Getting annotations for reference_id: {reference_id}")
    
    # Check if reference exists
    if reference_id not in REFERENCE_BUNDLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference bundle {reference_id} not found"
        )
    
    # Return existing annotations or empty structure
    if reference_id in REFERENCE_ANNOTATIONS:
        annotations = REFERENCE_ANNOTATIONS[reference_id]
        return annotations.model_dump()
    else:
        # Return empty structure
        return {
            "referenceId": reference_id,
            "regions": []
        }


@router.post("/{reference_id}/annotations")
async def create_or_update_annotations(
    reference_id: str,
    annotations: ReferenceAnnotations = Body(...)
):
    """
    Create or update Visual Composer annotations for a reference bundle.
    
    Args:
        reference_id: ID of the reference bundle (must match payload)
        annotations: Annotations data to store
    
    Returns:
        JSON with stored annotations data
    
    Raises:
        404 if Visual Composer feature is disabled
        404 if reference bundle not found
        400 if reference_id in payload doesn't match path parameter
    """
    # Check feature flag
    if not VISUAL_COMPOSER_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visual Composer annotations feature is disabled"
        )
    
    logger.info(f"Creating/updating annotations for reference_id: {reference_id}")
    
    # Check if reference exists
    if reference_id not in REFERENCE_BUNDLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference bundle {reference_id} not found"
        )
    
    # Force reference_id in payload to match path parameter
    if annotations.reference_id != reference_id:
        logger.warning(
            f"Reference ID mismatch: path={reference_id}, payload={annotations.reference_id}. "
            f"Overriding payload reference_id to match path."
        )
        annotations.reference_id = reference_id
    
    # Store annotations in memory
    REFERENCE_ANNOTATIONS[reference_id] = annotations
    logger.info(f"Stored annotations for reference {reference_id}: {len(annotations.regions)} regions")
    
    return annotations.model_dump()
