# Milestone 3: Visual Composer Annotations

## Overview

This milestone implements the Visual Composer feature, enabling manual annotation of regions with bar-based annotation blocks organized by stem categories. The implementation includes backend API endpoints, frontend state management, and a complete Visual Composer page component, all protected by feature flags.

## Implementation Summary

### Phase 0: Feature Flags and Scaffolding

#### Backend Changes
- **File: `backend/src/config.py`**
  - Added `VISUAL_COMPOSER_ENABLED` feature flag driven by `VISUAL_COMPOSER_ENABLED` environment variable
  - Flag defaults to `false` for safety

- **File: `backend/src/api/routes_reference.py`**
  - Verified `VISUAL_COMPOSER_ENABLED` import from config module
  - Prepared for future route implementations

#### Frontend Changes
- **Files Created:**
  - `frontend/.env.example` - Feature flag documentation (`VITE_VISUAL_COMPOSER_ENABLED=false`)
  - `frontend/.env.development` - Development flag enabled (`VITE_VISUAL_COMPOSER_ENABLED=true`)
  - `frontend/src/config.ts` - Centralized config export for feature flag
  - `frontend/src/tests/smoke.test.tsx` - Test harness verification

- **File: `frontend/src/App.tsx`**
  - Updated view type: `type AppView = 'ingest' | 'regionMap' | 'visualComposer'`
  - Changed state variable from `currentPage` to `view`
  - Added dev-only button that appears when:
    - `VISUAL_COMPOSER_ENABLED` is true
    - `referenceId` exists
    - Current view is `regionMap`
  - Added placeholder Visual Composer view

**Key Features:**
- Non-breaking changes (all existing functionality preserved)
- Feature flag protection on both backend and frontend
- Dev-only access path for testing

---

### Phase 1A: Backend Annotations API

#### Backend Implementation

- **File: `backend/src/models/annotations.py`** (Created)
  - `AnnotationBlock`: Single annotation block with `id`, `startBar`, `endBar`, `label`
  - `AnnotationLane`: Lane containing blocks for a stem category
  - `RegionAnnotations`: Annotations for a specific region
  - `ReferenceAnnotations`: Complete annotations for a reference track
  - All positions are bar-based as required
  - Pydantic validation for data integrity

- **File: `backend/src/models/store.py`**
  - Added `REFERENCE_ANNOTATIONS` in-memory store
  - Uses `TYPE_CHECKING` to avoid circular imports
  - Maps `reference_id -> ReferenceAnnotations`

- **File: `backend/src/api/routes_reference.py`**
  - **GET `/api/reference/{reference_id}/annotations`**:
    - Returns existing annotations or empty structure `{referenceId, regions: []}`
    - Returns 404 with "Visual Composer disabled" when feature flag is false
    - Returns 404 when reference bundle not found
  
  - **POST `/api/reference/{reference_id}/annotations`**:
    - Validates payload using Pydantic models
    - Forces `referenceId` in payload to match path parameter
    - Stores annotations in memory
    - Returns 404 when feature flag is false
    - Returns 404 when reference bundle not found

- **File: `backend/tests/test_annotations_api.py`** (Created)
  - Round-trip POST → GET test
  - Empty default test (verifies `regions == []`)
  - Flag-disabled test (404 for both GET and POST)
  - Reference ID overwriting test
  - Reference not found tests
  - Validation error tests

**Key Features:**
- Feature flag protection on all endpoints
- Automatic reference_id correction
- Comprehensive test coverage
- Bar-based positioning system

---

### Phase 1B: Frontend API Integration

#### Frontend Implementation

- **File: `frontend/src/api/reference.ts`**
  - Added TypeScript interfaces:
    - `AnnotationBlock`
    - `AnnotationLane`
    - `RegionAnnotations`
    - `ReferenceAnnotations`
  - **`getAnnotations(referenceId)`**:
    - Returns `{referenceId, regions: []}` on 404 (no throw)
    - Handles feature-disabled gracefully
  - **`saveAnnotations(referenceId, data)`**:
    - Saves annotations to backend
    - Proper error handling

