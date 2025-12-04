# Phase 3 Implementation Summary: Visual Composer Annotations Backend & Frontend

**Date:** Phase 3 Complete  
**Purpose:** Document the complete implementation of Visual Composer annotations system with backend models, API endpoints, frontend integration, region navigation, autosave, and error handling.

---

## Overview

Phase 3 implements a complete annotations persistence system for the Visual Composer feature, including:
- Backend Pydantic models and REST API endpoints
- Frontend TypeScript types and API client
- React hook for state management
- Region-aware annotations with metadata
- Carousel navigation between regions
- Debounced autosave functionality
- Comprehensive error handling and resilience

---

## P3-01: Backend Models & Endpoints

### Files Created/Modified
- `backend/src/models/visual_composer.py` (new)
- `backend/src/models/visual_composer_repository.py` (new)
- `backend/src/api/routes_visual_composer.py` (new)
- `backend/src/main.py` (modified - registered router)
- `backend/tests/test_visual_composer_api.py` (new)

### Implementation Details

#### Pydantic Models (`visual_composer.py`)

**VisualComposerLane**
- Fields: `id`, `name`, `color`, `collapsed`, `order`
- Metadata container for organizing blocks

**VisualComposerBlock**
- Fields: `id`, `laneId`, `startBar`, `endBar`, `color`, `type`, `notes`
- Represents events, motifs, calls, responses, variations, or fills
- Validation: `endBar` must be greater than `startBar`

**VisualComposerRegionAnnotations**
- Fields: `regionId`, `regionName`, `notes`, `startBar`, `endBar`, `regionType`, `displayOrder`, `lanes`, `blocks`
- Contains both lanes (metadata) and blocks (annotations)
- Includes region metadata for alignment with main Region model

**VisualComposerAnnotations**
- Fields: `projectId`, `regions`
- Top-level container for all Visual Composer annotations

#### Repository Layer (`visual_composer_repository.py`)

Abstracted persistence layer with functions:
- `get_annotations(project_id)` - Retrieve annotations
- `save_annotations(annotations)` - Save annotations
- `delete_annotations(project_id)` - Delete annotations
- `has_annotations(project_id)` - Check existence

Currently uses in-memory storage, but abstraction allows easy migration to database/file storage later.

#### REST Endpoints (`routes_visual_composer.py`)

**GET `/api/visual-composer/{project_id}/annotations`**
- Returns annotations for a project
- Cross-references with known regions and creates defaults for missing regions
- Returns empty structure `{ projectId, regions: [] }` if no annotations exist (not 500)

**POST `/api/visual-composer/{project_id}/annotations`**
- Upserts full annotations payload
- Validates projectId matches path parameter
- Returns saved annotations with camelCase field names

#### Tests

- Round-trip POST → GET test
- Missing project returns empty structure (not 500)
- Project ID mismatch handling
- Validation error tests

---

## P3-02: Frontend Types & API Client

### Files Created/Modified
- `frontend/src/api/visualComposerApi.ts` (new)
- `frontend/src/api/visualComposerApi.test.ts` (new)

### Implementation Details

#### TypeScript Interfaces

**VcLane**
- Matches `VisualComposerLane` backend model
- Fields: `id`, `name`, `color`, `collapsed`, `order`

**VcBlock**
- Matches `VisualComposerBlock` backend model
- Fields: `id`, `laneId`, `startBar`, `endBar`, `color`, `type`, `notes`

**VcRegionAnnotations**
- Matches `VisualComposerRegionAnnotations` backend model
- Includes: `regionId`, `regionName`, `notes`, `startBar`, `endBar`, `regionType`, `displayOrder`, `lanes`, `blocks`

**VcAnnotations**
- Matches `VisualComposerAnnotations` backend model
- Fields: `projectId`, `regions`

#### API Client Functions

**getVisualComposerAnnotations(projectId: string)**
- Fetches annotations from backend
- Returns empty structure `{ projectId, regions: [] }` on error (graceful degradation)
- Normalizes response data

**saveVisualComposerAnnotations(projectId: string, payload: VcAnnotations)**
- Saves annotations to backend
- Normalizes projectId to match path parameter
- Returns saved annotations

