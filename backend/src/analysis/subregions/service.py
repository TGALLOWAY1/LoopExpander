"""Service for computing subregion patterns from regions, motifs, and density data."""
from typing import List, Dict, Optional, Tuple
import numpy as np
import librosa

from models.region import Region
from models.reference_bundle import ReferenceBundle
from analysis.subregions.models import (
    StemCategory,
    SubRegionPattern,
    RegionSubRegions
)
from analysis.motif_detector.motif_detector import MotifInstance, MotifGroup, bars_to_seconds
from analysis.region_detector.features import compute_rms_envelope, _ensure_mono
from config import (
    DEFAULT_SUBREGION_BARS_PER_CHUNK,
    DEFAULT_SUBREGION_SILENCE_INTENSITY_THRESHOLD
)


class DensityCurves:
    """
    Density/intensity curves per stem for subregion analysis.
    
    Computes RMS envelopes for each stem and provides normalized intensity values
    over time for use in subregion pattern analysis.
    """
    
    def __init__(self, bundle: ReferenceBundle, hop_length: int = 512, frame_length: int = 2048):
        """
        Initialize density curves from a reference bundle.
        
        Args:
            bundle: ReferenceBundle containing stem audio files
            hop_length: Hop length for RMS computation (samples)
            frame_length: Frame length for RMS computation (samples)
        """
        self.bundle = bundle
        self.hop_length = hop_length
        self.frame_length = frame_length
        self.sr = bundle.drums.sr  # Assume all stems have same sample rate
        
        # Compute RMS envelopes for each stem
        self._rms_curves: Dict[StemCategory, np.ndarray] = {}
        self._time_arrays: Dict[StemCategory, np.ndarray] = {}
        self._global_max_rms: float = 0.0
        
        # Compute RMS for each stem category
        stem_map = {
            "drums": bundle.drums,
            "bass": bundle.bass,
            "vocals": bundle.vocals,
            "instruments": bundle.instruments
        }
        
        for stem_category, audio_file in stem_map.items():
            audio = audio_file.samples
            audio_mono = _ensure_mono(audio)
            
            # Compute RMS envelope
            rms = compute_rms_envelope(audio_mono, frame_length=frame_length, hop_length=hop_length)
            
            # Convert frames to time
            times = librosa.frames_to_time(
                np.arange(len(rms)),
                sr=self.sr,
                hop_length=hop_length
            )
            
            self._rms_curves[stem_category] = rms
            self._time_arrays[stem_category] = times
            
            # Track global max for normalization
            if rms.max() > self._global_max_rms:
                self._global_max_rms = rms.max()
    
    def get_intensity(
        self,
        stem_category: StemCategory,
        start_time: float,
        end_time: float,
        normalization: str = "global_max"
    ) -> float:
        """
        Get average intensity for a stem over a time window.
        
        Args:
            stem_category: Stem category to query
            start_time: Start time in seconds
            end_time: End time in seconds
            normalization: Normalization strategy ("global_max" or "local_max")
        
        Returns:
            Normalized intensity value in [0, 1]
        """
        if stem_category not in self._rms_curves:
            return 0.0
        
        rms = self._rms_curves[stem_category]
        times = self._time_arrays[stem_category]
        
        # Find frames within time window
        mask = (times >= start_time) & (times < end_time)
        if np.sum(mask) == 0:
            return 0.0
        
        window_rms = rms[mask]
        avg_rms = float(np.mean(window_rms))
        
        # Normalize
        if normalization == "global_max":
            if self._global_max_rms > 0:
                intensity = avg_rms / self._global_max_rms
            else:
                intensity = 0.0
        elif normalization == "local_max":
            # Normalize by this stem's max
            stem_max = rms.max()
            if stem_max > 0:
                intensity = avg_rms / stem_max
            else:
                intensity = 0.0
        else:
            intensity = avg_rms
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, intensity))


def seconds_to_bars(seconds: float, bpm: float) -> float:
    """
    Convert seconds to bars.
    
    Args:
        seconds: Duration in seconds
        bpm: Beats per minute
    
    Returns:
        Number of bars (assuming 4/4 time signature)
    
    Note:
        Bar positioning is derived from:
        - Song BPM (from ReferenceBundle)
        - Region start/end times (from Region.start/end in seconds)
        - Bar = (seconds * bpm) / (60 * 4) where 4 is beats per bar
    """
    beats_per_bar = 4.0  # Assuming 4/4 time signature
    beats = (seconds * bpm) / 60.0
    bars = beats / beats_per_bar
    return bars


