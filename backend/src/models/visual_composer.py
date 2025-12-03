"""Pydantic models for Visual Composer annotations (per project + region)."""
from typing import List, Optional
try:
    from typing import Literal
except ImportError:
    # Python < 3.8
    from typing_extensions import Literal
from pydantic import BaseModel, Field, field_validator


class VisualComposerLane(BaseModel):
    """A lane in Visual Composer (aligned with PRD).
    
    Lanes are metadata containers for organizing blocks.
    """
    id: str = Field(..., description="Unique identifier for the lane")
    name: str = Field(..., description="Display name for the lane")
    color: Optional[str] = Field(None, description="Color for the lane")
    collapsed: bool = Field(default=False, description="Whether the lane is collapsed")
    order: int = Field(..., ge=0, description="Display order of the lane")
    
    class Config:
        populate_by_name = True  # Allow both field names and aliases


class VisualComposerBlock(BaseModel):
    """A block in Visual Composer (aligned with PRD).
    
    Blocks represent events, motifs, calls, responses, variations, or fills.
    """
    id: str = Field(..., description="Unique identifier for the block")
    laneId: str = Field(..., description="ID of the lane this block belongs to")
    startBar: float = Field(..., ge=0.0, description="Start position in bars")
    endBar: float = Field(..., description="End position in bars")
    color: Optional[str] = Field(None, description="Optional color for the block")
    type: Literal['call', 'response', 'variation', 'fill', 'custom'] = Field(
        default='custom',
        description="Type of annotation block"
    )
    notes: Optional[str] = Field(None, description="Optional notes for the block")
    
    class Config:
        populate_by_name = True  # Allow both field names and aliases
    
    @field_validator('endBar')
    @classmethod
    def validate_end_bar(cls, v: float, info) -> float:
        """Ensure endBar is greater than startBar."""
        start_bar = info.data.get('startBar')
        if start_bar is not None and v <= start_bar:
            raise ValueError(f"endBar must be greater than startBar, got start={start_bar}, end={v}")
        return v


class VisualComposerRegionAnnotations(BaseModel):
    """Annotations for a specific region in Visual Composer (aligned with PRD).
    
    Contains both lanes (metadata) and blocks (actual annotations).
    Includes region metadata for alignment with the main Region model.
    """
    regionId: str = Field(..., description="ID of the region these annotations belong to")
    regionName: Optional[str] = Field(None, description="Optional name for the region")
    notes: Optional[str] = Field(None, description="Optional notes for the region")
    startBar: Optional[float] = Field(None, ge=0.0, description="Start position of the region in bars")
    endBar: Optional[float] = Field(None, ge=0.0, description="End position of the region in bars")
    regionType: Optional[str] = Field(None, description="Type of the region (e.g., 'low_energy', 'build', 'high_energy', 'drop')")
    displayOrder: Optional[int] = Field(None, ge=0, description="Display order of the region (for sorting)")
    lanes: List[VisualComposerLane] = Field(default_factory=list, description="List of lanes for this region")
    blocks: List[VisualComposerBlock] = Field(default_factory=list, description="List of blocks for this region")
    
    class Config:
        populate_by_name = True  # Allow both field names and aliases
    
    @field_validator('endBar')
    @classmethod
    def validate_end_bar(cls, v: Optional[float], info) -> Optional[float]:
        """Ensure endBar is greater than startBar if both are provided."""
        if v is None:
            return v
        start_bar = info.data.get('startBar')
        if start_bar is not None and v <= start_bar:
            raise ValueError(f"endBar must be greater than startBar, got start={start_bar}, end={v}")
        return v


class VisualComposerAnnotations(BaseModel):
    """Complete Visual Composer annotations for a project (aligned with PRD).
    
    Top-level container for all Visual Composer annotations.
    """
    projectId: str = Field(..., description="ID of the project")
    regions: List[VisualComposerRegionAnnotations] = Field(
        default_factory=list,
        description="List of region annotations"
    )
    
    class Config:
        populate_by_name = True  # Allow both field names and aliases

