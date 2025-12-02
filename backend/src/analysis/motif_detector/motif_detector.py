"""Motif detection engine for identifying repeated patterns in audio stems."""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import time
from os import getenv

try:
    from typing import Literal
except ImportError:
    # Python < 3.8 compatibility
    from typing_extensions import Literal

import numpy as np
import librosa
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

from models.reference_bundle import ReferenceBundle
from models.region import Region
from utils.logger import get_logger

logger = get_logger(__name__)

# Debug cap for motif segments (set via DEBUG_MAX_MOTIF_SEGMENTS env var)
DEBUG_MAX_MOTIF_SEGMENTS = int(getenv("DEBUG_MAX_MOTIF_SEGMENTS", "0") or "0")

# Configuration constants
DEFAULT_MOTIF_BARS = 2.0
DEFAULT_MOTIF_HOP_BARS = 1.0
MIN_SEGMENT_ENERGY_THRESHOLD = 0.01  # Minimum RMS energy to include a segment
MFCC_N_MELS = 13  # Number of MFCC coefficients to extract


@dataclass
class MotifInstance:
    """Represents a single instance of a motif in a stem."""
    id: str
    stem_role: Literal["drums", "bass", "vocals", "instruments", "full_mix"]
    start_time: float  # seconds
    end_time: float  # seconds
    features: np.ndarray  # Feature vector (e.g., MFCCs)
    group_id: Optional[str] = None  # Assigned after clustering
    is_variation: bool = False  # True if similar but not identical to canonical exemplar
    region_ids: List[str] = field(default_factory=list)  # Regions this motif belongs to
    
    @property
    def duration(self) -> float:
        """Get the duration of the motif instance in seconds."""
        return self.end_time - self.start_time


@dataclass
class MotifGroup:
    """Represents a group of similar motif instances."""
    id: str
    members: List[MotifInstance]
    label: Optional[str] = None  # Optional human-readable label
    
    @property
    def exemplar(self) -> MotifInstance:
        """Get the canonical exemplar (first member, or could be computed as centroid)."""
        return self.members[0] if self.members else None
    
    @property
    def variations(self) -> List[MotifInstance]:
        """Get all variations (non-exemplar members)."""
        return [m for m in self.members if m.is_variation]


def bars_to_seconds(bars: float, bpm: float) -> float:
    """
    Convert bars to seconds.
    
    Args:
        bars: Number of bars
        bpm: Beats per minute
    
    Returns:
        Duration in seconds
    """
    beats_per_bar = 4.0  # Assuming 4/4 time signature
    beats = bars * beats_per_bar
    seconds = (beats / bpm) * 60.0
    return seconds


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
        # Multi-channel: average across channels
        return np.mean(audio, axis=0)
    else:
        raise ValueError(f"Unexpected audio shape: {audio.shape}. Expected 1D or 2D array.")


def _segment_stem(
    audio: np.ndarray,
    sr: int,
    bpm: float,
    window_bars: float = DEFAULT_MOTIF_BARS,
    hop_bars: float = DEFAULT_MOTIF_HOP_BARS
) -> List[Tuple[float, float]]:
    """
    Segment a stem into overlapping windows.
    
    Args:
        audio: Audio signal (mono or multi-channel)
        sr: Sample rate
        bpm: Beats per minute
        window_bars: Window length in bars
        hop_bars: Hop size in bars
    
    Returns:
        List of (start_time, end_time) tuples in seconds
    """
    # Convert to mono
    audio_mono = _ensure_mono(audio)
    
    # Convert bars to seconds
    window_seconds = bars_to_seconds(window_bars, bpm)
    hop_seconds = bars_to_seconds(hop_bars, bpm)
    
    duration = len(audio_mono) / sr
    segments = []
    
    start_time = 0.0
    while start_time + window_seconds <= duration:
        end_time = start_time + window_seconds
        segments.append((start_time, end_time))
        start_time += hop_seconds
    
    logger.debug(f"Segmented audio into {len(segments)} windows (window={window_seconds:.2f}s, hop={hop_seconds:.2f}s)")
    
    return segments


