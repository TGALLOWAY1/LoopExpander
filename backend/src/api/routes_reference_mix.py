"""API routes for single full-mix reference track ingestion and analysis."""
import os
import uuid
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query
from pydantic import BaseModel

from models.store import (
    REFERENCE_MIXES,
    REFERENCE_REGIONS,
    REFERENCE_ROLE_ACTIVITY,
    REFERENCE_ENERGY_CURVES,
)
from models.reference_mix import ReferenceMix
from stem_ingest.ingest_service import load_reference_mix
from analysis.role_activity.role_detector import detect_role_activity
from analysis.energy.energy_curve import compute_energy_curve
from analysis.region_detector.region_detector import detect_regions
from models.reference_bundle import ReferenceBundle
from stem_ingest.audio_file import AudioFile
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/reference", tags=["reference-mix"])

TEMP_DIR = Path("tmp/reference_mix")


@router.post("/upload-mix")
async def upload_reference_mix(
    file: UploadFile = File(...),
    bpm_override: Optional[float] = Query(None, description="Optional BPM override"),
):
    """Upload a single full-mix reference track.

    Accepts one stereo WAV/AIFF/MP3 file, validates format and duration,
    detects BPM and computes beat grid.

    Returns:
        JSON with referenceId, bpm, duration, beatGrid.
    """
    reference_id = str(uuid.uuid4())
    logger.info(f"Starting single-mix upload for reference_id: {reference_id}")

    # Validate filename/extension
    original_filename = file.filename or "mix.wav"
    file_ext = Path(original_filename).suffix.lower()
    if file_ext not in [".wav", ".aiff", ".aif", ".mp3"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {file_ext}. Accepted: WAV, AIFF, MP3.",
        )

    # Save uploaded file to temp dir
    ref_dir = TEMP_DIR / reference_id
    ref_dir.mkdir(parents=True, exist_ok=True)
    file_path = ref_dir / f"mix{file_ext}"

    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"Saved uploaded mix to {file_path}")

        # Load and analyze
        mix = load_reference_mix(file_path, user_bpm_override=bpm_override)
        REFERENCE_MIXES[reference_id] = mix

        logger.info(f"Stored reference mix {reference_id}: {mix}")

        return {
            "referenceId": reference_id,
            "bpm": mix.bpm,
            "detectedBpm": mix.detected_bpm,
            "duration": mix.duration,
            "totalBars": mix.total_bars,
            "beatGrid": mix.beat_grid,
            "key": mix.key,
        }

    except ValueError as e:
        logger.error(f"Validation error for {reference_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error processing upload {reference_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process upload: {str(e)}",
        )


@router.post("/{reference_id}/analyze-mix")
async def analyze_reference_mix(reference_id: str):
    """Run full analysis pipeline on a single-mix reference.

    Performs: region detection, role activity detection, energy curve computation,
    and section labeling.

    Returns:
        JSON with analysis summary.
    """
    mix = REFERENCE_MIXES.get(reference_id)
    if not mix:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference mix {reference_id} not found",
        )

    logger.info(f"Starting analysis for reference mix {reference_id}")

    try:
        # Create a minimal ReferenceBundle for region detection compatibility
        # The region detector expects a bundle with a full_mix attribute
        audio = mix.audio
        dummy_bundle = _create_dummy_bundle(audio, mix.bpm)

        # 1. Region detection
        logger.info("Running region detection...")
        regions = detect_regions(dummy_bundle)
        REFERENCE_REGIONS[reference_id] = regions
        logger.info(f"Detected {len(regions)} regions")

        # 2. Role activity detection
        logger.info("Running role activity detection...")
        role_timelines = detect_role_activity(
            audio=audio.samples,
            sr=audio.sr,
            bpm=mix.bpm,
            duration=mix.duration,
        )
        REFERENCE_ROLE_ACTIVITY[reference_id] = role_timelines
        logger.info(f"Detected activity for {len(role_timelines)} roles")

        # 3. Energy curve
        logger.info("Computing energy curve...")
        energy_result = compute_energy_curve(
            audio=audio.samples,
            sr=audio.sr,
            bpm=mix.bpm,
            duration=mix.duration,
            regions=regions,
        )
        REFERENCE_ENERGY_CURVES[reference_id] = energy_result.to_dict()
        logger.info(
            f"Energy curve: {len(energy_result.bar_energies)} bars, "
            f"{len(energy_result.transition_markers)} transitions"
        )

        return {
            "referenceId": reference_id,
            "regionCount": len(regions),
            "roles": [t.role for t in role_timelines],
            "totalBars": int(len(energy_result.bar_energies)),
            "transitionCount": len(energy_result.transition_markers),
            "status": "complete",
        }

    except Exception as e:
        logger.error(f"Analysis error for {reference_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )


@router.get("/{reference_id}/role-activity")
async def get_role_activity(reference_id: str):
    """Get role activity timelines for a reference mix.

    Returns:
        JSON with per-role activity timelines.
    """
    if reference_id not in REFERENCE_MIXES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference mix {reference_id} not found",
        )

    timelines = REFERENCE_ROLE_ACTIVITY.get(reference_id, [])
    if not timelines:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role activity not yet computed for {reference_id}. Run analyze-mix first.",
        )

    return {
        "referenceId": reference_id,
        "timelines": [t.to_dict() for t in timelines],
    }


