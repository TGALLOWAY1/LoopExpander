"""Core mapping engine: arranges user loops across the approved reference structure.

Algorithm:
1. For each section in the approved structure:
   a. Determine section length in bars
   b. For each role lane (drums, bass, melodic, vocal, etc.):
      - Check reference role activity: is this role active in this section?
      - If active: repeat user's corresponding loop stem to fill section length
      - If inactive: leave silent (or apply dropout)
   c. Apply interaction labels:
      - If section has A/B labels, alternate between user stems accordingly
      - If "call/response" labeled, map call-stem to call bars, response-stem to response bars
   d. Preserve contrast moments from reference energy curve:
      - Breakdowns -> remove drums/bass
      - Drops -> restore full activity
      - Builds -> gradual layer addition
"""
import uuid
import math
from typing import List, Dict, Optional, Tuple

from arrangement.models import Arrangement, ArrangementSection, ArrangementBlock
from models.region import Region
from models.role_activity import RoleActivityTimeline, ActivitySegment
from models.interaction_label import InteractionLabel
from models.user_loop import UserLoopBundle, UserLoopStem

# Map broad role activity roles to user loop stem roles
# role_activity uses: drums, bass, melodic, vocal
# user loops use: drums, bass, chord, lead, vocal, fx, percussion, texture
ROLE_ACTIVITY_TO_STEM_ROLES: Dict[str, List[str]] = {
    "drums": ["drums", "percussion"],
    "bass": ["bass"],
    "melodic": ["chord", "lead", "texture"],
    "vocal": ["vocal"],
}

# Reverse map: stem role -> activity role
STEM_ROLE_TO_ACTIVITY_ROLE: Dict[str, str] = {}
for activity_role, stem_roles in ROLE_ACTIVITY_TO_STEM_ROLES.items():
    for sr in stem_roles:
        STEM_ROLE_TO_ACTIVITY_ROLE[sr] = activity_role

# Roles that should be removed during breakdowns
BREAKDOWN_REMOVE_ROLES = {"drums", "bass", "percussion"}

# Roles that should be removed during drops (pre-drop silence effect)
DROP_REMOVE_ROLES = {"drums", "bass", "percussion"}


def _is_role_active_in_range(
    timelines: List[RoleActivityTimeline],
    activity_role: str,
    start_bar: float,
    end_bar: float,
) -> bool:
    """Check if a broad role is active within a bar range.

    Returns True if any active segment overlaps the range. Defaults to True
    if no timeline data exists for the role.
    """
    for timeline in timelines:
        if timeline.role != activity_role:
            continue
        for seg in timeline.segments:
            if seg.active and seg.start_bar < end_bar and seg.end_bar > start_bar:
                return True
        # Timeline exists but no active segments overlap -> inactive
        return False
    # No timeline for this role -> default to active
    return True


def _get_active_ranges_for_role(
    timelines: List[RoleActivityTimeline],
    activity_role: str,
    section_start: float,
    section_end: float,
) -> List[Tuple[float, float]]:
    """Get list of (start_bar, end_bar) ranges where a role is active within a section."""
    # Minimum overlap in bars to count as active (avoids floating-point edge cases)
    MIN_OVERLAP_BARS = 0.1

    for timeline in timelines:
        if timeline.role != activity_role:
            continue
        ranges = []
        for seg in timeline.segments:
            if seg.active and seg.start_bar < section_end and seg.end_bar > section_start:
                range_start = max(seg.start_bar, section_start)
                range_end = min(seg.end_bar, section_end)
                if range_end - range_start >= MIN_OVERLAP_BARS:
                    ranges.append((range_start, range_end))
        return ranges if ranges else []
    # No timeline -> entire section is active
    return [(section_start, section_end)]


def _get_interaction_labels_for_section(
    labels: List[InteractionLabel],
    section_id: str,
) -> List[InteractionLabel]:
    """Get interaction labels belonging to a specific section."""
    return [lbl for lbl in labels if lbl.section_id == section_id]


def _find_stems_for_role(
    bundle: UserLoopBundle,
    stem_role: str,
) -> List[UserLoopStem]:
    """Find all user loop stems matching a given role."""
    return [s for s in bundle.stems if s.role == stem_role]


