"""Data models for the arrangement output."""
from dataclasses import dataclass, field
from typing import Optional, List
import uuid


@dataclass
class ArrangementBlock:
    """A single block in the arrangement timeline.

    Represents a user loop stem placed at a specific position in the arrangement.
    """
    id: str
    stem_id: str  # reference to user loop stem
    role: str  # drums, bass, chord, lead, vocal, fx, percussion, texture
    section_id: str
    start_bar: float
    end_bar: float
    active: bool = True
    variation_type: Optional[str] = None  # "mute", "dropout", "alternate", etc.
    source_loop_start: float = 0.0  # where in the source loop to pull from
    source_loop_end: float = 0.0  # where in the source loop to end

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "stemId": self.stem_id,
            "role": self.role,
            "sectionId": self.section_id,
            "startBar": self.start_bar,
            "endBar": self.end_bar,
            "active": self.active,
            "variationType": self.variation_type,
            "sourceLoopStart": self.source_loop_start,
            "sourceLoopEnd": self.source_loop_end,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArrangementBlock":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            stem_id=data["stemId"],
            role=data["role"],
            section_id=data["sectionId"],
            start_bar=data["startBar"],
            end_bar=data["endBar"],
            active=data.get("active", True),
            variation_type=data.get("variationType"),
            source_loop_start=data.get("sourceLoopStart", 0.0),
            source_loop_end=data.get("sourceLoopEnd", 0.0),
        )


@dataclass
class ArrangementSection:
    """A section within the arrangement, mirroring the reference structure."""
    id: str
    name: str
    label: str
    start_bar: float
    end_bar: float
    type: str  # intro, verse, chorus, bridge, drop, breakdown, outro, etc.

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "startBar": self.start_bar,
            "endBar": self.end_bar,
            "type": self.type,
        }


@dataclass
class Arrangement:
    """The full arrangement: user loops mapped onto the reference structure."""
    id: str
    project_id: str
    sections: List[ArrangementSection] = field(default_factory=list)
    blocks: List[ArrangementBlock] = field(default_factory=list)
    total_bars: int = 0
    bpm: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "sections": [s.to_dict() for s in self.sections],
            "blocks": [b.to_dict() for b in self.blocks],
            "totalBars": self.total_bars,
            "bpm": self.bpm,
        }
