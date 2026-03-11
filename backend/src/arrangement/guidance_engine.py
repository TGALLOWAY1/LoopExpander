"""Arrangement Guidance Engine (Phase 6B).

Analyzes the arrangement and provides actionable guidance messages:
1. Similar density warning: Adjacent sections with too-similar density
2. Transition cue: Missing transitions between sections
3. Missing role warning: Sections with very few active roles vs neighbors
4. Interaction coherence: Call/response labels with missing layers
5. Section purpose hints: Suggestions for what each section should achieve
"""
import uuid
from typing import List, Optional, Set

from arrangement.models import Arrangement, ArrangementBlock, ArrangementSection
from models.interaction_label import InteractionLabel


class GuidanceMessage:
    """A single guidance message for the arrangement."""

    def __init__(
        self,
        guidance_type: str,
        section_id: str,
        severity: str,
        message: str,
        action_hint: Optional[str] = None,
    ):
        self.id = str(uuid.uuid4())
        self.type = guidance_type
        self.section_id = section_id
        self.severity = severity  # "info", "suggestion", "warning"
        self.message = message
        self.action_hint = action_hint

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "sectionId": self.section_id,
            "severity": self.severity,
            "message": self.message,
            "actionHint": self.action_hint,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GuidanceMessage":
        g = cls(
            guidance_type=data["type"],
            section_id=data["sectionId"],
            severity=data["severity"],
            message=data["message"],
            action_hint=data.get("actionHint"),
        )
        g.id = data.get("id", g.id)
        return g


# Section types that suggest specific purposes
SECTION_PURPOSE_MAP = {
    "intro": "Set the mood and introduce elements gradually",
    "verse": "Establish the main groove with moderate energy",
    "chorus": "Peak energy and full instrumentation",
    "bridge": "Provide contrast — try different density or roles",
    "drop": "Maximum impact — all elements at full energy",
    "breakdown": "Strip back to minimal elements for contrast",
    "build": "Gradually add layers to create anticipation",
    "outro": "Wind down and remove elements gradually",
}

# Minimum role count to avoid "sparse" warning
MIN_ROLES_FOR_FULL_SECTION = 2


def generate_guidance_messages(
    arrangement: Arrangement,
    interaction_labels: Optional[List[InteractionLabel]] = None,
    energy_curve: Optional[dict] = None,
) -> List[GuidanceMessage]:
    """Generate guidance messages for the arrangement.

    Args:
        arrangement: The current arrangement.
        interaction_labels: User-defined interaction labels.
        energy_curve: Energy curve data with barEnergies.

    Returns:
        List of GuidanceMessage objects.
    """
    messages: List[GuidanceMessage] = []

    messages.extend(_check_similar_density(arrangement, energy_curve))
    messages.extend(_check_transition_cues(arrangement))
    messages.extend(_check_missing_roles(arrangement))
    messages.extend(_check_interaction_coherence(arrangement, interaction_labels))
    messages.extend(_generate_section_purpose_hints(arrangement))

    return messages


def _get_section_role_count(
    blocks: List[ArrangementBlock],
    section_id: str,
) -> int:
    """Count distinct active roles in a section."""
    return len({b.role for b in blocks if b.section_id == section_id and b.active})


def _get_section_active_roles(
    blocks: List[ArrangementBlock],
    section_id: str,
) -> Set[str]:
    """Get set of active roles in a section."""
    return {b.role for b in blocks if b.section_id == section_id and b.active}


