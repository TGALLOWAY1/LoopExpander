"""API routes for user loop/stem upload and management."""
import uuid
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query, Form
from pydantic import BaseModel

from models.store import USER_LOOPS, REFERENCE_MIXES
from models.user_loop import UserLoopStem, UserLoopBundle, VALID_ROLES
from stem_ingest.ingest_service import estimate_bpm
from stem_ingest.audio_file import load_audio_file
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/project", tags=["user-loops"])

TEMP_DIR = Path("tmp/user_loops")


def _detect_loop_length_bars(duration_seconds: float, bpm: float) -> int:
    """Detect the likely loop length in bars from audio duration and BPM.

    Rounds to the nearest power-of-2 bar count (1, 2, 4, 8, 16, 32, 64).
    """
    if bpm <= 0:
        return 8  # fallback
    seconds_per_bar = (60.0 / bpm) * 4.0
    raw_bars = duration_seconds / seconds_per_bar
    # Snap to nearest standard bar length
    standard_lengths = [1, 2, 4, 8, 16, 32, 64]
    closest = min(standard_lengths, key=lambda x: abs(x - raw_bars))
    return closest


@router.post("/{project_id}/loops/upload")
async def upload_user_loops(
    project_id: str,
    files: List[UploadFile] = File(...),
    bpm_override: Optional[float] = Query(None, description="Optional BPM override for loops"),
):
    """Upload one or more loop stems for a project.

    Accepts WAV/AIFF/MP3 audio files. Detects BPM and loop length.
    Creates or updates the UserLoopBundle for this project.

    Returns:
        JSON with bundle info and stem details.
    """
    logger.info(f"Uploading {len(files)} loop stems for project {project_id}")

    # Create or get existing bundle
    bundle = USER_LOOPS.get(project_id)
    if not bundle:
        bundle = UserLoopBundle(
            id=str(uuid.uuid4()),
            project_id=project_id,
        )

    # Save and process each file
    loop_dir = TEMP_DIR / project_id
    loop_dir.mkdir(parents=True, exist_ok=True)

    new_stems = []
    for upload_file in files:
        original_filename = upload_file.filename or "loop.wav"
        file_ext = Path(original_filename).suffix.lower()
        if file_ext not in [".wav", ".aiff", ".aif", ".mp3"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format for '{original_filename}': {file_ext}",
            )

        stem_id = str(uuid.uuid4())
        file_path = loop_dir / f"{stem_id}{file_ext}"

        try:
            content = await upload_file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            # Load audio for analysis
            audio = load_audio_file(file_path, role="user_loop")

            # Detect BPM if not yet set for the bundle
            if bundle.bpm <= 0:
                if bpm_override:
                    bundle.bpm = bpm_override
                    bundle.detected_bpm = estimate_bpm(audio)
                else:
                    detected = estimate_bpm(audio)
                    bundle.bpm = detected
                    bundle.detected_bpm = detected

            # Detect loop length
            loop_length = _detect_loop_length_bars(audio.duration, bundle.bpm)

            stem = UserLoopStem(
                id=stem_id,
                filename=original_filename,
                role="drums",  # default role, user reassigns in UI
                loop_length_bars=loop_length,
                start_bar=0.0,
                end_bar=float(loop_length),
                audio_path=str(file_path),
                duration_seconds=audio.duration,
            )
            new_stems.append(stem)
            bundle.stems.append(stem)
            logger.info(f"Added stem '{original_filename}': {loop_length} bars at {bundle.bpm} BPM")

        except Exception as e:
            logger.error(f"Error processing loop '{original_filename}': {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process '{original_filename}': {str(e)}",
            )

    # Compute BPM ratio if reference exists
    ref_mix = REFERENCE_MIXES.get(project_id)
    if ref_mix and bundle.bpm > 0:
        bundle.compute_bpm_ratio(ref_mix.bpm)
        logger.info(f"BPM ratio (loop/reference): {bundle.bpm_ratio:.3f}")

    USER_LOOPS[project_id] = bundle

    return {
        "projectId": project_id,
        "bundleId": bundle.id,
        "bpm": bundle.bpm,
        "detectedBpm": bundle.detected_bpm,
        "bpmRatio": bundle.bpm_ratio,
        "stemCount": len(bundle.stems),
        "newStems": [s.to_dict() for s in new_stems],
        "allStems": [s.to_dict() for s in bundle.stems],
    }