#### Test Documentation

- Structure validation tests
- Empty annotations handling
- Example usage documentation

---

## P3-03: Visual Composer Page State Integration

### Files Created/Modified
- `frontend/src/hooks/useVisualComposerAnnotations.ts` (new)
- `frontend/src/pages/VisualComposerPage.tsx` (modified)
- `frontend/src/pages/VisualComposerPage.css` (modified)

### Implementation Details

#### Custom Hook (`useVisualComposerAnnotations.ts`)

**State Management**
- `annotations`: Current annotations data
- `isLoading`: Loading state
- `error`: Error state
- `saveAnnotations()`: Manual save function
- `isSaving`: Saving state

**Features**
- Loads annotations on mount via `getVisualComposerAnnotations(projectId)`
- Handles empty responses by normalizing to `{ projectId, regions: [] }`
- Provides manual save functionality

#### VisualComposerPage Integration

**Type Conversion Helpers**
- `vcLaneToAnnotationLane()` / `annotationLaneToVcLane()`
- `vcBlockToAnnotationBlock()` / `annotationBlockToVcBlock()`
- `vcRegionToRegionAnnotations()` / `regionAnnotationsToVcRegion()`

These helpers maintain compatibility with existing components that use legacy `Annotation` types while using new `Vc` types internally.

**State Flow**
1. Hook loads annotations on mount
2. Page converts Vc types to Annotation types for components
3. User edits update local state
4. Changes sync to Vc annotations via `updateVcAnnotations()`
5. Manual Save button triggers `saveVcAnnotations()`

**Save Button**
- Added to header with loading state
- Success/error status messages with auto-dismiss
- Disabled during loading or saving

**Empty Regions Handling**
- Creates region entries on demand when user starts annotating
- `addLane()` ensures region exists in Vc annotations before adding

---

## P3-04: Region-Aware Annotations Structure

### Files Modified
- `backend/src/models/visual_composer.py`
- `backend/src/api/routes_visual_composer.py`
- `frontend/src/api/visualComposerApi.ts`
- `frontend/src/pages/VisualComposerPage.tsx`
- `backend/tests/test_visual_composer_api.py`

### Implementation Details

#### Backend Model Updates

**VisualComposerRegionAnnotations** now includes:
- `startBar`: Optional float for region start in bars
- `endBar`: Optional float for region end in bars
- `regionType`: Optional string (e.g., 'low_energy', 'build', 'high_energy', 'drop')
- `displayOrder`: Optional int for sorting regions

#### Backend GET Endpoint Enhancement

**Cross-Reference with Known Regions**
- Retrieves known regions from `REFERENCE_REGIONS`
- Gets BPM from `REFERENCE_BUNDLES` for time-to-bar conversion
- Creates default entries for missing regions using `create_default_region_annotations()`

**Time-to-Bar Conversion**
- `seconds_to_bars()` function converts region time (seconds) to bars using BPM
- Assumes 4/4 time signature (4 beats per bar)

**Default Region Creation**
- For each known region without annotations, creates default entry with:
  - Correct `regionId`, `regionName`, `regionType`
  - Calculated `startBar`, `endBar` from region time
  - `displayOrder` based on region index
  - Empty `lanes` and `blocks` arrays

**Sorting**
- Regions sorted by `displayOrder` if available, otherwise by `regionId`

#### Frontend Updates

**Type Updates**
- `VcRegionAnnotations` interface includes new metadata fields

**Conversion Functions**
- Updated to handle region metadata when converting between types

**Timeline Bar Calculation**
- `getRegionBars()` now prefers bar range from annotations
- Falls back to duration-based estimate if annotations unavailable

#### Tests

**New Test: `test_get_annotations_with_regions_but_no_annotations_returns_defaults`**
- Verifies backend creates defaults for all known regions
- Validates region metadata (name, type, bars, displayOrder)
- Checks correct bar calculations from time and BPM
- Ensures regions are sorted by displayOrder

---

## P3-05: Region Carousel Navigation

### Files Modified
- `frontend/src/pages/VisualComposerPage.tsx`
- `frontend/src/pages/VisualComposerPage.css`

