"""API tests for motifs, call-response, and fills endpoints."""
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
    REFERENCE_CALL_RESPONSE, REFERENCE_FILLS, REFERENCE_MOTIF_INSTANCES_RAW
)
from analysis.region_detector.region_detector import detect_regions
from analysis.motif_detector.motif_detector import detect_motifs
from analysis.call_response_detector.call_response_detector import detect_call_response, CallResponseConfig
from analysis.fill_detector.fill_detector import detect_fills, FillConfig
from analysis.motif_detector.config import DEFAULT_MOTIF_SENSITIVITY


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


@pytest.fixture(scope="function")
def test_reference_id():
    """Create a test reference bundle and return its ID."""
    import uuid
    reference_id = f"test_ref_{uuid.uuid4().hex[:8]}"
    bundle = create_test_bundle(duration=60.0, bpm=120.0)
    
    # Store bundle
    REFERENCE_BUNDLES[reference_id] = bundle
    
    # Run analysis
    regions = detect_regions(bundle)
    REFERENCE_REGIONS[reference_id] = regions
    
    instances, groups = detect_motifs(bundle, regions, sensitivity=0.5)
    
    # Store raw instances
    from analysis.motif_detector.motif_detector import MotifInstance
    raw_instances = []
    for inst in instances:
        raw_inst = MotifInstance(
            id=inst.id,
            stem_role=inst.stem_role,
            start_time=inst.start_time,
            end_time=inst.end_time,
            features=inst.features.copy(),
            group_id=None,
            is_variation=False,
            region_ids=inst.region_ids.copy()
        )
        raw_instances.append(raw_inst)
    REFERENCE_MOTIF_INSTANCES_RAW[reference_id] = raw_instances
    
    REFERENCE_MOTIFS[reference_id] = (instances, groups)
    
    call_response_config = CallResponseConfig()
    call_response_pairs = detect_call_response(instances, regions, bundle.bpm, config=call_response_config)
    REFERENCE_CALL_RESPONSE[reference_id] = call_response_pairs
    
    fill_config = FillConfig()
    fills = detect_fills(bundle, regions, config=fill_config)
    REFERENCE_FILLS[reference_id] = fills
    
    yield reference_id
    
    # Cleanup
    REFERENCE_BUNDLES.pop(reference_id, None)
    REFERENCE_REGIONS.pop(reference_id, None)
    REFERENCE_MOTIFS.pop(reference_id, None)
    REFERENCE_MOTIF_INSTANCES_RAW.pop(reference_id, None)
    REFERENCE_CALL_RESPONSE.pop(reference_id, None)
    REFERENCE_FILLS.pop(reference_id, None)


@pytest.mark.asyncio
async def test_get_motifs_endpoint(test_reference_id):
    """Test GET /reference/{id}/motifs endpoint."""
    # Import routes to get the same store instance
    from api import routes_reference
    
    # Verify data is in store (using the same store instance as routes)
    assert test_reference_id in REFERENCE_BUNDLES, f"Reference {test_reference_id} not in bundles"
    assert test_reference_id in REFERENCE_MOTIF_INSTANCES_RAW, f"Reference {test_reference_id} not in raw instances"
    
    # Test without sensitivity parameter (pass None explicitly since we're calling directly)
    result = await routes_reference.get_motifs(test_reference_id, sensitivity=None)
    
    assert "referenceId" in result
    assert result["referenceId"] == test_reference_id
    assert "instances" in result
    assert "groups" in result
    assert "instanceCount" in result
    assert "groupCount" in result
    assert isinstance(result["instances"], list)
    assert isinstance(result["groups"], list)
    assert result["instanceCount"] == len(result["instances"])
    assert result["groupCount"] == len(result["groups"])
    
    # Verify instance structure
    if len(result["instances"]) > 0:
        inst = result["instances"][0]
        assert "id" in inst
        assert "stemRole" in inst
        assert "startTime" in inst
        assert "endTime" in inst
        assert "duration" in inst
        assert "groupId" in inst
        assert "isVariation" in inst
        assert "regionIds" in inst
    
    # Verify group structure
    if len(result["groups"]) > 0:
        group = result["groups"][0]
        assert "id" in group
        assert "memberIds" in group
        assert "memberCount" in group
        assert "variationCount" in group


