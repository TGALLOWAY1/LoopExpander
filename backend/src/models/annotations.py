"""Pydantic models for Visual Composer annotations."""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class AnnotationBlock(BaseModel):
    """A single annotation block within a lane."""
    id: str = Field(..., description="Unique identifier for the annotation block")
    start_bar: float = Field(..., ge=0.0, description="Start position in bars")
    end_bar: float = Field(..., description="End position in bars")
    label: Optional[str] = Field(None, description="Optional label for the block")
    
    @field_validator('end_bar')
    @classmethod
    def validate_end_bar(cls, v: float, info) -> float:
        """Ensure end_bar is greater than start_bar."""
        if 'start_bar' in info.data and v <= info.data['start_bar']:
            raise ValueError(f"end_bar must be greater than start_bar, got start={info.data['start_bar']}, end={v}")
        return v


class AnnotationLane(BaseModel):
    """A lane containing annotation blocks for a specific stem category."""
    stem_category: str = Field(..., description="Stem category (drums, bass, vocals, instruments)")
    blocks: List[AnnotationBlock] = Field(default_factory=list, description="List of annotation blocks in this lane")
    
    @field_validator('stem_category')
    @classmethod
    def validate_stem_category(cls, v: str) -> str:
        """Validate stem category is one of the allowed values."""
        allowed = {"drums", "bass", "vocals", "instruments"}
        if v not in allowed:
            raise ValueError(f"stem_category must be one of {allowed}, got {v}")
        return v


class RegionAnnotations(BaseModel):
    """Annotations for a specific region."""
    region_id: str = Field(..., description="ID of the region these annotations belong to")
    lanes: List[AnnotationLane] = Field(default_factory=list, description="List of annotation lanes for this region")


class ReferenceAnnotations(BaseModel):
    """Complete annotations for a reference track."""
    reference_id: str = Field(..., description="ID of the reference track")
    regions: List[RegionAnnotations] = Field(default_factory=list, description="List of region annotations")

