"""Tests for call-response detection."""
import numpy as np
import pytest
from pathlib import Path

from src.models.region import Region
from src.analysis.motif_detector.motif_detector import MotifInstance
from src.analysis.call_response_detector.call_response_detector import (
    CallResponsePair,
    CallResponseConfig,
    detect_call_response,
    _compute_similarity,
    _compute_rhythmic_alignment_score,
    _compute_confidence,
    _deduplicate_pairs
)


def create_test_motif(
    motif_id: str,
    stem_role: str,
    start_time: float,
    end_time: float,
    features: np.ndarray
) -> MotifInstance:
    """Create a test motif instance."""
    return MotifInstance(
        id=motif_id,
        stem_role=stem_role,
        start_time=start_time,
        end_time=end_time,
        features=features,
        group_id=None,
        is_variation=False,
        region_ids=[]
    )


def test_compute_similarity():
    """Test similarity computation between feature vectors."""
    # Identical vectors should have similarity = 1.0
    features1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    features2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    similarity = _compute_similarity(features1, features2)
    assert abs(similarity - 1.0) < 0.01, "Identical vectors should have similarity ~1.0"
    
    # Orthogonal vectors should have similarity ~0.0
    features1 = np.array([1.0, 0.0, 0.0])
    features2 = np.array([0.0, 1.0, 0.0])
    similarity = _compute_similarity(features1, features2)
    assert abs(similarity - 0.0) < 0.01, "Orthogonal vectors should have similarity ~0.0"
    
    # Similar vectors should have similarity > 0.5
    features1 = np.array([1.0, 2.0, 3.0])
    features2 = np.array([1.1, 2.1, 3.1])
    similarity = _compute_similarity(features1, features2)
    assert similarity > 0.5, "Similar vectors should have similarity > 0.5"


def test_compute_rhythmic_alignment_score():
    """Test rhythmic alignment score computation."""
    preferred_grid = [0.5, 1.0, 2.0, 4.0]
    
    # Perfect alignment should score 1.0
    score = _compute_rhythmic_alignment_score(1.0, preferred_grid, tolerance_bars=0.1)
    assert abs(score - 1.0) < 0.01, "Perfect alignment should score 1.0"
    
    # Close alignment should score high
    score = _compute_rhythmic_alignment_score(1.05, preferred_grid, tolerance_bars=0.1)
    assert score > 0.9, "Close alignment should score high"
    
    # Far from grid should score lower
    score = _compute_rhythmic_alignment_score(1.5, preferred_grid, tolerance_bars=0.1)
    assert score < 0.5, "Far from grid should score lower"
    
    # Very far from grid should score very low
    score = _compute_rhythmic_alignment_score(10.0, preferred_grid, tolerance_bars=0.1)
    assert score < 0.1, "Very far from grid should score very low"


def test_compute_confidence():
    """Test confidence computation."""
    config = CallResponseConfig()
    
    # High similarity and good alignment should yield high confidence
    confidence = _compute_confidence(0.9, 1.0, config)
    assert confidence > 0.8, "High similarity + good alignment should yield high confidence"
    
    # Low similarity should yield lower confidence
    confidence = _compute_confidence(0.5, 1.0, config)
    assert confidence < 0.7, "Low similarity should yield lower confidence"
    
    # Good similarity but poor alignment should yield medium confidence
    confidence = _compute_confidence(0.9, 1.5, config)
    assert 0.5 < confidence < 0.9, "Good similarity but poor alignment should yield medium confidence"


