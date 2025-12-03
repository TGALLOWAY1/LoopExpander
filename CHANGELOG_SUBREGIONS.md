# Subregion DNA Lanes Feature - Implementation Summary

## Overview
This feature implements a DNA-style visualization system for subregion patterns in the Region Map, replacing the previous floating motif dots with a more informative lane-based view showing pattern repetition, variations, silence, and intensity per stem category.

## Commits Included

### 1. Add subregion models/API and unified dev startup script (7f20e1d)
**Backend:**
- Created subregion pattern models (`SubRegionPattern`, `RegionSubRegions`) with Pydantic DTOs
- Implemented stub service for computing subregions with bar-based positioning
- Added `GET /reference/{id}/subregions` API endpoint with caching
- Added comprehensive unit and integration tests

**Dev Tools:**
- Created `run.sh` unified startup script for parallel backend/frontend execution
- Added `Procfile` for foreman support
- Added `backend/dev.py` Python entry script
- Updated frontend package.json dev script to specify port

**Bug Fix:**
- Fixed filename mismatch in Gallium test data paths

### 2. Implement real subregion analysis from motifs and density curves (59db2d3)
**Backend Analysis:**
- Added configuration: `DEFAULT_SUBREGION_BARS_PER_CHUNK=2`, `DEFAULT_SUBREGION_SILENCE_INTENSITY_THRESHOLD=0.15`
- Implemented `DensityCurves` class computing RMS envelopes per stem from ReferenceBundle
- Implemented full `compute_region_subregions` logic:
  - Segments regions into bar-based chunks (configurable bars_per_chunk)
  - Finds overlapping motifs per chunk and links to motif groups
  - Computes intensity from RMS density curves (normalized 0-1)
  - Detects silence/dropouts using intensity threshold
  - Marks variations based on motif `is_variation` flag
  - Generates labels from motif groups
- Updated API endpoint to use real `DensityCurves` from bundle
- Added comprehensive tests for real data computation, silence detection, motif finding, and density curves

**Example Output:**
- 8-bar region with 2 bars/chunk produces 4 chunks per stem
- Each chunk has motif associations, intensity values, and silence detection

### 3. Add frontend types, API client, and state for subregions (60d3a60)
**Frontend Types:**
- Added TypeScript types: `StemCategory`, `SubRegionPattern`, `RegionSubRegions`, `ReferenceSubRegionsResponse`
- Types match backend JSON schema with camelCase aliases

**API Client:**
- Created `fetchReferenceSubregions()` function with response normalization
- Ensures all 4 stem categories are present (fills missing with empty arrays)
- Type-safe error handling

**State Management:**
- Extended `ProjectContext` with `subregionsByRegionId: Record<string, RegionSubRegions>`
- Added `setSubregions()` setter that normalizes to indexed structure
- Integrated into `RegionMapPage` with loading state and console logging

**Tests:**
- Added test file documenting expected behavior and structure

### 4. Replace motif dots with DNA lanes view in Region Map (c029670)
**New Component:**
- Created `SubRegionLanes` component rendering 4 horizontal lanes (Drums, Bass, Inst, Vox)
- Each lane shows adjacent blocks for subregion patterns with:
  - Width proportional to bar span (endBar - startBar)
  - Intensity mapped to opacity (0-1)
  - Variation styling with dashed border and hatched background
  - Silence shown as faint border-only blocks
  - Labels displayed for patterns with motif groups

**Integration:**
- Integrated `SubRegionLanes` into `RegionBlock` bottom half
- Gated old motif dot overlay with `showMotifDots` prop (default: false)
- Updated `RegionBlock` CSS for two-section layout (info + lanes)
- Wired subregion data from `RegionMapPage` to `RegionBlock`
- Added loading skeleton for subregions

**Visual Mapping:**
- Block width: proportional to (endBar - startBar) within region
- Intensity → opacity: `pattern.intensity` (0-1)
- Variation: dashed border + hatched background pattern
- Silence: transparent with faint border (opacity 0.15)
- Colors: Red (drums), Teal (bass), Light teal (inst), Pink (vocals)

### 5. Fix Python 3.7 compatibility: use typing_extensions for Literal (0e8e26d)
**Compatibility Fix:**
- Updated `subregions/models.py` to use `typing_extensions` fallback for `Literal`
- Matches pattern used in other modules (`motif_detector.py`)
- Ensures compatibility with Python 3.7 while supporting Python 3.8+

