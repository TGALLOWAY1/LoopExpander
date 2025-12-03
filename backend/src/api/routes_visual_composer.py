"""Visual Composer API routes."""
from fastapi import APIRouter, HTTPException, status, Body
from utils.logger import get_logger

from models.visual_composer import VisualComposerAnnotations
from models.visual_composer_repository import (
    get_annotations,
    save_annotations,
    has_annotations
)

logger = get_logger(__name__)

router = APIRouter(prefix="/visual-composer", tags=["visual-composer"])


@router.get("/{project_id}/annotations")
async def get_visual_composer_annotations(project_id: str):
    """
    Get Visual Composer annotations for a project.
    
    Args:
        project_id: ID of the project
    
    Returns:
        JSON with annotations data, or empty structure if none exist
    
    Raises:
        500 if there's an error retrieving annotations
    """
    logger.info(f"Getting Visual Composer annotations for project_id: {project_id}")
    
    try:
        # Get existing annotations or return empty structure
        annotations = get_annotations(project_id)
        
        if annotations:
            # Return existing annotations with camelCase field names
            return annotations.model_dump(by_alias=True)
        else:
            # Return empty structure
            return {
                "projectId": project_id,
                "regions": []
            }
    
    except Exception as e:
        logger.error(f"Error getting annotations for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve annotations: {str(e)}"
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
        400 if project_id in payload doesn't match path parameter
        500 if there's an error saving annotations
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
        
        # Save annotations
        save_annotations(annotations)
        logger.info(f"Stored annotations for project {project_id}: {len(annotations.regions)} regions")
        
        # Return stored annotations with camelCase field names
        return annotations.model_dump(by_alias=True)
    
    except Exception as e:
        logger.error(f"Error saving annotations for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save annotations: {str(e)}"
        )

