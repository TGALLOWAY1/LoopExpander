"""Visual Composer API routes."""
from fastapi import APIRouter, HTTPException, status, Body
from utils.logger import get_logger

from models.visual_composer import (
    VisualComposerAnnotations,
    VisualComposerRegionAnnotations
)
from models.visual_composer_repository import (
    get_annotations,
    save_annotations,
    has_annotations
)
from models.store import REFERENCE_BUNDLES, REFERENCE_REGIONS

logger = get_logger(__name__)

router = APIRouter(prefix="/visual-composer", tags=["visual-composer"])


def seconds_to_bars(seconds: float, bpm: float) -> float:
    """
    Convert seconds to bars (assuming 4/4 time signature).
    
    Args:
        seconds: Time in seconds
        bpm: Beats per minute
    
    Returns:
        Time in bars
    """
    beats_per_second = bpm / 60.0
    beats = seconds * beats_per_second
    bars = beats / 4.0  # 4 beats per bar in 4/4 time
    return bars


def create_default_region_annotations(region, bpm: float, display_order: int) -> VisualComposerRegionAnnotations:
    """
    Create default region annotations from a Region model.
    
    Args:
        region: Region dataclass instance
        bpm: Beats per minute for time-to-bar conversion
        display_order: Display order for sorting
    
    Returns:
        VisualComposerRegionAnnotations with default values
    """
    start_bar = seconds_to_bars(region.start, bpm)
    end_bar = seconds_to_bars(region.end, bpm)
    
    return VisualComposerRegionAnnotations(
        regionId=region.id,
        regionName=region.name,
        notes=None,
        startBar=start_bar,
        endBar=end_bar,
        regionType=region.type,
        displayOrder=display_order,
        lanes=[],
        blocks=[]
    )


@router.get("/{project_id}/annotations")
async def get_visual_composer_annotations(project_id: str):
    """
    Get Visual Composer annotations for a project.
    
    Cross-references with known regions from the main analysis and creates
    default entries for any missing regions.
    
    Args:
        project_id: ID of the project (same as reference_id)
    
    Returns:
        JSON with annotations data, including defaults for missing regions
    
    Raises:
        500 if there's an error retrieving annotations
    """
    logger.info(f"Getting Visual Composer annotations for project_id: {project_id}")
    
    try:
        # Get existing annotations (returns None if none exist - this is expected)
        existing_annotations = get_annotations(project_id)
        
        # Get known regions from the main analysis (if available)
        known_regions = REFERENCE_REGIONS.get(project_id, [])
        bundle = REFERENCE_BUNDLES.get(project_id)
        bpm = bundle.bpm if bundle else 120.0  # Default to 120 BPM if bundle not found
        
        # Build a map of existing region annotations by regionId
        existing_regions_map = {}
        if existing_annotations:
            for region_ann in existing_annotations.regions:
                existing_regions_map[region_ann.regionId] = region_ann
        
        # Build the complete list of region annotations
        # Start with existing annotations, then add defaults for missing regions
        all_region_annotations = []
        existing_region_ids = set(existing_regions_map.keys())
        
        # Add existing annotations first
        for region_ann in existing_annotations.regions if existing_annotations else []:
            all_region_annotations.append(region_ann)
        
        # Add default entries for known regions that don't have annotations yet
        for display_order, region in enumerate(known_regions):
            if region.id not in existing_region_ids:
                logger.info(f"Creating default annotations for region {region.id} (not found in existing annotations)")
                default_region_ann = create_default_region_annotations(region, bpm, display_order)
                all_region_annotations.append(default_region_ann)
        
        # If we have known regions but no existing annotations, ensure all regions are included
        if known_regions and not existing_annotations:
            logger.info(f"Creating default annotations for all {len(known_regions)} known regions")
            all_region_annotations = [
                create_default_region_annotations(region, bpm, idx)
                for idx, region in enumerate(known_regions)
            ]
        
        # If no known regions and no existing annotations, return empty structure (still 200 OK)
        # This is the expected case for a new project
        if not known_regions and not existing_annotations:
            logger.info(f"No regions found for project {project_id}, returning empty annotations structure")
            final_annotations = VisualComposerAnnotations(
                projectId=project_id,
                regions=[]
            )
            return final_annotations.model_dump(by_alias=True)
        
        # Sort by displayOrder if available, otherwise by regionId
        all_region_annotations.sort(key=lambda r: (r.displayOrder if r.displayOrder is not None else 999, r.regionId))
        
        # Create the final annotations structure
        final_annotations = VisualComposerAnnotations(
            projectId=project_id,
            regions=all_region_annotations
        )
        
        # Return with camelCase field names
        return final_annotations.model_dump(by_alias=True)
    
    except ValueError as ve:
        # Validation errors
        logger.error(f"Validation error getting annotations for project {project_id}: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(ve)}"
        )
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error getting annotations for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve annotations: {str(e)}"
        )


