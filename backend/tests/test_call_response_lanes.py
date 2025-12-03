"""Tests for call/response lanes service and endpoint."""
import pytest
import numpy as np
from pathlib import Path
import sys
import os

# Add src to path to match how routes_reference imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.models.region import Region
from src.models.reference_bundle import ReferenceBundle
from src.models.store import (
    REFERENCE_BUNDLES, REFERENCE_REGIONS, REFERENCE_CALL_RESPONSE,
    REFERENCE_MOTIF_INSTANCES_RAW
)
from src.stem_ingest.audio_file import AudioFile
from src.analysis.call_response_detector.call_response_detector import CallResponsePair
from src.analysis.call_response_detector.lanes_service import build_call_response_lanes
from src.analysis.call_response_detector.lanes_models import CallResponseByStemResponse
from src.analysis.motif_detector.motif_detector import MotifInstance


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


def test_build_call_response_lanes_basic():
    """Test building lanes from call/response pairs."""
    # Create test regions
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
        ),
        Region(
            id="region_02",
            name="Section 2",
            type="high_energy",
            start=30.0,
            end=60.0,
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    
    # Create test call/response pairs (bass call/response)
    pairs = [
        CallResponsePair(
            id="pair_01",
            from_motif_id="motif_bass_001",
            to_motif_id="motif_bass_002",
            from_stem_role="bass",
            to_stem_role="bass",
            from_time=5.0,  # 2.5 bars at 120 BPM
            to_time=9.0,    # 4.5 bars at 120 BPM
            time_offset=4.0,
            confidence=0.8,
            region_id="region_01"
        ),
        CallResponsePair(
            id="pair_02",
            from_motif_id="motif_drums_001",
            to_motif_id="motif_bass_003",
            from_stem_role="drums",
            to_stem_role="bass",
            from_time=35.0,  # Inter-stem pair
            to_time=37.0,
            time_offset=2.0,
            confidence=0.7,
            region_id="region_02"
        )
    ]
    
    bpm = 120.0
    reference_id = "test_ref_001"
    
    # Build lanes
    result = build_call_response_lanes(
        reference_id=reference_id,
        regions=regions,
        call_response_pairs=pairs,
        bpm=bpm
    )
    
    # Verify response structure
    assert isinstance(result, CallResponseByStemResponse)
    assert result.reference_id == reference_id
    assert len(result.regions) == 2
    assert result.regions == ["region_01", "region_02"]
    
    # Verify lanes
    assert len(result.lanes) > 0, "Should have at least one lane"
    
    # Find bass lane
    bass_lane = next((lane for lane in result.lanes if lane.stem == "bass"), None)
    assert bass_lane is not None, "Should have a bass lane"
    assert len(bass_lane.events) >= 2, "Bass lane should have at least 2 events (call + response)"
    
    # Verify events
    bass_events = bass_lane.events
    call_events = [e for e in bass_events if e.role == "call"]
    response_events = [e for e in bass_events if e.role == "response"]
    
    assert len(call_events) > 0, "Should have call events in bass lane"
    assert len(response_events) > 0, "Should have response events in bass lane"
    
    # Verify no full_mix lane
    full_mix_lane = next((lane for lane in result.lanes if lane.stem == "full_mix"), None)
    assert full_mix_lane is None, "Should not have a full_mix lane"
    
    # Verify events are in bar coordinates
    for event in bass_events:
        assert event.start_bar >= 0, "Start bar should be >= 0"
        assert event.end_bar > event.start_bar, "End bar should be > start bar"
        assert event.region_id in ["region_01", "region_02"], "Event should be in a valid region"


def test_build_call_response_lanes_excludes_full_mix():
    """Test that full_mix call/response pairs are excluded."""
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
    
    # Create pairs including full_mix
    pairs = [
        CallResponsePair(
            id="pair_01",
            from_motif_id="motif_bass_001",
            to_motif_id="motif_bass_002",
            from_stem_role="bass",
            to_stem_role="bass",
            from_time=5.0,
            to_time=9.0,
            time_offset=4.0,
            confidence=0.8,
            region_id="region_01"
        ),
        CallResponsePair(
            id="pair_02",
            from_motif_id="motif_full_mix_001",
            to_motif_id="motif_full_mix_002",
            from_stem_role="full_mix",
            to_stem_role="full_mix",
            from_time=10.0,
            to_time=14.0,
            time_offset=4.0,
            confidence=0.8,
            region_id="region_01"
        )
    ]
    
    result = build_call_response_lanes(
        reference_id="test_ref",
        regions=regions,
        call_response_pairs=pairs,
        bpm=120.0
    )
    
    # Should only have bass lane, not full_mix
    assert len(result.lanes) == 1, "Should have only one lane (bass)"
    assert result.lanes[0].stem == "bass", "Should be bass lane"
    assert len(result.lanes[0].events) == 2, "Bass lane should have 2 events"


def test_build_call_response_lanes_with_motif_instances():
    """Test building lanes with motif instances for accurate end times."""
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
    
    # Create motif instances
    motif_instances = [
        MotifInstance(
            id="motif_bass_001",
            stem_role="bass",
            start_time=5.0,
            end_time=7.0,  # 2 seconds duration
            features=np.array([1.0, 2.0, 3.0])
        ),
        MotifInstance(
            id="motif_bass_002",
            stem_role="bass",
            start_time=9.0,
            end_time=11.0,  # 2 seconds duration
            features=np.array([1.1, 2.1, 3.1])
        )
    ]
    
    pairs = [
        CallResponsePair(
            id="pair_01",
            from_motif_id="motif_bass_001",
            to_motif_id="motif_bass_002",
            from_stem_role="bass",
            to_stem_role="bass",
            from_time=5.0,
            to_time=9.0,
            time_offset=4.0,
            confidence=0.8,
            region_id="region_01"
        )
    ]
    
    result = build_call_response_lanes(
        reference_id="test_ref",
        regions=regions,
        call_response_pairs=pairs,
        bpm=120.0,
        motif_instances=motif_instances
    )
    
    # Verify events use actual motif end times
    bass_lane = result.lanes[0]
    call_event = next((e for e in bass_lane.events if e.role == "call"), None)
    response_event = next((e for e in bass_lane.events if e.role == "response"), None)
    
    assert call_event is not None
    assert response_event is not None
    
    # At 120 BPM, 2 seconds = 1 bar
    # Call: 5.0s to 7.0s = 2.5 bars to 3.5 bars
    # Response: 9.0s to 11.0s = 4.5 bars to 5.5 bars
    assert abs(call_event.start_bar - 2.5) < 0.1, "Call start should be ~2.5 bars"
    assert abs(call_event.end_bar - 3.5) < 0.1, "Call end should be ~3.5 bars"
    assert abs(response_event.start_bar - 4.5) < 0.1, "Response start should be ~4.5 bars"
    assert abs(response_event.end_bar - 5.5) < 0.1, "Response end should be ~5.5 bars"


@pytest.mark.asyncio
async def test_get_call_response_by_stem_endpoint():
    """Test GET /reference/{id}/call-response-by-stem endpoint."""
    from src.api import routes_reference
    import uuid
    
    # Create test reference
    reference_id = f"test_ref_{uuid.uuid4().hex[:8]}"
    bundle = create_test_bundle(duration=60.0, bpm=120.0)
    REFERENCE_BUNDLES[reference_id] = bundle
    
    # Create regions
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
        ),
        Region(
            id="region_02",
            name="Section 2",
            type="high_energy",
            start=30.0,
            end=60.0,
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    REFERENCE_REGIONS[reference_id] = regions
    
    # Create call/response pairs
    pairs = [
        CallResponsePair(
            id="pair_01",
            from_motif_id="motif_bass_001",
            to_motif_id="motif_bass_002",
            from_stem_role="bass",
            to_stem_role="bass",
            from_time=5.0,
            to_time=9.0,
            time_offset=4.0,
            confidence=0.8,
            region_id="region_01"
        )
    ]
    REFERENCE_CALL_RESPONSE[reference_id] = pairs
    
    try:
        # Call endpoint
        result = await routes_reference.get_call_response_by_stem(reference_id)
        
        # Verify response structure
        assert result.reference_id == reference_id
        assert len(result.regions) == 2
        assert len(result.lanes) > 0
        
        # Verify bass lane exists
        bass_lane = next((lane for lane in result.lanes if lane.stem == "bass"), None)
        assert bass_lane is not None, "Should have a bass lane"
        assert len(bass_lane.events) == 2, "Bass lane should have 2 events"
        
        # Verify no full_mix lane
        full_mix_lane = next((lane for lane in result.lanes if lane.stem == "full_mix"), None)
        assert full_mix_lane is None, "Should not have a full_mix lane"
        
    finally:
        # Cleanup
        REFERENCE_BUNDLES.pop(reference_id, None)
        REFERENCE_REGIONS.pop(reference_id, None)
        REFERENCE_CALL_RESPONSE.pop(reference_id, None)


@pytest.mark.asyncio
async def test_get_call_response_by_stem_not_found():
    """Test GET /reference/{id}/call-response-by-stem with non-existent reference."""
    from src.api import routes_reference
    from fastapi import HTTPException
    
    with pytest.raises(HTTPException) as exc_info:
        await routes_reference.get_call_response_by_stem("nonexistent_id")
    
    assert exc_info.value.status_code == 404


def test_detect_call_response_per_stem_only():
    """Test that call/response is detected within each stem separately."""
    from src.analysis.call_response_detector.call_response_detector import detect_call_response, CallResponseConfig
    from src.analysis.motif_detector.motif_detector import MotifInstance
    from collections import Counter
    
    # Create bass motifs in a call → response → response pattern
    # Motif 1 (call) at 0s
    call_features = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    bass_call = MotifInstance(
        id="bass_001",
        stem_role="bass",
        start_time=0.0,
        end_time=2.0,
        features=call_features
    )
    
    # Motif 2 (response) at 4s (similar features)
    response_features = np.array([1.1, 2.1, 3.1, 4.1, 5.1])
    bass_response1 = MotifInstance(
        id="bass_002",
        stem_role="bass",
        start_time=4.0,
        end_time=6.0,
        features=response_features
    )
    
    # Motif 3 (response) at 8s (similar features)
    bass_response2 = MotifInstance(
        id="bass_003",
        stem_role="bass",
        start_time=8.0,
        end_time=10.0,
        features=response_features
    )
    
    # Create drums motif (different stem, should not pair with bass)
    drums_motif = MotifInstance(
        id="drums_001",
        stem_role="drums",
        start_time=2.0,
        end_time=4.0,
        features=np.array([10.0, 20.0, 30.0, 40.0, 50.0])  # Different features
    )
    
    motifs = [bass_call, bass_response1, bass_response2, drums_motif]
    
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
        )
    ]
    
    bpm = 120.0
    config = CallResponseConfig(
        min_offset_bars=0.5,
        max_offset_bars=4.0,
        min_similarity=0.7,
        min_confidence=0.5,
        use_full_mix=False  # Stem-only mode
    )
    
    pairs = detect_call_response(motifs, regions, bpm, config)
    
    # Should find pairs within bass stem only
    bass_pairs = [p for p in pairs if p.from_stem_role == "bass" and p.to_stem_role == "bass"]
    drums_pairs = [p for p in pairs if p.from_stem_role == "drums" and p.to_stem_role == "drums"]
    inter_stem_pairs = [p for p in pairs if p.from_stem_role != p.to_stem_role]
    
    # Should have bass pairs (call → response pattern)
    assert len(bass_pairs) > 0, "Should find call/response pairs within bass stem"
    
    # Should not have inter-stem pairs (bass ↔ drums)
    assert len(inter_stem_pairs) == 0, "Should not have inter-stem pairs when processing per-stem"
    
    # All pairs should be intra-stem
    assert all(p.is_intra_stem for p in pairs), "All pairs should be intra-stem"
    assert all(not p.is_inter_stem for p in pairs), "No pairs should be inter-stem"
    
    # Verify pairs are tagged correctly
    for pair in bass_pairs:
        assert pair.from_stem_role == "bass", "Bass pair should have from_stem_role='bass'"
        assert pair.to_stem_role == "bass", "Bass pair should have to_stem_role='bass'"
    
    # Count pairs by stem
    pairs_by_stem = Counter([p.from_stem_role for p in pairs])
    assert "bass" in pairs_by_stem, "Should have pairs for bass stem"
    assert pairs_by_stem.get("bass", 0) > 0, "Should have at least one bass pair"