def _extract_features(
    audio: np.ndarray,
    sr: int,
    start_time: float,
    end_time: float
) -> Optional[np.ndarray]:
    """
    Extract features (MFCCs) from an audio segment.
    
    Args:
        audio: Audio signal (mono)
        sr: Sample rate
        start_time: Start time in seconds
        end_time: End time in seconds
    
    Returns:
        Feature vector (MFCCs) or None if segment has negligible energy
    """
    # Extract segment
    start_sample = int(start_time * sr)
    end_sample = int(end_time * sr)
    segment = audio[start_sample:end_sample]
    
    if len(segment) == 0:
        return None
    
    # Check energy threshold
    rms = np.sqrt(np.mean(segment ** 2))
    if rms < MIN_SEGMENT_ENERGY_THRESHOLD:
        return None
    
    # Extract MFCCs
    mfccs = librosa.feature.mfcc(
        y=segment,
        sr=sr,
        n_mfcc=MFCC_N_MELS,
        hop_length=512
    )
    
    # Aggregate MFCCs across time (mean and std)
    # This gives us a fixed-size feature vector regardless of segment length
    mfcc_mean = np.mean(mfccs, axis=1)
    mfcc_std = np.std(mfccs, axis=1)
    
    # Combine mean and std into single feature vector
    features = np.concatenate([mfcc_mean, mfcc_std])
    
    return features


def _cluster_motifs(
    instances: List[MotifInstance],
    sensitivity: float = 0.5
) -> Tuple[List[MotifInstance], List[MotifGroup]]:
    """
    Cluster motif instances into groups using DBSCAN.
    
    Args:
        instances: List of motif instances to cluster
        sensitivity: Clustering sensitivity (0.0 = strict, 1.0 = loose)
                    Lower values create more groups, higher values create fewer groups
    
    Returns:
        Tuple of (updated instances with group_id, list of MotifGroups)
    """
    if len(instances) == 0:
        return instances, []
    
    # Extract feature vectors
    feature_matrix = np.array([inst.features for inst in instances])
    
    # Normalize features
    scaler = StandardScaler()
    features_normalized = scaler.fit_transform(feature_matrix)
    
    # Compute distance threshold based on sensitivity
    # sensitivity 0.0 -> very small eps (strict), sensitivity 1.0 -> larger eps (loose)
    # Use percentile of pairwise distances
    from scipy.spatial.distance import pdist
    distances = pdist(features_normalized, metric='euclidean')
    eps_percentile = 5.0 + (sensitivity * 45.0)  # Range from 5th to 50th percentile
    eps = np.percentile(distances, eps_percentile)
    
    # Ensure minimum eps to avoid too many clusters
    min_eps = np.percentile(distances, 2.0)
    max_eps = np.percentile(distances, 50.0)
    eps = np.clip(eps, min_eps, max_eps)
    
    logger.info(f"Clustering {len(instances)} motifs with sensitivity={sensitivity:.2f}, eps={eps:.4f}")
    
    # Apply DBSCAN
    clustering = DBSCAN(eps=eps, min_samples=2, metric='euclidean')
    labels = clustering.fit_predict(features_normalized)
    
    # Create groups
    groups = {}
    for idx, (instance, label) in enumerate(zip(instances, labels)):
        if label == -1:
            # Noise point (doesn't belong to any cluster)
            # Assign it its own group
            group_id = f"motif_group_{len(groups)}"
            instance.group_id = group_id
            groups[group_id] = [instance]
        else:
            group_id = f"motif_group_{label}"
            instance.group_id = group_id
            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(instance)
    
    # Create MotifGroup objects and mark variations
    motif_groups = []
    for group_id, members in groups.items():
        if len(members) == 0:
            continue
        
        # Compute centroid of the group
        group_features = np.array([m.features for m in members])
        centroid = np.mean(group_features, axis=0)
        
        # Mark exemplar (closest to centroid) and variations
        distances_to_centroid = [
            np.linalg.norm(m.features - centroid) for m in members
        ]
        exemplar_idx = np.argmin(distances_to_centroid)
        
        # Mark all as variations except the exemplar
        for i, member in enumerate(members):
            if i != exemplar_idx:
                member.is_variation = True
        
        # Create group
        group = MotifGroup(id=group_id, members=members)
        motif_groups.append(group)
    
    logger.info(f"Created {len(motif_groups)} motif groups from {len(instances)} instances")
    
    return instances, motif_groups


def _align_motifs_with_regions(
    instances: List[MotifInstance],
    regions: List[Region]
) -> None:
    """
    Align motif instances with regions by assigning region_ids.
    
    Args:
        instances: List of motif instances
        regions: List of detected regions
    """
    for instance in instances:
        instance.region_ids = []
        for region in regions:
            # Check if motif overlaps with region
            # Motif overlaps if it starts before region ends and ends after region starts
            if (instance.start_time < region.end and 
                instance.end_time > region.start):
                instance.region_ids.append(region.id)


