"""Tests for region detection."""
import numpy as np
import pytest
from pathlib import Path

from src.models.region import Region
from src.models.reference_bundle import ReferenceBundle
from src.stem_ingest.audio_file import AudioFile
from src.analysis.region_detector.region_detector import detect_regions
from src.analysis.region_detector.priors import estimate_initial_boundaries


def create_synthetic_audio_file(
    duration: float,
    sr: int = 44100,
    role: str = "full_mix",
    frequency: float = 440.0,
    amplitude: float = 0.5
) -> AudioFile:
    """
    Create a synthetic audio file for testing.
    
    Args:
        duration: Duration in seconds
        sr: Sample rate
        role: Role of the audio file
        frequency: Frequency of sine wave
        amplitude: Amplitude of sine wave
    
    Returns:
        AudioFile instance
    """
    t = np.linspace(0, duration, int(sr * duration))
    samples = amplitude * np.sin(2 * np.pi * frequency * t)
    
    return AudioFile(
        path=Path(f"{role}.wav"),
        role=role,
        sr=sr,
        duration=duration,
        channels=1,
        samples=samples
    )


def create_synthetic_bundle_with_changes(
    duration: float = 120.0,
    sr: int = 44100,
    bpm: float = 120.0
) -> ReferenceBundle:
    """
    Create a synthetic reference bundle with audio that has clear structural changes.
    
    The audio will have different characteristics at different times to trigger
    novelty peaks and region detection.
    
    Args:
        duration: Total duration in seconds
        sr: Sample rate
        bpm: Beats per minute
    
    Returns:
        ReferenceBundle instance
    """
    # Create audio with clear sections:
    # - First 30s: Low frequency, low amplitude (intro)
    # - 30-60s: Higher frequency, higher amplitude (build)
    # - 60-90s: High frequency, high amplitude (drop)
    # - 90-120s: Lower frequency, lower amplitude (outro)
    
    t1 = np.linspace(0, 30, int(sr * 30))
    intro = 0.2 * np.sin(2 * np.pi * 220 * t1)  # Low freq, low amp
    
    t2 = np.linspace(0, 30, int(sr * 30))
    build = 0.5 * np.sin(2 * np.pi * 440 * t2)  # Mid freq, mid amp
    
    t3 = np.linspace(0, 30, int(sr * 30))
    drop = 0.8 * np.sin(2 * np.pi * 880 * t3)  # High freq, high amp
    
    t4 = np.linspace(0, 30, int(sr * 30))
    outro = 0.3 * np.sin(2 * np.pi * 330 * t4)  # Mid freq, low amp
    
    # Concatenate sections
    full_mix_samples = np.concatenate([intro, build, drop, outro])
    
    # Create AudioFile for full mix
    full_mix = AudioFile(
        path=Path("full_mix.wav"),
        role="full_mix",
        sr=sr,
        duration=duration,
        channels=1,
        samples=full_mix_samples
    )
    
    # Create simple stems (just use same audio for simplicity in test)
    drums = create_synthetic_audio_file(duration, sr, "drums", 220, 0.3)
    bass = create_synthetic_audio_file(duration, sr, "bass", 110, 0.3)
    vocals = create_synthetic_audio_file(duration, sr, "vocals", 440, 0.3)
    instruments = create_synthetic_audio_file(duration, sr, "instruments", 660, 0.3)
    
    return ReferenceBundle(
        drums=drums,
        bass=bass,
        vocals=vocals,
        instruments=instruments,
        full_mix=full_mix,
        bpm=bpm
    )


