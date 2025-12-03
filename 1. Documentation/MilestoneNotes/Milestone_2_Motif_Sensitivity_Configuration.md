# Milestone 2: Motif Sensitivity Configuration & Diagnostics

## Overview

This milestone implements per-stem motif sensitivity configuration, diagnostic tools for tuning sensitivity values, and improvements to the motif clustering algorithm. The implementation includes backend sensitivity configuration management, frontend UI controls, diagnostic scripts, and algorithm refinements to address over-grouping issues.

## Implementation Summary

### Backend Implementation

#### 1. Per-Stem Motif Sensitivity Configuration (Prompts A-C)
- **Files Modified:**
  - `backend/src/analysis/motif_detector/config.py` - Added `MotifSensitivityConfig` type and normalization
  - `backend/src/models/reference_bundle.py` - Added `motif_sensitivity_config` field
  - `backend/src/api/routes_reference.py` - Added endpoints for sensitivity config management
  - `backend/src/analysis/motif_detector/motif_detector.py` - Updated to use per-stem sensitivity

- **Features:**
  - Per-stem sensitivity configuration (drums, bass, vocals, instruments)
  - Sensitivity values clamped to safe range [0.0, 1.0]
  - Default sensitivity config with safe defaults
  - Per-reference sensitivity storage in memory
  - API endpoints: `GET/PUT /api/reference/{id}/motif-sensitivity`
  - Motif detection uses per-stem sensitivity config
  - Explicit disable of full-mix motifs for lane view (`USE_FULL_MIX_FOR_LANE_VIEW` flag)

#### 2. Motif Sensitivity Sweep Diagnostic Script (Prompt A)
- **Files Created:**
  - `backend/scripts/motif_sensitivity_sweep.py` - Diagnostic script for sensitivity tuning
  - `backend/scripts/README.md` - Documentation for running scripts

- **Features:**
  - Sweeps through multiple sensitivity configurations
  - Generates tabular report with:
    - Motif counts per stem
    - Motif groups per stem
    - Compression ratios (motifs/groups)
    - Call/response pairs per stem
  - Supports loading test data from disk (`gallium` or `test` reference ID)
  - Automatic region detection if not already loaded
  - Fixed Python path resolution for standalone execution

#### 3. Compression Ratio Metric (Prompt B)
- **Files Modified:**
  - `backend/scripts/motif_sensitivity_sweep.py`

- **Features:**
  - Added `compression()` function to calculate motifs_per_stem / groups_per_stem
  - Compression ratio columns in report: `comp_dr`, `comp_bs`, `comp_vx`, `comp_in`
  - Interpretation guide:
    - Large value (e.g., 4.0) = good compression (many motifs → few groups)
    - Near 1.0 (e.g., 1.02) = over-segmentation (each motif is its own group)
    - 0.0 = no motifs detected
    - inf = motifs but no groups

#### 4. Recommended Config Heuristic (Prompt C)
- **Files Modified:**
  - `backend/scripts/motif_sensitivity_sweep.py`

- **Features:**
  - Added `looks_good()` function to flag configs with compression between 2.0-6.0
  - `good_stems` score counts number of stems with good compression
  - High `good_stems` (3-4) indicates good candidate for default sensitivity
  - Helps identify configs with good compression across multiple stems

#### 5. Diagnostic Logging for Motif Embeddings (Prompt A)
- **Files Modified:**
  - `backend/src/analysis/motif_detector/motif_detector.py`

- **Features:**
  - Added diagnostic logging before clustering:
    - Min, max, mean, median pairwise distances
    - First 20 distances for inspection
  - Helps debug over-grouping issues
  - Identifies if motifs are identical (tiny distances) or if eps threshold is too large

#### 6. Percentile-Based eps Calculation (Major Refactor)
- **Files Modified:**
  - `backend/src/analysis/motif_detector/motif_detector.py`

- **Problem Identified:**
  - Original formula: `eps = median_distance * (1.0 + 0.5 * sensitivity)`
  - eps values (6.9-7.5) were too close to mean distances (~6.5-7.0)
  - Caused almost all motifs to cluster together regardless of sensitivity

