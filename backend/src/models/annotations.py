"""Pydantic models for Visual Composer annotations."""
from typing import List, Optional
try:
    from typing import Literal
except ImportError:
    # Python < 3.8
    from typing_extensions import Literal
from pydantic import BaseModel, Field, field_validator


class AnnotationBlock(BaseModel):
    """A single annotation block (aligned with PRD).
    
    Blocks are stored at the region level and reference lanes via laneId.
    """
    id: str = Field(..., description="Unique identifier for the annotation block")
    lane_id: str = Field(..., alias="laneId", description="ID of the lane this block belongs to")
    start_bar: float = Field(..., ge=0.0, alias="startBar", description="Start position in bars")
    end_bar: float = Field(..., alias="endBar", description="End position in bars")
    color: Optional[str] = Field(None, description="Optional color for the block")
    type: Literal['call', 'response', 'variation', 'fill', 'custom'] = Field(
        default='custom',
        description="Type of annotation block"
    )
    label: Optional[str] = Field(None, description="Optional label for the block")
    notes: Optional[str] = Field(None, description="Optional notes for the block")
    
    class Config:
        populate_by_name = True  # Allow both field names and aliases
    
    @field_validator('end_bar')
    @classmethod
    def validate_end_bar(cls, v: float, info) -> float:
        """Ensure end_bar is greater than start_bar."""
        start_bar = info.data.get('start_bar') or info.data.get('startBar')
        if start_bar is not None and v <= start_bar:
            raise ValueError(f"end_bar must be greater than start_bar, got start={start_bar}, end={v}")
        return v


class AnnotationLane(BaseModel):
    """A lane metadata container (aligned with PRD).
    
    Lanes are metadata containers; blocks are stored separately at region level.
    For backward compatibility, old format with stemCategory and blocks is accepted.
    """
    id: Optional[str] = Field(None, description="Unique identifier for the lane (generated if missing)")
    name: Optional[str] = Field(None, description="Display name for the lane")
    color: Optional[str] = Field(None, description="Color for the lane")
    collapsed: bool = Field(default=False, description="Whether the lane is collapsed")
    order: Optional[int] = Field(None, ge=0, description="Display order of the lane")
    
    # Backward compatibility: accept old format
    stem_category: Optional[str] = Field(None, alias="stemCategory", description="Legacy: stem category (deprecated)")
    blocks: Optional[List[AnnotationBlock]] = Field(None, description="Legacy: blocks in lane (deprecated, use region-level blocks)")
    
    class Config:
        populate_by_name = True  # Allow both field names and aliases
    
    @field_validator('stem_category')
    @classmethod
    def validate_stem_category(cls, v: Optional[str]) -> Optional[str]:
        """Validate stem category if provided (for backward compatibility)."""
        if v is None:
            return v
        allowed = {"drums", "bass", "vocals", "instruments"}
        if v not in allowed:
            raise ValueError(f"stem_category must be one of {allowed}, got {v}")
        return v


class RegionAnnotations(BaseModel):
    """Annotations for a specific region (aligned with PRD).
    
    Contains both lanes (metadata) and blocks (actual annotations).
    For backward compatibility, old format with blocks inside lanes is accepted.
    Migration from legacy format is handled in the API layer.
    """
    region_id: str = Field(..., alias="regionId", description="ID of the region these annotations belong to")
    name: Optional[str] = Field(None, description="Optional name for the region")
    notes: Optional[str] = Field(None, alias="regionNotes", description="Optional notes for the region")
    lanes: List[AnnotationLane] = Field(default_factory=list, description="List of annotation lanes for this region")
    blocks: List[AnnotationBlock] = Field(default_factory=list, description="List of annotation blocks for this region")
    
    class Config:
        populate_by_name = True  # Allow both field names and aliases


class ReferenceAnnotations(BaseModel):
    """Complete annotations for a reference track."""
    reference_id: str = Field(..., alias="referenceId", description="ID of the reference track")
    regions: List[RegionAnnotations] = Field(default_factory=list, description="List of region annotations")
    
    class Config:
        populate_by_name = True  # Allow both field names and aliases

