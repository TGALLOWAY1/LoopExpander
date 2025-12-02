"""Call and response detection for identifying lead-lag motif relationships."""
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
from scipy.spatial.distance import cosine

from analysis.motif_detector.motif_detector import MotifInstance, bars_to_seconds
from models.region import Region
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CallResponseConfig:
    """Configuration for call-response detection."""
    min_offset_bars: float = 0.5  # Minimum time offset in bars
    max_offset_bars: float = 4.0  # Maximum time offset in bars
    min_similarity: float = 0.7  # Minimum cosine similarity threshold (0-1)
    preferred_rhythmic_grid: List[float] = None  # Preferred offsets in bars (e.g., [0.5, 1.0, 2.0, 4.0])
    max_responses_per_call: Optional[int] = None  # Limit number of responses per call (None = no limit)
    min_confidence: float = 0.5  # Minimum confidence to include a pair
    
    def __post_init__(self):
        """Initialize default preferred rhythmic grid if not provided."""
        if self.preferred_rhythmic_grid is None:
            # Default to common musical intervals: 0.5, 1, 2, 4 bars
            self.preferred_rhythmic_grid = [0.5, 1.0, 2.0, 4.0]


@dataclass
class CallResponsePair:
    """Represents a call-response relationship between two motifs."""
    id: str
    from_motif_id: str
    to_motif_id: str
    from_stem_role: str
    to_stem_role: str
    from_time: float  # seconds
    to_time: float  # seconds
    time_offset: float  # seconds (to_time - from_time)
    confidence: float  # 0.0 to 1.0
    region_id: Optional[str] = None  # Region where this pair occurs (if applicable)
    
    @property
    def is_inter_stem(self) -> bool:
        """Check if this is an inter-stem call-response (different stems)."""
        return self.from_stem_role != self.to_stem_role
    
    @property
    def is_intra_stem(self) -> bool:
        """Check if this is an intra-stem call-response (same stem)."""
        return self.from_stem_role == self.to_stem_role


def _compute_similarity(features1: np.ndarray, features2: np.ndarray) -> float:
    """
    Compute cosine similarity between two feature vectors.
    
    Args:
        features1: First feature vector
        features2: Second feature vector
    
    Returns:
        Similarity score between 0 and 1 (1 = identical, 0 = orthogonal)
    """
    # Cosine distance is 1 - cosine similarity
    # We want similarity, so convert distance to similarity
    try:
        distance = cosine(features1, features2)
        # Handle NaN or invalid values
        if np.isnan(distance) or distance < 0:
            return 0.0
        # Cosine similarity = 1 - cosine distance
        similarity = 1.0 - distance
        # Clamp to [0, 1]
        return max(0.0, min(1.0, similarity))
    except Exception as e:
        logger.warning(f"Error computing similarity: {e}")
        return 0.0


def _compute_rhythmic_alignment_score(
    offset_bars: float,
    preferred_grid: List[float],
    tolerance_bars: float = 0.1
) -> float:
    """
    Compute how well an offset aligns with preferred rhythmic grid points.
    
    Args:
        offset_bars: Time offset in bars
        preferred_grid: List of preferred offset values in bars
        tolerance_bars: Tolerance for considering an offset "close" to a grid point
    
    Returns:
        Alignment score between 0 and 1 (1 = perfectly aligned, 0 = far from grid)
    """
    if not preferred_grid:
        return 0.5  # Neutral score if no grid specified
    
    # Find closest grid point
    min_distance = min(abs(offset_bars - grid_point) for grid_point in preferred_grid)
    
    # Score based on distance: 1.0 if exactly on grid, decreasing with distance
    if min_distance <= tolerance_bars:
        # Perfect or near-perfect alignment
        return 1.0
    else:
        # Exponential decay with distance
        # Score drops to ~0.5 at 0.5 bars away, ~0.1 at 1 bar away
        score = np.exp(-min_distance / 0.5)
        return max(0.0, min(1.0, score))