- **Solution Implemented:**
  - Replaced median-based formula with percentile-based approach
  - Maps sensitivity [0,1] to distance percentile range [15th, 45th]
  - sensitivity=0.0 → strict (15th percentile, q_low)
  - sensitivity=1.0 → looser (45th percentile, q_high)
  - Formula: `eps = q_low + (q_high - q_low) * sensitivity`

- **Results:**
  - eps values now 3.2-5.0 (was 6.9-7.5)
  - Compression ratios improved: 5.91-22.67 (was 10.83-68.00)
  - Groups increased: 11/3/7/3 (was 6/1/1/2)
  - One stem (drums) now in target 2.0-6.0 range

#### 7. Rescue Sensitivity Fallback
- **Files Modified:**
  - `backend/src/analysis/motif_detector/motif_detector.py`

- **Features:**
  - If 0 motifs detected, automatically retries with rescue sensitivity (looser config)
  - Prevents UI from going completely blank due to extreme sensitivity values
  - Logs group and call/response counts for sanity checks

### Frontend Implementation

#### 1. Types & API Client for Sensitivity (Prompt D)
- **Files Created:**
  - `frontend/src/api/motifSensitivity.ts` - API client for sensitivity config

- **Features:**
  - TypeScript types for `MotifSensitivityConfig`
  - `fetchMotifSensitivity()` - Get current sensitivity config
  - `updateMotifSensitivity()` - Update sensitivity config
  - `reanalyzeMotifs()` - Trigger re-analysis after sensitivity change

#### 2. Sensitivity State Management Hook (Prompt E)
- **Files Created:**
  - `frontend/src/hooks/useMotifSensitivity.ts` - React hook for sensitivity state

- **Features:**
  - Manages sensitivity state per stem
  - Handles loading and error states
  - Provides `updateSensitivity()` function
  - Auto-fetches sensitivity config on mount

#### 3. UI Panel with Per-Stem Sliders (Prompt F)
- **Files Created:**
  - `frontend/src/components/MotifSensitivityPanel.tsx` - Sensitivity control panel

- **Features:**
  - Per-stem sensitivity sliders (drums, bass, vocals, instruments)
  - Range: 0.0 (strict) to 1.0 (loose)
  - Real-time value display
  - Save button to update configuration

#### 4. Trigger Re-Analysis After Sensitivity Change (Prompt G)
- **Files Modified:**
  - `frontend/src/pages/RegionMapPage.tsx`

- **Features:**
  - Auto-triggers re-analysis after sensitivity update
  - Shows loading state during re-analysis
  - Refreshes motifs and call/response data

#### 5. Remove Sliders From Right Panel (Prompt A)
- **Files Modified:**
  - `frontend/src/pages/RegionMapPage.tsx`
  - `frontend/src/components/MotifSensitivityPanel.tsx` (removed)

- **Changes:**
  - Removed sensitivity panel from right sidebar
  - Restored Motif Groups and Call & Response panels

#### 6. Lane Header Component with Sensitivity Slider (Prompt B)
- **Files Created:**
  - `frontend/src/components/StemLaneHeader.tsx` - Lane header with optional slider
  - `frontend/src/components/StemLaneHeader.css` - Styling for lane header

- **Features:**
  - Displays lane name (Drums, Bass, Vocals, Instruments)
  - Optional sensitivity slider in collapsible section
  - Chevron button to expand/collapse slider
  - Shows current sensitivity value inline next to label
  - Slider appears below lane name when expanded

#### 7. Show Sliders Only When Lane Is Focused (Prompt C)
- **Files Modified:**
  - `frontend/src/components/FiveLayerRegionMap.tsx`

- **Features:**
  - Sliders only appear when a lane is focused
  - Auto-expands when lane becomes focused
  - Collapses when lane loses focus

#### 8. Show Current Sensitivity Value in Lane Header (Prompt D)
- **Files Modified:**
  - `frontend/src/components/StemLaneHeader.tsx`
  - `frontend/src/components/StemLaneHeader.css`

