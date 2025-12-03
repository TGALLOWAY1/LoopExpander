# Visual Composer & Annotation Models Audit

**Date:** P2-01 Audit  
**Purpose:** Document current annotation model structure and data flow before making changes

## TypeScript Types (Frontend)

### Location: `frontend/src/api/reference.ts`

#### `ReferenceAnnotations`
```typescript
interface ReferenceAnnotations {
  referenceId: string;
  regions: RegionAnnotations[];
}
```

#### `RegionAnnotations`
```typescript
interface RegionAnnotations {
  regionId: string;
  lanes: AnnotationLane[];
  regionNotes?: string | null;  // ⚠️ NOT in backend model
}
```

#### `AnnotationLane`
```typescript
interface AnnotationLane {
  stemCategory: StemCategory;  // 'drums' | 'bass' | 'vocals' | 'instruments'
  blocks: AnnotationBlock[];
}
```

#### `AnnotationBlock`
```typescript
interface AnnotationBlock {
  id: string;
  startBar: number;
  endBar: number;
  label?: string | null;
}
```

## Backend Pydantic Models

### Location: `backend/src/models/annotations.py`

#### `ReferenceAnnotations`
```python
class ReferenceAnnotations(BaseModel):
    reference_id: str  # ⚠️ snake_case, not camelCase
    regions: List[RegionAnnotations]
```

#### `RegionAnnotations`
```python
class RegionAnnotations(BaseModel):
    region_id: str  # ⚠️ snake_case, not camelCase
    lanes: List[AnnotationLane]
    # ⚠️ NO regionNotes field - frontend expects this but backend doesn't have it
```

#### `AnnotationLane`
```python
class AnnotationLane(BaseModel):
    stem_category: str  # ⚠️ snake_case, not camelCase
    blocks: List[AnnotationBlock]
    
    @field_validator('stem_category')
    def validate_stem_category(cls, v: str) -> str:
        allowed = {"drums", "bass", "vocals", "instruments"}
        if v not in allowed:
            raise ValueError(f"stem_category must be one of {allowed}, got {v}")
        return v
```

#### `AnnotationBlock`
```python
class AnnotationBlock(BaseModel):
    id: str
    start_bar: float  # ⚠️ snake_case, not camelCase; float vs number
    end_bar: float  # ⚠️ snake_case, not camelCase; float vs number
    label: Optional[str]
    
    @field_validator('end_bar')
    def validate_end_bar(cls, v: float, info) -> float:
        if 'start_bar' in info.data and v <= info.data['start_bar']:
            raise ValueError(f"end_bar must be greater than start_bar")
        return v
```

## Key Differences & Issues

### 1. Naming Convention Mismatch
- **Backend:** Uses `snake_case` (e.g., `reference_id`, `region_id`, `start_bar`, `end_bar`, `stem_category`)
- **Frontend:** Uses `camelCase` (e.g., `referenceId`, `regionId`, `startBar`, `endBar`, `stemCategory`)
- **Impact:** The backend models do NOT have field aliases configured (unlike `SubRegionPatternDTO` which uses `Field(..., alias="...")`), so `model_dump()` returns snake_case. This could cause runtime issues if FastAPI doesn't automatically convert.

### 2. Missing `regionNotes` Field
- **Frontend:** `RegionAnnotations` includes optional `regionNotes?: string | null`
- **Backend:** `RegionAnnotations` does NOT have a `regionNotes` field
- **Impact:** 
  - Frontend can save `regionNotes` but backend will ignore it
  - Frontend expects `regionNotes` when loading but backend won't return it
  - This field is actively used in `VisualComposerPage.tsx` (lines 39, 288-295, 472-478)

### 3. Type Differences
- **Backend:** Uses `float` for `start_bar` and `end_bar`
- **Frontend:** Uses `number` (TypeScript)
- **Impact:** Compatible at runtime, but worth noting for precision considerations

## Data Flow

### Loading Annotations

1. **Trigger:** `ProjectContext.tsx` useEffect (lines 124-155) calls `getAnnotations(referenceId)` when `referenceId` changes
2. **API Call:** `frontend/src/api/reference.ts` → `getAnnotations()` → `GET /api/reference/{id}/annotations`
3. **Backend:** `backend/src/api/routes_reference.py` → `get_annotations()` (lines 978-1018)
   - Returns `annotations.model_dump()` (snake_case, no aliases)
   - Returns empty structure `{ referenceId, regions: [] }` if no annotations exist