def test_estimate_initial_boundaries():
    """Test that priors return reasonable boundaries."""
    duration = 120.0
    bpm = 120.0
    
    boundaries = estimate_initial_boundaries(duration, bpm)
    
    # Should return some boundaries
    assert len(boundaries) > 0, "Should return at least one boundary"
    
    # All boundaries should be within duration
    assert all(0 < b < duration for b in boundaries), \
        "All boundaries should be within track duration"
    
    # Boundaries should be sorted
    assert boundaries == sorted(boundaries), \
        "Boundaries should be sorted"
    
    # Should have boundaries in typical song structure positions
    # (intro around 5-10%, first chorus around 25-35%, etc.)
    assert any(5 < b < 15 for b in boundaries), \
        "Should have boundary in intro range (5-15%)"
    assert any(25 < b < 40 for b in boundaries), \
        "Should have boundary in first chorus range (25-40%)"


def test_detect_regions_returns_regions():
    """Test that detect_regions returns at least 2-3 regions for synthetic audio."""
    bundle = create_synthetic_bundle_with_changes(duration=120.0, bpm=120.0)
    
    regions = detect_regions(bundle)
    
    # Should return at least 2-3 regions
    assert len(regions) >= 2, \
        f"Expected at least 2 regions, got {len(regions)}"
    
    # All should be Region instances
    assert all(isinstance(r, Region) for r in regions), \
        "All returned items should be Region instances"
    
    # Regions should have valid properties
    for region in regions:
        assert region.id, "Region should have an id"
        assert region.name, "Region should have a name"
        assert region.type, "Region should have a type"
        assert region.start >= 0, "Region start should be >= 0"
        assert region.end > region.start, "Region end should be > start"
        assert isinstance(region.motifs, list), "Region motifs should be a list"
        assert isinstance(region.fills, list), "Region fills should be a list"
        assert isinstance(region.callResponse, list), "Region callResponse should be a list"


def test_detect_regions_covers_full_duration():
    """Test that detected regions cover the full track duration."""
    bundle = create_synthetic_bundle_with_changes(duration=120.0, bpm=120.0)
    
    regions = detect_regions(bundle)
    
    # First region should start at or near 0
    assert regions[0].start < 1.0, \
        f"First region should start near 0, got {regions[0].start}"
    
    # Last region should end at or near track duration
    assert abs(regions[-1].end - bundle.full_mix.duration) < 1.0, \
        f"Last region should end near track duration, got {regions[-1].end}"
    
    # Regions should be contiguous (no gaps)
    for i in range(len(regions) - 1):
        assert abs(regions[i].end - regions[i + 1].start) < 0.1, \
            f"Regions should be contiguous, gap between {i} and {i+1}"


def test_detect_regions_region_types():
    """Test that regions have appropriate types assigned."""
    bundle = create_synthetic_bundle_with_changes(duration=120.0, bpm=120.0)
    
    regions = detect_regions(bundle)
    
    # First region should be intro/low_energy
    assert regions[0].type in ["low_energy", "build"], \
        f"First region should be intro/low_energy, got {regions[0].type}"
    
    # Last region should be outro/low_energy
    assert regions[-1].type in ["low_energy", "build"], \
        f"Last region should be outro/low_energy, got {regions[-1].type}"
    
    # Should have at least one high_energy or build region
    region_types = [r.type for r in regions]
    assert any(t in ["high_energy", "build", "drop"] for t in region_types), \
        "Should have at least one high-energy or build region"


def test_region_model_validation():
    """Test that Region model validates input correctly."""
    # Valid region
    region = Region(
        id="region_01",
        name="Intro",
        type="low_energy",
        start=0.0,
        end=10.0,
        motifs=[],
        fills=[],
        callResponse=[]
    )
    assert region.duration == 10.0
    
    # Invalid: end <= start
    with pytest.raises(ValueError, match="end time must be > start"):
        Region(
            id="region_02",
            name="Invalid",
            type="low_energy",
            start=10.0,
            end=10.0,
            motifs=[],
            fills=[],
            callResponse=[]
        )
    
    # Invalid: negative start
    with pytest.raises(ValueError, match="start time must be >= 0"):
        Region(
            id="region_03",
            name="Invalid",
            type="low_energy",
            start=-1.0,
            end=10.0,
            motifs=[],
            fills=[],
            callResponse=[]
        )

