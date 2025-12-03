"""API tests for Visual Composer annotations endpoints."""
import pytest
import sys
import os
from fastapi.testclient import TestClient

# Add src to path to match how routes_visual_composer imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app
from models.visual_composer_repository import (
    get_annotations,
    save_annotations,
    delete_annotations
)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def setup_test_data():
    """Set up test data and clean up after."""
    # Clear any existing annotations
    test_project_id = "test_project_123"
    if get_annotations(test_project_id):
        delete_annotations(test_project_id)
    
    yield test_project_id
    
    # Cleanup
    if get_annotations(test_project_id):
        delete_annotations(test_project_id)


def test_get_annotations_empty(client, setup_test_data):
    """Test GET annotations when none exist returns empty structure (not 500)."""
    project_id = setup_test_data
    
    response = client.get(f"/api/visual-composer/{project_id}/annotations")
    assert response.status_code == 200
    
    data = response.json()
    assert data["projectId"] == project_id
    assert data["regions"] == []


def test_post_and_get_annotations_round_trip(client, setup_test_data):
    """Test round-trip POST→GET persists the same structure."""
    project_id = setup_test_data
    
    # Create annotations with multiple regions, lanes, and blocks
    annotations_data = {
        "projectId": project_id,
        "regions": [
            {
                "regionId": "region_01",
                "regionName": "Intro",
                "notes": "Region notes here",
                "lanes": [
                    {
                        "id": "lane_01",
                        "name": "Growl Bass",
                        "color": "#FF4A4A",
                        "collapsed": False,
                        "order": 0
                    },
                    {
                        "id": "lane_02",
                        "name": "Drums",
                        "color": "#4A4AFF",
                        "collapsed": False,
                        "order": 1
                    }
                ],
                "blocks": [
                    {
                        "id": "block_01",
                        "laneId": "lane_01",
                        "startBar": 0.0,
                        "endBar": 4.0,
                        "color": "#FF7A7A",
                        "type": "call",
                        "notes": "formant sweep / gritty tail"
                    },
                    {
                        "id": "block_02",
                        "laneId": "lane_01",
                        "startBar": 4.0,
                        "endBar": 8.0,
                        "color": "#FF7A7A",
                        "type": "response",
                        "notes": "variation with more grit"
                    },
                    {
                        "id": "block_03",
                        "laneId": "lane_02",
                        "startBar": 0.0,
                        "endBar": 8.0,
                        "color": "#6A6AFF",
                        "type": "custom",
                        "notes": None
                    }
                ]
            },
            {
                "regionId": "region_02",
                "regionName": "Verse",
                "notes": None,
                "lanes": [
                    {
                        "id": "lane_03",
                        "name": "Vocals",
                        "color": "#4AFF4A",
                        "collapsed": True,
                        "order": 0
                    }
                ],
                "blocks": [
                    {
                        "id": "block_04",
                        "laneId": "lane_03",
                        "startBar": 8.0,
                        "endBar": 16.0,
                        "color": None,
                        "type": "variation",
                        "notes": "vocal variation"
                    }
                ]
            }
        ]
    }
    
    # POST annotations
    post_response = client.post(
        f"/api/visual-composer/{project_id}/annotations",
        json=annotations_data
    )
    assert post_response.status_code == 200
    
    post_data = post_response.json()
    assert post_data["projectId"] == project_id
    assert len(post_data["regions"]) == 2
    assert post_data["regions"][0]["regionId"] == "region_01"
    assert post_data["regions"][0]["regionName"] == "Intro"
    assert post_data["regions"][0]["notes"] == "Region notes here"
    assert len(post_data["regions"][0]["lanes"]) == 2
    assert len(post_data["regions"][0]["blocks"]) == 3
    assert post_data["regions"][0]["blocks"][0]["id"] == "block_01"
    assert post_data["regions"][0]["blocks"][0]["type"] == "call"
    assert post_data["regions"][0]["blocks"][0]["notes"] == "formant sweep / gritty tail"
    
    # GET annotations
    get_response = client.get(f"/api/visual-composer/{project_id}/annotations")
    assert get_response.status_code == 200
    
    get_data = get_response.json()
    assert get_data["projectId"] == project_id
    assert len(get_data["regions"]) == 2
    assert get_data["regions"][0]["regionId"] == "region_01"
    assert get_data["regions"][0]["regionName"] == "Intro"
    assert get_data["regions"][0]["notes"] == "Region notes here"
    assert len(get_data["regions"][0]["lanes"]) == 2
    assert len(get_data["regions"][0]["blocks"]) == 3
    assert get_data["regions"][0]["blocks"][0]["id"] == "block_01"
    assert get_data["regions"][0]["blocks"][0]["type"] == "call"
    assert get_data["regions"][0]["blocks"][0]["notes"] == "formant sweep / gritty tail"
    
    # Verify data matches exactly
    assert get_data == post_data


def test_post_annotations_force_project_id_match(client, setup_test_data):
    """Test that POST forces projectId in payload to match path parameter."""
    project_id = setup_test_data
    
    # Create annotations with mismatched project_id
    annotations_data = {
        "projectId": "wrong_id",
        "regions": []
    }
    
    # POST annotations - should override project_id
    response = client.post(
        f"/api/visual-composer/{project_id}/annotations",
        json=annotations_data
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["projectId"] == project_id  # Should be corrected
    assert data["projectId"] != "wrong_id"


def test_post_annotations_validation_error(client, setup_test_data):
    """Test POST annotations with invalid data returns validation error."""
    project_id = setup_test_data
    
    # Invalid: endBar <= startBar
    annotations_data = {
        "projectId": project_id,
        "regions": [
            {
                "regionId": "region_01",
                "lanes": [],
                "blocks": [
                    {
                        "id": "block_1",
                        "laneId": "lane_01",
                        "startBar": 4.0,
                        "endBar": 2.0,  # Invalid: end < start
                        "type": "custom"
                    }
                ]
            }
        ]
    }
    
    response = client.post(
        f"/api/visual-composer/{project_id}/annotations",
        json=annotations_data
    )
    assert response.status_code == 422  # Validation error


def test_post_annotations_invalid_block_type(client, setup_test_data):
    """Test POST annotations with invalid block type returns validation error."""
    project_id = setup_test_data
    
    # Invalid block type
    annotations_data = {
        "projectId": project_id,
        "regions": [
            {
                "regionId": "region_01",
                "lanes": [],
                "blocks": [
                    {
                        "id": "block_1",
                        "laneId": "lane_01",
                        "startBar": 0.0,
                        "endBar": 4.0,
                        "type": "invalid_type"  # Invalid
                    }
                ]
            }
        ]
    }
    
    response = client.post(
        f"/api/visual-composer/{project_id}/annotations",
        json=annotations_data
    )
    assert response.status_code == 422  # Validation error


def test_get_annotations_missing_project_returns_empty(client):
    """Test GET annotations for missing project returns empty structure (not 500)."""
    # Use a project ID that definitely doesn't exist
    project_id = "nonexistent_project_999"
    
    # Ensure it doesn't exist
    if get_annotations(project_id):
        delete_annotations(project_id)
    
    response = client.get(f"/api/visual-composer/{project_id}/annotations")
    assert response.status_code == 200  # Should return 200, not 500
    
    data = response.json()
    assert data["projectId"] == project_id
    assert data["regions"] == []

