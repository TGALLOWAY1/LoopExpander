"""Data models for user loop/stem ingestion."""
from dataclasses import dataclass, field
from typing import Optional, List
import uuid

# Valid role assignments for user loop stems
VALID_ROLES = [
    "drums", "bass", "chord", "lead", "vocal",
    "fx", "percussion", "texture",
]


@dataclass
class UserLoopStem:
    """Represents a single user-uploaded loop stem."""
    id: str
    filename: str
    role: str  # one of VALID_ROLES
    loop_length_bars: int
    start_bar: float  # trim start (within the loop)
    end_bar: float  # trim end (within the loop)
    audio_path: str
    duration_seconds: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.role not in VALID_ROLES:
            raise ValueError(
                f"Invalid role '{self.role}'. Must be one of: {VALID_ROLES}"
            )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "role": self.role,
            "loopLengthBars": self.loop_length_bars,
            "startBar": self.start_bar,
            "endBar": self.end_bar,
            "audioPath": self.audio_path,
            "durationSeconds": self.duration_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserLoopStem":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            filename=data["filename"],
            role=data["role"],
            loop_length_bars=data["loopLengthBars"],
            start_bar=data.get("startBar", 0.0),
            end_bar=data.get("endBar", float(data["loopLengthBars"])),
            audio_path=data.get("audioPath", ""),
            duration_seconds=data.get("durationSeconds", 0.0),
        )


@dataclass
class UserLoopBundle:
    """A collection of user loop stems for a project."""
    id: str
    project_id: str  # reference ID this is associated with
    stems: List[UserLoopStem] = field(default_factory=list)
    bpm: float = 0.0
    detected_bpm: float = 0.0
    bpm_ratio: float = 1.0  # ratio for time-stretching to match reference

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def compute_bpm_ratio(self, reference_bpm: float) -> float:
        """Compute the time-stretch ratio needed to match reference BPM.

        Returns:
            Ratio to multiply loop duration by. >1 means slow down, <1 means speed up.
        """
        if self.bpm <= 0 or reference_bpm <= 0:
            return 1.0
        self.bpm_ratio = reference_bpm / self.bpm
        return self.bpm_ratio

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "stems": [s.to_dict() for s in self.stems],
            "bpm": self.bpm,
            "detectedBpm": self.detected_bpm,
            "bpmRatio": self.bpm_ratio,
        }