def _compute_confidence(
    similarity: float,
    offset_bars: float,
    config: CallResponseConfig
) -> float:
    """
    Compute confidence score for a call-response pair.
    
    Args:
        similarity: Feature similarity score (0-1)
        offset_bars: Time offset in bars
        config: Call-response configuration
    
    Returns:
        Confidence score between 0 and 1
    """
    # Base confidence from similarity
    similarity_weight = 0.7
    rhythmic_weight = 0.3
    
    # Rhythmic alignment score
    rhythmic_score = _compute_rhythmic_alignment_score(
        offset_bars,
        config.preferred_rhythmic_grid
    )
    
    # Weighted combination
    confidence = (similarity_weight * similarity) + (rhythmic_weight * rhythmic_score)
    
    return confidence


def _find_potential_responses(
    call_motif: MotifInstance,
    all_motifs: List[MotifInstance],
    min_offset_seconds: float,
    max_offset_seconds: float,
    bpm: float
) -> List[Tuple[MotifInstance, float]]:
    """
    Find potential response motifs for a given call motif.
    
    Args:
        call_motif: The call motif
        all_motifs: All available motifs
        min_offset_seconds: Minimum time offset in seconds
        max_offset_seconds: Maximum time offset in seconds
        bpm: Beats per minute for bar calculations
    
    Returns:
        List of (response_motif, offset_seconds) tuples
    """
    potential_responses = []
    call_start = call_motif.start_time
    
    for response_motif in all_motifs:
        # Skip self
        if response_motif.id == call_motif.id:
            continue
        
        response_start = response_motif.start_time
        offset_seconds = response_start - call_start
        
        # Check if response occurs within time window
        if min_offset_seconds <= offset_seconds <= max_offset_seconds:
            potential_responses.append((response_motif, offset_seconds))
    
    return potential_responses


def _deduplicate_pairs(pairs: List[CallResponsePair]) -> List[CallResponsePair]:
    """
    Remove duplicate call-response pairs (e.g., reciprocal duplicates).
    
    Args:
        pairs: List of call-response pairs
    
    Returns:
        Deduplicated list of pairs
    """
    seen = set()
    unique_pairs = []
    
    for pair in pairs:
        # Create a canonical key (always use lexicographically smaller ID first)
        key = tuple(sorted([pair.from_motif_id, pair.to_motif_id]))
        
        if key not in seen:
            seen.add(key)
            unique_pairs.append(pair)
        else:
            # If we've seen this pair before, keep the one with higher confidence
            existing_pair = next(p for p in unique_pairs if tuple(sorted([p.from_motif_id, p.to_motif_id])) == key)
            if pair.confidence > existing_pair.confidence:
                unique_pairs.remove(existing_pair)
                unique_pairs.append(pair)
    
    return unique_pairs


def _rank_and_filter_pairs(
    pairs: List[CallResponsePair],
    config: CallResponseConfig
) -> List[CallResponsePair]:
    """
    Rank and filter call-response pairs based on confidence and limits.
    
    Args:
        pairs: List of call-response pairs
        config: Call-response configuration
    
    Returns:
        Filtered and ranked list of pairs
    """
    # Filter by minimum confidence
    filtered = [p for p in pairs if p.confidence >= config.min_confidence]
    
    # Sort by confidence (descending)
    filtered.sort(key=lambda p: p.confidence, reverse=True)
    
    # Limit responses per call if configured
    if config.max_responses_per_call is not None:
        # Group by call motif
        calls_to_responses = {}
        for pair in filtered:
            if pair.from_motif_id not in calls_to_responses:
                calls_to_responses[pair.from_motif_id] = []
            calls_to_responses[pair.from_motif_id].append(pair)
        
        # Keep only top N responses per call
        limited_pairs = []
        for call_id, responses in calls_to_responses.items():
            top_responses = responses[:config.max_responses_per_call]
            limited_pairs.extend(top_responses)
        
        # Re-sort after limiting
        limited_pairs.sort(key=lambda p: p.confidence, reverse=True)
        return limited_pairs
    
    return filtered


