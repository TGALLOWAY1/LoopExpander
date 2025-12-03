"""API tests for subregions endpoint."""
import pytest
import numpy as np
from pathlib import Path
import sys
import os

# Add src to path to match how routes_reference imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.reference_bundle import ReferenceBundle
from stem_ingest.audio_file import AudioFile
from models.store import (
    REFERENCE_BUNDLES, REFERENCE_REGIONS, REFERENCE_MOTIFS,
    REFERENCE_SUBREGIONS
)
from analysis.region_detector.region_detector import detect_regions
from analysis.motif_detector.motif_detector import detect_motifs
from analysis.call_response_detector.call_response_detector import detect_call_response, CallResponseConfig
from analysis.fill_detector.fill_detector import detect_fills, FillConfig


def create_synthetic_audio_file(
    duration: float,
    sr: int = 44100,
    role: str = "full_mix",
    frequency: float = 440.0,
    amplitude: float = 0.5
) -> AudioFile:
    """Create a synthetic audio file for testing."""
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


def create_test_bundle(duration: float = 60.0, bpm: float = 120.0) -> ReferenceBundle:
    """Create a test reference bundle."""
    drums = create_synthetic_audio_file(duration, 44100, "drums", 220, 0.5)
    bass = create_synthetic_audio_file(duration, 44100, "bass", 110, 0.3)
    vocals = create_synthetic_audio_file(duration, 44100, "vocals", 440, 0.3)
    instruments = create_synthetic_audio_file(duration, 44100, "instruments", 660, 0.3)
    full_mix = create_synthetic_audio_file(duration, 44100, "full_mix", 440, 0.5)
    
    return ReferenceBundle(
        drums=drums,
        bass=bass,
        vocals=vocals,
        instruments=instruments,
        full_mix=full_mix,
        bpm=bpm
    )


@pytest.fixture
def setup_test_data():
    """Set up test data and clean up after."""
    # Clear stores
    REFERENCE_BUNDLES.clear()
    REFERENCE_REGIONS.clear()
    REFERENCE_MOTIFS.clear()
    REFERENCE_SUBREGIONS.clear()
    
    # Create test bundle
    bundle = create_test_bundle(duration=60.0, bpm=120.0)
    reference_id = "test_ref_123"
    REFERENCE_BUNDLES[reference_id] = bundle
    
    # Detect regions
    regions = detect_regions(bundle)
    REFERENCE_REGIONS[reference_id] = regions
    
    # Detect motifs
    instances, groups = detect_motifs(bundle, regions, sensitivity=0.5)
    REFERENCE_MOTIFS[reference_id] = (instances, groups)
    
    yield reference_id, bundle, regions
    
    # Cleanup
    REFERENCE_BUNDLES.clear()
    REFERENCE_REGIONS.clear()
    REFERENCE_MOTIFS.clear()
    REFERENCE_SUBREGIONS.clear()


@pytest.mark.asyncio
async def test_get_subregions_endpoint_structure(setup_test_data):
    """Test that GET /reference/{id}/subregions returns correct structure."""
    reference_id, bundle, regions = setup_test_data
    
    # Import here to avoid circular imports
    from api import routes_reference
    
    # Call the endpoint function directly
    response = await routes_reference.get_subregions(reference_id)
    
    # Check response structure
    assert "referenceId" in response
    assert response["referenceId"] == reference_id
    assert "regions" in response
    assert isinstance(response["regions"], list)
    
    # Should have one region entry per detected region
    assert len(response["regions"]) == len(regions)
    
    # Check each region structure
    for region_data in response["regions"]:
        assert "regionId" in region_data
        assert "lanes" in region_data
        assert isinstance(region_data["lanes"], dict)
        
        # Should have all 4 stem categories
        assert "drums" in region_data["lanes"]
        assert "bass" in region_data["lanes"]
        assert "vocals" in region_data["lanes"]
        assert "instruments" in region_data["lanes"]
        
        # Check each lane
        for stem_category in ["drums", "bass", "vocals", "instruments"]:
            lane = region_data["lanes"][stem_category]
            assert isinstance(lane, list)
            
            # Each lane should have at least one pattern (stub creates placeholder)
            assert len(lane) >= 1
            
            # Check pattern structure
            pattern = lane[0]
            assert "id" in pattern
            assert "regionId" in pattern
            assert "stemCategory" in pattern
            assert pattern["stemCategory"] == stem_category
            assert "startBar" in pattern
            assert "endBar" in pattern
            assert "isVariation" in pattern
            assert "isSilence" in pattern
            assert "intensity" in pattern
            assert 0.0 <= pattern["intensity"] <= 1.0


@pytest.mark.asyncio
async def test_get_subregions_endpoint_not_found():
    """Test that endpoint returns 404 for non-existent reference."""
    from api import routes_reference
    from fastapi import HTTPException
    
    with pytest.raises(HTTPException) as exc_info:
        await routes_reference.get_subregions("nonexistent_id")
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_subregions_endpoint_no_regions():
    """Test that endpoint returns 404 if regions not analyzed."""
    from api import routes_reference
    from fastapi import HTTPException
    
    # Create bundle but don't analyze
    bundle = create_test_bundle()
    reference_id = "test_no_regions"
    REFERENCE_BUNDLES[reference_id] = bundle
    
    try:
        with pytest.raises(HTTPException) as exc_info:
            await routes_reference.get_subregions(reference_id)
        
        assert exc_info.value.status_code == 404
        assert "Regions not found" in str(exc_info.value.detail)
    finally:
        REFERENCE_BUNDLES.clear()


@pytest.mark.asyncio
async def test_get_subregions_endpoint_caching(setup_test_data):
    """Test that subregions are cached after first computation."""
    reference_id, bundle, regions = setup_test_data
    
    from api import routes_reference
    
    # First call should compute
    response1 = await routes_reference.get_subregions(reference_id)
    
    # Second call should use cache
    response2 = await routes_reference.get_subregions(reference_id)
    
    # Responses should be identical
    assert response1 == response2
    
    # Cache should be populated
    assert reference_id in REFERENCE_SUBREGIONS
    assert len(REFERENCE_SUBREGIONS[reference_id]) == len(regions)

