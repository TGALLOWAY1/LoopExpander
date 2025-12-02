"""Region model for song structure analysis."""
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class Region:
    """Represents a region (section) of a song."""
    id: str
    name: str
    type: str  # e.g., "low_energy", "build", "high_energy", "drop"
    start: float  # seconds
    end: float  # seconds
    motifs: List[str]
    fills: List[str]
    callResponse: List[Dict[str, Any]]
    
    def __post_init__(self):
        """Validate region data after initialization."""
        if self.start < 0:
            raise ValueError(f"Region start time must be >= 0, got {self.start}")
        if self.end <= self.start:
            raise ValueError(f"Region end time must be > start time, got start={self.start}, end={self.end}")
        if not self.id:
            raise ValueError("Region id cannot be empty")
        if not self.name:
            raise ValueError("Region name cannot be empty")
    
    @property
    def duration(self) -> float:
        """Get the duration of the region in seconds."""
        return self.end - self.start
    
    def __repr__(self) -> str:
        """String representation of Region."""
        return (
            f"Region(id={self.id}, name={self.name}, type={self.type}, "
            f"start={self.start:.2f}s, end={self.end:.2f}s, duration={self.duration:.2f}s)"
        )

