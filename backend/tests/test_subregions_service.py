"""Unit tests for subregion service."""
import pytest
from models.region import Region
from analysis.subregions.service import (
    compute_region_subregions,
    seconds_to_bars,
    DensityCurves
)
from analysis.motif_detector.motif_detector import MotifInstance, MotifGroup
import numpy as np


def test_seconds_to_bars():
    """Test seconds to bars conversion."""
    bpm = 120.0
    
    # 1 bar = 4 beats, at 120 BPM = 2 seconds
    assert abs(seconds_to_bars(2.0, bpm) - 1.0) < 0.001
    
    # 8 seconds = 4 bars at 120 BPM
    assert abs(seconds_to_bars(8.0, bpm) - 4.0) < 0.001
    
    # Test with different BPM
    bpm_140 = 140.0
    # At 140 BPM, 1 bar = 60/140 * 4 = ~1.714 seconds
    bars = seconds_to_bars(1.714, bpm_140)
    assert abs(bars - 1.0) < 0.01


def test_compute_region_subregions_stub_structure():
    """Test that compute_region_subregions returns correct structure shape."""
    # Create test regions
    regions = [
        Region(
            id="region_01",
            name="Intro",
            type="low_energy",
            start=0.0,
            end=16.0,  # 8 bars at 120 BPM
            motifs=[],
            fills=[],
            callResponse=[]
        ),
        Region(
            id="region_02",
            name="Verse",
            type="medium_energy",
            start=16.0,
            end=32.0,  # 8 more bars
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    
    # Create empty motifs and groups (stub doesn't use them yet)
    motifs: list[MotifInstance] = []
    motif_groups: list[MotifGroup] = []
    density_curves = DensityCurves()
    bpm = 120.0
    
    # Compute subregions
    result = compute_region_subregions(
        regions=regions,
        motifs=motifs,
        motif_groups=motif_groups,
        density_curves=density_curves,
        bpm=bpm,
        bars_per_chunk=2
    )
    
    # Should return one RegionSubRegions per region
    assert len(result) == 2
    
    # Check first region
    region_01_subregions = result[0]
    assert region_01_subregions.region_id == "region_01"
    assert len(region_01_subregions.lanes) == 4
    assert "drums" in region_01_subregions.lanes
    assert "bass" in region_01_subregions.lanes
    assert "vocals" in region_01_subregions.lanes
    assert "instruments" in region_01_subregions.lanes
    
    # Each lane should have at least one pattern (stub creates one placeholder)
    for stem_category in ["drums", "bass", "vocals", "instruments"]:
        assert len(region_01_subregions.lanes[stem_category]) >= 1
        pattern = region_01_subregions.lanes[stem_category][0]
        assert pattern.region_id == "region_01"
        assert pattern.stem_category == stem_category
        assert pattern.start_bar >= 0.0
        assert pattern.end_bar > pattern.start_bar
        assert 0.0 <= pattern.intensity <= 1.0
    
    # Check second region
    region_02_subregions = result[1]
    assert region_02_subregions.region_id == "region_02"
    assert len(region_02_subregions.lanes) == 4


def test_compute_region_subregions_bar_positions():
    """Test that bar positions are correctly computed from region times."""
    # Create a region at 120 BPM
    # 8 seconds = 4 bars at 120 BPM
    regions = [
        Region(
            id="region_01",
            name="Test",
            type="low_energy",
            start=0.0,
            end=8.0,  # 4 bars
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    
    motifs: list[MotifInstance] = []
    motif_groups: list[MotifGroup] = []
    density_curves = DensityCurves()
    bpm = 120.0
    
    result = compute_region_subregions(
        regions=regions,
        motifs=motifs,
        motif_groups=motif_groups,
        density_curves=density_curves,
        bpm=bpm
    )
    
    # Check that bar positions are reasonable
    pattern = result[0].lanes["drums"][0]
    # Start should be around 0 bars (region starts at 0 seconds)
    assert abs(pattern.start_bar - 0.0) < 0.1
    # End should be around 4 bars (8 seconds = 4 bars at 120 BPM)
    assert abs(pattern.end_bar - 4.0) < 0.1

