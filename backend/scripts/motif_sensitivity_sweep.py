"""
Diagnostic script to sweep through motif sensitivity configurations and log results.

This script helps debug whether sensitivity is the reason for seeing 0 motif groups
or call-response patterns. It runs motif detection multiple times with different
sensitivity values and logs the number of motifs per stem for each configuration.
"""
import sys
import logging
from pathlib import Path
from collections import Counter

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.store import REFERENCE_BUNDLES, REFERENCE_REGIONS
from src.analysis.motif_detector.config import MotifSensitivityConfig, normalize_sensitivity_config
from src.analysis.motif_detector.motif_detector import detect_motifs

logger = logging.getLogger(__name__)

# Test configurations to sweep through
TEST_CONFIGS: list[MotifSensitivityConfig] = [
    {"drums": 0.2, "bass": 0.2, "vocals": 0.2, "instruments": 0.2},
    {"drums": 0.4, "bass": 0.4, "vocals": 0.4, "instruments": 0.4},
    {"drums": 0.6, "bass": 0.6, "vocals": 0.6, "instruments": 0.6},
    {"drums": 0.8, "bass": 0.8, "vocals": 0.8, "instruments": 0.8},
]


def run_sweep(reference_id: str):
    """
    Run motif detection with different sensitivity configurations and log results.
    
    Args:
        reference_id: ID of the reference bundle to test
    """
    logger.info("=" * 80)
    logger.info(f"Starting motif sensitivity sweep for reference: {reference_id}")
    logger.info("=" * 80)
    
    # Load reference bundle
    if reference_id not in REFERENCE_BUNDLES:
        logger.error(f"Reference {reference_id} not found in REFERENCE_BUNDLES")
        logger.error(f"Available references: {list(REFERENCE_BUNDLES.keys())}")
        return
    
    bundle = REFERENCE_BUNDLES[reference_id]
    logger.info(f"Loaded reference bundle: {bundle}")
    logger.info(f"BPM: {bundle.bpm}")
    
    # Load regions (required for motif detection)
    if reference_id not in REFERENCE_REGIONS:
        logger.error(f"Regions not found for reference {reference_id}. Run /analyze first.")
        logger.error("Regions are required for motif detection.")
        return
    
    regions = REFERENCE_REGIONS[reference_id]
    logger.info(f"Loaded {len(regions)} regions")
    
    # TODO: Motif features are computed on-the-fly in detect_motifs
    # The function extracts features from audio segments during detection
    # No separate feature loading step is needed
    
    results = []
    
    # Run detection with each test configuration
    for i, cfg in enumerate(TEST_CONFIGS, 1):
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"Test {i}/{len(TEST_CONFIGS)}: Sensitivity sweep config: {cfg}")
        logger.info("=" * 80)
        
        try:
            # Normalize config to ensure values are in safe range
            normalized_cfg = normalize_sensitivity_config(cfg)
            if normalized_cfg != cfg:
                logger.info(f"Config normalized: {cfg} -> {normalized_cfg}")
            
            # Run motif detection with this configuration
            # NOTE: exclude_full_mix=True for stem-only analysis (matching production behavior)
            instances, groups = detect_motifs(
                bundle,
                regions,
                sensitivity_config=normalized_cfg,
                exclude_full_mix=True
            )
            
            # Count motifs by stem
            total = len(instances)
            by_stem = Counter([inst.stem_role for inst in instances])
            
            # Count groups by stem (if groups have stem_role info)
            group_count = len(groups)
            
            # Store results
            result = {
                "config": normalized_cfg,
                "total_instances": total,
                "total_groups": group_count,
                "by_stem": dict(by_stem)
            }
            results.append(result)
            
            # Log results
            logger.info(f"Results for config {normalized_cfg}:")
            logger.info(f"  Total motif instances: {total}")
            logger.info(f"  Total motif groups: {group_count}")
            logger.info(f"  Instances by stem: {dict(by_stem)}")
            
            # Log per-stem breakdown
            for stem in ["drums", "bass", "vocals", "instruments"]:
                count = by_stem.get(stem, 0)
                logger.info(f"    {stem}: {count} instances")
            
            # Warn if no motifs found
            if total == 0:
                logger.warning(f"  ⚠️  No motifs detected with this configuration!")
            elif total > 0:
                logger.info(f"  ✓ Motifs detected successfully")
                
        except Exception as e:
            logger.error(f"Error running detection with config {cfg}: {e}", exc_info=True)
            results.append({
                "config": cfg,
                "error": str(e)
            })
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    
    for i, result in enumerate(results, 1):
        if "error" in result:
            logger.info(f"Test {i}: ERROR - {result['error']}")
        else:
            cfg = result["config"]
            total = result["total_instances"]
            groups = result["total_groups"]
            by_stem = result["by_stem"]
            
            logger.info(f"Test {i} (sensitivity={cfg.get('drums', 'N/A')}): "
                       f"{total} instances, {groups} groups, by_stem={by_stem}")
    
    # Check if any config produced motifs
    any_motifs = any(r.get("total_instances", 0) > 0 for r in results if "error" not in r)
    
    if not any_motifs:
        logger.warning("")
        logger.warning("⚠️  WARNING: No motifs detected with ANY configuration!")
        logger.warning("This suggests the issue is NOT just sensitivity settings.")
        logger.warning("Possible causes:")
        logger.warning("  - Audio files may be too short or too quiet")
        logger.warning("  - Feature extraction may be failing")
        logger.warning("  - Segmentation may not be producing valid segments")
        logger.warning("  - Clustering threshold may be too strict even at 0.2")
    else:
        logger.info("")
        logger.info("✓ At least one configuration produced motifs")
        logger.info("Sensitivity may be a factor, but motifs are being detected.")


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

