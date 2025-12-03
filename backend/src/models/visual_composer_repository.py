"""Repository for Visual Composer annotations persistence.

This module abstracts read/write operations for Visual Composer annotations,
allowing the storage implementation to be changed later without affecting the API layer.
"""
from typing import Dict, Optional
from models.visual_composer import VisualComposerAnnotations


# In-memory storage for Visual Composer annotations per project
# Maps project_id -> VisualComposerAnnotations
_VISUAL_COMPOSER_ANNOTATIONS: Dict[str, VisualComposerAnnotations] = {}


def get_annotations(project_id: str) -> Optional[VisualComposerAnnotations]:
    """
    Get Visual Composer annotations for a project.
    
    Args:
        project_id: ID of the project
        
    Returns:
        VisualComposerAnnotations if found, None otherwise
    """
    return _VISUAL_COMPOSER_ANNOTATIONS.get(project_id)


def save_annotations(annotations: VisualComposerAnnotations) -> None:
    """
    Save Visual Composer annotations for a project.
    
    Args:
        annotations: VisualComposerAnnotations to save
    """
    _VISUAL_COMPOSER_ANNOTATIONS[annotations.projectId] = annotations


def delete_annotations(project_id: str) -> bool:
    """
    Delete Visual Composer annotations for a project.
    
    Args:
        project_id: ID of the project
        
    Returns:
        True if annotations were deleted, False if they didn't exist
    """
    if project_id in _VISUAL_COMPOSER_ANNOTATIONS:
        del _VISUAL_COMPOSER_ANNOTATIONS[project_id]
        return True
    return False


def has_annotations(project_id: str) -> bool:
    """
    Check if annotations exist for a project.
    
    Args:
        project_id: ID of the project
        
    Returns:
        True if annotations exist, False otherwise
    """
    return project_id in _VISUAL_COMPOSER_ANNOTATIONS