4. **Storage:** Result stored in `ProjectContext.annotations: ReferenceAnnotations | null`
5. **Mapping:** `VisualComposerPage.tsx` useEffect (lines 63-100) finds `RegionAnnotations` by `regionId` and sets `localRegionAnnotations`

### Saving Annotations

1. **Trigger:** `VisualComposerPage.tsx` useEffect (lines 128-132) calls `debouncedSave(annotations)` when annotations change
2. **Debounce:** 1 second delay (line 124)
3. **API Call:** `frontend/src/api/reference.ts` → `saveAnnotations(referenceId, data)` → `POST /api/reference/{id}/annotations`
   - Sends `ReferenceAnnotations` in camelCase
4. **Backend:** `backend/src/api/routes_reference.py` → `create_or_update_annotations()` (lines 1021-1069)
   - Receives `ReferenceAnnotations` Pydantic model (expects snake_case in JSON)
   - Stores in `REFERENCE_ANNOTATIONS[reference_id]`
   - Returns `annotations.model_dump()` (snake_case)

### Local State Management

- **Global State:** `ProjectContext.annotations: ReferenceAnnotations | null`
- **Local State:** `VisualComposerPage.localRegionAnnotations: RegionAnnotations`
- **Sync Logic:**
  - Global → Local: useEffect (lines 63-100) syncs when `regionId` or `annotations` change
  - Local → Global: useEffect (lines 103-107) updates global when local changes (unless syncing from global)
  - Uses `isSyncingFromGlobalRef` to prevent circular updates

## API Endpoints

### GET `/api/reference/{reference_id}/annotations`
- **Handler:** `get_annotations()` in `routes_reference.py` (lines 978-1018)
- **Returns:** `ReferenceAnnotations.model_dump()` (snake_case)
- **Empty Response:** `{ "referenceId": string, "regions": [] }` if no annotations exist
- **404:** If `VISUAL_COMPOSER_ENABLED = False` or reference not found

### POST `/api/reference/{reference_id}/annotations`
- **Handler:** `create_or_update_annotations()` in `routes_reference.py` (lines 1021-1069)
- **Accepts:** `ReferenceAnnotations` Pydantic model (expects snake_case in JSON body)
- **Returns:** `ReferenceAnnotations.model_dump()` (snake_case)
- **Validation:** Forces `reference_id` in payload to match path parameter
- **404:** If `VISUAL_COMPOSER_ENABLED = False` or reference not found

## Potential Issues

### 1. Snake_case vs camelCase Mismatch
**Severity:** HIGH  
**Description:** Backend returns snake_case but frontend expects camelCase. FastAPI may handle this automatically via Pydantic, but it's not explicitly configured.

**Evidence:**
- Backend models have no field aliases (unlike `SubRegionPatternDTO` which uses `Field(..., alias="...")`)
- `model_dump()` called without `by_alias=True` returns field names as-is (snake_case)
- Frontend types strictly expect camelCase

**Recommendation:** Add field aliases to backend models or configure FastAPI to use camelCase serialization.

### 2. Missing `regionNotes` Field
**Severity:** HIGH  
**Description:** Frontend uses `regionNotes` but backend model doesn't include it.

**Evidence:**
- `VisualComposerPage.tsx` line 39: `regionNotes: ''` in initial state
- `VisualComposerPage.tsx` lines 288-295: `handleRegionNotesChange()` function
- `VisualComposerPage.tsx` lines 472-478: Textarea bound to `localRegionAnnotations.regionNotes`
- Backend `RegionAnnotations` model has no `regionNotes` field

**Recommendation:** Add `region_notes: Optional[str] = None` to backend `RegionAnnotations` model with alias `regionNotes`.

### 3. Type Precision
**Severity:** LOW  
**Description:** Backend uses `float` (Python) vs frontend `number` (TypeScript). Compatible but worth noting.

## Files Involved

### Frontend
- `frontend/src/pages/VisualComposerPage.tsx` - Main component
- `frontend/src/context/ProjectContext.tsx` - Global state management
- `frontend/src/api/reference.ts` - API client and type definitions

### Backend
- `backend/src/models/annotations.py` - Pydantic models
- `backend/src/api/routes_reference.py` - API endpoints (lines 978-1069)

## Next Steps

1. **Fix naming mismatch:** Add field aliases to backend Pydantic models or configure camelCase serialization
2. **Add `regionNotes` field:** Add to backend `RegionAnnotations` model with proper alias
3. **Test data flow:** Verify annotations load/save correctly with both naming conventions
4. **Update validation:** Ensure backend validation works with camelCase input

