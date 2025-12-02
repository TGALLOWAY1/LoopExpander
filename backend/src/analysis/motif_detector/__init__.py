"""Motif detection module for identifying repeated patterns in audio."""
from .motif_detector import (
    MotifInstance,
    MotifGroup,
    detect_motifs,
    bars_to_seconds,
    _cluster_motifs,
    _align_motifs_with_regions
)

__all__ = [
    "MotifInstance",
    "MotifGroup",
    "detect_motifs",
    "bars_to_seconds",
    "_cluster_motifs",
    "_align_motifs_with_regions"
]