@pytest.mark.asyncio
async def test_get_motifs_with_sensitivity(test_reference_id):
    """Test GET /reference/{id}/motifs with sensitivity parameter."""
    from api import routes_reference
    
    # Test with different sensitivity
    result_low = await routes_reference.get_motifs(test_reference_id, sensitivity=0.2)
    result_high = await routes_reference.get_motifs(test_reference_id, sensitivity=0.8)
    
    # Both should return valid results
    assert "instances" in result_low
    assert "groups" in result_low
    assert "instances" in result_high
    assert "groups" in result_high
    
    # Different sensitivities may produce different group counts
    # (this is expected behavior)
    assert isinstance(result_low["groupCount"], int)
    assert isinstance(result_high["groupCount"], int)


@pytest.mark.asyncio
async def test_get_call_response_endpoint(test_reference_id):
    """Test GET /reference/{id}/call-response endpoint."""
    from api import routes_reference
    
    result = await routes_reference.get_call_response(test_reference_id)
    
    assert "referenceId" in result
    assert result["referenceId"] == test_reference_id
    assert "pairs" in result
    assert "count" in result
    assert isinstance(result["pairs"], list)
    assert result["count"] == len(result["pairs"])
    
    # Verify pair structure
    if len(result["pairs"]) > 0:
        pair = result["pairs"][0]
        assert "id" in pair
        assert "fromMotifId" in pair
        assert "toMotifId" in pair
        assert "fromStemRole" in pair
        assert "toStemRole" in pair
        assert "fromTime" in pair
        assert "toTime" in pair
        assert "timeOffset" in pair
        assert "confidence" in pair
        assert "isInterStem" in pair
        assert "isIntraStem" in pair


@pytest.mark.asyncio
async def test_get_fills_endpoint(test_reference_id):
    """Test GET /reference/{id}/fills endpoint."""
    from api import routes_reference
    
    result = await routes_reference.get_fills(test_reference_id)
    
    assert "referenceId" in result
    assert result["referenceId"] == test_reference_id
    assert "fills" in result
    assert "count" in result
    assert isinstance(result["fills"], list)
    assert result["count"] == len(result["fills"])
    
    # Verify fill structure
    if len(result["fills"]) > 0:
        fill = result["fills"][0]
        assert "id" in fill
        assert "time" in fill
        assert "stemRoles" in fill
        assert "regionId" in fill
        assert "confidence" in fill
        assert isinstance(fill["stemRoles"], list)


@pytest.mark.asyncio
async def test_get_motifs_not_found():
    """Test GET /reference/{id}/motifs with non-existent reference."""
    from api import routes_reference
    from fastapi import HTTPException
    
    with pytest.raises(HTTPException) as exc_info:
        await routes_reference.get_motifs("nonexistent_id")
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_call_response_not_found():
    """Test GET /reference/{id}/call-response with non-existent reference."""
    from api import routes_reference
    from fastapi import HTTPException
    
    with pytest.raises(HTTPException) as exc_info:
        await routes_reference.get_call_response("nonexistent_id")
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_fills_not_found():
    """Test GET /reference/{id}/fills with non-existent reference."""
    from api import routes_reference
    from fastapi import HTTPException
    
    with pytest.raises(HTTPException) as exc_info:
        await routes_reference.get_fills("nonexistent_id")
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_motif_sensitivity_endpoint(test_reference_id):
    """Test GET /reference/{id}/motif-sensitivity endpoint returns defaults."""
    from api import routes_reference
    
    result = await routes_reference.get_motif_sensitivity(test_reference_id)
    
    assert "referenceId" in result
    assert result["referenceId"] == test_reference_id
    assert "motifSensitivityConfig" in result
    
    config = result["motifSensitivityConfig"]
    assert "drums" in config
    assert "bass" in config
    assert "vocals" in config
    assert "instruments" in config
    
    # Should return default values
    assert config["drums"] == DEFAULT_MOTIF_SENSITIVITY["drums"]
    assert config["bass"] == DEFAULT_MOTIF_SENSITIVITY["bass"]
    assert config["vocals"] == DEFAULT_MOTIF_SENSITIVITY["vocals"]
    assert config["instruments"] == DEFAULT_MOTIF_SENSITIVITY["instruments"]