- **File: `frontend/src/context/ProjectContext.tsx`**
  - Added `annotations: ReferenceAnnotations | null` to state
  - Added `setAnnotations` setter function
  - Implemented `useEffect` to load annotations when `referenceId` changes:
    - Resets to `null` when `referenceId` is `null`
    - Calls `getAnnotations(referenceId)` when reference exists
    - Handles cancellation correctly with cleanup function
    - Falls back to empty structure on error to avoid breaking UI
  - Exported `annotations` and `setAnnotations` via context

**Key Features:**
- Automatic annotation loading on reference selection
- Proper cleanup to prevent memory leaks
- Graceful error handling with fallback
- Non-breaking (optional field with sensible default)

---

### Phase 1C: Region-Aware State Management

#### Frontend Implementation

- **File: `frontend/src/pages/VisualComposerPage.tsx`**
  - **Context Access:**
    - Uses `referenceId`, `regions`, `annotations`, `setAnnotations` from `useProject()`
  
  - **Region State Management:**
    - Added `currentRegionIndex` state
    - Derived `currentRegion = regions?.[currentRegionIndex]`
    - Derived `regionId = currentRegion?.id`
  
  - **Local Region Annotations:**
    - Added `localRegionAnnotations` state of type `RegionAnnotations`
    - Stores annotations for current region only
  
  - **useEffect for Region Sync:**
    - When `regionId` or `annotations` change:
      - Finds existing `RegionAnnotations` for current region, OR
      - Creates empty structure: `{regionId, lanes: [], regionNotes: ""}`
    - Uses ref to prevent circular updates when syncing from global
  
  - **updateGlobalAnnotations Function:**
    - Merges updated region into global annotations
    - Filters out old region and adds updated one
    - Called whenever `localRegionAnnotations` changes
    - Wrapped in `useCallback` for stability
  
  - **Refactored Handlers:**
    - All handlers work with `localRegionAnnotations`:
      - `handleAddLane` - Adds new lane to current region
      - `handleDeleteBlock` - Removes block from lane
      - `handleRegionNotesChange` - Updates region notes
      - Bar grid interaction handlers
  
  - **Navigation:**
    - Prev/Next region buttons (already implemented)
    - Proper boundary checking

**Key Features:**
- Region-specific state management
- Automatic sync between local and global annotations
- Circular update prevention
- Simplified state management focused on current region

---

### Phase 1D: Component Integration

#### Frontend Implementation

- **File: `frontend/src/App.tsx`**
  - Confirmed `AppView` type includes `'visualComposer'`
  - Confirmed view state initialized to `'ingest'`
  - Added import: `import VisualComposerPage from './pages/VisualComposerPage'`
  - Replaced placeholder div with real `VisualComposerPage` component
  - Passed `onBack` handler to navigate back to `regionMap`
  - Verified dev-only button conditions:
    - `VISUAL_COMPOSER_ENABLED` is `true`
    - `referenceId` exists
    - Current view is `regionMap`

**Key Features:**
- Real component integration
- Proper navigation flow
- Feature flag protection maintained

---

## Technical Architecture

### State Flow
```
ProjectContext (Global)
  ↓ annotations: ReferenceAnnotations
  ↓ setAnnotations()
  ↓
VisualComposerPage (Local)
  ↓ localRegionAnnotations: RegionAnnotations
  ↓ updateGlobalAnnotations()
  ↓
Automatic sync on changes
```

### Data Flow
1. User selects reference → `ProjectContext` loads annotations via API
2. User navigates to Visual Composer → `VisualComposerPage` finds/creates region annotations
3. User edits annotations → Updates `localRegionAnnotations`
4. Changes sync → `updateGlobalAnnotations()` merges into global state
5. Auto-save → Debounced save to backend API (1 second delay)