def _find_region_for_pair(
    pair: CallResponsePair,
    regions: List[Region]
) -> Optional[str]:
    """
    Find the region ID where a call-response pair occurs.
    
    Args:
        pair: Call-response pair
        regions: List of regions
    
    Returns:
        Region ID if found, None otherwise
    """
    # Use the midpoint between call and response
    midpoint = (pair.from_time + pair.to_time) / 2.0
    
    for region in regions:
        if region.start <= midpoint <= region.end:
            return region.id
    
    return None


def detect_call_response(
    motifs: List[MotifInstance],
    regions: List[Region],
    bpm: float,
    config: Optional[CallResponseConfig] = None
) -> List[CallResponsePair]:
    """
    Detect call-response relationships between motifs.
    
    Args:
        motifs: List of detected motif instances
        regions: List of detected regions
        bpm: Beats per minute for time calculations
        config: Optional configuration (uses defaults if None)
    
    Returns:
        List of detected call-response pairs
    """
    if config is None:
        config = CallResponseConfig()
    
    logger.info(f"Starting call-response detection for {len(motifs)} motifs")
    logger.info(f"Config: min_offset={config.min_offset_bars} bars, "
                f"max_offset={config.max_offset_bars} bars, "
                f"min_similarity={config.min_similarity}")
    
    # Convert bar offsets to seconds
    min_offset_seconds = bars_to_seconds(config.min_offset_bars, bpm)
    max_offset_seconds = bars_to_seconds(config.max_offset_bars, bpm)
    
    pairs = []
    pair_counter = 0
    
    # For each motif as a potential call
    for call_motif in motifs:
        # Skip full_mix as call - prioritize cross-stem relationships
        if call_motif.stem_role == "full_mix":
            continue
        
        # Find potential responses within time window
        potential_responses = _find_potential_responses(
            call_motif,
            motifs,
            min_offset_seconds,
            max_offset_seconds,
            bpm
        )
        
        # Evaluate each potential response
        for response_motif, offset_seconds in potential_responses:
            # Skip self-instance pairs (defensive check)
            if call_motif.id == response_motif.id:
                continue
            
            # Skip full_mix → full_mix pairs
            if call_motif.stem_role == "full_mix" and response_motif.stem_role == "full_mix":
                continue
            
            # Enforce minimum time offset (defensive check - should already be filtered by _find_potential_responses)
            if abs(offset_seconds) < min_offset_seconds:
                continue
            
            # Convert offset to bars for rhythmic alignment (needed for logging and confidence)
            offset_bars = (offset_seconds / 60.0) * bpm / 4.0  # Convert seconds to bars
            
            # Compute similarity
            similarity = _compute_similarity(call_motif.features, response_motif.features)
            
            # Debug logging
            logger.debug(
                "Call/response candidate",
                extra={
                    "from_role": call_motif.stem_role,
                    "to_role": response_motif.stem_role,
                    "time_offset": round(offset_seconds, 3),
                    "offset_bars": round(offset_bars, 3),
                    "similarity": round(similarity, 3),
                },
            )
            
            # Skip if similarity is too low
            if similarity < config.min_similarity:
                continue
            
            # Compute confidence
            confidence = _compute_confidence(similarity, offset_bars, config)
            
            # Skip if confidence is too low
            if confidence < config.min_confidence:
                continue
            
            # Create pair
            pair_id = f"call_response_{pair_counter:04d}"
            pair = CallResponsePair(
                id=pair_id,
                from_motif_id=call_motif.id,
                to_motif_id=response_motif.id,
                from_stem_role=call_motif.stem_role,
                to_stem_role=response_motif.stem_role,
                from_time=call_motif.start_time,
                to_time=response_motif.start_time,
                time_offset=offset_seconds,
                confidence=confidence
            )
            
            # Find associated region
            pair.region_id = _find_region_for_pair(pair, regions)
            
            pairs.append(pair)
            pair_counter += 1
    
    logger.info(f"Found {len(pairs)} potential call-response pairs")
    
    # Deduplicate
    pairs = _deduplicate_pairs(pairs)
    logger.info(f"After deduplication: {len(pairs)} pairs")
    
    # Rank and filter
    pairs = _rank_and_filter_pairs(pairs, config)
    logger.info(f"After filtering: {len(pairs)} call-response pairs")
    
    return pairs

