"""Unit tests for subregion models."""
import pytest
from analysis.subregions.models import (
    StemCategory,
    SubRegionPattern,
    RegionSubRegions,
    SubRegionPatternDTO,
    RegionSubRegionsDTO
)


def test_subregion_pattern_creation():
    """Test creating a SubRegionPattern."""
    pattern = SubRegionPattern(
        id="test_1",
        region_id="region_01",
        stem_category="drums",
        start_bar=0.0,
        end_bar=2.0,
        label="Pat A",
        motif_group_id="group_1",
        is_variation=False,
        is_silence=False,
        intensity=0.8
    )
    
    assert pattern.id == "test_1"
    assert pattern.region_id == "region_01"
    assert pattern.stem_category == "drums"
    assert pattern.start_bar == 0.0
    assert pattern.end_bar == 2.0
    assert pattern.label == "Pat A"
    assert pattern.motif_group_id == "group_1"
    assert pattern.intensity == 0.8


def test_subregion_pattern_validation():
    """Test SubRegionPattern validation."""
    # Test invalid start_bar
    with pytest.raises(ValueError, match="start_bar must be >= 0"):
        SubRegionPattern(
            id="test",
            region_id="region_01",
            stem_category="drums",
            start_bar=-1.0,
            end_bar=2.0
        )
    
    # Test invalid end_bar
    with pytest.raises(ValueError, match="end_bar must be > start_bar"):
        SubRegionPattern(
            id="test",
            region_id="region_01",
            stem_category="drums",
            start_bar=2.0,
            end_bar=1.0
        )
    
    # Test invalid intensity
    with pytest.raises(ValueError, match="intensity must be between 0.0 and 1.0"):
        SubRegionPattern(
            id="test",
            region_id="region_01",
            stem_category="drums",
            start_bar=0.0,
            end_bar=2.0,
            intensity=1.5
        )
    
    # Test empty id
    with pytest.raises(ValueError, match="id cannot be empty"):
        SubRegionPattern(
            id="",
            region_id="region_01",
            stem_category="drums",
            start_bar=0.0,
            end_bar=2.0
        )


def test_region_subregions_creation():
    """Test creating a RegionSubRegions."""
    patterns = {
        "drums": [
            SubRegionPattern(
                id="drum_1",
                region_id="region_01",
                stem_category="drums",
                start_bar=0.0,
                end_bar=2.0
            )
        ],
        "bass": [],
        "vocals": [],
        "instruments": []
    }
    
    region_subregions = RegionSubRegions(
        region_id="region_01",
        lanes=patterns
    )
    
    assert region_subregions.region_id == "region_01"
    assert len(region_subregions.lanes) == 4
    assert len(region_subregions.lanes["drums"]) == 1
    assert len(region_subregions.lanes["bass"]) == 0


def test_region_subregions_auto_fills_missing_categories():
    """Test that RegionSubRegions automatically fills missing stem categories."""
    # Create with only drums
    patterns = {
        "drums": [
            SubRegionPattern(
                id="drum_1",
                region_id="region_01",
                stem_category="drums",
                start_bar=0.0,
                end_bar=2.0
            )
        ]
    }
    
    region_subregions = RegionSubRegions(
        region_id="region_01",
        lanes=patterns
    )
    
    # Should have all 4 categories
    assert "drums" in region_subregions.lanes
    assert "bass" in region_subregions.lanes
    assert "vocals" in region_subregions.lanes
    assert "instruments" in region_subregions.lanes
    assert len(region_subregions.lanes["bass"]) == 0


def test_subregion_pattern_dto_serialization():
    """Test Pydantic DTO serialization."""
    pattern = SubRegionPattern(
        id="test_1",
        region_id="region_01",
        stem_category="drums",
        start_bar=0.0,
        end_bar=2.0,
        label="Pat A",
        motif_group_id="group_1",
        is_variation=True,
        is_silence=False,
        intensity=0.8
    )
    
    dto = SubRegionPatternDTO.model_validate(pattern)
    assert dto.id == "test_1"
    assert dto.region_id == "region_01"
    assert dto.stem_category == "drums"
    
    # Test JSON serialization with aliases
    json_data = dto.model_dump(by_alias=True)
    assert "regionId" in json_data
    assert "stemCategory" in json_data
    assert "startBar" in json_data
    assert "endBar" in json_data
    assert "motifGroupId" in json_data
    assert "isVariation" in json_data
    assert "isSilence" in json_data


def test_region_subregions_dto_serialization():
    """Test RegionSubRegions DTO serialization."""
    patterns = {
        "drums": [
            SubRegionPattern(
                id="drum_1",
                region_id="region_01",
                stem_category="drums",
                start_bar=0.0,
                end_bar=2.0,
                intensity=0.7
            )
        ],
        "bass": [],
        "vocals": [],
        "instruments": []
    }
    
    region_subregions = RegionSubRegions(
        region_id="region_01",
        lanes=patterns
    )
    
    dto = RegionSubRegionsDTO.model_validate(region_subregions)
    assert dto.region_id == "region_01"
    assert len(dto.lanes) == 4
    assert len(dto.lanes["drums"]) == 1
    
    # Test JSON serialization
    json_data = dto.model_dump(by_alias=True)
    assert "regionId" in json_data
    assert "lanes" in json_data
    assert "drums" in json_data["lanes"]
    assert len(json_data["lanes"]["drums"]) == 1