def _fill_range_with_loop(
    stem: UserLoopStem,
    range_start: float,
    range_end: float,
    section_id: str,
    role: str,
    variation_type: Optional[str] = None,
) -> List[ArrangementBlock]:
    """Generate arrangement blocks by repeating a loop stem to fill a bar range.

    The loop material is repeated as many times as needed. Partial repetitions
    at the end use only the needed portion of the loop.
    """
    blocks = []
    loop_length = stem.end_bar - stem.start_bar
    if loop_length <= 0:
        return blocks

    cursor = range_start
    while cursor < range_end:
        block_end = min(cursor + loop_length, range_end)
        source_end = stem.start_bar + (block_end - cursor)

        blocks.append(ArrangementBlock(
            id=str(uuid.uuid4()),
            stem_id=stem.id,
            role=role,
            section_id=section_id,
            start_bar=cursor,
            end_bar=block_end,
            active=True,
            variation_type=variation_type,
            source_loop_start=stem.start_bar,
            source_loop_end=source_end,
        ))
        cursor = block_end

    return blocks


def _apply_transition_dropouts(
    blocks: List[ArrangementBlock],
    transition_markers: List[dict],
    sections: List[ArrangementSection],
) -> List[ArrangementBlock]:
    """Apply contrast-preserving dropouts based on energy transition markers.

    - Breakdowns: mute drums/bass in the affected section
    - Drops: create 1-2 bar silence before high-energy restores
    """
    if not transition_markers:
        return blocks

    for marker in transition_markers:
        marker_bar = marker.get("bar", 0)
        marker_type = marker.get("type", "")

        if marker_type == "breakdown":
            # Find section containing this marker
            for section in sections:
                if section.start_bar <= marker_bar < section.end_bar:
                    for block in blocks:
                        if (
                            block.section_id == section.id
                            and block.role in BREAKDOWN_REMOVE_ROLES
                            and block.start_bar >= marker_bar
                        ):
                            block.active = False
                            block.variation_type = "dropout_breakdown"
                    break

        elif marker_type == "lift":
            # Before a lift (energy increase), add a 2-bar gap for impact
            gap_start = max(0, marker_bar - 2)
            gap_end = marker_bar
            for block in blocks:
                if (
                    block.role in DROP_REMOVE_ROLES
                    and block.start_bar < gap_end
                    and block.end_bar > gap_start
                ):
                    # Only mute the portion within the gap
                    if block.start_bar >= gap_start and block.end_bar <= gap_end:
                        block.active = False
                        block.variation_type = "dropout_pre_lift"

    return blocks


def _apply_interaction_labels_to_blocks(
    blocks: List[ArrangementBlock],
    labels: List[InteractionLabel],
    bundle: UserLoopBundle,
    section_id: str,
) -> List[ArrangementBlock]:
    """Modify blocks based on interaction labels (A/B alternation, call/response).

    - A/B labels: if user has multiple stems for the same role, alternate
    - call/response: map primary stem to call bars, secondary to response bars
    - break: mute all blocks in the break range
    """
    if not labels:
        return blocks

    # Group labels by type
    break_labels = [l for l in labels if l.label == "break"]
    ab_labels = [l for l in labels if l.label in ("A", "B", "ABAB")]
    cr_labels = [l for l in labels if l.label in ("call", "response")]

    # Apply breaks: mute blocks in break ranges
    for brk in break_labels:
        for block in blocks:
            if (
                block.section_id == section_id
                and block.start_bar < brk.end_bar
                and block.end_bar > brk.start_bar
            ):
                block.active = False
                block.variation_type = "break"

    # Apply A/B alternation: use different stems for A vs B regions
    if ab_labels:
        for block in blocks:
            if block.section_id != section_id:
                continue
            stems_for_role = _find_stems_for_role(bundle, block.role)
            if len(stems_for_role) < 2:
                continue

            for lbl in ab_labels:
                if block.start_bar >= lbl.start_bar and block.end_bar <= lbl.end_bar:
                    if lbl.label == "B":
                        # Switch to secondary stem
                        secondary = stems_for_role[1]
                        block.stem_id = secondary.id
                        block.variation_type = "alternate_B"
                        block.source_loop_start = secondary.start_bar
                        block.source_loop_end = min(
                            secondary.end_bar,
                            secondary.start_bar + (block.end_bar - block.start_bar),
                        )

    # Apply call/response: mute non-matching role in call/response ranges
    if cr_labels:
        for lbl in cr_labels:
            for block in blocks:
                if block.section_id != section_id:
                    continue
                if block.start_bar >= lbl.start_bar and block.end_bar <= lbl.end_bar:
                    if lbl.label == "call":
                        block.variation_type = "call"
                    elif lbl.label == "response":
                        block.variation_type = "response"

    return blocks


