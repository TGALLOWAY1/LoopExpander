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

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.store import REFERENCE_BUNDLES, REFERENCE_REGIONS
from src.analysis.motif_detector.config import MotifSensitivityConfig, normalize_sensitivity_config
from src.analysis.motif_detector.motif_detector import detect_motifs, MotifInstance, MotifGroup
from src.analysis.call_response_detector.call_response_detector import detect_call_response, CallResponseConfig

logger = logging.getLogger(__name__)

# Sensitivity grid to sweep through
SENSITIVITY_GRID: List[MotifSensitivityConfig] = [
    # Uniform settings
    {"drums": 0.2, "bass": 0.2, "vocals": 0.2, "instruments": 0.2},
    {"drums": 0.4, "bass": 0.4, "vocals": 0.4, "instruments": 0.4},
    {"drums": 0.6, "bass": 0.6, "vocals": 0.6, "instruments": 0.6},
    {"drums": 0.8, "bass": 0.8, "vocals": 0.8, "instruments": 0.8},
    # Example "drums stricter, bass looser"
    {"drums": 0.3, "bass": 0.6, "vocals": 0.5, "instruments": 0.5},
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


def run_sweep(reference_id: str):
    """
    Run motif + grouping + call/response analysis with different sensitivity configs.
    
    Prints a compact tabular report showing motifs, groups, and pairs per stem.
    
    Args:
        reference_id: ID of the reference bundle to test
    """
    # Load reference bundle
    # TODO: Adapt load_reference_by_id to your actual storage layer
    if reference_id not in REFERENCE_BUNDLES:
        print(f"ERROR: Reference {reference_id} not found in REFERENCE_BUNDLES")
        print(f"Available references: {list(REFERENCE_BUNDLES.keys())}")
        return
    
    bundle = REFERENCE_BUNDLES[reference_id]
    
    # Load regions (required for motif detection)
    if reference_id not in REFERENCE_REGIONS:
        print(f"ERROR: Regions not found for reference {reference_id}. Run /analyze first.")
        return
    
    regions = REFERENCE_REGIONS[reference_id]
    
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
            
            # Print table row
            row = [
                str(idx),
                f"{norm_cfg['drums']:.2f}",
                f"{norm_cfg['bass']:.2f}",
                f"{norm_cfg['vocals']:.2f}",
                f"{norm_cfg['instruments']:.2f}",
                str(motifs_by_stem.get("drums", 0)),
                str(motifs_by_stem.get("bass", 0)),
                str(motifs_by_stem.get("vocals", 0)),
                str(motifs_by_stem.get("instruments", 0)),
                str(groups_by_stem.get("drums", 0)),
                str(groups_by_stem.get("bass", 0)),
                str(groups_by_stem.get("vocals", 0)),
                str(groups_by_stem.get("instruments", 0)),
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
            ]
            print("\t".join(row))
    
    print()
    print("Legend:")
    print("  idx: Configuration index")
    print("  drums/bass/vox/inst: Sensitivity values for each stem")
    print("  motifs_dr/bs/vx/in: Total motif instances per stem")
    print("  groups_dr/bs/vx/in: Motif groups per stem")
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

