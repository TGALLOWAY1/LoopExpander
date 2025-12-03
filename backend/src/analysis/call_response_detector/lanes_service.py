"""Service for building call/response lane data structures."""
from typing import List, Dict
from collections import defaultdict

from models.region import Region
from analysis.call_response_detector.call_response_detector import CallResponsePair
from analysis.subregions.service import seconds_to_bars
from analysis.call_response_detector.lanes_models import (
    StemCallResponseEvent,
    StemCallResponseLane,
    CallResponseByStemResponse,
    StemCategory
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Valid stem categories (exclude full_mix)
VALID_STEM_CATEGORIES: List[StemCategory] = ["drums", "bass", "instruments", "vocals"]


def _is_valid_stem(stem_role: str) -> bool:
    """Check if stem role is valid for lane visualization (excludes full_mix)."""
    return stem_role in VALID_STEM_CATEGORIES


def _find_region_for_time(time_seconds: float, regions: List[Region]) -> str:
    """
    Find the region that contains a given time.
    
    Args:
        time_seconds: Time in seconds
        regions: List of regions
    
    Returns:
        Region ID, or first region if none found (fallback)
    """
    for region in regions:
        if region.start <= time_seconds < region.end:
            return region.id
    # Fallback to first region if time is outside all regions
    return regions[0].id if regions else "unknown"


def _calculate_motif_duration_bars(
    start_time: float,
    end_time: float,
    bpm: float
) -> float:
    """
    Calculate motif duration in bars.
    
    Args:
        start_time: Start time in seconds
        end_time: End time in seconds
        bpm: Beats per minute
    
    Returns:
        Duration in bars
    """
    duration_seconds = end_time - start_time
    return seconds_to_bars(duration_seconds, bpm)


def build_call_response_lanes(
    reference_id: str,
    regions: List[Region],
    call_response_pairs: List[CallResponsePair],
    bpm: float,
    motif_instances: List = None  # Optional: for getting motif end times
) -> CallResponseByStemResponse:
    """
    Build call/response lane data structure from existing call/response pairs.
    
    This function maps existing call/response analysis into per-stem lane events.
    Only uses stem-level call/response info (ignores full-mix motifs).
    
    The Region Map's 5-layer view is stem-centric; we intentionally ignore full-mix motifs here.
    
    Args:
        reference_id: ID of the reference bundle
        regions: List of detected regions (in timeline order)
        call_response_pairs: List of detected call/response pairs (should be stem-only if use_full_mix=False)
        bpm: Beats per minute for time-to-bar conversion
        motif_instances: Optional list of motif instances (for getting end times)
    
    Returns:
        CallResponseByStemResponse with lanes organized by stem
    """
    logger.info(f"Building call/response lanes for reference {reference_id}")
    
    # Create a map of motif ID to instance (if provided) for getting end times
    motif_map = {}
    if motif_instances:
        for inst in motif_instances:
            motif_map[inst.id] = inst
    
    # Group pairs by a group_id (for now, use pair ID as group_id)
    # TODO: Improve grouping logic to link related calls/responses
    # For intra-stem pairs, both call and response are in same group
    # For inter-stem pairs, we might want separate groups or linked groups
    
    # Collect events by stem
    events_by_stem: Dict[StemCategory, List[StemCallResponseEvent]] = defaultdict(list)
    
    # Process each call/response pair
    for pair in call_response_pairs:
        # Only process pairs involving valid stems (exclude full_mix)
        if not _is_valid_stem(pair.from_stem_role) and not _is_valid_stem(pair.to_stem_role):
            continue
        
        # Determine region for the pair
        region_id = pair.region_id
        if not region_id:
            # Fallback: find region based on call time
            region_id = _find_region_for_time(pair.from_time, regions)
        
        # Create group_id from pair ID (for now)
        # TODO: Improve grouping to link related calls/responses across pairs
        group_id = f"group_{pair.id}"
        
        # Process call event (from_stem_role)
        if _is_valid_stem(pair.from_stem_role):
            # Get motif end time if available, otherwise estimate
            call_end_time = pair.from_time + 2.0  # Default 2 seconds if not available
            if pair.from_motif_id in motif_map:
                inst = motif_map[pair.from_motif_id]
                call_end_time = inst.end_time
            
            # Convert to bars
            call_start_bar = seconds_to_bars(pair.from_time, bpm)
            call_duration_bars = _calculate_motif_duration_bars(pair.from_time, call_end_time, bpm)
            call_end_bar = call_start_bar + call_duration_bars
            
            call_event = StemCallResponseEvent(
                id=f"{pair.id}_call",
                region_id=region_id,
                stem=pair.from_stem_role,  # type: ignore
                start_bar=call_start_bar,
                end_bar=call_end_bar,
                role="call",
                group_id=group_id,
                label=None,  # TODO: Add label from motif group if available
                intensity=None  # TODO: Calculate intensity from audio features
            )
            events_by_stem[pair.from_stem_role].append(call_event)  # type: ignore
        
        # Process response event (to_stem_role)
        if _is_valid_stem(pair.to_stem_role):
            # Get motif end time if available, otherwise estimate
            response_end_time = pair.to_time + 2.0  # Default 2 seconds if not available
            if pair.to_motif_id in motif_map:
                inst = motif_map[pair.to_motif_id]
                response_end_time = inst.end_time
            
            # Convert to bars
            response_start_bar = seconds_to_bars(pair.to_time, bpm)
            response_duration_bars = _calculate_motif_duration_bars(pair.to_time, response_end_time, bpm)
            response_end_bar = response_start_bar + response_duration_bars
            
            response_event = StemCallResponseEvent(
                id=f"{pair.id}_response",
                region_id=region_id,
                stem=pair.to_stem_role,  # type: ignore
                start_bar=response_start_bar,
                end_bar=response_end_bar,
                role="response",
                group_id=group_id,
                label=None,  # TODO: Add label from motif group if available
                intensity=None  # TODO: Calculate intensity from audio features
            )
            events_by_stem[pair.to_stem_role].append(response_event)  # type: ignore
    
    # Build lanes for each stem (in order)
    lanes: List[StemCallResponseLane] = []
    for stem in VALID_STEM_CATEGORIES:
        events = events_by_stem[stem]
        if events:  # Only include lanes with events
            # Sort events by start_bar
            events.sort(key=lambda e: e.start_bar)
            lanes.append(StemCallResponseLane(
                stem=stem,
                events=events
            ))
    
    # Get region IDs in timeline order
    sorted_regions = sorted(regions, key=lambda r: r.start)
    region_ids = [r.id for r in sorted_regions]
    
    logger.info(f"Built {len(lanes)} lanes with {sum(len(lane.events) for lane in lanes)} total events")
    
    return CallResponseByStemResponse(
        reference_id=reference_id,
        regions=region_ids,
        lanes=lanes
    )

