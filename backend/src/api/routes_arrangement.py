"""API routes for arrangement generation and management (Phase 5-8)."""
import uuid
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

from models.store import (
    REFERENCE_MIXES,
    REFERENCE_REGIONS,
    REFERENCE_ROLE_ACTIVITY,
    REFERENCE_ENERGY_CURVES,
    INTERACTION_LABELS,
    USER_LOOPS,
    ARRANGEMENTS,
    VARIATION_SUGGESTIONS,
    GUIDANCE_MESSAGES,
    GUIDE_MARKERS,
)
from arrangement.mapping_engine import generate_arrangement
from arrangement.models import Arrangement, ArrangementBlock
from arrangement.presets import get_preset, list_presets
from arrangement.variation_engine import (
    generate_variation_suggestions,
    apply_suggestion as apply_variation_suggestion,
    VariationSuggestion,
)
from arrangement.guidance_engine import (
    generate_guidance_messages,
    GuidanceMessage,
)
from arrangement.guide_content import (
    generate_guide_markers,
    GuideMarker,
)
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/project", tags=["arrangement"])


class GenerateArrangementRequest(BaseModel):
    """Optional parameters for arrangement generation."""
    includeInactive: bool = False  # Include inactive role ranges as muted blocks
    presetId: Optional[str] = None  # Genre preset ID (e.g., "future_bass", "dubstep")


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

    # Resolve preset if provided
    preset = None
    if request and request.presetId:
        preset = get_preset(request.presetId)
        if not preset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown preset ID: {request.presetId}",
            )

    # Validate regions exist (not required when using a preset)
    regions = REFERENCE_REGIONS.get(project_id, [])
    if not regions and not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No regions found. Run analyze-mix first or select a genre preset.",
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
        f"preset={preset.id if preset else 'none'}, "
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
            preset=preset,
        )

        ARRANGEMENTS[project_id] = arrangement

        # Clear cached suggestions, guidance, and guide markers for regeneration
        VARIATION_SUGGESTIONS.pop(project_id, None)
        GUIDANCE_MESSAGES.pop(project_id, None)
        GUIDE_MARKERS.pop(project_id, None)

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


@router.get("/presets")
async def get_presets():
    """List all available genre presets for arrangement generation."""
    return [p.to_dict() for p in list_presets()]


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


# ========== Variation Suggestions (Phase 6A) ==========


@router.get("/{project_id}/suggestions")
async def get_suggestions(project_id: str):
    """Get variation suggestions for the current arrangement.

    Generates fresh suggestions if none exist, or returns cached ones.
    """
    arrangement = ARRANGEMENTS.get(project_id)
    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No arrangement found for project {project_id}.",
        )

    # Generate suggestions if not cached
    if project_id not in VARIATION_SUGGESTIONS:
        # Count stems per role for A/B alternation suggestions
        loop_bundle = USER_LOOPS.get(project_id)
        user_stem_roles = {}
        if loop_bundle:
            for stem in loop_bundle.stems:
                user_stem_roles[stem.role] = user_stem_roles.get(stem.role, 0) + 1

        energy_curve = REFERENCE_ENERGY_CURVES.get(project_id)

        suggestions = generate_variation_suggestions(
            arrangement=arrangement,
            user_stem_roles=user_stem_roles,
            energy_curve=energy_curve,
        )
        VARIATION_SUGGESTIONS[project_id] = suggestions
        logger.info(f"Generated {len(suggestions)} variation suggestions for {project_id}")

    suggestions = VARIATION_SUGGESTIONS[project_id]
    return {
        "projectId": project_id,
        "suggestions": [s.to_dict() for s in suggestions],
        "total": len(suggestions),
        "applied": sum(1 for s in suggestions if s.applied),
        "dismissed": sum(1 for s in suggestions if s.dismissed),
    }


@router.post("/{project_id}/suggestions/regenerate")
async def regenerate_suggestions(project_id: str):
    """Force regeneration of variation suggestions."""
    arrangement = ARRANGEMENTS.get(project_id)
    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No arrangement found for project {project_id}.",
        )

    loop_bundle = USER_LOOPS.get(project_id)
    user_stem_roles = {}
    if loop_bundle:
        for stem in loop_bundle.stems:
            user_stem_roles[stem.role] = user_stem_roles.get(stem.role, 0) + 1

    energy_curve = REFERENCE_ENERGY_CURVES.get(project_id)

    suggestions = generate_variation_suggestions(
        arrangement=arrangement,
        user_stem_roles=user_stem_roles,
        energy_curve=energy_curve,
    )
    VARIATION_SUGGESTIONS[project_id] = suggestions
    logger.info(f"Regenerated {len(suggestions)} variation suggestions for {project_id}")

    return {
        "projectId": project_id,
        "suggestions": [s.to_dict() for s in suggestions],
        "total": len(suggestions),
    }


@router.post("/{project_id}/suggestions/{suggestion_id}/apply")
async def apply_suggestion(project_id: str, suggestion_id: str):
    """Apply a variation suggestion to the arrangement."""
    arrangement = ARRANGEMENTS.get(project_id)
    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No arrangement found for project {project_id}.",
        )

    suggestions = VARIATION_SUGGESTIONS.get(project_id, [])
    target = next((s for s in suggestions if s.id == suggestion_id), None)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Suggestion {suggestion_id} not found.",
        )

    if target.applied:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Suggestion already applied.",
        )

    if target.dismissed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Suggestion was dismissed. Regenerate suggestions to get it back.",
        )

    success = apply_variation_suggestion(arrangement, target)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply suggestion.",
        )

    logger.info(f"Applied suggestion {suggestion_id} ({target.type}) for {project_id}")

    return {
        "suggestion": target.to_dict(),
        "arrangement": arrangement.to_dict(),
    }