### Implementation Details

#### Ordered Region List

**`orderedRegions` useMemo**
- Builds ordered list from annotations with metadata
- Merges region data from context with annotation metadata
- Sorts by `displayOrder` from annotations when available
- Falls back to original region order if no displayOrder

**Metadata Integration**
- Includes `startBar`, `endBar` from annotations
- Includes `displayOrder` for proper sorting
- Preserves all region properties from context

#### Header Display

**Region Info Display**
- Shows current region name and type (existing)
- **NEW:** Displays bar range: "Bars X.X - Y.Y" when available from annotations
- Shows region index: "Region N of M"
- Styled bar range with monospace font

#### Navigation Controls

**Previous/Next Buttons**
- Already in header (existing)
- Properly disabled: Previous at index 0, Next at last index
- Uses `orderedRegions.length` for boundary checks

**Navigation Handlers**
- `handlePrevRegion()` and `handleNextRegion()` updated
- Clear selected block when navigating
- Edits preserved automatically (stored in `vcAnnotations` keyed by regionId)

#### Edit Preservation

**How It Works**
1. Edits stored in `localRegionAnnotations` (current region's edits)
2. `useEffect` syncs `localRegionAnnotations` to `vcAnnotations` (keyed by regionId)
3. Navigating changes `currentRegionIndex`, triggering `useEffect`
4. New region's annotations loaded from `vcAnnotations` into `localRegionAnnotations`
5. Previous region's edits remain in `vcAnnotations` (unsaved until Save clicked)

**Result:** Unsaved edits preserved in React state across region navigation

#### Timeline Bar Calculation

**Updated `getRegionBars()`**
- Prefers bar range from annotations if available
- Falls back to duration-based estimate if annotations unavailable
- Ensures timeline displays correct bar count

---

## P3-06: Autosave & Debounced Save

### Files Modified
- `frontend/src/hooks/useVisualComposerAnnotations.ts`
- `frontend/src/pages/VisualComposerPage.tsx`
- `frontend/src/pages/VisualComposerPage.css`

### Implementation Details

#### Hook Enhancements

**New State**
- `saveStatus`: 'idle' | 'saving' | 'saved' | 'error'
- `isDirty`: Boolean flag for unsaved changes
- `lastSavedAnnotationsRef`: Ref to track last saved state for dirty detection

**Debounced Autosave**
- `setAnnotationsWithAutosave()`: Wrapper that marks as dirty and triggers autosave
- 1.5-second debounce after last change
- Clears and restarts timer on subsequent edits
- Prevents API spam during rapid edits

**Save Functions**
- `performSave()`: Internal save shared by autosave and manual save
- `saveAnnotations()`: Manual save (explicit button)
- `forceSave()`: Immediate save (for region navigation)

**Dirty Detection**
- Compares current annotations with last saved using JSON.stringify
- Marks as dirty only when annotations actually change
- Resets dirty flag after successful save

**Save Status Management**
- Updates status: 'saving' → 'saved' → 'idle' (after 2 seconds)
- Sets to 'error' on save failure
- Auto-clears 'saved' status after 2 seconds

#### Region Navigation Integration

**Immediate Save on Navigation**
- `handlePrevRegion()` and `handleNextRegion()` call `forceSave()` if dirty
- Shows alert if save fails before navigation
- Still allows navigation even if save fails (with warning)

**Force Save**
- Clears any pending autosave timeout
- Triggers immediate save if dirty
- Ensures edits are saved before switching regions

#### UI Updates

**Save Status Indicator**
- Shows "Saving..." during save
- Shows "All changes saved" when saved (auto-clears after 2 seconds)
- Shows "Save failed" on error
- Shows "Unsaved changes" when dirty and idle

**Manual Save Button**
- Still works as explicit save
- Uses same `performSave()` implementation
- Disabled during save or loading

**CSS Styling**
- Color-coded statuses: saving (blue), saved (green), error (red), unsaved (orange)
- Non-blocking visual feedback

---

## P3-07: Error Handling & Resilience

### Files Modified
- `backend/src/api/routes_visual_composer.py`
- `frontend/src/hooks/useVisualComposerAnnotations.ts`
- `frontend/src/pages/VisualComposerPage.tsx`
- `frontend/src/pages/VisualComposerPage.css`

### Implementation Details

#### Backend Error Handling

**Status Code Improvements**
- **400 (Bad Request)**: Critical validation errors
- **422 (Unprocessable Entity)**: Pydantic validation errors
- **500 (Internal Server Error)**: Unexpected errors
- Clear, descriptive error messages in all responses

**Validation Function (`validate_annotations`)**
- Validates region IDs against known regions (logs warnings, doesn't reject)
- Detects overlapping blocks in same lane (logs warnings)
- Non-blocking: logs warnings instead of rejecting unless critical
- Helps identify data issues without breaking user workflow

**Error Handling Structure**
```python
try:
    # Validation
    validate_annotations(annotations, project_id)
except ValueError:
    # Critical validation → 400
except HTTPException:
    # Re-raise HTTP exceptions
except ValueError:
    # Pydantic validation → 422
except Exception:
    # Unexpected errors → 500
```

#### Frontend Error Handling

**Separate Error States**
- `loadError`: Errors from initial GET (for retry)
- `error`/`saveError`: Errors from save operations
- Distinguishes load vs save failures for better UX

**Retry Functionality**
- `retryLoad()` function exposed for manual retry
- `loadAnnotations()` extracted as reusable function
- Allows users to retry failed initial loads

**State Preservation**
- On load error, preserves existing annotations if present
- Only initializes empty structure if no annotations exist
- **Critical:** Prevents wiping unsaved edits on load failures

**Error Flow**
1. Load error → set `loadError`, preserve existing annotations
2. Save error → set `saveStatus` to 'error', preserve in-memory state
3. User can continue editing even with errors
4. Retry available for load errors

#### UI Error Display

**Load Error Badge**
- Non-blocking error badge with retry button
- Shows in header when load fails
- Also shows in empty state if no regions
- Styled with red border and background
- Retry button disabled during loading

**Save Error Display**
- Save errors shown in status indicator
- Tooltip with error message on hover (`title` attribute)
- Non-blocking: doesn't prevent editing

**Error Styling**
- `.load-error-badge`: Red border, light red background
- `.retry-button`: Red button with hover effects
- Clear visual hierarchy

---

## Data Flow Summary

### Loading Annotations
1. User opens Visual Composer page
2. `useVisualComposerAnnotations` hook calls `getVisualComposerAnnotations(projectId)`
3. Backend GET endpoint cross-references with known regions
4. Creates default entries for missing regions
5. Returns complete annotations structure
6. Hook stores in state, marks as clean

### Editing Annotations
1. User edits lanes/blocks/notes
2. `localRegionAnnotations` updated
3. `useEffect` syncs to `vcAnnotations` via `updateVcAnnotations()`
4. `setAnnotationsWithAutosave()` marks as dirty
5. Debounced autosave timer starts (1.5 seconds)
6. After debounce, `performSave()` called automatically
7. Save status updates: 'saving' → 'saved' → 'idle'

### Region Navigation
1. User clicks Previous/Next
2. If dirty, `forceSave()` called immediately
3. Current region's edits saved to backend
4. `currentRegionIndex` updated
5. `useEffect` loads new region's annotations from `vcAnnotations`
6. Previous region's edits remain in `vcAnnotations` (already saved)

### Error Handling
1. **Load Error**: Sets `loadError`, preserves existing annotations, shows retry button
2. **Save Error**: Sets `saveStatus` to 'error', preserves in-memory state, shows error badge
3. User can continue editing, retry load, or manually save

---

## Key Design Decisions

### 1. Separate Vc Types from Legacy Annotation Types
- **Rationale**: Clean separation allows gradual migration
- **Implementation**: Conversion helpers maintain component compatibility
- **Benefit**: Existing components continue working without changes

### 2. Repository Abstraction
- **Rationale**: Allows easy migration from in-memory to persistent storage
- **Implementation**: Simple module with get/save/delete functions
- **Benefit**: Can swap storage implementation without changing API layer

### 3. Debounced Autosave
- **Rationale**: Prevents API spam while ensuring data safety
- **Implementation**: 1.5-second debounce, clears on new edits
- **Benefit**: Smooth UX with automatic persistence

### 4. State Preservation on Errors
- **Rationale**: Users shouldn't lose work due to network issues
- **Implementation**: Errors don't wipe in-memory state
- **Benefit**: Resilient to temporary failures

### 5. Region Metadata in Annotations
- **Rationale**: Enables proper region ordering and bar range display
- **Implementation**: Backend creates defaults with metadata from Region model
- **Benefit**: Annotations self-contained with all necessary context

### 6. Non-Blocking Error UI
- **Rationale**: Errors shouldn't prevent users from working
- **Implementation**: Error badges with retry buttons, tooltips for details
- **Benefit**: Users can continue editing while resolving errors

---

## Testing Coverage

### Backend Tests (`test_visual_composer_api.py`)
- ✅ GET annotations when none exist (returns empty structure)
- ✅ Round-trip POST → GET persistence
- ✅ Project ID mismatch handling
- ✅ Validation error handling (invalid endBar, invalid block type)
- ✅ Missing project returns empty structure
- ✅ **NEW:** GET with regions but no annotations returns per-region defaults

### Frontend Tests (`visualComposerApi.test.ts`)
- ✅ Structure validation
- ✅ Empty annotations handling
- ✅ Example usage documentation

### Manual Testing Scenarios
- ✅ Opening Visual Composer loads annotations
- ✅ Editing and clicking Save persists changes
- ✅ Rapid edits trigger single autosave (not spam)
- ✅ Navigating between regions preserves edits
- ✅ Region labels and bar ranges update on navigation
- ✅ Correct region's annotations shown after navigating
- ✅ Error states don't wipe in-memory edits
- ✅ Retry button works for failed loads

---

## Files Summary

### Backend
- `backend/src/models/visual_composer.py` - Pydantic models
- `backend/src/models/visual_composer_repository.py` - Persistence abstraction
- `backend/src/api/routes_visual_composer.py` - REST endpoints
- `backend/src/main.py` - Router registration
- `backend/tests/test_visual_composer_api.py` - API tests

### Frontend
- `frontend/src/api/visualComposerApi.ts` - API client and types
- `frontend/src/api/visualComposerApi.test.ts` - Test documentation
- `frontend/src/hooks/useVisualComposerAnnotations.ts` - State management hook
- `frontend/src/pages/VisualComposerPage.tsx` - Main page component
- `frontend/src/pages/VisualComposerPage.css` - Styling

---

## Commit History

1. `VC Phase 3: add backend models and API for Visual Composer annotations`
2. `VC Phase 3: add TS models and API client for composer annotations`
3. `VC Phase 3: wire Visual Composer UI to annotations API`
4. `VC Phase 3: align composer annotations with per-region metadata and defaults`
5. `VC Phase 3: add region carousel navigation to Visual Composer`
6. `VC Phase 3: add autosave and save status to Visual Composer annotations`
7. `VC Phase 3: improve robustness of Visual Composer annotation persistence`

---

## Next Steps / Future Enhancements

### Potential Improvements
1. **Persistent Storage**: Migrate from in-memory to file-based or database storage
2. **Router Integration**: Add URL params for region navigation (`/visual-composer/:projectId/:regionIndex`)
3. **Optimistic Updates**: Show UI changes immediately, sync in background
4. **Conflict Resolution**: Handle concurrent edits from multiple sessions
5. **Undo/Redo**: Add history stack for annotation edits
6. **Export/Import**: Allow exporting annotations as JSON for backup/sharing

### Known Limitations
1. In-memory storage: Data lost on server restart
2. No conflict detection: Multiple users editing same project could overwrite
3. No version history: Can't revert to previous annotation states
4. Manual retry only: No automatic retry with exponential backoff

---

## Conclusion

Phase 3 successfully implements a complete, robust annotations persistence system for Visual Composer. The implementation follows best practices for error handling, state management, and user experience. The system is resilient to failures, preserves user work, and provides clear feedback about save status and errors.

The architecture is designed for extensibility, with clear separation of concerns and abstraction layers that allow future enhancements without major refactoring.