def generate_arrangement(
    project_id: str,
    regions: List[Region],
    role_timelines: List[RoleActivityTimeline],
    interaction_labels: List[InteractionLabel],
    user_loops: UserLoopBundle,
    energy_curve: Optional[dict] = None,
    bpm: float = 120.0,
) -> Arrangement:
    """Generate an arrangement by mapping user loops onto the reference structure.

    Args:
        project_id: Project/reference ID.
        regions: Approved reference structure sections.
        role_timelines: Role activity timelines from analysis.
        interaction_labels: User-created interaction labels.
        user_loops: User's uploaded loop stems.
        energy_curve: Energy curve data with barEnergies and transitionMarkers.
        bpm: Reference BPM.

    Returns:
        A complete Arrangement with sections and blocks.
    """
    arrangement_id = str(uuid.uuid4())

    # Build arrangement sections from regions
    seconds_per_bar = (60.0 / bpm) * 4.0 if bpm > 0 else 2.0
    sections: List[ArrangementSection] = []
    for region in regions:
        # Round to 2 decimal places to avoid floating-point edge cases
        start_bar = round(region.start / seconds_per_bar, 2)
        end_bar = round(region.end / seconds_per_bar, 2)

        # Use label or provisional_label or region type
        label = region.label or region.provisional_label or region.type or "unknown"

        sections.append(ArrangementSection(
            id=region.id,
            name=region.name,
            label=label,
            start_bar=start_bar,
            end_bar=end_bar,
            type=region.type or "unknown",
        ))

    total_bars = max((s.end_bar for s in sections), default=0)
    total_bars = int(math.ceil(total_bars))

    # Collect all unique stem roles the user has provided
    available_roles = set(s.role for s in user_loops.stems)

    # Generate blocks: for each section, for each available stem role
    all_blocks: List[ArrangementBlock] = []

    for section in sections:
        section_labels = _get_interaction_labels_for_section(
            interaction_labels, section.id
        )

        for stem_role in available_roles:
            # Skip FX stems from auto-mapping (they're special)
            if stem_role == "fx":
                continue

            # Determine the corresponding activity role
            activity_role = STEM_ROLE_TO_ACTIVITY_ROLE.get(stem_role)

            # Check if this role should be active in this section
            if activity_role:
                active_ranges = _get_active_ranges_for_role(
                    role_timelines,
                    activity_role,
                    section.start_bar,
                    section.end_bar,
                )
            else:
                # Unknown mapping -> default to full section
                active_ranges = [(section.start_bar, section.end_bar)]

            if not active_ranges:
                continue

            # Find the primary stem for this role
            stems = _find_stems_for_role(user_loops, stem_role)
            if not stems:
                continue

            primary_stem = stems[0]

            # Fill each active range with the loop
            for range_start, range_end in active_ranges:
                blocks = _fill_range_with_loop(
                    stem=primary_stem,
                    range_start=range_start,
                    range_end=range_end,
                    section_id=section.id,
                    role=stem_role,
                )
                all_blocks.extend(blocks)

        # Apply interaction labels to blocks in this section
        all_blocks = _apply_interaction_labels_to_blocks(
            all_blocks, section_labels, user_loops, section.id
        )

    # Apply energy-based transition dropouts
    transition_markers = []
    if energy_curve and "transitionMarkers" in energy_curve:
        transition_markers = energy_curve["transitionMarkers"]
    elif energy_curve and "transition_markers" in energy_curve:
        transition_markers = energy_curve["transition_markers"]

    all_blocks = _apply_transition_dropouts(all_blocks, transition_markers, sections)

    return Arrangement(
        id=arrangement_id,
        project_id=project_id,
        sections=sections,
        blocks=all_blocks,
        total_bars=total_bars,
        bpm=bpm,
    )
