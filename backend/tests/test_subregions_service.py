"""Unit tests for subregion service."""
import pytest
import numpy as np
from models.region import Region
from models.reference_bundle import ReferenceBundle
from stem_ingest.audio_file import AudioFile
from pathlib import Path
from analysis.subregions.service import (
    compute_region_subregions,
    seconds_to_bars,
    DensityCurves,
    _find_motifs_in_chunk
)
from analysis.motif_detector.motif_detector import MotifInstance, MotifGroup
from config import DEFAULT_SUBREGION_BARS_PER_CHUNK, DEFAULT_SUBREGION_SILENCE_INTENSITY_THRESHOLD


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
    bundle = create_test_bundle(duration=32.0, bpm=120.0)
    
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
    
    # Create empty motifs and groups
    motifs: list[MotifInstance] = []
    motif_groups: list[MotifGroup] = []
    density_curves = DensityCurves(bundle)
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
    
    # Each lane should have 4 chunks (8 bars / 2 bars per chunk)
    for stem_category in ["drums", "bass", "vocals", "instruments"]:
        assert len(region_01_subregions.lanes[stem_category]) == 4
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


def create_test_bundle(duration: float = 60.0, bpm: float = 120.0) -> ReferenceBundle:
    """Create a test reference bundle with synthetic audio."""
    sr = 44100
    t = np.linspace(0, duration, int(sr * duration))
    
    # Create different frequencies for each stem
    drums_samples = 0.5 * np.sin(2 * np.pi * 220 * t)
    bass_samples = 0.3 * np.sin(2 * np.pi * 110 * t)
    vocals_samples = 0.3 * np.sin(2 * np.pi * 440 * t)
    instruments_samples = 0.3 * np.sin(2 * np.pi * 660 * t)
    full_mix_samples = 0.5 * np.sin(2 * np.pi * 440 * t)
    
    drums = AudioFile(
        path=Path("drums.wav"),
        role="drums",
        sr=sr,
        duration=duration,
        channels=1,
        samples=drums_samples
    )
    bass = AudioFile(
        path=Path("bass.wav"),
        role="bass",
        sr=sr,
        duration=duration,
        channels=1,
        samples=bass_samples
    )
    vocals = AudioFile(
        path=Path("vocals.wav"),
        role="vocals",
        sr=sr,
        duration=duration,
        channels=1,
        samples=vocals_samples
    )
    instruments = AudioFile(
        path=Path("instruments.wav"),
        role="instruments",
        sr=sr,
        duration=duration,
        channels=1,
        samples=instruments_samples
    )
    full_mix = AudioFile(
        path=Path("full_mix.wav"),
        role="full_mix",
        sr=sr,
        duration=duration,
        channels=1,
        samples=full_mix_samples
    )
    
    return ReferenceBundle(
        drums=drums,
        bass=bass,
        vocals=vocals,
        instruments=instruments,
        full_mix=full_mix,
        bpm=bpm
    )


