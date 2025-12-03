"""
Diagnostic script to sweep through motif sensitivity configurations and generate a report.

This script runs motif + grouping + call/response analysis multiple times with different
sensitivity configs and prints a compact tabular report per run showing:
- total motifs per stem
- motif groups per stem
- call/response pairs per stem

This helps choose a good sensitivity range when the lanes look over-segmented.
"""
import sys
import logging
from pathlib import Path
from collections import Counter
from typing import List

# Add backend/src to path to allow imports
# The script is in backend/scripts/, so parent.parent is backend/, then we need backend/src
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

from src.models.store import REFERENCE_BUNDLES, REFERENCE_REGIONS
from src.stem_ingest.ingest_service import load_reference_bundle
from src.analysis.region_detector.region_detector import detect_regions
from src.analysis.motif_detector.config import MotifSensitivityConfig, normalize_sensitivity_config
from src.analysis.motif_detector.motif_detector import detect_motifs, MotifInstance, MotifGroup
from src.analysis.call_response_detector.call_response_detector import detect_call_response, CallResponseConfig

logger = logging.getLogger(__name__)

# Sensitivity grid to sweep through
SENSITIVITY_GRID: List[MotifSensitivityConfig] = [
    # Very strict across the board
    {"drums": 0.10, "bass": 0.10, "vocals": 0.10, "instruments": 0.10},
    # Slightly looser, still strict
    {"drums": 0.15, "bass": 0.15, "vocals": 0.15, "instruments": 0.15},
    # Moderate
    {"drums": 0.20, "bass": 0.20, "vocals": 0.20, "instruments": 0.20},
    # Drums a bit looser, others still tight
    {"drums": 0.25, "bass": 0.15, "vocals": 0.20, "instruments": 0.20},
    # Vocals/instruments looser, rhythm stricter
    {"drums": 0.15, "bass": 0.15, "vocals": 0.25, "instruments": 0.25},
]


def summarize_motifs(motifs: List[MotifInstance]) -> Counter:
    """Count motifs by stem_role (stem_category)."""
    return Counter([m.stem_role for m in motifs])


def summarize_groups(motif_groups: List[MotifGroup]) -> Counter:
    """
    Count motif groups by stem.
    
    Each group's members are checked for their stem_role, and the group
    is counted for each unique stem it contains.
    """
    stem_counts = Counter()
    for group in motif_groups:
        # Get unique stems from group members
        stems = {m.stem_role for m in group.members if hasattr(m, 'stem_role')}
        # If a group somehow mixes stems, count each stem represented
        for stem in stems:
            if stem in ["drums", "bass", "vocals", "instruments"]:  # Only count valid stems
                stem_counts[stem] += 1
    return stem_counts


def summarize_pairs(pairs) -> Counter:
    """
    Count call/response pairs by stem.
    
    Uses from_stem_role (the call stem) to categorize pairs.
    """
    return Counter([p.from_stem_role for p in pairs if hasattr(p, 'from_stem_role')])


def compression(motifs_count: int, groups_count: int) -> float:
    """
    Compute compression ratio: motifs_per_stem / groups_per_stem.
    
    Large value → many motifs collapsed into fewer groups (good compression)
    Value near 1.0 → each motif is its own group (over-segmentation)
    
    Args:
        motifs_count: Number of motif instances
        groups_count: Number of motif groups
    
    Returns:
        Compression ratio (0.0 if no motifs, inf if motifs but no groups)
    """
    if motifs_count == 0:
        return 0.0
    if groups_count <= 0:
        return float("inf")
    return motifs_count / groups_count


def looks_good(comp: float) -> bool:
    """
    Check if compression ratio is in the "good" range.
    
    Good compression is between 2.0 and 6.0:
    - Below 2.0: May be over-grouping (too loose)
    - Above 6.0: May be under-grouping (too strict)
    - Between 2.0-6.0: Good balance (many motifs → reasonable number of groups)
    
    Args:
        comp: Compression ratio
    
    Returns:
        True if compression is in good range (2.0 <= comp <= 6.0)
    """
    # Tweak these bounds after seeing real data
    if comp == float("inf") or comp == 0.0:
        return False
    return 2.0 <= comp <= 6.0


