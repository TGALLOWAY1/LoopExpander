"""Region detection using novelty curves and structural priors."""
from typing import List, Tuple, Dict
import numpy as np
import librosa
from scipy.signal import find_peaks

from models.region import Region
from models.reference_bundle import ReferenceBundle
from .features import compute_novelty_curve, compute_rms_envelope
from .priors import estimate_initial_boundaries
from config import MIN_BOUNDARY_GAP_SEC, MIN_REGION_DURATION_SEC
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


def _deduplicate_boundaries(boundaries: List[float], min_separation: float = None) -> List[float]:
    """
    Remove boundaries that are too close together.
    
    Args:
        boundaries: List of boundary times (sorted)
        min_separation: Minimum separation in seconds (uses config if None)
    
    Returns:
        Deduplicated list of boundaries
    """
    if not boundaries:
        return []
    
    if min_separation is None:
        min_separation = MIN_BOUNDARY_GAP_SEC
    
    boundaries = sorted(boundaries)
    cleaned = []
    
    for b in boundaries:
        if not cleaned:
            cleaned.append(b)
        elif b - cleaned[-1] >= min_separation:
            cleaned.append(b)
        else:
            # Too close; skip this boundary
            logger.debug(f"Dropping boundary {b:.2f}s (too close to {cleaned[-1]:.2f}s)")
    
    return cleaned


def enforce_min_region_duration(regions: List[Region], min_duration: float) -> List[Region]:
    """
    Merge regions that are shorter than the minimum duration.
    
    Args:
        regions: List of Region objects
        min_duration: Minimum region duration in seconds
    
    Returns:
        List of merged regions
    """
    if not regions:
        return []
    
    merged = []
    i = 0
    
    while i < len(regions):
        current = regions[i]
        
        # Check if current region is too short
        if current.duration < min_duration:
            # Try to merge with next region if available
            if i + 1 < len(regions):
                next_region = regions[i + 1]
                # Merge current into next by extending next's start
                merged_region = Region(
                    id=next_region.id,
                    name=next_region.name,
                    type=next_region.type,
                    start=current.start,
                    end=next_region.end,
                    motifs=current.motifs + next_region.motifs,
                    fills=current.fills + next_region.fills,
                    callResponse=current.callResponse + next_region.callResponse
                )
                merged.append(merged_region)
                i += 2  # Skip both regions
                logger.debug(f"Merged region {current.id} ({current.duration:.1f}s) into {next_region.id}")
            else:
                # Last region is too short, merge with previous if available
                if merged:
                    prev = merged[-1]
                    merged_region = Region(
                        id=prev.id,
                        name=prev.name,
                        type=prev.type,
                        start=prev.start,
                        end=current.end,
                        motifs=prev.motifs + current.motifs,
                        fills=prev.fills + current.fills,
                        callResponse=prev.callResponse + current.callResponse
                    )
                    merged[-1] = merged_region
                    logger.debug(f"Merged region {current.id} ({current.duration:.1f}s) into previous {prev.id}")
                else:
                    # Only one region and it's too short - keep it anyway
                    merged.append(current)
                i += 1
        else:
            merged.append(current)
            i += 1
    
    # Final pass: ensure no region is still below minimum
    final_merged = []
    for i, region in enumerate(merged):
        if region.duration < min_duration and i < len(merged) - 1:
            # Merge with next
            next_region = merged[i + 1]
            merged_region = Region(
                id=next_region.id,
                name=next_region.name,
                type=next_region.type,
                start=region.start,
                end=next_region.end,
                motifs=region.motifs + next_region.motifs,
                fills=region.fills + next_region.fills,
                callResponse=region.callResponse + next_region.callResponse
            )
            final_merged.append(merged_region)
            # Skip next region
            merged = merged[:i+1] + merged[i+2:]
            break
        else:
            final_merged.append(region)
    
    if len(final_merged) < len(merged):
        # Recursively check again
        return enforce_min_region_duration(final_merged, min_duration)
    
    return final_merged