def test_compute_region_subregions_with_real_data():
    """Test subregion computation with real density curves and motifs."""
    # Create test bundle
    bundle = create_test_bundle(duration=32.0, bpm=120.0)  # 16 bars at 120 BPM
    
    # Create a region of 8 bars (16 seconds)
    regions = [
        Region(
            id="region_01",
            name="Verse",
            type="medium_energy",
            start=0.0,
            end=16.0,  # 8 bars at 120 BPM
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    
    # Create test motifs
    # Drums: motif in first 4 bars (0-8 seconds)
    drums_motif = MotifInstance(
        id="motif_drums_1",
        stem_role="drums",
        start_time=0.0,
        end_time=8.0,
        features=np.array([1.0, 2.0, 3.0]),
        group_id="group_1",
        is_variation=False,
        region_ids=["region_01"]
    )
    
    # Bass: same motif group, repeating
    bass_motif = MotifInstance(
        id="motif_bass_1",
        stem_role="bass",
        start_time=0.0,
        end_time=8.0,
        features=np.array([1.0, 2.0, 3.0]),
        group_id="group_1",
        is_variation=False,
        region_ids=["region_01"]
    )
    
    # Vocals: active only in middle 4 bars (8-16 seconds)
    vocals_motif = MotifInstance(
        id="motif_vocals_1",
        stem_role="vocals",
        start_time=8.0,
        end_time=16.0,
        features=np.array([2.0, 3.0, 4.0]),
        group_id="group_2",
        is_variation=False,
        region_ids=["region_01"]
    )
    
    # Drums fill/variation in last 2 bars (14-16 seconds)
    drums_fill = MotifInstance(
        id="motif_drums_fill",
        stem_role="drums",
        start_time=14.0,
        end_time=16.0,
        features=np.array([1.5, 2.5, 3.5]),
        group_id="group_1",
        is_variation=True,  # This is a variation
        region_ids=["region_01"]
    )
    
    motifs = [drums_motif, bass_motif, vocals_motif, drums_fill]
    
    # Create motif groups
    motif_groups = [
        MotifGroup(
            id="group_1",
            members=[drums_motif, bass_motif, drums_fill],
            label="Main Pattern"
        ),
        MotifGroup(
            id="group_2",
            members=[vocals_motif],
            label="Vocal Pattern"
        )
    ]
    
    # Create density curves
    density_curves = DensityCurves(bundle)
    
    # Compute subregions with 2 bars per chunk (should create 4 chunks for 8-bar region)
    result = compute_region_subregions(
        regions=regions,
        motifs=motifs,
        motif_groups=motif_groups,
        density_curves=density_curves,
        bpm=bundle.bpm,
        bars_per_chunk=2
    )
    
    # Should have one region
    assert len(result) == 1
    region_subregions = result[0]
    
    # Should have 4 chunks per stem (8 bars / 2 bars per chunk)
    for stem_category in ["drums", "bass", "vocals", "instruments"]:
        patterns = region_subregions.lanes[stem_category]
        assert len(patterns) == 4, f"Expected 4 chunks for {stem_category}, got {len(patterns)}"
    
    # Check drums: first chunk should have motif, last chunk should be variation
    drums_patterns = region_subregions.lanes["drums"]
    assert drums_patterns[0].motif_group_id == "group_1"
    assert drums_patterns[0].is_variation is False
    assert drums_patterns[3].motif_group_id == "group_1"
    assert drums_patterns[3].is_variation is True  # Fill is a variation
    
    # Check bass: first chunk should have motif
    bass_patterns = region_subregions.lanes["bass"]
    assert bass_patterns[0].motif_group_id == "group_1"
    
    # Check vocals: first two chunks should be silence, last two should have motif
    vocals_patterns = region_subregions.lanes["vocals"]
    # First chunk (0-2 bars) should have no motif (vocals start at 8 seconds = 4 bars)
    assert vocals_patterns[0].motif_group_id is None or vocals_patterns[0].is_silence
    # Third chunk (4-6 bars, i.e., 8-12 seconds) should have motif
    assert vocals_patterns[2].motif_group_id == "group_2"


def test_compute_region_subregions_silence_detection():
    """Test that silence detection works correctly."""
    # Create bundle with very quiet audio (should trigger silence)
    bundle = create_test_bundle(duration=16.0, bpm=120.0)
    
    # Make vocals very quiet
    bundle.vocals.samples = bundle.vocals.samples * 0.01  # 1% amplitude
    
    regions = [
        Region(
            id="region_01",
            name="Test",
            type="low_energy",
            start=0.0,
            end=16.0,
            motifs=[],
            fills=[],
            callResponse=[]
        )
    ]
    
    motifs: list[MotifInstance] = []
    motif_groups: list[MotifGroup] = []
    density_curves = DensityCurves(bundle)
    
    # Use a higher silence threshold to catch the quiet vocals
    result = compute_region_subregions(
        regions=regions,
        motifs=motifs,
        motif_groups=motif_groups,
        density_curves=density_curves,
        bpm=bundle.bpm,
        bars_per_chunk=2,
        silence_threshold=0.05  # Lower threshold
    )
    
    vocals_patterns = result[0].lanes["vocals"]
    # Vocals should be marked as silence
    assert all(p.is_silence for p in vocals_patterns), "Quiet vocals should be marked as silence"
    assert all(p.intensity < 0.05 for p in vocals_patterns), "Quiet vocals should have low intensity"


def test_find_motifs_in_chunk():
    """Test the _find_motifs_in_chunk helper function."""
    # Create test motifs
    motif1 = MotifInstance(
        id="m1",
        stem_role="drums",
        start_time=2.0,
        end_time=6.0,
        features=np.array([1.0]),
        group_id="group_1",
        is_variation=False,
        region_ids=[]
    )
    
    motif2 = MotifInstance(
        id="m2",
        stem_role="drums",
        start_time=8.0,
        end_time=12.0,
        features=np.array([2.0]),
        group_id="group_1",
        is_variation=True,  # This is a variation
        region_ids=[]
    )
    
    motif3 = MotifInstance(
        id="m3",
        stem_role="bass",
        start_time=2.0,
        end_time=6.0,
        features=np.array([3.0]),
        group_id="group_2",
        is_variation=False,
        region_ids=[]
    )
    
    motifs = [motif1, motif2, motif3]
    
    motif_groups = [
        MotifGroup(id="group_1", members=[motif1, motif2], label="Pattern A"),
        MotifGroup(id="group_2", members=[motif3], label="Pattern B")
    ]
    
    # Test chunk that overlaps with motif1 (drums, 0-4 seconds)
    group_id, is_variation, label = _find_motifs_in_chunk(
        motifs, motif_groups, "drums", 0.0, 4.0
    )
    assert group_id == "group_1"
    assert is_variation is False
    assert label == "Pattern A"
    
    # Test chunk that overlaps with motif2 (drums, 6-10 seconds) - variation
    group_id, is_variation, label = _find_motifs_in_chunk(
        motifs, motif_groups, "drums", 6.0, 10.0
    )
    assert group_id == "group_1"
    assert is_variation is True  # motif2 is a variation
    assert label == "Pattern A"
    
    # Test chunk with no motifs (drums, 14-18 seconds)
    group_id, is_variation, label = _find_motifs_in_chunk(
        motifs, motif_groups, "drums", 14.0, 18.0
    )
    assert group_id is None
    assert is_variation is False
    assert label is None
    
    # Test bass chunk (should find motif3)
    group_id, is_variation, label = _find_motifs_in_chunk(
        motifs, motif_groups, "bass", 0.0, 4.0
    )
    assert group_id == "group_2"
    assert is_variation is False
    assert label == "Pattern B"


def test_density_curves_computation():
    """Test DensityCurves class computes RMS envelopes correctly."""
    bundle = create_test_bundle(duration=10.0, bpm=120.0)
    
    density_curves = DensityCurves(bundle)
    
    # Check that all stem categories have curves
    for stem_category in ["drums", "bass", "vocals", "instruments"]:
        assert stem_category in density_curves._rms_curves
        assert stem_category in density_curves._time_arrays
        assert len(density_curves._rms_curves[stem_category]) > 0
    
    # Test intensity retrieval
    intensity = density_curves.get_intensity("drums", 0.0, 2.0)
    assert 0.0 <= intensity <= 1.0
    
    # Test that quiet sections have lower intensity
    # (This depends on the synthetic audio, but should generally hold)
    intensity_full = density_curves.get_intensity("drums", 0.0, 10.0)
    assert intensity_full > 0.0


def test_compute_region_subregions_bar_positions():
    """Test that bar positions are correctly computed from region times."""
    bundle = create_test_bundle(duration=16.0, bpm=120.0)
    
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
    density_curves = DensityCurves(bundle)
    bpm = 120.0
    
    result = compute_region_subregions(
        regions=regions,
        motifs=motifs,
        motif_groups=motif_groups,
        density_curves=density_curves,
        bpm=bpm,
        bars_per_chunk=2
    )
    
    # Should have 2 chunks (4 bars / 2 bars per chunk)
    patterns = result[0].lanes["drums"]
    assert len(patterns) == 2
    
    # Check bar positions
    assert abs(patterns[0].start_bar - 0.0) < 0.1
    assert abs(patterns[0].end_bar - 2.0) < 0.1
    assert abs(patterns[1].start_bar - 2.0) < 0.1
    assert abs(patterns[1].end_bar - 4.0) < 0.1