@router.get("/{reference_id}/energy")
async def get_energy_curve(reference_id: str):
    """Get energy curve and transition markers for a reference mix.

    Returns:
        JSON with bar energies, section densities, and transition markers.
    """
    if reference_id not in REFERENCE_MIXES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference mix {reference_id} not found",
        )

    energy_data = REFERENCE_ENERGY_CURVES.get(reference_id)
    if not energy_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Energy curve not yet computed for {reference_id}. Run analyze-mix first.",
        )

    return {
        "referenceId": reference_id,
        **energy_data,
    }


@router.get("/{reference_id}/mix-regions")
async def get_mix_regions(reference_id: str):
    """Get detected regions for a reference mix.

    Returns:
        JSON with regions including labels and types.
    """
    if reference_id not in REFERENCE_MIXES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference mix {reference_id} not found",
        )

    regions = REFERENCE_REGIONS.get(reference_id, [])
    mix = REFERENCE_MIXES[reference_id]

    seconds_per_bar = (60.0 / mix.bpm) * 4.0

    return {
        "referenceId": reference_id,
        "regions": [
            {
                "id": r.id,
                "name": r.name,
                "type": r.type,
                "start": r.start,
                "end": r.end,
                "duration": r.duration,
                "startBar": r.start / seconds_per_bar,
                "endBar": r.end / seconds_per_bar,
                "label": r.name,
                "provisionalLabel": r.name,
            }
            for r in regions
        ],
        "count": len(regions),
    }


##############################################################################
# Structure Canvas: Section editing endpoints (Phase 2B)
##############################################################################


class RegionPatch(BaseModel):
    id: str
    name: Optional[str] = None
    label: Optional[str] = None
    type: Optional[str] = None
    startBar: Optional[float] = None
    endBar: Optional[float] = None


class PatchRegionsRequest(BaseModel):
    patches: List[RegionPatch]


class SplitRegionRequest(BaseModel):
    regionId: str
    splitBar: float


class MergeRegionRequest(BaseModel):
    regionId1: str
    regionId2: str


class RoleActivityOverride(BaseModel):
    role: str
    startBar: float
    endBar: float
    active: bool


class PatchRoleActivityRequest(BaseModel):
    overrides: List[RoleActivityOverride]


def _regions_to_response(reference_id: str, regions, mix):
    """Helper to serialize regions list to response dict."""
    seconds_per_bar = (60.0 / mix.bpm) * 4.0
    return {
        "referenceId": reference_id,
        "regions": [
            {
                "id": r.id,
                "name": r.name,
                "type": r.type,
                "start": r.start,
                "end": r.end,
                "duration": r.duration,
                "startBar": r.start / seconds_per_bar,
                "endBar": r.end / seconds_per_bar,
                "label": r.label or r.name,
                "provisionalLabel": r.provisional_label or r.name,
            }
            for r in regions
        ],
        "count": len(regions),
    }


@router.patch("/{reference_id}/regions")
async def patch_regions(reference_id: str, request: PatchRegionsRequest):
    """Update region boundaries, labels, and types.

    Accepts a list of partial updates keyed by region id.
    """
    mix = REFERENCE_MIXES.get(reference_id)
    if not mix:
        raise HTTPException(status_code=404, detail=f"Reference mix {reference_id} not found")

    regions = REFERENCE_REGIONS.get(reference_id, [])
    if not regions:
        raise HTTPException(status_code=404, detail="No regions found. Run analyze-mix first.")

    seconds_per_bar = (60.0 / mix.bpm) * 4.0
    region_map = {r.id: r for r in regions}

    for patch in request.patches:
        region = region_map.get(patch.id)
        if not region:
            continue
        if patch.name is not None:
            region.name = patch.name
        if patch.label is not None:
            region.label = patch.label
        if patch.type is not None:
            region.type = patch.type
        if patch.startBar is not None:
            region.start = patch.startBar * seconds_per_bar
        if patch.endBar is not None:
            region.end = patch.endBar * seconds_per_bar

    REFERENCE_REGIONS[reference_id] = list(region_map.values())
    return _regions_to_response(reference_id, REFERENCE_REGIONS[reference_id], mix)