@router.get("/{project_id}/loops")
async def get_user_loops(project_id: str):
    """Get all user loop stems for a project."""
    bundle = USER_LOOPS.get(project_id)
    if not bundle:
        return {
            "projectId": project_id,
            "bundle": None,
            "stemCount": 0,
        }

    return {
        "projectId": project_id,
        "bundle": bundle.to_dict(),
        "stemCount": len(bundle.stems),
    }


class UpdateStemRoleRequest(BaseModel):
    role: str


@router.patch("/{project_id}/loops/{stem_id}/role")
async def update_stem_role(project_id: str, stem_id: str, request: UpdateStemRoleRequest):
    """Update the role assignment for a user loop stem."""
    bundle = USER_LOOPS.get(project_id)
    if not bundle:
        raise HTTPException(status_code=404, detail=f"No loops found for project {project_id}")

    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{request.role}'. Must be one of: {VALID_ROLES}",
        )

    target = None
    for stem in bundle.stems:
        if stem.id == stem_id:
            target = stem
            break

    if not target:
        raise HTTPException(status_code=404, detail=f"Stem {stem_id} not found")

    target.role = request.role
    logger.info(f"Updated stem {stem_id} role to '{request.role}'")

    return {"stemId": stem_id, "role": target.role, "stem": target.to_dict()}


class UpdateStemBoundsRequest(BaseModel):
    loopLengthBars: Optional[int] = None
    startBar: Optional[float] = None
    endBar: Optional[float] = None


@router.patch("/{project_id}/loops/{stem_id}/bounds")
async def update_stem_bounds(project_id: str, stem_id: str, request: UpdateStemBoundsRequest):
    """Update the loop length and trim boundaries for a stem."""
    bundle = USER_LOOPS.get(project_id)
    if not bundle:
        raise HTTPException(status_code=404, detail=f"No loops found for project {project_id}")

    target = None
    for stem in bundle.stems:
        if stem.id == stem_id:
            target = stem
            break

    if not target:
        raise HTTPException(status_code=404, detail=f"Stem {stem_id} not found")

    if request.loopLengthBars is not None:
        target.loop_length_bars = request.loopLengthBars
    if request.startBar is not None:
        target.start_bar = request.startBar
    if request.endBar is not None:
        target.end_bar = request.endBar

    return {"stemId": stem_id, "stem": target.to_dict()}


@router.delete("/{project_id}/loops/{stem_id}")
async def delete_user_stem(project_id: str, stem_id: str):
    """Delete a user loop stem."""
    bundle = USER_LOOPS.get(project_id)
    if not bundle:
        raise HTTPException(status_code=404, detail=f"No loops found for project {project_id}")

    original_len = len(bundle.stems)
    bundle.stems = [s for s in bundle.stems if s.id != stem_id]

    if len(bundle.stems) == original_len:
        raise HTTPException(status_code=404, detail=f"Stem {stem_id} not found")

    logger.info(f"Deleted stem {stem_id} from project {project_id}")
    return {"projectId": project_id, "deleted": stem_id, "remainingStems": len(bundle.stems)}


class UpdateBundleBpmRequest(BaseModel):
    bpm: float


@router.patch("/{project_id}/loops/bpm")
async def update_loop_bpm(project_id: str, request: UpdateBundleBpmRequest):
    """Override the BPM for the user's loop bundle.

    Also recomputes BPM ratio and loop lengths.
    """
    bundle = USER_LOOPS.get(project_id)
    if not bundle:
        raise HTTPException(status_code=404, detail=f"No loops found for project {project_id}")

    if request.bpm <= 0:
        raise HTTPException(status_code=400, detail="BPM must be positive")

    old_bpm = bundle.bpm
    bundle.bpm = request.bpm

    # Recompute loop lengths based on new BPM
    for stem in bundle.stems:
        stem.loop_length_bars = _detect_loop_length_bars(stem.duration_seconds, bundle.bpm)
        stem.end_bar = float(stem.loop_length_bars)

    # Recompute BPM ratio
    ref_mix = REFERENCE_MIXES.get(project_id)
    if ref_mix:
        bundle.compute_bpm_ratio(ref_mix.bpm)

    logger.info(f"Updated bundle BPM: {old_bpm} -> {bundle.bpm}, ratio: {bundle.bpm_ratio:.3f}")

    return {
        "projectId": project_id,
        "bpm": bundle.bpm,
        "bpmRatio": bundle.bpm_ratio,
        "bundle": bundle.to_dict(),
    }
