"""API routes for arrangement generation and management (Phase 5)."""
import uuid
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from models.store import (
    REFERENCE_MIXES,
    REFERENCE_REGIONS,
    REFERENCE_ROLE_ACTIVITY,
    REFERENCE_ENERGY_CURVES,
    INTERACTION_LABELS,
    USER_LOOPS,
    ARRANGEMENTS,
)
from arrangement.mapping_engine import generate_arrangement
from arrangement.models import Arrangement, ArrangementBlock
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/project", tags=["arrangement"])


class GenerateArrangementRequest(BaseModel):
    """Optional parameters for arrangement generation."""
    includeInactive: bool = False  # Include inactive role ranges as muted blocks


@router.post("/{project_id}/arrange")
async def generate_arrangement_endpoint(
    project_id: str,
    request: Optional[GenerateArrangementRequest] = None,
):
    """Generate an arrangement from the approved structure and user loops.

    Requires:
    - Reference mix with regions (from analyze-mix)
    - Role activity timelines (from analyze-mix)
    - User loop stems (from loop upload)

    Optional:
    - Interaction labels (from Phase 3)
    - Energy curve data (from analyze-mix)

    Returns:
        Full arrangement with sections and blocks.
    """
    # Validate reference mix exists
    mix = REFERENCE_MIXES.get(project_id)
    if not mix:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference mix {project_id} not found. Upload and analyze a reference first.",
        )

    # Validate regions exist
    regions = REFERENCE_REGIONS.get(project_id, [])
    if not regions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No regions found. Run analyze-mix first.",
        )

    # Validate user loops exist
    loop_bundle = USER_LOOPS.get(project_id)
    if not loop_bundle or not loop_bundle.stems:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user loop stems found. Upload loops first.",
        )

    # Gather optional data
    role_timelines = REFERENCE_ROLE_ACTIVITY.get(project_id, [])
    interaction_labels = INTERACTION_LABELS.get(project_id, [])
    energy_curve = REFERENCE_ENERGY_CURVES.get(project_id)

    logger.info(
        f"Generating arrangement for {project_id}: "
        f"{len(regions)} regions, {len(loop_bundle.stems)} stems, "
        f"{len(role_timelines)} role timelines, "
        f"{len(interaction_labels)} interaction labels"
    )

    try:
        arrangement = generate_arrangement(
            project_id=project_id,
            regions=regions,
            role_timelines=role_timelines,
            interaction_labels=interaction_labels,
            user_loops=loop_bundle,
            energy_curve=energy_curve,
            bpm=mix.bpm,
        )

        ARRANGEMENTS[project_id] = arrangement

        logger.info(
            f"Arrangement generated: {len(arrangement.sections)} sections, "
            f"{len(arrangement.blocks)} blocks, {arrangement.total_bars} bars"
        )

        return arrangement.to_dict()

    except Exception as e:
        logger.error(f"Arrangement generation failed for {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Arrangement generation failed: {str(e)}",
        )


@router.get("/{project_id}/arrangement")
async def get_arrangement(project_id: str):
    """Retrieve the current arrangement for a project.

    Returns:
        The full arrangement if one has been generated, or 404.
    """
    arrangement = ARRANGEMENTS.get(project_id)
    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No arrangement found for project {project_id}. Generate one first with POST /arrange.",
        )

    return arrangement.to_dict()


class UpdateBlockRequest(BaseModel):
    """Payload for updating an arrangement block."""
    active: Optional[bool] = None
    variationType: Optional[str] = None
    startBar: Optional[float] = None
    endBar: Optional[float] = None


@router.patch("/{project_id}/arrangement/blocks/{block_id}")
async def update_arrangement_block(
    project_id: str,
    block_id: str,
    request: UpdateBlockRequest,
):
    """Update a single arrangement block (mute/unmute, move, resize)."""
    arrangement = ARRANGEMENTS.get(project_id)
    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No arrangement found for project {project_id}.",
        )

    target = None
    for block in arrangement.blocks:
        if block.id == block_id:
            target = block
            break

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block {block_id} not found in arrangement.",
        )

    if request.active is not None:
        target.active = request.active
    if request.variationType is not None:
        target.variation_type = request.variationType
    if request.startBar is not None:
        target.start_bar = request.startBar
    if request.endBar is not None:
        target.end_bar = request.endBar

    return {"blockId": block_id, "block": target.to_dict()}


@router.delete("/{project_id}/arrangement/blocks/{block_id}")
async def delete_arrangement_block(project_id: str, block_id: str):
    """Delete a block from the arrangement."""
    arrangement = ARRANGEMENTS.get(project_id)
    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No arrangement found for project {project_id}.",
        )

    original_len = len(arrangement.blocks)
    arrangement.blocks = [b for b in arrangement.blocks if b.id != block_id]

    if len(arrangement.blocks) == original_len:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block {block_id} not found in arrangement.",
        )

    return {"deleted": block_id, "remainingBlocks": len(arrangement.blocks)}
