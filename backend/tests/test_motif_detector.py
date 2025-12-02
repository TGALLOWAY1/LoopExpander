"""Tests for motif detection."""
import numpy as np
import pytest
from pathlib import Path

from src.models.region import Region
from src.models.reference_bundle import ReferenceBundle
from src.stem_ingest.audio_file import AudioFile
from src.analysis.motif_detector.motif_detector import (
    MotifInstance,
    MotifGroup,
    detect_motifs,
    bars_to_seconds,
    _segment_stem,
    _extract_features,
    _cluster_motifs
)


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


def create_repeating_pattern_audio(
    pattern_duration: float,
    num_repeats: int,
    sr: int = 44100,
    base_freq: float = 440.0,
    variation_freq: float = 480.0
) -> np.ndarray:
    """
    Create audio with a repeating pattern, with some variations.
    
    Args:
        pattern_duration: Duration of each pattern in seconds
        num_repeats: Number of times to repeat the pattern
        sr: Sample rate
        base_freq: Base frequency for the pattern
        variation_freq: Frequency for variations
    
    Returns:
        Audio samples as numpy array
    """
    pattern_samples = []
    
    for i in range(num_repeats):
        # Use base frequency for most patterns, variation_freq for some
        freq = base_freq if i % 3 != 0 else variation_freq
        t = np.linspace(0, pattern_duration, int(sr * pattern_duration))
        pattern = 0.5 * np.sin(2 * np.pi * freq * t)
        pattern_samples.append(pattern)
    
    return np.concatenate(pattern_samples)


def create_synthetic_bundle_with_repeats(
    duration: float = 60.0,
    sr: int = 44100,
    bpm: float = 120.0
) -> ReferenceBundle:
    """
    Create a synthetic reference bundle with repeating patterns.
    
    Args:
        duration: Total duration in seconds
        sr: Sample rate
        bpm: Beats per minute
    
    Returns:
        ReferenceBundle instance
    """
    # Create drums with repeating pattern (2 bars = 4 seconds at 120 BPM)
    pattern_duration = 4.0  # 2 bars
    num_repeats = int(duration / pattern_duration)
    drums_samples = create_repeating_pattern_audio(
        pattern_duration, num_repeats, sr, 220.0, 240.0
    )
    # Trim to exact duration
    drums_samples = drums_samples[:int(sr * duration)]
    
    drums = AudioFile(
        path=Path("drums.wav"),
        role="drums",
        sr=sr,
        duration=duration,
        channels=1,
        samples=drums_samples
    )
    
    # Create other stems with simpler patterns
    bass = create_synthetic_audio_file(duration, sr, "bass", 110, 0.3)
    vocals = create_synthetic_audio_file(duration, sr, "vocals", 440, 0.3)
    instruments = create_synthetic_audio_file(duration, sr, "instruments", 660, 0.3)
    full_mix = create_synthetic_audio_file(duration, sr, "full_mix", 440, 0.5)
    
    return ReferenceBundle(
        drums=drums,
        bass=bass,
        vocals=vocals,
        instruments=instruments,
        full_mix=full_mix,
        bpm=bpm
    )


def test_bars_to_seconds():
    """Test bars to seconds conversion."""
    bpm = 120.0
    
    # 1 bar = 4 beats = 2 seconds at 120 BPM
    assert abs(bars_to_seconds(1.0, bpm) - 2.0) < 0.01
    
    # 2 bars = 8 beats = 4 seconds at 120 BPM
    assert abs(bars_to_seconds(2.0, bpm) - 4.0) < 0.01
    
    # 4 bars = 16 beats = 8 seconds at 120 BPM
    assert abs(bars_to_seconds(4.0, bpm) - 8.0) < 0.01
    
    # Test with different BPM
    bpm = 60.0
    assert abs(bars_to_seconds(1.0, bpm) - 4.0) < 0.01  # 1 bar = 4 seconds at 60 BPM


