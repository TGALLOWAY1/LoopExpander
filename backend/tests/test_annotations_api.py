"""API tests for Visual Composer annotations endpoints."""
import pytest
import numpy as np
from pathlib import Path
import sys
import os
from fastapi.testclient import TestClient

# Add src to path to match how routes_reference imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app
from models.reference_bundle import ReferenceBundle
from stem_ingest.audio_file import AudioFile
from models.store import (
    REFERENCE_BUNDLES, REFERENCE_ANNOTATIONS
)
from models.annotations import ReferenceAnnotations, RegionAnnotations, AnnotationLane, AnnotationBlock
from config import VISUAL_COMPOSER_ENABLED


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
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def setup_test_data():
    """Set up test data and clean up after."""
    # Clear stores
    REFERENCE_BUNDLES.clear()
    REFERENCE_ANNOTATIONS.clear()
    
    # Create test bundle
    bundle = create_test_bundle(duration=60.0, bpm=120.0)
    reference_id = "test_ref_annotations"
    REFERENCE_BUNDLES[reference_id] = bundle
    
    yield reference_id
    
    # Cleanup
    REFERENCE_BUNDLES.clear()
    REFERENCE_ANNOTATIONS.clear()


def test_get_annotations_when_feature_disabled(client, setup_test_data):
    """Test that GET annotations returns 404 when feature is disabled."""
    reference_id = setup_test_data
    
    # Temporarily disable feature flag
    import config
    original_value = config.VISUAL_COMPOSER_ENABLED
    try:
        config.VISUAL_COMPOSER_ENABLED = False
        
        response = client.get(f"/api/reference/{reference_id}/annotations")
        assert response.status_code == 404
        assert "disabled" in response.json()["detail"].lower()
    finally:
        config.VISUAL_COMPOSER_ENABLED = original_value


def test_post_annotations_when_feature_disabled(client, setup_test_data):
    """Test that POST annotations returns 404 when feature is disabled."""
    reference_id = setup_test_data
    
    annotations_data = {
        "referenceId": reference_id,
        "regions": []
    }
    
    # Temporarily disable feature flag
    import config
    original_value = config.VISUAL_COMPOSER_ENABLED
    try:
        config.VISUAL_COMPOSER_ENABLED = False
        
        response = client.post(
            f"/api/reference/{reference_id}/annotations",
            json=annotations_data
        )
        assert response.status_code == 404
        assert "disabled" in response.json()["detail"].lower()
    finally:
        config.VISUAL_COMPOSER_ENABLED = original_value


@pytest.mark.skipif(not VISUAL_COMPOSER_ENABLED, reason="Visual Composer feature is disabled")
def test_get_annotations_empty(client, setup_test_data):
    """Test GET annotations when none exist returns empty structure."""
    reference_id = setup_test_data
    
    response = client.get(f"/api/reference/{reference_id}/annotations")
    assert response.status_code == 200
    
    data = response.json()
    assert data["referenceId"] == reference_id
    assert data["regions"] == []


