"""Reference mix model for single full-mix reference track."""
from typing import Optional, List

from stem_ingest.audio_file import AudioFile


class ReferenceMix:
    """Container for a single full-mix reference track and its analysis metadata."""

    def __init__(
        self,
        audio: AudioFile,
        bpm: float,
        beat_grid: Optional[List[float]] = None,
        key: Optional[str] = None,
        user_bpm_override: Optional[float] = None,
    ):
        self.audio = audio
        self.bpm = user_bpm_override if user_bpm_override else bpm
        self.detected_bpm = bpm
        self.beat_grid = beat_grid or []
        self.key = key
        self.duration = audio.duration

    @property
    def total_bars(self) -> float:
        """Estimate total bars based on BPM and duration (assumes 4/4)."""
        if self.bpm <= 0:
            return 0.0
        beats = self.bpm * self.duration / 60.0
        return beats / 4.0

    def __repr__(self) -> str:
        return (
            f"ReferenceMix(bpm={self.bpm:.1f}, duration={self.duration:.2f}s, "
            f"bars={self.total_bars:.1f})"
        )
