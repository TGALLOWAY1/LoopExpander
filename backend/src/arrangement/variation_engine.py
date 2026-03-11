"""Variation Suggestion Engine (Phase 6A).

Rules-based suggestions for improving arrangement variety:
1. Mute on repetition: If a role repeats identically for >2 sections, suggest muting it in one
2. Pre-impact dropout: Before high-energy sections, suggest 1-2 bar silence in drums/bass
3. Half-section density: Suggest lighter first half / fuller second half for long sections
4. A/B alternation: If user has multiple stems for same role, suggest ABAB patterning
5. Transition gaps: Suggest brief silence before section changes
"""
import uuid
from typing import List, Dict, Optional, Set

from arrangement.models import Arrangement, ArrangementBlock, ArrangementSection


class VariationSuggestion:
    """A single variation suggestion for the arrangement."""

    def __init__(
        self,
        suggestion_type: str,
        target_block_id: str,
        section_id: str,
        description: str,
        parameters: Optional[dict] = None,
    ):
        self.id = str(uuid.uuid4())
        self.type = suggestion_type
        self.target_block_id = target_block_id
        self.section_id = section_id
        self.description = description
        self.applied = False
        self.dismissed = False
        self.parameters = parameters or {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "targetBlockId": self.target_block_id,
            "sectionId": self.section_id,
            "description": self.description,
            "applied": self.applied,
            "dismissed": self.dismissed,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VariationSuggestion":
        s = cls(
            suggestion_type=data["type"],
            target_block_id=data["targetBlockId"],
            section_id=data["sectionId"],
            description=data["description"],
            parameters=data.get("parameters", {}),
        )
        s.id = data.get("id", s.id)
        s.applied = data.get("applied", False)
        s.dismissed = data.get("dismissed", False)
        return s


# Roles considered "rhythmic foundation" for dropout suggestions
FOUNDATION_ROLES = {"drums", "bass", "percussion"}

# Minimum section length (bars) to suggest half-section density changes
MIN_LONG_SECTION_BARS = 8


def generate_variation_suggestions(
    arrangement: Arrangement,
    user_stem_roles: Optional[Dict[str, int]] = None,
    energy_curve: Optional[dict] = None,
) -> List[VariationSuggestion]:
    """Generate variation suggestions for the given arrangement.

    Args:
        arrangement: The current arrangement with sections and blocks.
        user_stem_roles: Dict mapping role -> count of stems the user has for that role.
        energy_curve: Energy curve data with barEnergies and transitionMarkers.

    Returns:
        List of VariationSuggestion objects.
    """
    suggestions: List[VariationSuggestion] = []

    suggestions.extend(_suggest_mute_on_repetition(arrangement))
    suggestions.extend(_suggest_pre_impact_dropout(arrangement, energy_curve))
    suggestions.extend(_suggest_half_section_density(arrangement))
    suggestions.extend(_suggest_ab_alternation(arrangement, user_stem_roles))
    suggestions.extend(_suggest_transition_gaps(arrangement))

    return suggestions


def _get_blocks_for_section(
    blocks: List[ArrangementBlock],
    section_id: str,
) -> List[ArrangementBlock]:
    """Get active blocks belonging to a section."""
    return [b for b in blocks if b.section_id == section_id and b.active]


def _get_section_roles(
    blocks: List[ArrangementBlock],
    section_id: str,
) -> Set[str]:
    """Get the set of active roles in a section."""
    return {b.role for b in blocks if b.section_id == section_id and b.active}


def _suggest_mute_on_repetition(
    arrangement: Arrangement,
) -> List[VariationSuggestion]:
    """Rule 1: If a role repeats identically for >2 consecutive sections, suggest muting."""
    suggestions = []
    if len(arrangement.sections) < 3:
        return suggestions

    # For each role, track consecutive sections with that role active
    all_roles = {b.role for b in arrangement.blocks if b.active}

    for role in all_roles:
        consecutive_sections: List[ArrangementSection] = []

        for section in arrangement.sections:
            section_blocks = [
                b for b in arrangement.blocks
                if b.section_id == section.id and b.role == role and b.active
            ]
            if section_blocks:
                consecutive_sections.append(section)
            else:
                # Check if we had a long consecutive run
                if len(consecutive_sections) > 2:
                    _add_mute_suggestions(suggestions, arrangement, role, consecutive_sections)
                consecutive_sections = []

        # Check final run
        if len(consecutive_sections) > 2:
            _add_mute_suggestions(suggestions, arrangement, role, consecutive_sections)

    return suggestions


def _add_mute_suggestions(
    suggestions: List[VariationSuggestion],
    arrangement: Arrangement,
    role: str,
    sections: List[ArrangementSection],
) -> None:
    """Add mute suggestions for the middle section(s) of a consecutive run."""
    # Suggest muting the role in the middle section of the run
    mid_idx = len(sections) // 2
    mid_section = sections[mid_idx]

    # Find a block to target
    target_blocks = [
        b for b in arrangement.blocks
        if b.section_id == mid_section.id and b.role == role and b.active
    ]
    if not target_blocks:
        return

    suggestions.append(VariationSuggestion(
        suggestion_type="mute_layer",
        target_block_id=target_blocks[0].id,
        section_id=mid_section.id,
        description=(
            f"Mute {role} in {mid_section.label} "
            f"(bars {mid_section.start_bar:.0f}-{mid_section.end_bar:.0f}) "
            f"to add variety — it plays for {len(sections)} consecutive sections"
        ),
        parameters={
            "role": role,
            "consecutiveSections": len(sections),
            "affectedBlockIds": [b.id for b in target_blocks],
        },
    ))


def _suggest_pre_impact_dropout(
    arrangement: Arrangement,
    energy_curve: Optional[dict] = None,
) -> List[VariationSuggestion]:
    """Rule 2: Before high-energy sections, suggest 1-2 bar silence in drums/bass."""
    suggestions = []
    if len(arrangement.sections) < 2:
        return suggestions

    # Use energy data if available, otherwise use section types as heuristic
    high_energy_types = {"chorus", "drop", "high_energy"}

    bar_energies = []
    if energy_curve:
        bar_energies = energy_curve.get("barEnergies", energy_curve.get("bar_energies", []))

    for i, section in enumerate(arrangement.sections):
        if i == 0:
            continue

        is_high_energy = section.type in high_energy_types

        # Also check energy curve if available
        if bar_energies and not is_high_energy:
            start_idx = int(section.start_bar)
            if start_idx < len(bar_energies):
                section_energies = bar_energies[start_idx:min(int(section.end_bar), len(bar_energies))]
                if section_energies and (sum(section_energies) / len(section_energies)) > 0.7:
                    is_high_energy = True

        if not is_high_energy:
            continue

        prev_section = arrangement.sections[i - 1]
        # Find foundation role blocks in the last 2 bars of the previous section
        dropout_start = max(prev_section.start_bar, prev_section.end_bar - 2)

        for role in FOUNDATION_ROLES:
            target_blocks = [
                b for b in arrangement.blocks
                if (b.section_id == prev_section.id
                    and b.role == role
                    and b.active
                    and b.end_bar > dropout_start)
            ]
            if not target_blocks:
                continue

            suggestions.append(VariationSuggestion(
                suggestion_type="dropout",
                target_block_id=target_blocks[0].id,
                section_id=prev_section.id,
                description=(
                    f"Drop {role} in the last 2 bars of {prev_section.label} "
                    f"(before {section.label}) for impact"
                ),
                parameters={
                    "role": role,
                    "dropoutStartBar": dropout_start,
                    "dropoutEndBar": prev_section.end_bar,
                    "impactSectionId": section.id,
                    "affectedBlockIds": [b.id for b in target_blocks],
                },
            ))

    return suggestions


def _suggest_half_section_density(
    arrangement: Arrangement,
) -> List[VariationSuggestion]:
    """Rule 3: For long sections, suggest lighter first half / fuller second half."""
    suggestions = []

    for section in arrangement.sections:
        section_length = section.end_bar - section.start_bar
        if section_length < MIN_LONG_SECTION_BARS:
            continue

        section_blocks = _get_blocks_for_section(arrangement.blocks, section.id)
        if not section_blocks:
            continue

        # Count roles
        roles = {b.role for b in section_blocks}
        if len(roles) < 2:
            continue

        half_bar = section.start_bar + section_length / 2

        # Find non-essential roles to mute in the first half
        # (keep drums and bass, suggest muting melodic/texture elements)
        non_essential = [r for r in roles if r not in FOUNDATION_ROLES]
        if not non_essential:
            continue

        target_role = non_essential[0]
        first_half_blocks = [
            b for b in section_blocks
            if b.role == target_role and b.start_bar < half_bar
        ]
        if not first_half_blocks:
            continue

        suggestions.append(VariationSuggestion(
            suggestion_type="density_shift",
            target_block_id=first_half_blocks[0].id,
            section_id=section.id,
            description=(
                f"Mute {target_role} in the first half of {section.label} "
                f"(bars {section.start_bar:.0f}-{half_bar:.0f}) "
                f"for a build-up effect"
            ),
            parameters={
                "role": target_role,
                "muteStartBar": section.start_bar,
                "muteEndBar": half_bar,
                "sectionLength": section_length,
                "affectedBlockIds": [b.id for b in first_half_blocks],
            },
        ))

    return suggestions


def _suggest_ab_alternation(
    arrangement: Arrangement,
    user_stem_roles: Optional[Dict[str, int]] = None,
) -> List[VariationSuggestion]:
    """Rule 4: If user has multiple stems for same role, suggest ABAB patterning."""
    suggestions = []
    if not user_stem_roles:
        return suggestions

    # Find roles with multiple stems
    multi_stem_roles = {role for role, count in user_stem_roles.items() if count >= 2}
    if not multi_stem_roles:
        return suggestions

    for role in multi_stem_roles:
        # Find sections where this role is present and uses the same stem
        role_sections = []
        for section in arrangement.sections:
            blocks = [
                b for b in arrangement.blocks
                if b.section_id == section.id and b.role == role and b.active
            ]
            if blocks:
                role_sections.append((section, blocks))

        if len(role_sections) < 2:
            continue

        # Check if all sections use the same stem
        stem_ids = set()
        for _, blocks in role_sections:
            for b in blocks:
                stem_ids.add(b.stem_id)

        if len(stem_ids) > 1:
            # Already using multiple stems
            continue

        # Suggest alternating for even-indexed sections
        for idx, (section, blocks) in enumerate(role_sections):
            if idx % 2 == 1:  # Suggest switching the second, fourth, etc.
                suggestions.append(VariationSuggestion(
                    suggestion_type="alternate",
                    target_block_id=blocks[0].id,
                    section_id=section.id,
                    description=(
                        f"Use alternate {role} stem in {section.label} "
                        f"for ABAB variation"
                    ),
                    parameters={
                        "role": role,
                        "currentStemId": blocks[0].stem_id,
                        "affectedBlockIds": [b.id for b in blocks],
                    },
                ))

    return suggestions


def _suggest_transition_gaps(
    arrangement: Arrangement,
) -> List[VariationSuggestion]:
    """Rule 5: Suggest brief silence before section changes."""
    suggestions = []
    if len(arrangement.sections) < 2:
        return suggestions

    for i in range(len(arrangement.sections) - 1):
        current = arrangement.sections[i]
        next_section = arrangement.sections[i + 1]

        # Only suggest if sections are different types (transitions matter more)
        if current.type == next_section.type:
            continue

        section_length = current.end_bar - current.start_bar
        if section_length < 4:
            continue

        # Suggest a 1-bar gap at the end of the current section
        gap_start = current.end_bar - 1

        # Find blocks that span the last bar
        gap_blocks = [
            b for b in arrangement.blocks
            if (b.section_id == current.id
                and b.active
                and b.end_bar > gap_start
                and b.role in FOUNDATION_ROLES)
        ]
        if not gap_blocks:
            continue

        suggestions.append(VariationSuggestion(
            suggestion_type="gap",
            target_block_id=gap_blocks[0].id,
            section_id=current.id,
            description=(
                f"Add a 1-bar silence at the end of {current.label} "
                f"(bar {gap_start:.0f}) before {next_section.label} transition"
            ),
            parameters={
                "gapStartBar": gap_start,
                "gapEndBar": current.end_bar,
                "nextSectionId": next_section.id,
                "affectedBlockIds": [b.id for b in gap_blocks],
            },
        ))

    return suggestions


def apply_suggestion(
    arrangement: Arrangement,
    suggestion: VariationSuggestion,
) -> bool:
    """Apply a suggestion to the arrangement by modifying affected blocks.

    Returns True if the suggestion was successfully applied.
    """
    if suggestion.applied or suggestion.dismissed:
        return False

    affected_ids = suggestion.parameters.get("affectedBlockIds", [])
    if not affected_ids:
        affected_ids = [suggestion.target_block_id]

    if suggestion.type == "mute_layer":
        for block in arrangement.blocks:
            if block.id in affected_ids:
                block.active = False
                block.variation_type = "muted_suggestion"
        suggestion.applied = True
        return True

    elif suggestion.type == "dropout":
        dropout_start = suggestion.parameters.get("dropoutStartBar")
        for block in arrangement.blocks:
            if block.id in affected_ids and dropout_start is not None:
                if block.end_bar > dropout_start:
                    block.active = False
                    block.variation_type = "dropout_suggestion"
        suggestion.applied = True
        return True

    elif suggestion.type == "density_shift":
        mute_end = suggestion.parameters.get("muteEndBar")
        for block in arrangement.blocks:
            if block.id in affected_ids and mute_end is not None:
                if block.start_bar < mute_end:
                    block.active = False
                    block.variation_type = "density_shift"
        suggestion.applied = True
        return True

    elif suggestion.type == "gap":
        gap_start = suggestion.parameters.get("gapStartBar")
        for block in arrangement.blocks:
            if block.id in affected_ids and gap_start is not None:
                if block.end_bar > gap_start:
                    block.active = False
                    block.variation_type = "transition_gap"
        suggestion.applied = True
        return True

    elif suggestion.type == "alternate":
        # Mark for alternation — actual stem swap requires user loop data
        for block in arrangement.blocks:
            if block.id in affected_ids:
                block.variation_type = "alternate_suggested"
        suggestion.applied = True
        return True

    return False
