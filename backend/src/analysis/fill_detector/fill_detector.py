"""Fill detection using transient density near region boundaries."""
from dataclasses import dataclass
from typing import List, Optional, Dict
import numpy as np
import librosa

from models.reference_bundle import ReferenceBundle
from models.region import Region
from analysis.region_detector.features import compute_transient_density
from analysis.motif_detector.motif_detector import bars_to_seconds
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FillConfig:
    """Configuration for fill detection."""
    pre_boundary_window_bars: float = 2.0  # Window before boundary to analyze (in bars)
    transient_density_threshold_multiplier: float = 1.5  # Multiplier above region average
    min_transient_density: float = 0.3  # Minimum absolute transient density
    hop_length: int = 512  # Hop length for feature extraction
    window_size: int = 2048  # Window size for transient density computation


@dataclass
class Fill:
    """Represents a fill (transient-rich region near a boundary)."""
    id: str
    time: float  # seconds - time position of the fill
    stem_roles: List[str]  # Stems where transients are concentrated
    region_id: str  # The downstream region (region that starts after the boundary)
    confidence: float  # 0.0 to 1.0 - confidence in the fill detection
    fill_type: Optional[str] = None  # e.g., "drum_fill", "bass_slide", "vocal_adlib"
    
    def __repr__(self) -> str:
        """String representation of Fill."""
        type_str = f", type={self.fill_type}" if self.fill_type else ""
        return (
            f"Fill(id={self.id}, time={self.time:.2f}s, "
            f"stems={self.stem_roles}, region_id={self.region_id}, "
            f"confidence={self.confidence:.2f}{type_str})"
        )


def _ensure_mono(audio: np.ndarray) -> np.ndarray:
    """
    Convert multi-channel audio to mono by averaging channels.
    
    Args:
        audio: Audio array (1D for mono, 2D for multi-channel)
    
    Returns:
        Mono audio array (1D)
    """
    if audio.ndim == 1:
        return audio
    elif audio.ndim == 2:
        return np.mean(audio, axis=0)
    else:
        raise ValueError(f"Unexpected audio shape: {audio.shape}. Expected 1D or 2D array.")


def _compute_region_average_transient_density(
    transient_density: np.ndarray,
    times: np.ndarray,
    region_start: float,
    region_end: float
) -> float:
    """
    Compute average transient density within a region.
    
    Args:
        transient_density: Frame-wise transient density values
        times: Time array corresponding to density frames
        region_start: Start time of region in seconds
        region_end: End time of region in seconds
    
    Returns:
        Average transient density in the region
    """
    # Find frames within region
    mask = (times >= region_start) & (times <= region_end)
    if np.sum(mask) == 0:
        return 0.0
    
    region_density = transient_density[mask]
    return np.mean(region_density)


