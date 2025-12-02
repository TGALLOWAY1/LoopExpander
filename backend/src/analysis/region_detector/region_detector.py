"""Region detection using novelty curves and structural priors."""
from typing import List, Tuple
import numpy as np
from scipy.signal import find_peaks

from models.region import Region
from models.reference_bundle import ReferenceBundle
from .features import compute_novelty_curve, compute_rms_envelope
from .priors import estimate_initial_boundaries
from utils.logger import get_logger

logger = get_logger(__name__)


def _find_novelty_peaks(
    novelty: np.ndarray,
    sr: int,
    hop_length: int = 512,
    min_distance_frames: int = 50,
    height_threshold: float = 0.3
) -> List[float]:
    """
    Find peaks in the novelty curve and convert to time in seconds.
    
    Args:
        novelty: Novelty curve (1D array)
        sr: Sample rate
        hop_length: Hop length used for feature extraction
        min_distance_frames: Minimum distance between peaks (in frames)
        height_threshold: Minimum peak height (normalized, 0-1)
    
    Returns:
        List of peak times in seconds
    """
    # Find peaks using scipy
    peaks, properties = find_peaks(
        novelty,
        distance=min_distance_frames,
        height=height_threshold
    )
    
    # Convert frame indices to time
    peak_times = peaks * hop_length / sr
    
    logger.info(f"Found {len(peak_times)} novelty peaks above threshold {height_threshold}")
    
    return peak_times.tolist()


def _snap_prior_to_nearest_peak(prior_time: float, peak_times: List[float], window_seconds: float = 5.0) -> float:
    """
    Snap a prior boundary to the nearest novelty peak within a window.
    
    Args:
        prior_time: Prior boundary time in seconds
        peak_times: List of novelty peak times
        window_seconds: Maximum distance to snap (in seconds)
    
    Returns:
        Snapped time (prior_time if no peak within window)
    """
    if not peak_times:
        return prior_time
    
    # Find peaks within window
    nearby_peaks = [p for p in peak_times if abs(p - prior_time) <= window_seconds]
    
    if not nearby_peaks:
        return prior_time
    
    # Return the nearest peak
    nearest = min(nearby_peaks, key=lambda p: abs(p - prior_time))
    return nearest


def _deduplicate_boundaries(boundaries: List[float], min_separation: float = 2.0) -> List[float]:
    """
    Remove boundaries that are too close together.
    
    Args:
        boundaries: List of boundary times (sorted)
        min_separation: Minimum separation in seconds
    
    Returns:
        Deduplicated list of boundaries
    """
    if not boundaries:
        return []
    
    boundaries = sorted(boundaries)
    deduplicated = [boundaries[0]]
    
    for b in boundaries[1:]:
        if b - deduplicated[-1] >= min_separation:
            deduplicated.append(b)
    
    return deduplicated


def _assign_region_type(
    regions: List[Tuple[float, float]],
    full_mix_samples: np.ndarray,
    sr: int
) -> List[Tuple[str, str]]:
    """
    Assign region types based on position and energy.
    
    Args:
        regions: List of (start, end) tuples in seconds
        full_mix_samples: Full mix audio samples
        sr: Sample rate
    
    Returns:
        List of region types corresponding to regions
    """
    if not regions:
        return []
    
    # Compute RMS envelope for energy analysis
    rms = compute_rms_envelope(full_mix_samples)
    hop_length = 512
    frame_times = np.arange(len(rms)) * hop_length / sr
    
    region_types = []
    duration = len(full_mix_samples) / sr
    
    for i, (start, end) in enumerate(regions):
        # Get RMS values for this region
        region_mask = (frame_times >= start) & (frame_times < end)
        if np.any(region_mask):
            region_rms = np.mean(rms[region_mask])
        else:
            region_rms = 0.0
        
        # Assign type based on position and energy
        relative_start = start / duration
        
        if i == 0:
            # First region: Intro
            region_type = "low_energy"
            region_name = "Intro"
        elif i == len(regions) - 1:
            # Last region: Outro
            region_type = "low_energy"
            region_name = "Outro"
        elif relative_start < 0.4:
            # Early regions: Build
            region_type = "build"
            region_name = "Build"
        elif region_rms > np.percentile(rms, 75):
            # High energy: Drop/Chorus
            region_type = "high_energy"
            region_name = "Drop"
        else:
            # Default: Build
            region_type = "build"
            region_name = "Build"
        
        region_types.append((region_type, region_name))
    
    return region_types