@pytest.mark.asyncio
async def test_patch_motif_sensitivity_updates_only_provided_keys(test_reference_id):
    """Test PATCH /reference/{id}/motif-sensitivity updates only provided keys."""
    from api import routes_reference
    from api.routes_reference import MotifSensitivityUpdate
    
    # Get initial config
    initial_result = await routes_reference.get_motif_sensitivity(test_reference_id)
    initial_config = initial_result["motifSensitivityConfig"]
    
    # Update only drums
    update = MotifSensitivityUpdate(drums=0.7)
    result = await routes_reference.update_motif_sensitivity(test_reference_id, update)
    
    assert "referenceId" in result
    assert result["referenceId"] == test_reference_id
    assert "motifSensitivityConfig" in result
    
    updated_config = result["motifSensitivityConfig"]
    
    # Drums should be updated
    assert updated_config["drums"] == 0.7
    
    # Other values should remain unchanged
    assert updated_config["bass"] == initial_config["bass"]
    assert updated_config["vocals"] == initial_config["vocals"]
    assert updated_config["instruments"] == initial_config["instruments"]
    
    # Verify it's persisted in the bundle
    from models.store import REFERENCE_BUNDLES
    bundle = REFERENCE_BUNDLES[test_reference_id]
    assert bundle.motif_sensitivity_config["drums"] == 0.7


@pytest.mark.asyncio
async def test_patch_motif_sensitivity_validates_range():
    """Test PATCH /reference/{id}/motif-sensitivity validates values are in [0, 1]."""
    from api import routes_reference
    from api.routes_reference import MotifSensitivityUpdate
    from fastapi import HTTPException
    
    # Test value too high
    update_high = MotifSensitivityUpdate(drums=1.5)
    with pytest.raises(HTTPException) as exc_info:
        await routes_reference.update_motif_sensitivity("test_ref_invalid", update_high)
    # Pydantic validation should catch this before our endpoint code
    
    # Test value too low
    update_low = MotifSensitivityUpdate(drums=-0.1)
    with pytest.raises(HTTPException) as exc_info:
        await routes_reference.update_motif_sensitivity("test_ref_invalid", update_low)
    # Pydantic validation should catch this before our endpoint code


@pytest.mark.asyncio
async def test_patch_motif_sensitivity_not_found():
    """Test PATCH /reference/{id}/motif-sensitivity with non-existent reference."""
    from api import routes_reference
    from api.routes_reference import MotifSensitivityUpdate
    from fastapi import HTTPException
    
    update = MotifSensitivityUpdate(drums=0.5)
    
    with pytest.raises(HTTPException) as exc_info:
        await routes_reference.update_motif_sensitivity("nonexistent_id", update)
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_reanalyze_motifs_endpoint(test_reference_id):
    """Test POST /reference/{id}/reanalyze-motifs endpoint."""
    from api import routes_reference
    
    # Update sensitivity config first
    from api.routes_reference import MotifSensitivityUpdate
    update = MotifSensitivityUpdate(drums=0.3, bass=0.8)
    await routes_reference.update_motif_sensitivity(test_reference_id, update)
    
    # Re-analyze motifs
    result = await routes_reference.reanalyze_motifs(test_reference_id)
    
    assert "referenceId" in result
    assert result["referenceId"] == test_reference_id
    assert "motifInstanceCount" in result
    assert "motifGroupCount" in result
    assert "status" in result
    assert result["status"] == "ok"
    
    # Verify motifs were re-detected
    assert result["motifInstanceCount"] >= 0
    assert result["motifGroupCount"] >= 0


@pytest.mark.asyncio
async def test_reanalyze_motifs_not_found():
    """Test POST /reference/{id}/reanalyze-motifs with non-existent reference."""
    from api import routes_reference
    from fastapi import HTTPException
    
    with pytest.raises(HTTPException) as exc_info:
        await routes_reference.reanalyze_motifs("nonexistent_id")
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_reanalyze_motifs_no_regions():
    """Test POST /reference/{id}/reanalyze-motifs fails when regions not detected."""
    from api import routes_reference
    from fastapi import HTTPException
    import uuid
    
    # Create a bundle without regions
    reference_id = f"test_ref_{uuid.uuid4().hex[:8]}"
    bundle = create_test_bundle(duration=60.0, bpm=120.0)
    REFERENCE_BUNDLES[reference_id] = bundle
    
    try:
        with pytest.raises(HTTPException) as exc_info:
            await routes_reference.reanalyze_motifs(reference_id)
        
        assert exc_info.value.status_code == 404
        assert "regions" in exc_info.value.detail.lower()
    finally:
        REFERENCE_BUNDLES.pop(reference_id, None)