@router.post("/{reference_id}/regions/split")
async def split_region_endpoint(reference_id: str, request: SplitRegionRequest):
    """Split a region at a given bar position into two regions."""
    mix = REFERENCE_MIXES.get(reference_id)
    if not mix:
        raise HTTPException(status_code=404, detail=f"Reference mix {reference_id} not found")

    regions = REFERENCE_REGIONS.get(reference_id, [])
    if not regions:
        raise HTTPException(status_code=404, detail="No regions found.")

    seconds_per_bar = (60.0 / mix.bpm) * 4.0
    split_time = request.splitBar * seconds_per_bar

    target = None
    target_idx = -1
    for i, r in enumerate(regions):
        if r.id == request.regionId:
            target = r
            target_idx = i
            break

    if target is None:
        raise HTTPException(status_code=404, detail=f"Region {request.regionId} not found")

    if split_time <= target.start or split_time >= target.end:
        raise HTTPException(status_code=400, detail="Split point must be within the region boundaries")

    from models.region import Region

    first = Region(
        id=str(uuid.uuid4()),
        name=f"{target.name} (A)",
        type=target.type,
        start=target.start,
        end=split_time,
        motifs=[],
        fills=[],
        callResponse=[],
        label=f"{target.label or target.name} (A)",
        provisional_label=target.provisional_label,
    )
    second = Region(
        id=str(uuid.uuid4()),
        name=f"{target.name} (B)",
        type=target.type,
        start=split_time,
        end=target.end,
        motifs=[],
        fills=[],
        callResponse=[],
        label=f"{target.label or target.name} (B)",
        provisional_label=target.provisional_label,
    )

    regions = regions[:target_idx] + [first, second] + regions[target_idx + 1:]
    REFERENCE_REGIONS[reference_id] = regions
    return _regions_to_response(reference_id, regions, mix)


@router.post("/{reference_id}/regions/merge")
async def merge_regions_endpoint(reference_id: str, request: MergeRegionRequest):
    """Merge two adjacent regions into one."""
    mix = REFERENCE_MIXES.get(reference_id)
    if not mix:
        raise HTTPException(status_code=404, detail=f"Reference mix {reference_id} not found")

    regions = REFERENCE_REGIONS.get(reference_id, [])
    if not regions:
        raise HTTPException(status_code=404, detail="No regions found.")

    idx1 = None
    idx2 = None
    for i, r in enumerate(regions):
        if r.id == request.regionId1:
            idx1 = i
        if r.id == request.regionId2:
            idx2 = i

    if idx1 is None or idx2 is None:
        raise HTTPException(status_code=404, detail="One or both regions not found")

    # Ensure they are adjacent
    if abs(idx1 - idx2) != 1:
        raise HTTPException(status_code=400, detail="Regions must be adjacent to merge")

    first_idx = min(idx1, idx2)
    second_idx = max(idx1, idx2)
    r1 = regions[first_idx]
    r2 = regions[second_idx]

    from models.region import Region

    merged = Region(
        id=r1.id,
        name=r1.name,
        type=r1.type,
        start=r1.start,
        end=r2.end,
        motifs=r1.motifs + r2.motifs,
        fills=r1.fills + r2.fills,
        callResponse=r1.callResponse + r2.callResponse,
        label=r1.label or r1.name,
        provisional_label=r1.provisional_label,
    )

    regions = regions[:first_idx] + [merged] + regions[second_idx + 1:]
    REFERENCE_REGIONS[reference_id] = regions
    return _regions_to_response(reference_id, regions, mix)


##############################################################################
# Structure Canvas: Role activity override (Phase 2D)
##############################################################################


@router.patch("/{reference_id}/role-activity")
async def patch_role_activity(reference_id: str, request: PatchRoleActivityRequest):
    """Apply user overrides to role activity segments."""
    if reference_id not in REFERENCE_MIXES:
        raise HTTPException(status_code=404, detail=f"Reference mix {reference_id} not found")

    timelines = REFERENCE_ROLE_ACTIVITY.get(reference_id, [])
    if not timelines:
        raise HTTPException(status_code=404, detail="Role activity not yet computed.")

    from models.role_activity import ActivitySegment

    timeline_map = {t.role: t for t in timelines}

    for override in request.overrides:
        timeline = timeline_map.get(override.role)
        if not timeline:
            continue
        for seg in timeline.segments:
            if seg.start_bar == override.startBar and seg.end_bar == override.endBar:
                seg.active = override.active
                break

    REFERENCE_ROLE_ACTIVITY[reference_id] = list(timeline_map.values())
    return {
        "referenceId": reference_id,
        "timelines": [t.to_dict() for t in REFERENCE_ROLE_ACTIVITY[reference_id]],
    }


def _create_dummy_bundle(audio: AudioFile, bpm: float) -> ReferenceBundle:
    """Create a minimal ReferenceBundle from a single AudioFile for region detection.

    The region detector expects a bundle with a full_mix attribute. This wraps
    the single audio file to satisfy that interface.
    """
    return ReferenceBundle(
        drums=audio,
        bass=audio,
        vocals=audio,
        instruments=audio,
        full_mix=audio,
        bpm=bpm,
    )