## Technical Details

### Backend Architecture

**Subregion Models:**
- `SubRegionPattern`: Individual pattern block with bar positions, motif linkage, intensity, silence flag
- `RegionSubRegions`: Container organizing patterns by stem category (lanes)
- Pydantic DTOs for API serialization with camelCase aliases

**Analysis Service:**
- `DensityCurves`: Computes RMS envelopes per stem, provides normalized intensity values
- `compute_region_subregions()`: Main analysis function segmenting regions into bar-based chunks
- Bar positioning: Converts region times to bars using BPM (assumes 4/4 time signature)
- Motif integration: Finds overlapping motifs, links to groups, detects variations
- Density integration: Samples RMS curves, normalizes to 0-1 for intensity

**API Endpoint:**
- `GET /reference/{id}/subregions`: Returns per-region lane data
- Caches computed subregions in `REFERENCE_SUBREGIONS` store
- Requires regions and motifs to be analyzed first

### Frontend Architecture

**Component Hierarchy:**
```
RegionMapPage
  └─ RegionBlock (per region)
      ├─ Region info (top half)
      └─ SubRegionLanes (bottom half)
          ├─ Lane: Drums
          ├─ Lane: Bass
          ├─ Lane: Instruments
          └─ Lane: Vocals
              └─ SubRegionPattern blocks
```

**Data Flow:**
1. `RegionMapPage` fetches subregions via `fetchReferenceSubregions()`
2. Stores in `ProjectContext.subregionsByRegionId` (indexed by region ID)
3. Passes `subregionsByRegionId[region.id]` to each `RegionBlock`
4. `RegionBlock` calculates bar positions and passes lanes to `SubRegionLanes`
5. `SubRegionLanes` renders blocks with visual mappings

**Visual Customization Points:**
- Block width: `calculateBlockWidth()` in `SubRegionLanes.tsx`
- Intensity → opacity: Direct mapping in block style
- Variation styling: CSS class `.subregion-block--variation` in `SubRegionLanes.css`
- Stem colors: `getStemCategoryColor()` in `SubRegionLanes.tsx`
- Silence rendering: Block style logic in `SubRegionLanes.tsx`

## Testing

**Backend Tests:**
- Unit tests for models (validation, serialization)
- Unit tests for service (bar conversion, structure, silence detection)
- API integration tests (response structure, error handling, caching)

**Frontend Tests:**
- Test file documenting expected behavior and structure
- Mock data matching backend response format

## Configuration

**Backend Config (`config.py`):**
- `DEFAULT_SUBREGION_BARS_PER_CHUNK = 2` (bars per subregion chunk)
- `DEFAULT_SUBREGION_SILENCE_INTENSITY_THRESHOLD = 0.15` (intensity threshold for silence)

**Frontend:**
- Default BPM: 120 (TODO: Get from context or reference bundle)
- Feature flag: `showMotifDots = false` (gates old dot overlay)

## Future Improvements

1. **BPM Storage**: Add BPM to `ProjectContext` to avoid hardcoded default
2. **Performance**: Optimize density curve computation for long tracks
3. **Visual Enhancements**: Add tooltips, zoom controls, pattern grouping
4. **Interaction**: Click patterns to highlight related motifs across regions
5. **Responsive Design**: Improve mobile/tablet layout for DNA lanes

## Files Changed

**Backend:**
- `backend/src/analysis/subregions/` (new module)
- `backend/src/api/routes_reference.py`
- `backend/src/models/store.py`
- `backend/src/config.py`
- `backend/tests/test_subregions_*.py` (new tests)
- `backend/dev.py` (new)
- `run.sh` (new)
- `Procfile` (new)

**Frontend:**
- `frontend/src/api/reference.ts`
- `frontend/src/context/ProjectContext.tsx`
- `frontend/src/pages/RegionMapPage.tsx`
- `frontend/src/components/SubRegionLanes.tsx` (new)
- `frontend/src/components/SubRegionLanes.css` (new)
- `frontend/src/components/RegionBlock.tsx`
- `frontend/src/components/RegionBlock.css`
- `frontend/src/api/referenceSubregions.test.ts` (new)