def detect_motifs(
    reference_bundle: ReferenceBundle,
    regions: List[Region],
    sensitivity: float = 0.5,
    window_bars: float = DEFAULT_MOTIF_BARS,
    hop_bars: float = DEFAULT_MOTIF_HOP_BARS
) -> Tuple[List[MotifInstance], List[MotifGroup]]:
    """
    Detect motifs in a reference bundle.
    
    Args:
        reference_bundle: ReferenceBundle with loaded audio files
        regions: List of detected regions
        sensitivity: Clustering sensitivity (0.0 = strict, 1.0 = loose)
        window_bars: Window length in bars for segmentation
        hop_bars: Hop size in bars for segmentation
    
    Returns:
        Tuple of (list of MotifInstances, list of MotifGroups)
    """
    t0 = time.time()
    logger.info("Motif detection started", extra={"sensitivity": sensitivity, "window_bars": window_bars, "hop_bars": hop_bars})
    
    bpm = reference_bundle.bpm
    all_instances = []
    
    # Process each stem
    stems = {
        "drums": reference_bundle.drums,
        "bass": reference_bundle.bass,
        "vocals": reference_bundle.vocals,
        "instruments": reference_bundle.instruments,
        "full_mix": reference_bundle.full_mix
    }
    
    instance_counter = 0
    
    for stem_role, audio_file in stems.items():
        logger.info(f"Processing {stem_role} stem...")
        
        audio = audio_file.samples
        sr = audio_file.sr
        
        # Convert to mono
        audio_mono = _ensure_mono(audio)
        
        # Segment the stem
        t_seg_start = time.time()
        segments = _segment_stem(audio_mono, sr, bpm, window_bars, hop_bars)
        t_seg_end = time.time()
        
        logger.info(
            "Motif segmentation raw count",
            extra={"segment_count": len(segments)},
        )
        
        # Apply debug cap if set
        if DEBUG_MAX_MOTIF_SEGMENTS and len(segments) > DEBUG_MAX_MOTIF_SEGMENTS:
            logger.warning(
                "Truncating motif segments for debug",
                extra={
                    "raw_segment_count": len(segments),
                    "max_segments": DEBUG_MAX_MOTIF_SEGMENTS,
                },
            )
            segments = segments[:DEBUG_MAX_MOTIF_SEGMENTS]
        
        logger.info("Motif segmentation complete", extra={"stem_role": stem_role, "segment_count": len(segments), "elapsed_sec": round(t_seg_end - t_seg_start, 3)})
        
        # Extract features for each segment
        t_feat_start = time.time()
        for start_time, end_time in segments:
            features = _extract_features(audio_mono, sr, start_time, end_time)
            
            if features is not None:
                instance_id = f"motif_{stem_role}_{instance_counter:04d}"
                instance = MotifInstance(
                    id=instance_id,
                    stem_role=stem_role,
                    start_time=start_time,
                    end_time=end_time,
                    features=features
                )
                all_instances.append(instance)
                instance_counter += 1
        t_feat_end = time.time()
        stem_instance_count = len([i for i in all_instances if i.stem_role == stem_role])
        logger.info("Motif feature extraction complete", extra={"stem_role": stem_role, "segment_count": len(segments), "instance_count": stem_instance_count, "elapsed_sec": round(t_feat_end - t_feat_start, 3)})
    
    logger.info(f"Total motif instances extracted: {len(all_instances)}")
    
    # Cluster motifs
    t_cluster_start = time.time()
    instances, groups = _cluster_motifs(all_instances, sensitivity)
    t_cluster_end = time.time()
    logger.info(
        "Motif clustering complete",
        extra={
            "motif_instance_count": len(instances),
            "motif_group_count": len(groups),
            "elapsed_sec": round(t_cluster_end - t_cluster_start, 3),
        },
    )
    
    # Align motifs with regions
    _align_motifs_with_regions(instances, regions)
    
    t1 = time.time()
    elapsed = round(t1 - t0, 3)
    logger.info(
        "Motif detection finished",
        extra={"total_elapsed_sec": elapsed, "sensitivity": sensitivity, "instance_count": len(instances), "group_count": len(groups)},
    )
    
    return instances, groups

