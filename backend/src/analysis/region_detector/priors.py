"""Probabilistic priors for song structure boundaries."""
from typing import List

from utils.logger import get_logger

logger = get_logger(__name__)


def estimate_initial_boundaries(duration_seconds: float, bpm: float) -> List[float]:
    """
    Estimate initial boundary times based on typical song structure priors.
    
    Uses heuristics based on common song structure patterns:
    - Intro: first 5-10% of track
    - First high-energy/chorus: ~25-35%
    - Breakdown/bridge: 60-75%
    - Outro: last 10-15%
    
    Args:
        duration_seconds: Total duration of the track in seconds
        bpm: Beats per minute (used for validation, not directly in this heuristic)
    
    Returns:
        List of boundary times in seconds (sorted, excluding 0 and duration)
    """
    if duration_seconds <= 0:
        raise ValueError(f"Duration must be positive, got {duration_seconds}")
    
    logger.info(f"Estimating initial boundaries for {duration_seconds:.2f}s track at {bpm:.1f} BPM")
    
    boundaries = []
    
    # Intro boundary: 5-10% of track (use 7.5% as middle)
    intro_boundary = duration_seconds * 0.075
    boundaries.append(intro_boundary)
    
    # First high-energy section (chorus/drop): 25-35% (use 30%)
    first_chorus = duration_seconds * 0.30
    boundaries.append(first_chorus)
    
    # Mid-point transition: 45-55% (use 50%)
    midpoint = duration_seconds * 0.50
    boundaries.append(midpoint)
    
    # Breakdown/bridge: 60-75% (use 67.5%)
    breakdown = duration_seconds * 0.675
    boundaries.append(breakdown)
    
    # Build-up before final section: 80-85% (use 82.5%)
    build_up = duration_seconds * 0.825
    boundaries.append(build_up)
    
    # Sort and remove duplicates
    boundaries = sorted(set(boundaries))
    
    # Filter out boundaries too close to start or end
    min_boundary = duration_seconds * 0.05  # At least 5% from start
    max_boundary = duration_seconds * 0.95  # At least 5% from end
    
    boundaries = [b for b in boundaries if min_boundary <= b <= max_boundary]
    
    logger.info(f"Estimated {len(boundaries)} prior boundaries: {[f'{b:.2f}s' for b in boundaries]}")
    
    return boundaries

