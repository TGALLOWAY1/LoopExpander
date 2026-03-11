"""Data models for interaction labels (call-and-response / A-B labeling)."""
from dataclasses import dataclass, field
from typing import Optional, List
import uuid


@dataclass
class InteractionLabel:
    """Represents a labeled interaction region on the timeline.

    Used for marking call-and-response patterns, A/B alternation,
    fills, sustains, breaks, and transitions within sections.
    """
    id: str
    section_id: str  # which section this belongs to
    start_bar: float
    end_bar: float
    label: str  # "A", "B", "call", "response", "fill", "sustain", "break", "transition", "ABAB"
    color: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.end_bar <= self.start_bar:
            raise ValueError(
                f"end_bar ({self.end_bar}) must be > start_bar ({self.start_bar})"
            )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sectionId": self.section_id,
            "startBar": self.start_bar,
            "endBar": self.end_bar,
            "label": self.label,
            "color": self.color,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InteractionLabel":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            section_id=data.get("sectionId", ""),
            start_bar=data["startBar"],
            end_bar=data["endBar"],
            label=data["label"],
            color=data.get("color"),
            notes=data.get("notes"),
        )


def duplicate_labels_to_section(
    labels: List[InteractionLabel],
    source_section_start_bar: float,
    target_section_id: str,
    target_section_start_bar: float,
    target_section_end_bar: float,
) -> List[InteractionLabel]:
    """Duplicate a set of interaction labels to a target section.

    Adjusts bar positions relative to the target section start.
    Clips labels that would extend beyond the target section.

    Args:
        labels: Source labels to duplicate.
        source_section_start_bar: Start bar of the source section.
        target_section_id: ID of the target section.
        target_section_start_bar: Start bar of the target section.
        target_section_end_bar: End bar of the target section.

    Returns:
        List of new InteractionLabel instances positioned in the target section.
    """
    duplicated = []
    for lbl in labels:
        offset = lbl.start_bar - source_section_start_bar
        new_start = target_section_start_bar + offset
        new_end = target_section_start_bar + (lbl.end_bar - source_section_start_bar)

        # Clip to target section boundaries
        if new_start >= target_section_end_bar:
            continue
        new_end = min(new_end, target_section_end_bar)
        if new_end <= new_start:
            continue

        duplicated.append(InteractionLabel(
            id=str(uuid.uuid4()),
            section_id=target_section_id,
            start_bar=new_start,
            end_bar=new_end,
            label=lbl.label,
            color=lbl.color,
            notes=lbl.notes,
        ))

    return duplicated