### Feature Flag Protection
- **Backend:** `VISUAL_COMPOSER_ENABLED` env var controls API endpoints
- **Frontend:** `VITE_VISUAL_COMPOSER_ENABLED` env var controls UI visibility
- Both return 404/empty when disabled

---

## Files Created/Modified

### Backend Files
- `backend/src/config.py` - Feature flag definition
- `backend/src/api/routes_reference.py` - Annotations endpoints (GET/POST)
- `backend/src/models/store.py` - In-memory annotations store
- `backend/src/models/annotations.py` - Pydantic models (NEW)
- `backend/tests/test_annotations_api.py` - Comprehensive tests (NEW)

### Frontend Files
- `frontend/src/config.ts` - Feature flag export (NEW)
- `frontend/src/api/reference.ts` - API client functions
- `frontend/src/context/ProjectContext.tsx` - Annotations state management
- `frontend/src/pages/VisualComposerPage.tsx` - Main component
- `frontend/src/pages/VisualComposerPage.css` - Component styling
- `frontend/src/App.tsx` - View routing and integration
- `frontend/.env.example` - Feature flag documentation (NEW)
- `frontend/.env.development` - Development flag enabled (NEW)
- `frontend/src/tests/smoke.test.tsx` - Test harness (NEW)
- `frontend/src/tests/VisualComposerPage.test.tsx` - Component tests (NEW)

---

## Testing Coverage

### Backend Tests (`test_annotations_api.py`)
- ✅ Round-trip POST → GET with multiple RegionAnnotations
- ✅ Empty default structure test (regions == [])
- ✅ Feature flag disabled test (404 for both GET and POST)
- ✅ Reference ID overwriting test
- ✅ Reference not found tests
- ✅ Validation error tests (invalid bar ranges, invalid stem categories)

### Frontend
- ✅ Automatic loading in ProjectContext
- ✅ Region-specific state management
- ✅ Navigation between regions
- ✅ Error handling and fallbacks
- ✅ Circular update prevention

---

## Key Achievements

1. **Non-Breaking:** All existing functionality preserved
2. **Feature-Flagged:** Controlled by environment variables
3. **Type-Safe:** Full TypeScript coverage
4. **Tested:** Comprehensive backend test suite
5. **Performant:** Debounced saves, proper cleanup
6. **User-Friendly:** Automatic loading, graceful error handling
7. **Well-Architected:** Clean separation of concerns, proper state management

---

## Commit History

1. `feat: add Visual Composer feature flags and initial view scaffolding` (Phase 0)
2. `feat: verify and stabilize backend annotations API` (Phase 1A)
3. `feat: load annotations into ProjectContext with API fallback behavior` (Phase 1B)
4. `feat: add region-specific annotation state logic to VisualComposerPage` (Phase 1C)
5. `feat: integrate real VisualComposerPage behind feature flag` (Phase 1D)

---

## Usage

### Enabling the Feature

**Backend:**
```bash
export VISUAL_COMPOSER_ENABLED=true
```

**Frontend:**
```bash
# In .env.development or .env
VITE_VISUAL_COMPOSER_ENABLED=true
```

### Accessing Visual Composer

1. Load a reference track via Ingest page
2. Analyze the reference to detect regions
3. Navigate to Region Map view
4. Click "[Dev] Open Visual Composer" button (only visible when feature flag enabled)
5. Use Prev/Next buttons to navigate between regions
6. Add lanes, create annotation blocks, and add region notes
7. Changes auto-save after 1 second of inactivity

---

## Next Steps (Future Phases)

- **Phase 2:** Enhanced UI for block/lane editing (drag-to-resize, labels, etc.)
- **Phase 3:** Advanced annotation features (copy/paste, templates, etc.)
- **Phase 4:** Export/import functionality
- **Phase 5:** Collaboration features

---

## Notes

- All annotations use bar-based positioning (`startBar`, `endBar`)
- Stem categories are: `drums`, `bass`, `vocals`, `instruments`
- Annotations are stored in-memory (backend) and will need persistence layer in future
- The Visual Composer is currently dev-only and requires feature flag to be enabled

