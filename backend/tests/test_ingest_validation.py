"""Tests for ingest validation."""
import numpy as np
import pytest
from pathlib import Path

from src.models.reference_bundle import ReferenceBundle
from src.stem_ingest.audio_file import AudioFile


def test_validate_lengths_success():
    """Test that validate_lengths passes when durations are within tolerance."""
    # Create mock AudioFile instances with matching durations
    base_duration = 120.0  # 2 minutes
    base_sr = 44100
    base_samples = np.random.randn(int(base_duration * base_sr))
    
    drums = AudioFile(
        path=Path("drums.wav"),
        role="drums",
        sr=base_sr,
        duration=base_duration,
        channels=1,
        samples=base_samples
    )
    
    bass = AudioFile(
        path=Path("bass.wav"),
        role="bass",
        sr=base_sr,
        duration=base_duration + 0.01,  # Within 0.05s tolerance
        channels=1,
        samples=base_samples
    )
    
    vocals = AudioFile(
        path=Path("vocals.wav"),
        role="vocals",
        sr=base_sr,
        duration=base_duration - 0.02,
        channels=1,
        samples=base_samples
    )
    
    instruments = AudioFile(
        path=Path("instruments.wav"),
        role="instruments",
        sr=base_sr,
        duration=base_duration,
        channels=1,
        samples=base_samples
    )
    
    full_mix = AudioFile(
        path=Path("full_mix.wav"),
        role="full_mix",
        sr=base_sr,
        duration=base_duration + 0.01,
        channels=1,
        samples=base_samples
    )
    
    bundle = ReferenceBundle(
        drums=drums,
        bass=bass,
        vocals=vocals,
        instruments=instruments,
        full_mix=full_mix,
        bpm=120.0
    )
    
    # Should not raise an exception
    bundle.validate_lengths(tolerance=0.05)


def test_validate_lengths_failure():
    """Test that validate_lengths raises ValueError when durations differ too much."""
    base_duration = 120.0
    base_sr = 44100
    base_samples = np.random.randn(int(base_duration * base_sr))
    
    drums = AudioFile(
        path=Path("drums.wav"),
        role="drums",
        sr=base_sr,
        duration=base_duration,
        channels=1,
        samples=base_samples
    )
    
    bass = AudioFile(
        path=Path("bass.wav"),
        role="bass",
        sr=base_sr,
        duration=base_duration + 0.1,  # Exceeds 0.05s tolerance
        channels=1,
        samples=base_samples
    )
    
    vocals = AudioFile(
        path=Path("vocals.wav"),
        role="vocals",
        sr=base_sr,
        duration=base_duration,
        channels=1,
        samples=base_samples
    )
    
    instruments = AudioFile(
        path=Path("instruments.wav"),
        role="instruments",
        sr=base_sr,
        duration=base_duration,
        channels=1,
        samples=base_samples
    )
    
    full_mix = AudioFile(
        path=Path("full_mix.wav"),
        role="full_mix",
        sr=base_sr,
        duration=base_duration,
        channels=1,
        samples=base_samples
    )
    
    bundle = ReferenceBundle(
        drums=drums,
        bass=bass,
        vocals=vocals,
        instruments=instruments,
        full_mix=full_mix,
        bpm=120.0
    )
    
    # Should raise ValueError
    with pytest.raises(ValueError, match="Audio file durations differ"):
        bundle.validate_lengths(tolerance=0.05)