def _get_gallium_test_paths() -> dict:
    """Get file paths for Gallium test stems."""
    # Get project root (2 levels up from backend/scripts/ = backend/, then 1 more = root)
    script_file = Path(__file__).resolve()
    backend_dir = script_file.parents[1]  # backend/
    project_root = backend_dir.parent  # project root
    root = project_root / "2. Test Data" / "Song-1-Gallium-MakeEmWatch-130BPM"
    return {
        "drums": root / "DRUMS.wav",
        "bass": root / "BASS.wav",
        "vocals": root / "VOCALS.wav",
        "instruments": root / "INSTRUMENTS.wav",
        "full_mix": root / "FULL.wav",
    }


def run_sweep(reference_id: str):
    """
    Run motif + grouping + call/response analysis with different sensitivity configs.
    
    Prints a compact tabular report showing motifs, groups, and pairs per stem.
    
    Args:
        reference_id: ID of the reference bundle to test (or "gallium" to use test data)
    """
    # Load reference bundle
    bundle = None
    regions = None
    
    # Try in-memory store first (in case server is running in same process)
    if reference_id in REFERENCE_BUNDLES:
        bundle = REFERENCE_BUNDLES[reference_id]
        if reference_id in REFERENCE_REGIONS:
            regions = REFERENCE_REGIONS[reference_id]
    
    # If not in memory, try loading from disk (for Gallium test data)
    if bundle is None:
        if reference_id.lower() == "gallium" or reference_id == "test":
            logger.info("Loading Gallium test data from disk...")
            paths = _get_gallium_test_paths()
            # Validate files exist
            missing = [k for k, v in paths.items() if not v.exists()]
            if missing:
                print(f"ERROR: Missing test files: {missing}")
                return
            bundle = load_reference_bundle(paths)
            logger.info(f"Loaded bundle: BPM={bundle.bpm}, duration={bundle.full_mix.duration}")
        else:
            print(f"ERROR: Reference {reference_id} not found in memory and not a known test dataset.")
            print("Available in-memory references:", list(REFERENCE_BUNDLES.keys()))
            print("Use 'gallium' or 'test' as reference_id to load test data from disk.")
            return
    
    # Detect regions if not already loaded
    if regions is None:
        logger.info("Detecting regions...")
        regions = detect_regions(bundle)
        logger.info(f"Detected {len(regions)} regions")
    
    # TODO: If your pipeline precomputes features, add that here and reuse
    # features = compute_motif_features(reference)
    
    print("=== Motif Sensitivity Sweep ===")
    print(f"Reference: {reference_id}")
    print(f"BPM: {bundle.bpm}")
    print(f"Regions: {len(regions)}")
    print()
    
    # Print table header
    header = (
        "idx",
        "drums",
        "bass",
        "vox",
        "inst",
        "motifs_dr",
        "motifs_bs",
        "motifs_vx",
        "motifs_in",
        "groups_dr",
        "groups_bs",
        "groups_vx",
        "groups_in",
        "comp_dr",
        "comp_bs",
        "comp_vx",
        "comp_in",
        "good_stems",
        "pairs_dr",
        "pairs_bs",
        "pairs_vx",
        "pairs_in",
    )
    print("\t".join(header))
    
    # Run analysis with each sensitivity configuration
    for idx, cfg in enumerate(SENSITIVITY_GRID):
        try:
            # Normalize config to ensure values are in safe range
            norm_cfg = normalize_sensitivity_config(cfg)
            logger.info("=== Sweep %d cfg=%s ===", idx, norm_cfg)
            
            # Run motif analysis with this sensitivity
            # TODO: Adapt this call to your real API; we want motifs + motif_groups out
            instances, motif_groups = detect_motifs(
                reference_bundle=bundle,
                regions=regions,
                sensitivity_config=norm_cfg,
                exclude_full_mix=True  # Stem-only analysis
            )
            
            # Run call/response based on these motifs
            # TODO: Adapt detect_call_response call to your real API
            call_response_config = CallResponseConfig(
                min_offset_bars=0.5,
                max_offset_bars=4.0,
                min_similarity=0.7,
                min_confidence=0.5,
                use_full_mix=False  # Stem-only analysis
            )
            pairs = detect_call_response(
                motifs=instances,
                regions=regions,
                bpm=bundle.bpm,
                config=call_response_config
            )
            
            # Summarize results by stem
            motifs_by_stem = summarize_motifs(instances)
            groups_by_stem = summarize_groups(motif_groups)
            pairs_by_stem = summarize_pairs(pairs)
            
            # Compute compression ratios per stem
            m_dr = motifs_by_stem.get("drums", 0)
            g_dr = groups_by_stem.get("drums", 0)
            m_bs = motifs_by_stem.get("bass", 0)
            g_bs = groups_by_stem.get("bass", 0)
            m_vx = motifs_by_stem.get("vocals", 0)
            g_vx = groups_by_stem.get("vocals", 0)
            m_in = motifs_by_stem.get("instruments", 0)
            g_in = groups_by_stem.get("instruments", 0)
            
            comp_dr = compression(m_dr, g_dr)
            comp_bs = compression(m_bs, g_bs)
            comp_vx = compression(m_vx, g_vx)
            comp_in = compression(m_in, g_in)
            
            # Compute "good stems" score (number of stems with good compression)
            good_stems = sum(
                looks_good(c)
                for c in (comp_dr, comp_bs, comp_vx, comp_in)
            )
            
            # Print table row
            row = [
                str(idx),
                f"{norm_cfg['drums']:.2f}",
                f"{norm_cfg['bass']:.2f}",
                f"{norm_cfg['vocals']:.2f}",
                f"{norm_cfg['instruments']:.2f}",
                str(m_dr),
                str(m_bs),
                str(m_vx),
                str(m_in),
                str(g_dr),
                str(g_bs),
                str(g_vx),
                str(g_in),
                f"{comp_dr:.2f}" if comp_dr != float("inf") else "inf",
                f"{comp_bs:.2f}" if comp_bs != float("inf") else "inf",
                f"{comp_vx:.2f}" if comp_vx != float("inf") else "inf",
                f"{comp_in:.2f}" if comp_in != float("inf") else "inf",
                str(good_stems),
                str(pairs_by_stem.get("drums", 0)),
                str(pairs_by_stem.get("bass", 0)),
                str(pairs_by_stem.get("vocals", 0)),
                str(pairs_by_stem.get("instruments", 0)),
            ]
            print("\t".join(row))
            
        except Exception as e:
            logger.error(f"Error running sweep {idx} with config {cfg}: {e}", exc_info=True)
            # Print error row
            row = [
                str(idx),
                f"{cfg.get('drums', 0):.2f}",
                f"{cfg.get('bass', 0):.2f}",
                f"{cfg.get('vocals', 0):.2f}",
                f"{cfg.get('instruments', 0):.2f}",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
            ]
            print("\t".join(row))
    
    print()
    print("Legend:")
    print("  idx: Configuration index")
    print("  drums/bass/vox/inst: Sensitivity values for each stem")
    print("  motifs_dr/bs/vx/in: Total motif instances per stem")
    print("  groups_dr/bs/vx/in: Motif groups per stem")
    print("  comp_dr/bs/vx/in: Compression ratio (motifs/groups)")
    print("    - Large value (e.g., 4.0) = good compression (many motifs → few groups)")
    print("    - Near 1.0 (e.g., 1.02) = over-segmentation (each motif is its own group)")
    print("    - 0.0 = no motifs detected")
    print("    - inf = motifs but no groups")
    print("  good_stems: Number of stems with good compression (2.0 <= comp <= 6.0)")
    print("    - High value (3-4) = good candidate for default sensitivity config")
    print("    - Look for configs with high good_stems AND reasonable motif counts")
    print("  pairs_dr/bs/vx/in: Call/response pairs per stem")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.motif_sensitivity_sweep <reference_id>")
        print("")
        print("Example:")
        print("  python -m scripts.motif_sensitivity_sweep 1c430928-c0cf-49c4-b655-6e5ff48fbbbc")
        print("")
        print("Note: The reference must already be loaded and analyzed (regions must exist).")
        sys.exit(1)
    
    reference_id = sys.argv[1]
    run_sweep(reference_id)