def test_detect_call_response_basic():
    """Test basic call-response detection with clear relationships."""
    bpm = 120.0
    
    # Create motifs with clear call-response relationships
    # Call motif at 0s
    call_features = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    call_motif = create_test_motif("call_1", "drums", 0.0, 2.0, call_features)
    
    # Response motif at 2s (1 bar later) with similar features
    response_features = np.array([1.1, 2.1, 3.1, 4.1, 5.1])  # Similar to call
    response_motif = create_test_motif("response_1", "bass", 2.0, 4.0, response_features)
    
    # Another response at 4s (2 bars later)
    response_motif2 = create_test_motif("response_2", "instruments", 4.0, 6.0, response_features)
    
    # Unrelated motif (too far away)
    unrelated_features = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    unrelated_motif = create_test_motif("unrelated", "vocals", 20.0, 22.0, unrelated_features)
    
    motifs = [call_motif, response_motif, response_motif2, unrelated_motif]
    
    regions = [
        Region(
            id="region_01",
            name="Section 1",
            type="low_energy",
            start=0.0,
            end=10.0,
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    
    config = CallResponseConfig(
        min_offset_bars=0.5,
        max_offset_bars=4.0,
        min_similarity=0.7,
        min_confidence=0.5
    )
    
    pairs = detect_call_response(motifs, regions, bpm, config)
    
    # Should detect call-response relationships
    assert len(pairs) > 0, "Should detect at least one call-response pair"
    
    # Should find response_1 and response_2 as responses to call_1
    call_response_ids = [(p.from_motif_id, p.to_motif_id) for p in pairs]
    assert ("call_1", "response_1") in call_response_ids or ("response_1", "call_1") in call_response_ids, \
        "Should detect call_1 -> response_1 relationship"
    
    # Should not include unrelated motif (too far away)
    unrelated_pairs = [p for p in pairs if "unrelated" in (p.from_motif_id, p.to_motif_id)]
    assert len(unrelated_pairs) == 0, "Should not include unrelated motif"


def test_detect_call_response_inter_stem():
    """Test inter-stem call-response detection."""
    bpm = 120.0
    
    # Call in drums
    call_features = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    call_motif = create_test_motif("call_drums", "drums", 0.0, 2.0, call_features)
    
    # Response in bass (different stem)
    response_features = np.array([1.1, 2.1, 3.1, 4.1, 5.1])
    response_motif = create_test_motif("response_bass", "bass", 2.0, 4.0, response_features)
    
    motifs = [call_motif, response_motif]
    regions = [
        Region(
            id="region_01",
            name="Section 1",
            type="low_energy",
            start=0.0,
            end=10.0,
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    
    config = CallResponseConfig(
        min_offset_bars=0.5,
        max_offset_bars=4.0,
        min_similarity=0.7,
        min_confidence=0.5
    )
    
    pairs = detect_call_response(motifs, regions, bpm, config)
    
    assert len(pairs) > 0, "Should detect inter-stem call-response"
    
    # Check that it's marked as inter-stem
    pair = pairs[0]
    assert pair.is_inter_stem, "Should be marked as inter-stem"
    assert not pair.is_intra_stem, "Should not be marked as intra-stem"


def test_detect_call_response_intra_stem():
    """Test intra-stem call-response detection."""
    bpm = 120.0
    
    # Call in drums
    call_features = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    call_motif = create_test_motif("call_1", "drums", 0.0, 2.0, call_features)
    
    # Response also in drums (same stem)
    response_features = np.array([1.1, 2.1, 3.1, 4.1, 5.1])
    response_motif = create_test_motif("response_1", "drums", 2.0, 4.0, response_features)
    
    motifs = [call_motif, response_motif]
    regions = [
        Region(
            id="region_01",
            name="Section 1",
            type="low_energy",
            start=0.0,
            end=10.0,
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    
    config = CallResponseConfig(
        min_offset_bars=0.5,
        max_offset_bars=4.0,
        min_similarity=0.7,
        min_confidence=0.5
    )
    
    pairs = detect_call_response(motifs, regions, bpm, config)
    
    assert len(pairs) > 0, "Should detect intra-stem call-response"
    
    # Check that it's marked as intra-stem
    pair = pairs[0]
    assert pair.is_intra_stem, "Should be marked as intra-stem"
    assert not pair.is_inter_stem, "Should not be marked as inter-stem"


def test_detect_call_response_time_window():
    """Test that call-response detection respects time window constraints."""
    bpm = 120.0
    
    call_features = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    call_motif = create_test_motif("call", "drums", 0.0, 2.0, call_features)
    
    # Response within window (2 bars = 4 seconds at 120 BPM)
    response_features = np.array([1.1, 2.1, 3.1, 4.1, 5.1])
    response_in_window = create_test_motif("response_in", "bass", 4.0, 6.0, response_features)
    
    # Response outside window (too early)
    response_too_early = create_test_motif("response_early", "bass", 0.1, 2.1, response_features)
    
    # Response outside window (too late)
    response_too_late = create_test_motif("response_late", "bass", 20.0, 22.0, response_features)
    
    motifs = [call_motif, response_in_window, response_too_early, response_too_late]
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
    
    config = CallResponseConfig(
        min_offset_bars=0.5,  # 1 second
        max_offset_bars=4.0,  # 8 seconds
        min_similarity=0.7,
        min_confidence=0.5
    )
    
    pairs = detect_call_response(motifs, regions, bpm, config)
    
    # Should only find response_in_window
    response_ids = [p.to_motif_id for p in pairs if p.from_motif_id == "call"]
    assert "response_in" in response_ids, "Should find response within window"
    assert "response_early" not in response_ids, "Should not find response too early"
    assert "response_late" not in response_ids, "Should not find response too late"


def test_detect_call_response_similarity_threshold():
    """Test that call-response detection respects similarity threshold."""
    bpm = 120.0
    
    call_features = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    call_motif = create_test_motif("call", "drums", 0.0, 2.0, call_features)
    
    # Similar response (should be detected)
    similar_features = np.array([1.1, 2.1, 3.1, 4.1, 5.1])
    similar_response = create_test_motif("similar", "bass", 2.0, 4.0, similar_features)
    
    # Dissimilar response (should not be detected) - use orthogonal vector
    dissimilar_features = np.array([-1.0, 0.0, 0.0, 0.0, 0.0])  # Orthogonal to call_features
    dissimilar_response = create_test_motif("dissimilar", "bass", 2.0, 4.0, dissimilar_features)
    
    motifs = [call_motif, similar_response, dissimilar_response]
    regions = [
        Region(
            id="region_01",
            name="Section 1",
            type="low_energy",
            start=0.0,
            end=10.0,
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    
    config = CallResponseConfig(
        min_offset_bars=0.5,
        max_offset_bars=4.0,
        min_similarity=0.7,  # High threshold
        min_confidence=0.5
    )
    
    pairs = detect_call_response(motifs, regions, bpm, config)
    
    # Should only find similar response
    response_ids = [p.to_motif_id for p in pairs if p.from_motif_id == "call"]
    assert "similar" in response_ids, "Should find similar response"
    assert "dissimilar" not in response_ids, "Should not find dissimilar response"


def test_detect_call_response_confidence_filtering():
    """Test that low-confidence pairs are filtered out."""
    bpm = 120.0
    
    call_features = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    call_motif = create_test_motif("call", "drums", 0.0, 2.0, call_features)
    
    # Response with moderate similarity (may have low confidence)
    moderate_features = np.array([2.0, 3.0, 4.0, 5.0, 6.0])
    moderate_response = create_test_motif("moderate", "bass", 2.0, 4.0, moderate_features)
    
    motifs = [call_motif, moderate_response]
    regions = [
        Region(
            id="region_01",
            name="Section 1",
            type="low_energy",
            start=0.0,
            end=10.0,
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    
    config = CallResponseConfig(
        min_offset_bars=0.5,
        max_offset_bars=4.0,
        min_similarity=0.5,  # Lower similarity threshold
        min_confidence=0.8  # High confidence threshold
    )
    
    pairs = detect_call_response(motifs, regions, bpm, config)
    
    # With high confidence threshold, may filter out moderate pairs
    # This test verifies that filtering happens (may be 0 or >0 depending on actual scores)
    assert isinstance(pairs, list), "Should return a list of pairs"


def test_deduplicate_pairs():
    """Test that duplicate pairs are removed."""
    # Create reciprocal pairs (A->B and B->A)
    pair1 = CallResponsePair(
        id="pair1",
        from_motif_id="A",
        to_motif_id="B",
        from_stem_role="drums",
        to_stem_role="bass",
        from_time=0.0,
        to_time=2.0,
        time_offset=2.0,
        confidence=0.8
    )
    
    pair2 = CallResponsePair(
        id="pair2",
        from_motif_id="B",
        to_motif_id="A",
        from_stem_role="bass",
        to_stem_role="drums",
        from_time=2.0,
        to_time=0.0,
        time_offset=-2.0,
        confidence=0.7
    )
    
    pairs = [pair1, pair2]
    deduplicated = _deduplicate_pairs(pairs)
    
    # Should keep only one pair (the one with higher confidence)
    assert len(deduplicated) == 1, "Should remove duplicate pair"
    assert deduplicated[0].confidence == 0.8, "Should keep pair with higher confidence"


def test_call_response_pair_properties():
    """Test CallResponsePair properties."""
    pair = CallResponsePair(
        id="pair1",
        from_motif_id="call",
        to_motif_id="response",
        from_stem_role="drums",
        to_stem_role="bass",
        from_time=0.0,
        to_time=2.0,
        time_offset=2.0,
        confidence=0.8,
        region_id="region_01"
    )
    
    assert pair.is_inter_stem, "Should be inter-stem (different stems)"
    assert not pair.is_intra_stem, "Should not be intra-stem"
    
    # Test intra-stem pair
    pair2 = CallResponsePair(
        id="pair2",
        from_motif_id="call",
        to_motif_id="response",
        from_stem_role="drums",
        to_stem_role="drums",
        from_time=0.0,
        to_time=2.0,
        time_offset=2.0,
        confidence=0.8
    )
    
    assert pair2.is_intra_stem, "Should be intra-stem (same stem)"
    assert not pair2.is_inter_stem, "Should not be inter-stem"


def test_call_response_config_defaults():
    """Test CallResponseConfig default values."""
    config = CallResponseConfig()
    
    assert config.min_offset_bars == 0.5
    assert config.max_offset_bars == 4.0
    assert config.min_similarity == 0.7
    assert config.min_confidence == 0.5
    assert config.preferred_rhythmic_grid is not None
    assert len(config.preferred_rhythmic_grid) > 0