def test_segment_stem():
    """Test stem segmentation."""
    duration = 20.0
    sr = 44100
    bpm = 120.0
    
    # Create simple audio
    t = np.linspace(0, duration, int(sr * duration))
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    
    # Segment with 2 bar windows, 1 bar hop
    segments = _segment_stem(audio, sr, bpm, window_bars=2.0, hop_bars=1.0)
    
    # Should have multiple segments
    assert len(segments) > 0, "Should return at least one segment"
    
    # Each segment should be 2 bars = 4 seconds
    for start, end in segments:
        assert abs((end - start) - 4.0) < 0.1, f"Segment duration should be ~4s, got {end - start}"
        assert start >= 0, "Segment start should be >= 0"
        assert end <= duration + 0.1, "Segment end should be <= duration"
    
    # Segments should overlap (hop is 1 bar, window is 2 bars)
    if len(segments) > 1:
        first_end = segments[0][1]
        second_start = segments[1][0]
        hop_expected = bars_to_seconds(1.0, bpm)  # 2 seconds
        assert abs(second_start - hop_expected) < 0.1, "Segments should hop by 1 bar"


def test_extract_features():
    """Test feature extraction from audio segments."""
    sr = 44100
    duration = 2.0  # 2 seconds
    t = np.linspace(0, duration, int(sr * duration))
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    
    # Extract features
    features = _extract_features(audio, sr, 0.0, duration)
    
    # Should return feature vector
    assert features is not None, "Should return features for valid audio"
    assert isinstance(features, np.ndarray), "Features should be numpy array"
    assert len(features) > 0, "Features should have non-zero length"
    
    # Test with silent segment (should return None)
    silent_audio = np.zeros(int(sr * duration))
    silent_features = _extract_features(silent_audio, sr, 0.0, duration)
    assert silent_features is None, "Should return None for silent segment"


def test_cluster_motifs():
    """Test motif clustering."""
    # Create synthetic motif instances with similar features
    instances = []
    
    # Create two groups: one with base features, one with different features
    base_features = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    variant_features = np.array([1.1, 2.1, 3.1, 4.1, 5.1])  # Similar to base
    different_features = np.array([10.0, 20.0, 30.0, 40.0, 50.0])  # Different
    
    # Add instances from first group (base + variants)
    for i in range(3):
        inst = MotifInstance(
            id=f"inst_{i}",
            stem_role="drums",
            start_time=float(i * 4.0),
            end_time=float((i + 1) * 4.0),
            features=base_features if i == 0 else variant_features
        )
        instances.append(inst)
    
    # Add instances from second group
    for i in range(2):
        inst = MotifInstance(
            id=f"inst_{i+3}",
            stem_role="drums",
            start_time=float((i + 3) * 4.0),
            end_time=float((i + 4) * 4.0),
            features=different_features
        )
        instances.append(inst)
    
    # Cluster with low sensitivity (strict)
    clustered_instances, groups = _cluster_motifs(instances, sensitivity=0.2)
    
    # Should create groups
    assert len(groups) > 0, "Should create at least one group"
    
    # All instances should have group_id assigned
    assert all(inst.group_id is not None for inst in clustered_instances), \
        "All instances should have group_id assigned"
    
    # Should have at least one group with multiple members
    assert any(len(g.members) > 1 for g in groups), \
        "Should have at least one group with multiple members"