def _check_similar_density(
    arrangement: Arrangement,
    energy_curve: Optional[dict] = None,
) -> List[GuidanceMessage]:
    """Rule 1: Warn if adjacent sections have very similar density."""
    messages = []
    if len(arrangement.sections) < 2:
        return messages

    bar_energies = []
    if energy_curve:
        bar_energies = energy_curve.get("barEnergies", energy_curve.get("bar_energies", []))

    for i in range(len(arrangement.sections) - 1):
        current = arrangement.sections[i]
        next_sec = arrangement.sections[i + 1]

        curr_roles = _get_section_active_roles(arrangement.blocks, current.id)
        next_roles = _get_section_active_roles(arrangement.blocks, next_sec.id)

        # Check role overlap
        if curr_roles and next_roles and curr_roles == next_roles:
            # Same exact roles in both sections
            # Also check energy if available
            energy_similar = True
            if bar_energies:
                curr_start = int(current.start_bar)
                curr_end = min(int(current.end_bar), len(bar_energies))
                next_start = int(next_sec.start_bar)
                next_end = min(int(next_sec.end_bar), len(bar_energies))

                if curr_end > curr_start and next_end > next_start:
                    curr_avg = sum(bar_energies[curr_start:curr_end]) / (curr_end - curr_start)
                    next_avg = sum(bar_energies[next_start:next_end]) / (next_end - next_start)
                    energy_similar = abs(curr_avg - next_avg) < 0.15

            if energy_similar:
                messages.append(GuidanceMessage(
                    guidance_type="density_warning",
                    section_id=current.id,
                    severity="warning",
                    message=(
                        f"{current.label} and {next_sec.label} use the same roles "
                        f"with similar energy — they may sound too alike"
                    ),
                    action_hint=(
                        f"Try muting a role in one section or adding a layer in the other "
                        f"to create contrast"
                    ),
                ))

    return messages


def _check_transition_cues(
    arrangement: Arrangement,
) -> List[GuidanceMessage]:
    """Rule 2: Suggest fills or silence at section boundaries without transitions."""
    messages = []
    if len(arrangement.sections) < 2:
        return messages

    for i in range(len(arrangement.sections) - 1):
        current = arrangement.sections[i]
        next_sec = arrangement.sections[i + 1]

        # Skip if sections are the same type (less need for transition)
        if current.type == next_sec.type:
            continue

        # Check if there are any blocks with transition-related variation types
        # near the boundary
        boundary_bar = current.end_bar
        has_transition = False
        for block in arrangement.blocks:
            if (block.section_id == current.id
                    and block.end_bar >= boundary_bar - 1
                    and block.variation_type in (
                        "transition_gap", "dropout_pre_lift",
                        "dropout_breakdown", "break",
                    )):
                has_transition = True
                break

        if not has_transition:
            messages.append(GuidanceMessage(
                guidance_type="transition_cue",
                section_id=current.id,
                severity="suggestion",
                message=(
                    f"No transition element before {next_sec.label} "
                    f"(at bar {boundary_bar:.0f})"
                ),
                action_hint=(
                    f"Consider adding a fill, a brief silence, or dropping a layer "
                    f"in the last bar of {current.label} to smooth the transition"
                ),
            ))

    return messages


def _check_missing_roles(
    arrangement: Arrangement,
) -> List[GuidanceMessage]:
    """Rule 3: Warn if a section has very few active roles compared to neighbors."""
    messages = []
    if len(arrangement.sections) < 2:
        return messages

    # Skip intro/outro — they're expected to be sparse
    sparse_ok_types = {"intro", "outro", "breakdown"}

    section_role_counts = [
        _get_section_role_count(arrangement.blocks, s.id)
        for s in arrangement.sections
    ]

    for i, section in enumerate(arrangement.sections):
        if section.type in sparse_ok_types:
            continue

        count = section_role_counts[i]
        if count >= MIN_ROLES_FOR_FULL_SECTION:
            continue

        # Compare to neighbors
        neighbor_counts = []
        if i > 0:
            neighbor_counts.append(section_role_counts[i - 1])
        if i < len(arrangement.sections) - 1:
            neighbor_counts.append(section_role_counts[i + 1])

        if neighbor_counts and count < max(neighbor_counts) - 1:
            messages.append(GuidanceMessage(
                guidance_type="missing_role",
                section_id=section.id,
                severity="warning",
                message=(
                    f"{section.label} has only {count} active role(s), "
                    f"while neighboring sections have up to {max(neighbor_counts)}"
                ),
                action_hint=(
                    f"Consider adding more layers to {section.label} or "
                    f"changing its type to breakdown if sparse is intentional"
                ),
            ))

    return messages


