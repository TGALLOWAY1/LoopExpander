"""Reference bundle model for holding reference track stems and metadata."""
from typing import Optional, List

from stem_ingest.audio_file import AudioFile


class ReferenceBundle:
    """Container for reference track stems and metadata."""
    
    def __init__(
        self,
        drums: AudioFile,
        bass: AudioFile,
        vocals: AudioFile,
        instruments: AudioFile,
        full_mix: AudioFile,
        bpm: float,
        key: Optional[str] = None
    ):
        """
        Initialize a ReferenceBundle.
        
        Args:
            drums: Drums stem audio file
            bass: Bass stem audio file
            vocals: Vocals stem audio file
            instruments: Instruments stem audio file
            full_mix: Full mix audio file
            bpm: Beats per minute
            key: Optional musical key (e.g., "C major", "A minor")
        """
        self.drums = drums
        self.bass = bass
        self.vocals = vocals
        self.instruments = instruments
        self.full_mix = full_mix
        self.bpm = bpm
        self.key = key
    
    def validate_lengths(self, tolerance: float = 0.05) -> None:
        """
        Validate that all audio files have durations within tolerance seconds of each other.
        
        Args:
            tolerance: Maximum allowed difference in seconds between any two files
        
        Raises:
            ValueError: If any file durations differ by more than tolerance
        """
        durations = {
            'drums': self.drums.duration,
            'bass': self.bass.duration,
            'vocals': self.vocals.duration,
            'instruments': self.instruments.duration,
            'full_mix': self.full_mix.duration,
        }
        
        # Find min and max durations
        min_duration = min(durations.values())
        max_duration = max(durations.values())
        duration_diff = max_duration - min_duration
        
        if duration_diff > tolerance:
            # Build detailed error message
            duration_str = ", ".join([f"{role}: {dur:.3f}s" for role, dur in durations.items()])
            raise ValueError(
                f"Audio file durations differ by {duration_diff:.3f}s (tolerance: {tolerance}s). "
                f"Durations: {duration_str}"
            )
    
    def get_all_stems(self) -> List[AudioFile]:
        """Get all stem audio files (excluding full_mix)."""
        return [self.drums, self.bass, self.vocals, self.instruments]
    
    def __repr__(self) -> str:
        """String representation of ReferenceBundle."""
        key_str = f", key={self.key}" if self.key else ""
        return (
            f"ReferenceBundle(bpm={self.bpm:.1f}{key_str}, "
            f"duration={self.full_mix.duration:.2f}s)"
        )