def test_build_call_response_lanes_per_stem_pattern():
    """Test building lanes with per-stem call → response → response pattern."""
    from src.analysis.call_response_detector.call_response_detector import CallResponsePair
    
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
        )
    ]
    
    # Create bass call → response → response pattern (all intra-stem)
    pairs = [
        CallResponsePair(
            id="pair_01",
            from_motif_id="bass_001",
            to_motif_id="bass_002",
            from_stem_role="bass",
            to_stem_role="bass",
            from_time=0.0,
            to_time=4.0,
            time_offset=4.0,
            confidence=0.8,
            region_id="region_01"
        ),
        CallResponsePair(
            id="pair_02",
            from_motif_id="bass_001",
            to_motif_id="bass_003",
            from_stem_role="bass",
            to_stem_role="bass",
            from_time=0.0,
            to_time=8.0,
            time_offset=8.0,
            confidence=0.75,
            region_id="region_01"
        )
    ]
    
    # Create motif instances for accurate end times
    motif_instances = [
        MotifInstance(
            id="bass_001",
            stem_role="bass",
            start_time=0.0,
            end_time=2.0,
            features=np.array([1.0, 2.0, 3.0])
        ),
        MotifInstance(
            id="bass_002",
            stem_role="bass",
            start_time=4.0,
            end_time=6.0,
            features=np.array([1.1, 2.1, 3.1])
        ),
        MotifInstance(
            id="bass_003",
            stem_role="bass",
            start_time=8.0,
            end_time=10.0,
            features=np.array([1.2, 2.2, 3.2])
        )
    ]
    
    bpm = 120.0
    result = build_call_response_lanes(
        reference_id="test_ref",
        regions=regions,
        call_response_pairs=pairs,
        bpm=bpm,
        motif_instances=motif_instances
    )
    
    # Should have one lane with stem="bass"
    assert len(result.lanes) == 1, "Should have exactly one lane (bass)"
    bass_lane = result.lanes[0]
    assert bass_lane.stem == "bass", "Lane should be for bass stem"
    
    # Should have multiple events (1 call + 2 responses)
    assert len(bass_lane.events) == 3, "Should have 3 events (1 call + 2 responses)"
    
    # Verify call event
    call_events = [e for e in bass_lane.events if e.role == "call"]
    assert len(call_events) == 1, "Should have exactly one call event"
    assert call_events[0].stem == "bass", "Call event should be in bass lane"
    
    # Verify response events
    response_events = [e for e in bass_lane.events if e.role == "response"]
    assert len(response_events) == 2, "Should have exactly two response events"
    assert all(e.stem == "bass" for e in response_events), "All response events should be in bass lane"
    
    # Verify events are sorted by start_bar
    start_bars = [e.start_bar for e in bass_lane.events]
    assert start_bars == sorted(start_bars), "Events should be sorted by start_bar"
    
    # Verify no other stem lanes
    assert all(lane.stem == "bass" for lane in result.lanes), "All lanes should be bass"

