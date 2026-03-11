"""Role activity models for broad role detection from full mix."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class ActivitySegment:
    """A segment where a role is active or inactive."""
    start_bar: float
    end_bar: float
    active: bool
    confidence: float


@dataclass
class RoleActivityTimeline:
    """Activity timeline for a single role."""
    role: str  # "drums", "bass", "melodic", "vocal"
    segments: List[ActivitySegment] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "segments": [
                {
                    "startBar": seg.start_bar,
                    "endBar": seg.end_bar,
                    "active": seg.active,
                    "confidence": seg.confidence,
                }
                for seg in self.segments
            ],
        }