def _check_interaction_coherence(
    arrangement: Arrangement,
    interaction_labels: Optional[List[InteractionLabel]] = None,
) -> List[GuidanceMessage]:
    """Rule 4: Check that call/response labels have matching layers."""
    messages = []
    if not interaction_labels:
        return messages

    cr_labels = [l for l in interaction_labels if l.label in ("call", "response")]
    if not cr_labels:
        return messages

    # Group by section
    sections_with_cr: dict = {}
    for lbl in cr_labels:
        sections_with_cr.setdefault(lbl.section_id, []).append(lbl)

    for section_id, labels in sections_with_cr.items():
        has_call = any(l.label == "call" for l in labels)
        has_response = any(l.label == "response" for l in labels)

        section = next(
            (s for s in arrangement.sections if s.id == section_id), None
        )
        section_label = section.label if section else section_id

        if has_call and not has_response:
            messages.append(GuidanceMessage(
                guidance_type="interaction",
                section_id=section_id,
                severity="warning",
                message=f"{section_label} has call labels but no response labels",
                action_hint="Add response interaction labels or remove the call labels",
            ))
        elif has_response and not has_call:
            messages.append(GuidanceMessage(
                guidance_type="interaction",
                section_id=section_id,
                severity="warning",
                message=f"{section_label} has response labels but no call labels",
                action_hint="Add call interaction labels or remove the response labels",
            ))

        # Check if there are enough roles to support call/response
        active_roles = _get_section_active_roles(arrangement.blocks, section_id)
        if len(active_roles) < 2 and (has_call or has_response):
            messages.append(GuidanceMessage(
                guidance_type="interaction",
                section_id=section_id,
                severity="info",
                message=(
                    f"{section_label} has call/response labels but only "
                    f"{len(active_roles)} role(s) — the pattern may not be audible"
                ),
                action_hint="Add more layers to make the call/response pattern effective",
            ))

    return messages


def _generate_section_purpose_hints(
    arrangement: Arrangement,
) -> List[GuidanceMessage]:
    """Rule 5: Provide purpose hints based on section type and position."""
    messages = []

    for i, section in enumerate(arrangement.sections):
        purpose = SECTION_PURPOSE_MAP.get(section.type)
        if not purpose:
            continue

        # Only generate hints for sections that might not match their purpose
        active_roles = _get_section_active_roles(arrangement.blocks, section.id)
        role_count = len(active_roles)

        # Check mismatches
        if section.type in ("chorus", "drop") and role_count < 2:
            messages.append(GuidanceMessage(
                guidance_type="purpose",
                section_id=section.id,
                severity="suggestion",
                message=(
                    f"{section.label} is marked as {section.type} but has few active roles"
                ),
                action_hint=purpose,
            ))
        elif section.type in ("breakdown",) and role_count > 3:
            messages.append(GuidanceMessage(
                guidance_type="purpose",
                section_id=section.id,
                severity="suggestion",
                message=(
                    f"{section.label} is marked as breakdown but has {role_count} active roles"
                ),
                action_hint=purpose,
            ))
        elif section.type == "intro" and i > 0:
            # Intro not at the start is unusual
            messages.append(GuidanceMessage(
                guidance_type="purpose",
                section_id=section.id,
                severity="info",
                message=f"{section.label} is labeled as intro but is not the first section",
                action_hint="Consider relabeling this section or reviewing the structure",
            ))
        elif section.type == "outro" and i < len(arrangement.sections) - 1:
            messages.append(GuidanceMessage(
                guidance_type="purpose",
                section_id=section.id,
                severity="info",
                message=f"{section.label} is labeled as outro but is not the last section",
                action_hint="Consider relabeling this section or reviewing the structure",
            ))

    return messages