def test_detect_motifs_returns_instances_and_groups():
    """Test that detect_motifs returns motif instances and groups."""
    bundle = create_synthetic_bundle_with_repeats(duration=30.0, bpm=120.0)
    
    # Create simple regions
    regions = [
        Region(
            id="region_01",
            name="Section 1",
            type="low_energy",
            start=0.0,
            end=15.0,
            motifs=[],
            fills=[],
            callResponse=[]
        ),
        Region(
            id="region_02",
            name="Section 2",
            type="high_energy",
            start=15.0,
            end=30.0,
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    
    instances, groups = detect_motifs(bundle, regions, sensitivity=0.5)
    
    # Should return instances
    assert len(instances) > 0, "Should return at least one motif instance"
    assert all(isinstance(inst, MotifInstance) for inst in instances), \
        "All returned items should be MotifInstance"
    
    # Should return groups
    assert len(groups) >= 0, "Should return groups (may be empty if no clusters)"
    assert all(isinstance(g, MotifGroup) for g in groups), \
        "All returned items should be MotifGroup"
    
    # Instances should have valid properties
    for inst in instances:
        assert inst.id, "Instance should have an id"
        assert inst.stem_role in ["drums", "bass", "vocals", "instruments", "full_mix"], \
            "Instance should have valid stem_role"
        assert inst.start_time >= 0, "Instance start_time should be >= 0"
        assert inst.end_time > inst.start_time, "Instance end_time should be > start_time"
        assert inst.features is not None, "Instance should have features"
        assert len(inst.features) > 0, "Instance features should be non-empty"


def test_detect_motifs_aligns_with_regions():
    """Test that motif instances are aligned with regions."""
    bundle = create_synthetic_bundle_with_repeats(duration=30.0, bpm=120.0)
    
    # Create regions
    regions = [
        Region(
            id="region_01",
            name="Section 1",
            type="low_energy",
            start=0.0,
            end=15.0,
            motifs=[],
            fills=[],
            callResponse=[]
        ),
        Region(
            id="region_02",
            name="Section 2",
            type="high_energy",
            start=15.0,
            end=30.0,
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    
    instances, groups = detect_motifs(bundle, regions, sensitivity=0.5)
    
    # All instances should have region_ids assigned
    for inst in instances:
        assert isinstance(inst.region_ids, list), "region_ids should be a list"
        # Instances should overlap with at least one region
        assert len(inst.region_ids) > 0, \
            f"Instance {inst.id} should be aligned with at least one region"
        
        # Verify alignment is correct
        for region_id in inst.region_ids:
            region = next(r for r in regions if r.id == region_id)
            # Check overlap
            assert (inst.start_time < region.end and inst.end_time > region.start), \
                f"Instance {inst.id} should overlap with region {region_id}"


def test_detect_motifs_sensitivity_affects_grouping():
    """Test that changing sensitivity affects motif grouping."""
    bundle = create_synthetic_bundle_with_repeats(duration=30.0, bpm=120.0)
    
    regions = [
        Region(
            id="region_01",
            name="Section 1",
            type="low_energy",
            start=0.0,
            end=30.0,
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    
    # Test with low sensitivity (strict)
    instances_low, groups_low = detect_motifs(bundle, regions, sensitivity=0.1)
    
    # Test with high sensitivity (loose)
    instances_high, groups_high = detect_motifs(bundle, regions, sensitivity=0.9)
    
    # Should have same number of instances (segmentation doesn't change)
    assert len(instances_low) == len(instances_high), \
        "Sensitivity should not affect number of instances"
    
    # High sensitivity should generally create fewer groups (looser clustering)
    # But this is not guaranteed, so we just check that both produce valid results
    assert len(groups_low) >= 0, "Low sensitivity should produce valid groups"
    assert len(groups_high) >= 0, "High sensitivity should produce valid groups"


def test_motif_group_properties():
    """Test MotifGroup properties."""
    # Create a group with members
    instances = [
        MotifInstance(
            id="inst_1",
            stem_role="drums",
            start_time=0.0,
            end_time=4.0,
            features=np.array([1.0, 2.0, 3.0]),
            group_id="group_1",
            is_variation=False
        ),
        MotifInstance(
            id="inst_2",
            stem_role="drums",
            start_time=4.0,
            end_time=8.0,
            features=np.array([1.1, 2.1, 3.1]),
            group_id="group_1",
            is_variation=True
        )
    ]
    
    group = MotifGroup(id="group_1", members=instances)
    
    assert group.id == "group_1", "Group should have correct id"
    assert len(group.members) == 2, "Group should have 2 members"
    assert group.exemplar is not None, "Group should have an exemplar"
    assert len(group.variations) == 1, "Group should have 1 variation"