def detect_regions(bundle: ReferenceBundle) -> List[Region]:
    """
    Detect regions in a reference bundle using novelty curves and structural priors.
    
    Algorithm:
    1. Compute novelty curve from full mix
    2. Find peaks in novelty curve
    3. Get prior boundaries based on typical song structure
    4. Snap priors to nearest novelty peaks
    5. Include high-strength peaks not near priors
    6. Deduplicate and sort boundaries
    7. Generate regions between boundaries
    8. Assign types and names based on position and energy
    
    Args:
        bundle: ReferenceBundle with loaded audio files
    
    Returns:
        List of Region instances
    """
    logger.info(f"Starting region detection for bundle: {bundle}")
    
    # Get full mix audio
    full_mix = bundle.full_mix
    audio = full_mix.samples
    sr = full_mix.sr
    duration = full_mix.duration
    
    # Ensure mono for processing
    if audio.ndim > 1:
        audio_mono = np.mean(audio, axis=0) if audio.ndim == 2 else audio[0]
    else:
        audio_mono = audio
    
    logger.info(f"Processing audio: {duration:.2f}s, {sr} Hz, shape: {audio_mono.shape}")
    
    # Step 1: Compute novelty curve
    hop_length = 512
    novelty = compute_novelty_curve(audio_mono, sr=sr, hop_length=hop_length)
    logger.info(f"Computed novelty curve: {len(novelty)} frames")
    
    # Step 2: Find novelty peaks
    peak_times = _find_novelty_peaks(novelty, sr=sr, hop_length=hop_length)
    logger.info(f"Found {len(peak_times)} novelty peaks")
    
    # Step 3: Get prior boundaries
    prior_boundaries = estimate_initial_boundaries(duration, bundle.bpm)
    logger.info(f"Estimated {len(prior_boundaries)} prior boundaries")
    
    # Step 4: Snap priors to nearest peaks
    snapped_boundaries = []
    for prior in prior_boundaries:
        snapped = _snap_prior_to_nearest_peak(prior, peak_times, window_seconds=5.0)
        snapped_boundaries.append(snapped)
        if snapped != prior:
            logger.debug(f"Snapped prior {prior:.2f}s to peak {snapped:.2f}s")
    
    # Step 5: Include high-strength peaks not near priors
    # Find peaks that are far from any prior
    all_boundaries = set(snapped_boundaries)
    for peak in peak_times:
        # Check if peak is far from all priors
        min_distance = min([abs(peak - prior) for prior in prior_boundaries], default=float('inf'))
        if min_distance > 5.0:  # More than 5 seconds from any prior
            # Check if it's a strong peak
            peak_frame = int(peak * sr / hop_length)
            if peak_frame < len(novelty) and novelty[peak_frame] > 0.5:
                all_boundaries.add(peak)
                logger.debug(f"Added high-strength peak at {peak:.2f}s (far from priors)")
    
    # Step 6: Deduplicate and sort
    boundaries = _deduplicate_boundaries(list(all_boundaries), min_separation=2.0)
    boundaries = sorted(boundaries)
    
    # Ensure we have boundaries at start and end
    if not boundaries or boundaries[0] > 1.0:
        boundaries.insert(0, 0.0)
    if not boundaries or boundaries[-1] < duration - 1.0:
        boundaries.append(duration)
    
    logger.info(f"Final boundaries ({len(boundaries)}): {[f'{b:.2f}s' for b in boundaries]}")
    
    # Step 7: Generate regions
    regions = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        regions.append((start, end))
    
    logger.info(f"Generated {len(regions)} regions")
    
    # Step 8: Assign types and names
    region_types = _assign_region_type(regions, full_mix.samples, sr)
    
    # Step 9: Create Region objects
    region_objects = []
    for i, ((start, end), (region_type, region_name)) in enumerate(zip(regions, region_types)):
        region_id = f"region_{i+1:02d}"
        region = Region(
            id=region_id,
            name=region_name,
            type=region_type,
            start=start,
            end=end,
            motifs=[],
            fills=[],
            callResponse=[]
        )
        region_objects.append(region)
        logger.debug(f"Created {region}")
    
    logger.info(f"Region detection complete: {len(region_objects)} regions detected")
    
    return region_objects

