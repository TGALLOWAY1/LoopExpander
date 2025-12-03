"""Models for subregion pattern analysis."""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

try:
    from typing import Literal
except ImportError:
    # Python < 3.8 compatibility
    from typing_extensions import Literal

from pydantic import BaseModel, Field


# Stem categories matching the 4 stem roles
StemCategory = Literal["drums", "bass", "vocals", "instruments"]


@dataclass
class SubRegionPattern:
    """
    Represents a subregion pattern within a region for a specific stem category.
    
    This captures small segments inside each Arrangement Region for each stem category,
    including repeated patterns, variations, silence/dropouts, and density information.
    """
    id: str
    region_id: str
    stem_category: StemCategory
    start_bar: float  # Bar index inside the song/region (bar-based positioning)
    end_bar: float
    label: Optional[str] = None  # e.g., "Pat A", "Riff 1", "Chords", "Voc A"
    motif_group_id: Optional[str] = None  # Link to motif group if applicable
    is_variation: bool = False  # True if this is a variation of a pattern
    is_silence: bool = False  # True if this segment is silence/dropout
    intensity: float = 0.0  # 0-1, mapped to opacity in UI
    metadata: Optional[Dict[str, Any]] = None  # Future-proofing for additional data
    
    def __post_init__(self):
        """Validate subregion pattern data."""
        if self.start_bar < 0:
            raise ValueError(f"start_bar must be >= 0, got {self.start_bar}")
        if self.end_bar <= self.start_bar:
            raise ValueError(f"end_bar must be > start_bar, got start={self.start_bar}, end={self.end_bar}")
        if not (0.0 <= self.intensity <= 1.0):
            raise ValueError(f"intensity must be between 0.0 and 1.0, got {self.intensity}")
        if not self.id:
            raise ValueError("id cannot be empty")
        if not self.region_id:
            raise ValueError("region_id cannot be empty")


@dataclass
class RegionSubRegions:
    """
    Container for all subregion patterns within a single region.
    
    Organizes patterns by stem category (lanes) for DNA-style visualization.
    """
    region_id: str
    lanes: Dict[StemCategory, List[SubRegionPattern]]
    
    def __post_init__(self):
        """Validate region subregions data."""
        if not self.region_id:
            raise ValueError("region_id cannot be empty")
        # Ensure all 4 stem categories are present (even if empty lists)
        expected_categories: List[StemCategory] = ["drums", "bass", "vocals", "instruments"]
        for category in expected_categories:
            if category not in self.lanes:
                self.lanes[category] = []


# Pydantic DTOs for API responses
class SubRegionPatternDTO(BaseModel):
    """Pydantic model for SubRegionPattern API response."""
    id: str
    region_id: str = Field(..., alias="regionId")
    stem_category: StemCategory = Field(..., alias="stemCategory")
    start_bar: float = Field(..., alias="startBar")
    end_bar: float = Field(..., alias="endBar")
    label: Optional[str] = None
    motif_group_id: Optional[str] = Field(None, alias="motifGroupId")
    is_variation: bool = Field(..., alias="isVariation")
    is_silence: bool = Field(..., alias="isSilence")
    intensity: float
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        populate_by_name = True  # Allow both field names and aliases
        from_attributes = True  # Allow creation from dataclass instances


class RegionSubRegionsDTO(BaseModel):
    """Pydantic model for RegionSubRegions API response."""
    region_id: str = Field(..., alias="regionId")
    lanes: Dict[StemCategory, List[SubRegionPatternDTO]]
    
    class Config:
        populate_by_name = True
        from_attributes = True