@pytest.mark.skipif(not VISUAL_COMPOSER_ENABLED, reason="Visual Composer feature is disabled")
def test_post_and_get_annotations_round_trip(client, setup_test_data):
    """Test round-trip POST→GET with multiple RegionAnnotations."""
    reference_id = setup_test_data
    
    # Create annotations with multiple regions
    annotations_data = {
        "referenceId": reference_id,
        "regions": [
            {
                "regionId": "region_01",
                "lanes": [
                    {
                        "stemCategory": "drums",
                        "blocks": [
                            {
                                "id": "block_1",
                                "startBar": 0.0,
                                "endBar": 4.0,
                                "label": "Intro"
                            },
                            {
                                "id": "block_2",
                                "startBar": 4.0,
                                "endBar": 8.0,
                                "label": "Verse"
                            }
                        ]
                    },
                    {
                        "stemCategory": "bass",
                        "blocks": [
                            {
                                "id": "block_3",
                                "startBar": 0.0,
                                "endBar": 8.0,
                                "label": "Bass Line"
                            }
                        ]
                    }
                ]
            },
            {
                "regionId": "region_02",
                "lanes": [
                    {
                        "stemCategory": "vocals",
                        "blocks": [
                            {
                                "id": "block_4",
                                "startBar": 8.0,
                                "endBar": 16.0,
                                "label": "Chorus"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    # POST annotations
    post_response = client.post(
        f"/api/reference/{reference_id}/annotations",
        json=annotations_data
    )
    assert post_response.status_code == 200
    
    post_data = post_response.json()
    assert post_data["referenceId"] == reference_id
    assert len(post_data["regions"]) == 2
    assert post_data["regions"][0]["regionId"] == "region_01"
    assert len(post_data["regions"][0]["lanes"]) == 2
    assert len(post_data["regions"][0]["lanes"][0]["blocks"]) == 2
    assert post_data["regions"][0]["lanes"][0]["blocks"][0]["label"] == "Intro"
    
    # GET annotations
    get_response = client.get(f"/api/reference/{reference_id}/annotations")
    assert get_response.status_code == 200
    
    get_data = get_response.json()
    assert get_data["referenceId"] == reference_id
    assert len(get_data["regions"]) == 2
    assert get_data["regions"][0]["regionId"] == "region_01"
    assert len(get_data["regions"][0]["lanes"]) == 2
    assert len(get_data["regions"][0]["lanes"][0]["blocks"]) == 2
    assert get_data["regions"][0]["lanes"][0]["blocks"][0]["label"] == "Intro"
    
    # Verify data matches
    assert get_data == post_data


@pytest.mark.skipif(not VISUAL_COMPOSER_ENABLED, reason="Visual Composer feature is disabled")
def test_post_annotations_force_reference_id_match(client, setup_test_data):
    """Test that POST forces referenceId in payload to match path parameter."""
    reference_id = setup_test_data
    
    # Create annotations with mismatched reference_id
    annotations_data = {
        "referenceId": "wrong_id",
        "regions": []
    }
    
    # POST annotations - should override reference_id
    response = client.post(
        f"/api/reference/{reference_id}/annotations",
        json=annotations_data
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["referenceId"] == reference_id  # Should be corrected
    assert data["referenceId"] != "wrong_id"


@pytest.mark.skipif(not VISUAL_COMPOSER_ENABLED, reason="Visual Composer feature is disabled")
def test_get_annotations_reference_not_found(client):
    """Test GET annotations returns 404 when reference doesn't exist."""
    REFERENCE_BUNDLES.clear()
    
    response = client.get("/api/reference/nonexistent_ref/annotations")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.skipif(not VISUAL_COMPOSER_ENABLED, reason="Visual Composer feature is disabled")
def test_post_annotations_reference_not_found(client):
    """Test POST annotations returns 404 when reference doesn't exist."""
    REFERENCE_BUNDLES.clear()
    
    annotations_data = {
        "referenceId": "nonexistent_ref",
        "regions": []
    }
    
    response = client.post(
        "/api/reference/nonexistent_ref/annotations",
        json=annotations_data
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.skipif(not VISUAL_COMPOSER_ENABLED, reason="Visual Composer feature is disabled")
def test_post_annotations_validation_error(client, setup_test_data):
    """Test POST annotations with invalid data returns validation error."""
    reference_id = setup_test_data
    
    # Invalid: end_bar <= start_bar
    annotations_data = {
        "referenceId": reference_id,
        "regions": [
            {
                "regionId": "region_01",
                "lanes": [
                    {
                        "stemCategory": "drums",
                        "blocks": [
                            {
                                "id": "block_1",
                                "startBar": 4.0,
                                "endBar": 2.0,  # Invalid: end < start
                                "label": "Invalid"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    response = client.post(
        f"/api/reference/{reference_id}/annotations",
        json=annotations_data
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.skipif(not VISUAL_COMPOSER_ENABLED, reason="Visual Composer feature is disabled")
def test_post_annotations_invalid_stem_category(client, setup_test_data):
    """Test POST annotations with invalid stem category returns validation error."""
    reference_id = setup_test_data
    
    # Invalid stem category
    annotations_data = {
        "referenceId": reference_id,
        "regions": [
            {
                "regionId": "region_01",
                "lanes": [
                    {
                        "stemCategory": "invalid_category",  # Invalid
                        "blocks": []
                    }
                ]
            }
        ]
    }
    
    response = client.post(
        f"/api/reference/{reference_id}/annotations",
        json=annotations_data
    )
    assert response.status_code == 422  # Validation error