def validate_annotations(annotations: VisualComposerAnnotations, project_id: str) -> None:
    """
    Validate annotations payload and log warnings for issues.
    
    Args:
        annotations: Annotations to validate
        project_id: Expected project ID
    
    Raises:
        HTTPException with 400 status if validation fails critically
    """
    # Check project ID match (non-critical, we'll override, but log)
    if annotations.projectId != project_id:
        logger.warning(
            f"Project ID mismatch: path={project_id}, payload={annotations.projectId}. "
            f"Overriding payload projectId to match path."
        )
    
    # Get known regions for validation
    known_regions = REFERENCE_REGIONS.get(project_id, [])
    known_region_ids = {r.id for r in known_regions}
    
    # Validate region IDs exist (log warning, don't reject)
    for region_ann in annotations.regions:
        if known_regions and region_ann.regionId not in known_region_ids:
            logger.warning(
                f"Region ID {region_ann.regionId} in annotations not found in known regions. "
                f"Known region IDs: {list(known_region_ids)}"
            )
        
        # Check for overlapping blocks in the same lane (log warning)
        blocks_by_lane: dict[str, list] = {}
        for block in region_ann.blocks:
            if block.laneId not in blocks_by_lane:
                blocks_by_lane[block.laneId] = []
            blocks_by_lane[block.laneId].append(block)
        
        for lane_id, blocks in blocks_by_lane.items():
            # Sort blocks by startBar
            sorted_blocks = sorted(blocks, key=lambda b: b.startBar)
            for i in range(len(sorted_blocks) - 1):
                current = sorted_blocks[i]
                next_block = sorted_blocks[i + 1]
                # Check if blocks overlap (endBar > next startBar)
                if current.endBar > next_block.startBar:
                    logger.warning(
                        f"Overlapping blocks detected in region {region_ann.regionId}, lane {lane_id}: "
                        f"block {current.id} (bars {current.startBar}-{current.endBar}) overlaps with "
                        f"block {next_block.id} (bars {next_block.startBar}-{next_block.endBar})"
                    )


@router.post("/{project_id}/annotations")
async def create_or_update_visual_composer_annotations(
    project_id: str,
    annotations: VisualComposerAnnotations = Body(...)
):
    """
    Create or update Visual Composer annotations for a project.
    
    Args:
        project_id: ID of the project (must match payload)
        annotations: Annotations data to store
    
    Returns:
        JSON with stored annotations data
    
    Raises:
        400 if validation fails (invalid data structure)
        422 if Pydantic validation fails
        500 if there's an unexpected error saving annotations
    """
    logger.info(f"Creating/updating Visual Composer annotations for project_id: {project_id}")
    
    try:
        # Force project_id in payload to match path parameter
        if annotations.projectId != project_id:
            logger.warning(
                f"Project ID mismatch: path={project_id}, payload={annotations.projectId}. "
                f"Overriding payload projectId to match path."
            )
            annotations.projectId = project_id
        
        # Validate annotations (logs warnings, doesn't reject unless critical)
        try:
            validate_annotations(annotations, project_id)
        except ValueError as ve:
            # Critical validation error
            logger.error(f"Validation error for project {project_id}: {ve}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid annotations data: {str(ve)}"
            )
        
        # Save annotations
        save_annotations(annotations)
        logger.info(f"Stored annotations for project {project_id}: {len(annotations.regions)} regions")
        
        # Return stored annotations with camelCase field names
        return annotations.model_dump(by_alias=True)
    
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    except ValueError as ve:
        # Pydantic validation errors
        logger.error(f"Pydantic validation error for project {project_id}: {ve}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(ve)}"
        )
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error saving annotations for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save annotations: {str(e)}"
        )