def compute_region_stats(
    regions: List[Region],
    rms: np.ndarray,
    times: np.ndarray,
    track_duration: float,
) -> List[Dict]:
    """
    Compute energy statistics for each region.
    
    Args:
        regions: List of Region objects
        rms: RMS envelope array
        times: Time array corresponding to RMS frames
        track_duration: Total track duration in seconds
    
    Returns:
        List of dictionaries with region statistics
    """
    stats = []
    
    for region in regions:
        start, end = region.start, region.end
        
        # Get frame indices within region
        idx = np.where((times >= start) & (times < end))[0]
        
        if len(idx) == 0:
            # Fallback: use nearest frame
            center_time = (start + end) / 2.0
            nearest = np.argmin(np.abs(times - center_time))
            idx = np.array([nearest])
        
        region_rms = rms[idx]
        mean_rms = float(region_rms.mean())
        
        n = len(region_rms)
        if n >= 3:
            third = max(1, n // 3)
            start_rms = float(region_rms[:third].mean())
            end_rms = float(region_rms[-third:].mean())
        else:
            start_rms = end_rms = mean_rms
        
        energy_slope = end_rms - start_rms
        
        center_time = 0.5 * (start + end)
        relative_pos = center_time / max(track_duration, 1e-6)
        
        stats.append({
            "mean_rms": mean_rms,
            "start_rms": start_rms,
            "end_rms": end_rms,
            "energy_slope": energy_slope,
            "relative_pos": relative_pos,
            "duration": end - start,
        })
    
    # Compute global stats for z-score normalization
    all_mean_rms = np.array([s["mean_rms"] for s in stats])
    global_mean = float(all_mean_rms.mean())
    global_std = float(all_mean_rms.std() or 1e-6)
    
    for s in stats:
        s["energy_z"] = (s["mean_rms"] - global_mean) / global_std
    
    return stats


def assign_region_labels(regions: List[Region], stats: List[Dict]) -> None:
    """
    Assign region labels based on energy statistics and position.
    
    Args:
        regions: List of Region objects (modified in place)
        stats: List of region statistics dictionaries
    """
    if len(regions) != len(stats):
        raise ValueError(f"Regions and stats must have same length: {len(regions)} vs {len(stats)}")
    
    if len(regions) == 0:
        return
    
    # Safety checks for very few regions
    if len(regions) == 1:
        # Single region: label as Intro or Drop based on energy
        if stats[0]["energy_z"] > 0:
            regions[0].name = "Drop"
            regions[0].type = "high_energy"
        else:
            regions[0].name = "Intro"
            regions[0].type = "low_energy"
        return
    
    if len(regions) == 2:
        # Two regions: Intro + Drop or Intro + Outro
        if stats[1]["energy_z"] > stats[0]["energy_z"]:
            regions[0].name = "Intro"
            regions[0].type = "low_energy"
            regions[1].name = "Drop"
            regions[1].type = "high_energy"
        else:
            regions[0].name = "Intro"
            regions[0].type = "low_energy"
            regions[1].name = "Outro"
            regions[1].type = "low_energy"
        return
    
    if len(regions) == 3:
        # Three regions: Intro, Drop, Outro
        regions[0].name = "Intro"
        regions[0].type = "low_energy"
        
        # Find highest energy region (middle one)
        energy_zs = [s["energy_z"] for s in stats]
        max_idx = np.argmax(energy_zs)
        if max_idx == 0:
            max_idx = 1
        elif max_idx == 2:
            max_idx = 1
        
        regions[1].name = "Drop"
        regions[1].type = "high_energy"
        regions[2].name = "Outro"
        regions[2].type = "low_energy"
        return
    
    # Normal case: 4+ regions
    
    # 1. Intro & Outro (by position)
    regions[0].name = "Intro"
    regions[0].type = "low_energy"
    
    regions[-1].name = "Outro"
    regions[-1].type = "low_energy"
    
    # 2. Drop / High-Energy (highest energy, prefer middle position)
    energy_zs = [s["energy_z"] for s in stats]
    max_energy_idx = np.argmax(energy_zs)
    
    # If multiple regions have same max energy, pick one closest to middle
    max_energy = energy_zs[max_energy_idx]
    candidates = [i for i, z in enumerate(energy_zs) if abs(z - max_energy) < 0.1]
    
    if len(candidates) > 1:
        # Pick candidate closest to middle (0.5 relative position)
        best_idx = min(candidates, key=lambda i: abs(stats[i]["relative_pos"] - 0.5))
    else:
        best_idx = max_energy_idx
    
    # Don't assign Drop to first or last region
    if best_idx > 0 and best_idx < len(regions) - 1:
        regions[best_idx].name = "Drop"
        regions[best_idx].type = "high_energy"
    
    # 3. Build vs Breakdown vs Verse (remaining regions)
    for i in range(1, len(regions) - 1):
        # Skip if already labeled as Drop
        if regions[i].name == "Drop":
            continue
        
        s = stats[i]
        energy_z = s["energy_z"]
        energy_slope = s["energy_slope"]
        relative_pos = s["relative_pos"]
        
        if energy_slope > 0 and energy_z >= -0.5:
            # Rising energy: Build
            regions[i].name = "Build"
            regions[i].type = "build"
        elif energy_slope < 0 and energy_z <= 0:
            # Falling energy, low overall: Breakdown
            regions[i].name = "Breakdown"
            regions[i].type = "low_energy"
        else:
            # Default: Verse or Post-Drop based on position
            if relative_pos < 0.5:
                regions[i].name = "Verse"
                regions[i].type = "medium_energy"
            else:
                regions[i].name = "Post-Drop"
                regions[i].type = "medium_energy"


def detect_regions(bundle: ReferenceBundle) -> List[Region]:
    """
    Detect regions in a reference bundle using novelty curves and structural priors.
    
    Algorithm:
    1. Compute novelty curve from full mix
    2. Find peaks in novelty curve
    3. Get prior boundaries based on typical song structure
    4. Snap priors to nearest novelty peaks
    5. Include high-strength peaks not near priors
    6. Deduplicate boundaries with minimum gap
    7. Generate regions between boundaries
    8. Enforce minimum region duration
    9. Compute region energy statistics
    10. Assign labels based on energy and position
    11. Log diagnostic information
    
    Args:
        bundle: ReferenceBundle with loaded audio files
    
    Returns:
        List of Region instances
    """
    logger.info(f"Starting region detection for bundle: {bundle}")
    logger.info(f"Using thresholds: MIN_BOUNDARY_GAP_SEC={MIN_BOUNDARY_GAP_SEC}, MIN_REGION_DURATION_SEC={MIN_REGION_DURATION_SEC}")
    
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
    all_boundaries = set(snapped_boundaries)
    for peak in peak_times:
        min_distance = min([abs(peak - prior) for prior in prior_boundaries], default=float('inf'))
        if min_distance > 5.0:
            peak_frame = int(peak * sr / hop_length)
            if peak_frame < len(novelty) and novelty[peak_frame] > 0.5:
                all_boundaries.add(peak)
                logger.debug(f"Added high-strength peak at {peak:.2f}s (far from priors)")
    
    # Step 6: Deduplicate boundaries with minimum gap
    boundaries = _deduplicate_boundaries(list(all_boundaries))
    boundaries = sorted(boundaries)
    
    # Ensure we have boundaries at start and end
    if not boundaries or boundaries[0] > 1.0:
        boundaries.insert(0, 0.0)
    if not boundaries or boundaries[-1] < duration - 1.0:
        boundaries.append(duration)
    
    logger.info(f"Final boundaries after de-duplication ({len(boundaries)}): {[f'{b:.2f}s' for b in boundaries]}")
    
    # Step 7: Generate regions
    region_tuples = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        region_tuples.append((start, end))
    
    logger.info(f"Generated {len(region_tuples)} initial regions")
    
    # Step 8: Create temporary Region objects for duration enforcement
    temp_regions = []
    for i, (start, end) in enumerate(region_tuples):
        region_id = f"region_{i+1:02d}"
        temp_region = Region(
            id=region_id,
            name="Temp",
            type="temp",
            start=start,
            end=end,
            motifs=[],
            fills=[],
            callResponse=[]
        )
        temp_regions.append(temp_region)
    
    # Step 9: Enforce minimum region duration
    regions = enforce_min_region_duration(temp_regions, MIN_REGION_DURATION_SEC)
    logger.info(f"After enforcing min duration ({MIN_REGION_DURATION_SEC}s): {len(regions)} regions")
    
    # Step 10: Compute RMS and time arrays for energy analysis
    rms = compute_rms_envelope(audio_mono, frame_length=2048, hop_length=hop_length)
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
    
    # Step 11: Compute region statistics
    region_stats = compute_region_stats(regions, rms, times, duration)
    
    # Step 12: Assign labels
    assign_region_labels(regions, region_stats)
    
    # Step 13: Re-assign IDs after merging
    for i, region in enumerate(regions):
        region.id = f"region_{i+1:02d}"
    
    # Step 14: Diagnostic logging
    logger.info("=" * 80)
    logger.info("Region Detection Summary:")
    logger.info(f"Total regions: {len(regions)}")
    logger.info("-" * 80)
    logger.info(f"{'Index':<6} {'Start-End':<15} {'Duration':<10} {'Energy Z':<10} {'Slope':<10} {'Label':<15} {'Type':<15}")
    logger.info("-" * 80)
    
    for i, (region, stats) in enumerate(zip(regions, region_stats)):
        logger.info(
            f"region[{i:02d}]: {region.start:6.1f}-{region.end:6.1f}s "
            f"(dur={stats['duration']:5.1f}s), "
            f"energy_z={stats['energy_z']:6.2f}, "
            f"slope={stats['energy_slope']:7.4f} -> "
            f"name={region.name:<12}, type={region.type:<15}"
        )
    
    logger.info("=" * 80)
    logger.info(f"Region detection complete: {len(regions)} regions detected")
    
    return regions