def _find_motifs_in_chunk(
    motifs: List[MotifInstance],
    motif_groups: List[MotifGroup],
    stem_category: StemCategory,
    chunk_start_time: float,
    chunk_end_time: float
) -> Tuple[Optional[str], bool, Optional[str]]:
    """
    Find motif instances that overlap with a time chunk.
    
    Args:
        motifs: List of motif instances
        motif_groups: List of motif groups
        stem_category: Stem category to filter by
        chunk_start_time: Chunk start time in seconds
        chunk_end_time: Chunk end time in seconds
    
    Returns:
        Tuple of (motif_group_id, is_variation, label)
        Returns (None, False, None) if no motifs found
    """
    # Filter motifs by stem category and time overlap
    overlapping_motifs = []
    for motif in motifs:
        if motif.stem_role != stem_category:
            continue
        
        # Check if motif overlaps with chunk
        # Overlap if: motif_start < chunk_end AND motif_end > chunk_start
        if motif.start_time < chunk_end_time and motif.end_time > chunk_start_time:
            overlapping_motifs.append(motif)
    
    if not overlapping_motifs:
        return (None, False, None)
    
    # Find dominant motif group (most common group_id)
    group_counts: Dict[str, int] = {}
    variation_count = 0
    
    for motif in overlapping_motifs:
        if motif.group_id:
            group_counts[motif.group_id] = group_counts.get(motif.group_id, 0) + 1
        if motif.is_variation:
            variation_count += 1
    
    if not group_counts:
        return (None, False, None)
    
    # Get dominant group
    dominant_group_id = max(group_counts.items(), key=lambda x: x[1])[0]
    
    # Check if any overlapping motif is a variation
    is_variation = variation_count > 0 or any(m.is_variation for m in overlapping_motifs if m.group_id == dominant_group_id)
    
    # Generate label from group ID or use group index
    label = None
    for group in motif_groups:
        if group.id == dominant_group_id:
            if group.label:
                label = group.label
            else:
                # Generate label from group index
                group_index = next((i for i, g in enumerate(motif_groups) if g.id == dominant_group_id), -1)
                if group_index >= 0:
                    label = f"Motif G{group_index + 1}"
            break
    
    if not label:
        label = f"Motif {dominant_group_id[:8]}"
    
    return (dominant_group_id, is_variation, label)


def compute_region_subregions(
    regions: List[Region],
    motifs: List[MotifInstance],
    motif_groups: List[MotifGroup],
    density_curves: DensityCurves,
    bpm: float,
    bars_per_chunk: int = DEFAULT_SUBREGION_BARS_PER_CHUNK,
    silence_threshold: float = DEFAULT_SUBREGION_SILENCE_INTENSITY_THRESHOLD,
) -> List[RegionSubRegions]:
    """
    Compute subregion patterns for all regions.
    
    This function creates a DNA-style segmentation of each region into subregions
    per stem category, capturing patterns, variations, silence, and intensity.
    
    Args:
        regions: List of detected regions
        motifs: List of motif instances (from motif detection)
        motif_groups: List of motif groups (clustered motifs)
        density_curves: Density/intensity curves per stem
        bpm: Beats per minute of the song
        bars_per_chunk: Number of bars per subregion chunk (default: 2)
        silence_threshold: Intensity threshold below which a chunk is considered silence (default: 0.15)
    
    Returns:
        List of RegionSubRegions, one per input region
    """
    result: List[RegionSubRegions] = []
    
    for region in regions:
        # Convert region times to bars
        region_start_bar = seconds_to_bars(region.start, bpm)
        region_end_bar = seconds_to_bars(region.end, bpm)
        region_duration_bars = region_end_bar - region_start_bar
        
        # Calculate number of chunks
        num_chunks = max(1, int(np.ceil(region_duration_bars / bars_per_chunk)))
        
        # Initialize lanes for all 4 stem categories
        lanes: Dict[StemCategory, List[SubRegionPattern]] = {
            "drums": [],
            "bass": [],
            "vocals": [],
            "instruments": []
        }
        
        # Process each stem category
        for stem_category in ["drums", "bass", "vocals", "instruments"]:
            patterns: List[SubRegionPattern] = []
            
            # Create chunks for this region and stem
            for chunk_idx in range(num_chunks):
                # Calculate chunk bar boundaries
                chunk_start_bar = region_start_bar + (chunk_idx * bars_per_chunk)
                chunk_end_bar = min(
                    region_start_bar + ((chunk_idx + 1) * bars_per_chunk),
                    region_end_bar
                )
                
                # Convert chunk bars to time
                chunk_start_time = bars_to_seconds(chunk_start_bar, bpm)
                chunk_end_time = bars_to_seconds(chunk_end_bar, bpm)
                
                # Get intensity from density curves
                intensity = density_curves.get_intensity(
                    stem_category,  # type: ignore
                    chunk_start_time,
                    chunk_end_time,
                    normalization="global_max"
                )
                
                # Detect silence
                is_silence = intensity < silence_threshold
                
                # Find motifs in this chunk
                motif_group_id, is_variation, label = _find_motifs_in_chunk(
                    motifs,
                    motif_groups,
                    stem_category,  # type: ignore
                    chunk_start_time,
                    chunk_end_time
                )
                
                # If silence, clear motif association
                if is_silence:
                    motif_group_id = None
                    label = None
                    is_variation = False
                
                # Create pattern ID
                pattern_id = f"{region.id}-{stem_category}-{chunk_idx}"
                
                # Create SubRegionPattern
                pattern = SubRegionPattern(
                    id=pattern_id,
                    region_id=region.id,
                    stem_category=stem_category,  # type: ignore
                    start_bar=chunk_start_bar,
                    end_bar=chunk_end_bar,
                    label=label,
                    motif_group_id=motif_group_id,
                    is_variation=is_variation,
                    is_silence=is_silence,
                    intensity=intensity,
                    metadata=None
                )
                
                patterns.append(pattern)
            
            lanes[stem_category] = patterns  # type: ignore
        
        # Create RegionSubRegions
        region_subregions = RegionSubRegions(
            region_id=region.id,
            lanes=lanes  # type: ignore
        )
        result.append(region_subregions)
    
    return result