def _detect_fills_at_boundary(
    boundary_time: float,
    downstream_region: Region,
    stems: Dict[str, np.ndarray],
    stem_roles: List[str],
    sr: int,
    bpm: float,
    config: FillConfig
) -> Optional[Fill]:
    """
    Detect fills near a specific boundary.
    
    Args:
        boundary_time: Time of the boundary in seconds
        downstream_region: The region that starts after the boundary
        stems: Dictionary of stem_role -> audio samples
        stem_roles: List of stem roles to analyze
        sr: Sample rate
        bpm: Beats per minute
        config: Fill detection configuration
    
    Returns:
        Fill object if detected, None otherwise
    """
    # Convert window from bars to seconds
    window_seconds = bars_to_seconds(config.pre_boundary_window_bars, bpm)
    
    # Define analysis window: [boundary_time - window_seconds, boundary_time]
    window_start = max(0.0, boundary_time - window_seconds)
    window_end = boundary_time
    
    if window_end <= window_start:
        return None
    
    # Analyze each stem
    stem_transient_densities = {}
    stem_averages = {}
    
    for stem_role in stem_roles:
        if stem_role not in stems:
            continue
        
        audio = stems[stem_role]
        audio_mono = _ensure_mono(audio)
        
        # Compute transient density
        transient_density = compute_transient_density(
            audio_mono,
            sr=sr,
            hop_length=config.hop_length,
            window_size=config.window_size
        )
        
        # Convert frames to time
        times = librosa.frames_to_time(
            np.arange(len(transient_density)),
            sr=sr,
            hop_length=config.hop_length
        )
        
        # Extract density in the analysis window
        window_mask = (times >= window_start) & (times <= window_end)
        if np.sum(window_mask) == 0:
            continue
        
        window_density = transient_density[window_mask]
        window_times = times[window_mask]
        
        # Compute average density in the window
        avg_density = np.mean(window_density)
        
        # Compute average density in the downstream region (for comparison)
        region_avg = _compute_region_average_transient_density(
            transient_density,
            times,
            downstream_region.start,
            downstream_region.end
        )
        
        stem_transient_densities[stem_role] = {
            'density': window_density,
            'times': window_times,
            'avg': avg_density
        }
        stem_averages[stem_role] = region_avg
    
    # Find stems with elevated transient density
    active_stems = []
    max_density = 0.0
    max_density_time = boundary_time
    
    for stem_role, density_data in stem_transient_densities.items():
        avg_density = density_data['avg']
        region_avg = stem_averages.get(stem_role, 0.0)
        
        # Check if density exceeds threshold
        threshold = max(
            region_avg * config.transient_density_threshold_multiplier,
            config.min_transient_density
        )
        
        if avg_density >= threshold:
            active_stems.append(stem_role)
            
            # Find peak density time
            peak_idx = np.argmax(density_data['density'])
            peak_time = density_data['times'][peak_idx]
            
            if density_data['density'][peak_idx] > max_density:
                max_density = density_data['density'][peak_idx]
                max_density_time = peak_time
    
    # If no active stems, no fill detected
    if not active_stems:
        return None
    
    # Compute confidence based on how much density exceeds threshold
    # Use the stem with highest density
    if active_stems:
        best_stem = active_stems[0]
        best_avg = stem_transient_densities[best_stem]['avg']
        best_region_avg = stem_averages.get(best_stem, 0.0)
        threshold = max(
            best_region_avg * config.transient_density_threshold_multiplier,
            config.min_transient_density
        )
        
        # Confidence is how much above threshold (normalized)
        excess = best_avg - threshold
        max_excess = 1.0 - threshold  # Maximum possible excess
        confidence = min(1.0, excess / max_excess) if max_excess > 0 else 0.5
        confidence = max(0.0, confidence)
    else:
        confidence = 0.5
    
    # Infer fill type based on active stems
    fill_type = None
    if len(active_stems) == 1:
        stem = active_stems[0]
        if stem == "drums":
            fill_type = "drum_fill"
        elif stem == "bass":
            fill_type = "bass_slide"
        elif stem == "vocals":
            fill_type = "vocal_adlib"
        elif stem == "instruments":
            fill_type = "instrument_fill"
    else:
        fill_type = "multi_stem_fill"
    
    # Create fill ID
    fill_id = f"fill_{downstream_region.id}_{int(max_density_time * 100)}"
    
    return Fill(
        id=fill_id,
        time=max_density_time,
        stem_roles=active_stems,
        region_id=downstream_region.id,
        confidence=confidence,
        fill_type=fill_type
    )


def detect_fills(
    reference_bundle: ReferenceBundle,
    regions: List[Region],
    config: Optional[FillConfig] = None
) -> List[Fill]:
    """
    Detect fills near region boundaries using transient density.
    
    Args:
        reference_bundle: ReferenceBundle with loaded audio files
        regions: List of detected regions
        config: Optional configuration (uses defaults if None)
    
    Returns:
        List of detected Fill objects
    """
    if config is None:
        config = FillConfig()
    
    logger.info(f"Starting fill detection for {len(regions)} regions")
    logger.info(f"Config: pre_boundary_window={config.pre_boundary_window_bars} bars, "
                f"threshold_multiplier={config.transient_density_threshold_multiplier}")
    
    # Prepare stems for analysis
    stems = {
        "drums": reference_bundle.drums.samples,
        "bass": reference_bundle.bass.samples,
        "vocals": reference_bundle.vocals.samples,
        "instruments": reference_bundle.instruments.samples
    }
    
    stem_roles = ["drums", "bass", "vocals", "instruments"]
    sr = reference_bundle.full_mix.sr
    bpm = reference_bundle.bpm
    
    fills = []
    
    # Detect fills at each region boundary
    # Skip the first region (no upstream boundary)
    for i in range(1, len(regions)):
        downstream_region = regions[i]
        boundary_time = downstream_region.start
        
        fill = _detect_fills_at_boundary(
            boundary_time,
            downstream_region,
            stems,
            stem_roles,
            sr,
            bpm,
            config
        )
        
        if fill is not None:
            fills.append(fill)
            logger.debug(f"Detected fill at {fill.time:.2f}s for region {downstream_region.id}: {fill}")
    
    logger.info(f"Detected {len(fills)} fills across {len(regions) - 1} boundaries")
    
    return fills