@router.post("/{project_id}/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(project_id: str, suggestion_id: str):
    """Dismiss a variation suggestion."""
    suggestions = VARIATION_SUGGESTIONS.get(project_id, [])
    target = next((s for s in suggestions if s.id == suggestion_id), None)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Suggestion {suggestion_id} not found.",
        )

    target.dismissed = True
    logger.info(f"Dismissed suggestion {suggestion_id} for {project_id}")

    return {"suggestion": target.to_dict()}


# ========== Arrangement Guidance (Phase 6B) ==========


@router.get("/{project_id}/guidance")
async def get_guidance(project_id: str):
    """Get arrangement guidance messages.

    Generates fresh guidance if none exist, or returns cached ones.
    """
    arrangement = ARRANGEMENTS.get(project_id)
    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No arrangement found for project {project_id}.",
        )

    # Generate guidance if not cached
    if project_id not in GUIDANCE_MESSAGES:
        interaction_labels = INTERACTION_LABELS.get(project_id, [])
        energy_curve = REFERENCE_ENERGY_CURVES.get(project_id)

        messages = generate_guidance_messages(
            arrangement=arrangement,
            interaction_labels=interaction_labels,
            energy_curve=energy_curve,
        )
        GUIDANCE_MESSAGES[project_id] = messages
        logger.info(f"Generated {len(messages)} guidance messages for {project_id}")

    messages = GUIDANCE_MESSAGES[project_id]
    return {
        "projectId": project_id,
        "messages": [m.to_dict() for m in messages],
        "total": len(messages),
        "warnings": sum(1 for m in messages if m.severity == "warning"),
        "suggestions": sum(1 for m in messages if m.severity == "suggestion"),
        "info": sum(1 for m in messages if m.severity == "info"),
    }


@router.post("/{project_id}/guidance/regenerate")
async def regenerate_guidance(project_id: str):
    """Force regeneration of guidance messages."""
    arrangement = ARRANGEMENTS.get(project_id)
    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No arrangement found for project {project_id}.",
        )

    interaction_labels = INTERACTION_LABELS.get(project_id, [])
    energy_curve = REFERENCE_ENERGY_CURVES.get(project_id)

    messages = generate_guidance_messages(
        arrangement=arrangement,
        interaction_labels=interaction_labels,
        energy_curve=energy_curve,
    )
    GUIDANCE_MESSAGES[project_id] = messages
    logger.info(f"Regenerated {len(messages)} guidance messages for {project_id}")

    return {
        "projectId": project_id,
        "messages": [m.to_dict() for m in messages],
        "total": len(messages),
    }


# ========== Guide Content (Phase 7) ==========


@router.get("/{project_id}/guide-markers")
async def get_guide_markers(project_id: str):
    """Get guide markers for the arrangement timeline.

    Generates fresh markers if none exist, or returns cached ones.
    """
    arrangement = ARRANGEMENTS.get(project_id)
    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No arrangement found for project {project_id}.",
        )

    if project_id not in GUIDE_MARKERS:
        interaction_labels = INTERACTION_LABELS.get(project_id, [])
        energy_curve = REFERENCE_ENERGY_CURVES.get(project_id)

        markers = generate_guide_markers(
            arrangement=arrangement,
            interaction_labels=interaction_labels,
            energy_curve=energy_curve,
        )
        GUIDE_MARKERS[project_id] = markers
        logger.info(f"Generated {len(markers)} guide markers for {project_id}")

    markers = GUIDE_MARKERS[project_id]
    return {
        "projectId": project_id,
        "markers": [m.to_dict() for m in markers],
        "total": len(markers),
    }


@router.post("/{project_id}/guide-markers/regenerate")
async def regenerate_guide_markers(project_id: str):
    """Force regeneration of guide markers."""
    arrangement = ARRANGEMENTS.get(project_id)
    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No arrangement found for project {project_id}.",
        )

    interaction_labels = INTERACTION_LABELS.get(project_id, [])
    energy_curve = REFERENCE_ENERGY_CURVES.get(project_id)

    markers = generate_guide_markers(
        arrangement=arrangement,
        interaction_labels=interaction_labels,
        energy_curve=energy_curve,
    )
    GUIDE_MARKERS[project_id] = markers
    logger.info(f"Regenerated {len(markers)} guide markers for {project_id}")

    return {
        "projectId": project_id,
        "markers": [m.to_dict() for m in markers],
        "total": len(markers),
    }


# ========== Section Audition (Phase 8B) ==========


class AuditionRequest(BaseModel):
    """Request payload for section audition."""
    sectionId: str
    soloRoles: Optional[List[str]] = None
    muteRoles: Optional[List[str]] = None


@router.post("/{project_id}/audition")
async def audition_section(project_id: str, request: AuditionRequest):
    """Render audio for a single section and return as WAV.

    Supports solo/mute filtering by role for isolated previewing.
    """
    arrangement = ARRANGEMENTS.get(project_id)
    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No arrangement found for project {project_id}.",
        )

    loop_bundle = USER_LOOPS.get(project_id)
    if not loop_bundle or not loop_bundle.stems:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user loop stems found.",
        )

    from arrangement.audition import render_section_audio

    try:
        wav_bytes = render_section_audio(
            arrangement=arrangement,
            loop_bundle=loop_bundle,
            section_id=request.sectionId,
            solo_roles=request.soloRoles,
            mute_roles=request.muteRoles,
        )

        section = next(
            (s for s in arrangement.sections if s.id == request.sectionId), None
        )
        filename = f"audition_{section.label if section else request.sectionId}.wav"

        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
            },
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Audition rendering failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audition rendering failed: {str(e)}",
        )