- **Features:**
  - Displays sensitivity value in parentheses next to lane label
  - Format: "Drums (0.50)"
  - Subtle styling (small, gray text)
  - Helps connect UI values with diagnostic sweep numbers

#### 9. Re-run Analysis Button
- **Files Modified:**
  - `frontend/src/pages/RegionMapPage.tsx`

- **Features:**
  - Added "Re-run Analysis" button
  - Triggers full re-analysis of reference
  - Shows loading state during analysis

#### 10. Explicit Empty States
- **Files Modified:**
  - `frontend/src/components/MotifGroupsPanel.tsx`
  - `frontend/src/components/CallResponsePanel.tsx`

- **Features:**
  - Shows "No Motifs Found" message when no motifs detected
  - Shows "No Call & Response" message when no pairs detected
  - Better user feedback for edge cases

### Bug Fixes

1. **Python Path Fix**
   - Fixed import path resolution in `motif_sensitivity_sweep.py`
   - Changed from adding `backend/` to adding `backend/src/` to Python path

2. **Undefined startBar/endBar**
   - Fixed handling of undefined `startBar`/`endBar` in `FiveLayerRegionMap`
   - Added null checks and fallbacks

3. **Missing Loading Prop**
   - Fixed missing `loading` prop in `MotifGroupsPanel`

4. **Snake Case to Camel Case**
   - Fixed API response transformation in `callResponseLanes.ts`

## Technical Details

### Sensitivity Configuration Format
```typescript
interface MotifSensitivityConfig {
  drums: number;      // 0.0 (strict) to 1.0 (loose)
  bass: number;
  vocals: number;
  instruments: number;
}
```

### eps Calculation Formula
```python
# Percentile-based approach
q_low = np.percentile(distances, 15.0)   # Stricter end
q_high = np.percentile(distances, 45.0)  # Looser end
eps = q_low + (q_high - q_low) * sensitivity
```

### Compression Ratio Interpretation
- **2.0-6.0**: Good compression (target range)
- **< 2.0**: May be over-grouping (too loose)
- **> 6.0**: May be under-grouping (too strict)
- **Near 1.0**: Over-segmentation (each motif is its own group)

## Testing & Validation

### Diagnostic Script Usage
```bash
cd backend
python -m scripts.motif_sensitivity_sweep gallium
```

### Expected Output
- Tabular report with sensitivity configs, motif counts, groups, compression ratios
- `good_stems` score to identify recommended configs
- Call/response pair counts per stem

### Results
- Initial: All compression ratios 10-68, good_stems = 0
- After percentile fix: Compression ratios 5.91-22.67, good_stems = 1 (drums in target range)

## Files Changed

### Backend
- `backend/src/analysis/motif_detector/config.py`
- `backend/src/analysis/motif_detector/motif_detector.py`
- `backend/src/models/reference_bundle.py`
- `backend/src/api/routes_reference.py`
- `backend/src/config.py`
- `backend/scripts/motif_sensitivity_sweep.py`
- `backend/scripts/README.md`
- `backend/scripts/__init__.py`

### Frontend
- `frontend/src/api/motifSensitivity.ts`
- `frontend/src/hooks/useMotifSensitivity.ts`
- `frontend/src/components/StemLaneHeader.tsx`
- `frontend/src/components/StemLaneHeader.css`
- `frontend/src/components/MotifSensitivityPanel.tsx` (removed)
- `frontend/src/components/FiveLayerRegionMap.tsx`
- `frontend/src/pages/RegionMapPage.tsx`
- `frontend/src/components/MotifGroupsPanel.tsx`
- `frontend/src/components/CallResponsePanel.tsx`

## Next Steps

1. Further tune percentile window (currently 15/45) to get more stems in 2.0-6.0 range
2. Consider per-stem percentile windows (different for drums vs vocals)
3. Add UI feedback for compression ratio in real-time
4. Persist sensitivity configs to database (currently in-memory only)

