"""Guide Content System (Phase 7A).

Generates lightweight structural event markers for the arrangement:
- Fill markers: Where fills/transitions should go
- Impact markers: Where impacts/drops should hit
- Build markers: Where energy should build
- Transition cue markers: Visual indicators at section transitions
- Response needed prompts: Based on interaction labels, where missing elements should go
"""
import uuid
from typing import List, Optional

from arrangement.models import Arrangement, ArrangementBlock, ArrangementSection
from models.interaction_label import InteractionLabel


class GuideMarker:
    """A structural guide marker on the arrangement timeline."""

    def __init__(
        self,
        marker_type: str,
        bar_position: float,
        section_id: str,
        label: str,
        description: str,
    ):
        self.id = str(uuid.uuid4())
        self.type = marker_type  # "fill", "impact", "build", "transition", "response_needed"
        self.bar_position = bar_position
        self.section_id = section_id
        self.label = label
        self.description = description

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "barPosition": self.bar_position,
            "sectionId": self.section_id,
            "label": self.label,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GuideMarker":
        m = cls(
            marker_type=data["type"],
            bar_position=data["barPosition"],
            section_id=data["sectionId"],
            label=data["label"],
            description=data["description"],
        )
        m.id = data.get("id", m.id)
        return m


# Section types that typically precede high-energy moments
PRE_IMPACT_TYPES = {"build", "breakdown", "bridge"}

# Section types that are high-energy
IMPACT_TYPES = {"drop", "chorus", "high_energy"}

# Minimum section length to suggest a fill at the end
MIN_FILL_SECTION_BARS = 4


def generate_guide_markers(
    arrangement: Arrangement,
    interaction_labels: Optional[List[InteractionLabel]] = None,
    energy_curve: Optional[dict] = None,
) -> List[GuideMarker]:
    """Generate guide markers for the arrangement.

    Args:
        arrangement: The current arrangement.
        interaction_labels: User-defined interaction labels.
        energy_curve: Energy curve data with transitionMarkers.

    Returns:
        List of GuideMarker objects.
    """
    markers: List[GuideMarker] = []

    markers.extend(_generate_transition_markers(arrangement))
    markers.extend(_generate_fill_markers(arrangement))
    markers.extend(_generate_impact_markers(arrangement, energy_curve))
    markers.extend(_generate_build_markers(arrangement))
    markers.extend(_generate_response_needed_markers(arrangement, interaction_labels))

    return markers


def _generate_transition_markers(
    arrangement: Arrangement,
) -> List[GuideMarker]:
    """Place transition cue markers at section boundaries."""
    markers = []
    if len(arrangement.sections) < 2:
        return markers

    for i in range(len(arrangement.sections) - 1):
        current = arrangement.sections[i]
        next_sec = arrangement.sections[i + 1]

        # Skip transitions between same-type sections
        if current.type == next_sec.type:
            continue

        markers.append(GuideMarker(
            marker_type="transition",
            bar_position=current.end_bar,
            section_id=current.id,
            label="Transition",
            description=(
                f"Transition from {current.label} to {next_sec.label} — "
                f"consider a fill, riser, or brief silence"
            ),
        ))

    return markers


def _generate_fill_markers(
    arrangement: Arrangement,
) -> List[GuideMarker]:
    """Suggest fill positions at the end of sections before transitions."""
    markers = []
    if len(arrangement.sections) < 2:
        return markers

    for i in range(len(arrangement.sections) - 1):
        current = arrangement.sections[i]
        next_sec = arrangement.sections[i + 1]

        section_length = current.end_bar - current.start_bar
        if section_length < MIN_FILL_SECTION_BARS:
            continue

        # Suggest fill 1 bar before section end
        fill_bar = current.end_bar - 1

        # Only suggest if transitioning to a different section type
        if current.type != next_sec.type:
            markers.append(GuideMarker(
                marker_type="fill",
                bar_position=fill_bar,
                section_id=current.id,
                label="Fill",
                description=(
                    f"Fill needed at bar {fill_bar:.0f} to transition "
                    f"from {current.label} into {next_sec.label}"
                ),
            ))

    return markers


def _generate_impact_markers(
    arrangement: Arrangement,
    energy_curve: Optional[dict] = None,
) -> List[GuideMarker]:
    """Place impact markers at high-energy section starts."""
    markers = []

    # Use energy transition markers if available
    if energy_curve:
        transition_markers = energy_curve.get(
            "transitionMarkers",
            energy_curve.get("transition_markers", []),
        )
        for tm in transition_markers:
            marker_bar = tm.get("bar", 0)
            marker_type = tm.get("type", "")
            if marker_type in ("lift", "drop"):
                # Find the section this belongs to
                section = _find_section_at_bar(arrangement.sections, marker_bar)
                if section:
                    markers.append(GuideMarker(
                        marker_type="impact",
                        bar_position=marker_bar,
                        section_id=section.id,
                        label="Impact",
                        description=f"Energy {marker_type} at bar {marker_bar:.0f} in {section.label}",
                    ))

    # Also mark starts of high-energy sections
    for i, section in enumerate(arrangement.sections):
        if section.type in IMPACT_TYPES and i > 0:
            prev = arrangement.sections[i - 1]
            if prev.type in PRE_IMPACT_TYPES or prev.type not in IMPACT_TYPES:
                # Avoid duplicating if we already have a marker nearby
                has_nearby = any(
                    m.type == "impact"
                    and abs(m.bar_position - section.start_bar) < 2
                    for m in markers
                )
                if not has_nearby:
                    markers.append(GuideMarker(
                        marker_type="impact",
                        bar_position=section.start_bar,
                        section_id=section.id,
                        label="Impact",
                        description=f"Impact point at start of {section.label} (bar {section.start_bar:.0f})",
                    ))

    return markers


def _generate_build_markers(
    arrangement: Arrangement,
) -> List[GuideMarker]:
    """Place build markers in sections typed as 'build'."""
    markers = []

    for section in arrangement.sections:
        if section.type == "build":
            markers.append(GuideMarker(
                marker_type="build",
                bar_position=section.start_bar,
                section_id=section.id,
                label="Build starts",
                description=(
                    f"Build section begins at bar {section.start_bar:.0f} — "
                    f"gradually add layers toward bar {section.end_bar:.0f}"
                ),
            ))

    return markers


def _generate_response_needed_markers(
    arrangement: Arrangement,
    interaction_labels: Optional[List[InteractionLabel]] = None,
) -> List[GuideMarker]:
    """Suggest where missing call/response elements should go."""
    markers = []
    if not interaction_labels:
        return markers

    # Find call labels without nearby response labels and vice versa
    for label in interaction_labels:
        if label.label != "call":
            continue

        # Check if there's a response label in the same section nearby
        has_response = any(
            l.label == "response"
            and l.section_id == label.section_id
            for l in interaction_labels
        )

        if not has_response:
            section = next(
                (s for s in arrangement.sections if s.id == label.section_id),
                None,
            )
            section_label = section.label if section else "section"
            markers.append(GuideMarker(
                marker_type="response_needed",
                bar_position=label.end_bar,
                section_id=label.section_id,
                label="Response needed",
                description=(
                    f"Call at bars {label.start_bar:.0f}-{label.end_bar:.0f} "
                    f"in {section_label} has no matching response"
                ),
            ))

    return markers


def _find_section_at_bar(
    sections: List[ArrangementSection],
    bar: float,
) -> Optional[ArrangementSection]:
    """Find the section that contains a given bar position."""
    for section in sections:
        if section.start_bar <= bar < section.end_bar:
            return section
    return None
