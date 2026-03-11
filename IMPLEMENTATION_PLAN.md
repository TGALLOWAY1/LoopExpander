# LoopExpander V1 Implementation Plan

## Current State Assessment

The existing codebase is a **stem-analysis tool** ("Song Structure Replicator") that accepts 4 pre-separated stems + full mix, analyzes them for regions/motifs/call-response/fills, and presents results in a Visual Composer UI. The PRD describes a fundamentally different product: a **reference-driven arrangement tool** that analyzes a single full-mix reference track, then maps user-provided loop material onto that structure.

### What Exists (Reusable)
- **FastAPI backend** with structured routes, models, and in-memory stores
- **BPM/beat-grid detection** (librosa-based, works on full mix)
- **Region detection** (novelty-curve based section segmentation)
- **Visual Composer UI** (lane/block editing with autosave — good foundation for Structure Canvas)
- **Frontend scaffolding** (React + TypeScript + Vite, ProjectContext, API client pattern)
- **Audio file handling** (WAV/AIFF loading, validation, feature extraction)

### What Needs to Change
- **Reference ingestion**: Accept single full-mix file instead of requiring 4 stems
- **Broad role activity detection**: Infer drums/bass/melody/vocal presence from full mix (new)
- **Energy/density curve**: Compute and expose for overlay (partially exists in subregion intensity)
- **Structure Canvas**: Transform Visual Composer from per-region annotation into full-song timeline
- **User loop ingestion**: Entirely new upload + role assignment flow
- **Loop Mapping Engine**: Entirely new — maps user material onto reference structure
- **Variation Suggestion System**: Entirely new
- **Arrangement Guidance Layer**: Entirely new
- **Export Module**: Entirely new (WAV stems + markers + JSON)

---

## Implementation Phases

### Phase 1: Reference Ingestion & Full-Mix Analysis
**Goal**: Accept a single full-mix reference track and produce the analysis outputs the PRD requires.

#### 1A — Single Full-Mix Upload Endpoint
**Files to modify:**
- `backend/src/api/routes_reference.py` — Add new `POST /api/reference/upload-mix` endpoint accepting a single audio file
- `backend/src/models/reference_bundle.py` — Create a `ReferenceMix` model (simpler than current `ReferenceBundle` which requires 4 stems)
- `backend/src/models/store.py` — Add `REFERENCE_MIXES` store
- `backend/src/stem_ingest/ingest_service.py` — Add `load_reference_mix()` function

**Behavior:**
- Accept single stereo WAV/AIFF/MP3
- Validate format, duration (e.g., 30s–600s)
- Detect BPM and compute beat grid
- Allow user BPM override via optional query param
- Store audio data + metadata for downstream analysis
- Return `referenceId`, `bpm`, `duration`, `beatGrid`

**Frontend:**
- `frontend/src/pages/IngestPage.tsx` — Add single-file upload mode (keep stem upload as advanced option)
- `frontend/src/api/reference.ts` — Add `uploadReferenceMix()` API client

#### 1B — Broad Role Activity Detection
**New files:**
- `backend/src/analysis/role_activity/role_detector.py` — Main detection module
- `backend/src/analysis/role_activity/spectral_bands.py` — Band-based energy analysis

**Approach:**
Use spectral band energy analysis on the full mix to estimate when broad roles are active:
- **Drums/percussion**: Onset detection + high-frequency transient density (percussive source separation via HPSS)
- **Bass**: Low-frequency energy (20–250 Hz band)
- **Melodic/harmonic**: Mid-frequency spectral content (250 Hz–4 kHz), harmonic ratio
- **Vocal/lead**: Mid-high frequency, spectral flatness, vocal likelihood estimation

Each role produces a time-series of activity confidence (0.0–1.0) aligned to the beat grid, then thresholded to produce on/off regions.

**Output model** (`backend/src/models/role_activity.py`):
```python
class RoleActivityTimeline:
    role: str  # "drums", "bass", "melodic", "vocal"
    segments: List[ActivitySegment]  # list of on/off segments with bar positions

class ActivitySegment:
    start_bar: float
    end_bar: float
    active: bool
    confidence: float
```

**API endpoint:**
- `GET /api/reference/{id}/role-activity` — Returns activity timelines per role

#### 1C — Energy Curve & Section Enhancement
**Files to modify:**
- `backend/src/analysis/region_detector/region_detector.py` — Enhance to produce energy curve alongside regions
- New: `backend/src/analysis/energy/energy_curve.py` — Compute smoothed RMS energy curve aligned to bars

**Outputs:**
- Per-bar energy values (normalized 0.0–1.0)
- Section-level density scores
- Transition moment candidates (large energy deltas between adjacent bars)
- Breakdown/drop/lift moment markers

**API endpoint:**
- `GET /api/reference/{id}/energy` — Returns energy curve + transition markers

#### 1D — Section Labeling
**Files to modify:**
- `backend/src/models/region.py` — Add `label` and `provisional_label` fields
- `backend/src/analysis/region_detector/region_detector.py` — Add heuristic labeling (intro, verse, chorus, bridge, outro) based on energy, density, position, and repetition patterns

**Heuristic rules:**
- First section with low energy → "Intro"
- Last section with energy decline → "Outro"
- High-energy repeated sections → "Chorus" candidates
- Medium-energy sections between choruses → "Verse" candidates
- Short high-energy single sections → "Drop" or "Bridge"
- Labels are provisional — user can rename in canvas

---

### Phase 2: Structure Canvas
**Goal**: Transform the Visual Composer into the full-song Structure Canvas described in the PRD.

#### 2A — Full-Song Timeline View
**Files to modify:**
- `frontend/src/pages/VisualComposerPage.tsx` → Rename/refactor to `StructureCanvasPage.tsx`
- `frontend/src/components/visualComposer/ComposerTimeline.tsx` → Refactor to show full song (all sections), not per-region

**Current state**: Visual Composer shows one region at a time with a carousel.
**Target state**: Full horizontal timeline showing all sections simultaneously, with bar/beat grid on x-axis.

**Key changes:**
- X-axis spans the full song duration in bars (not just one region)
- Sections shown as color-coded blocks spanning their bar ranges
- Multiple lanes visible simultaneously (one per broad role from analysis)
- Role activity shown as filled/empty blocks per lane
- Energy overlay as a line/area chart above or below the timeline

#### 2B — Section Editing Tools
**New component**: `frontend/src/components/structureCanvas/SectionEditor.tsx`

**Capabilities:**
- Drag section boundaries to resize
- Split section at cursor position
- Merge adjacent sections
- Rename/relabel sections (click to edit)
- Retag section type (dropdown: intro, verse, chorus, bridge, drop, outro, breakdown, custom)
- Draw new sections from scratch on empty timeline
- Editable section notes (click to open notes panel)

**Backend support:**
- `PATCH /api/reference/{id}/regions` — Update region boundaries, labels, types
- `POST /api/reference/{id}/regions/split` — Split a region at a given bar
- `POST /api/reference/{id}/regions/merge` — Merge two adjacent regions

#### 2C — Energy & Density Overlay
**New component**: `frontend/src/components/structureCanvas/EnergyOverlay.tsx`

- Render energy curve as area chart overlaid on timeline
- Toggle between energy and density views
- Color intensity indicating energy level
- Transition markers shown as vertical indicators

#### 2D — Role Activity Lanes
**New component**: `frontend/src/components/structureCanvas/RoleActivityLanes.tsx`

- One horizontal lane per detected role (drums, bass, melodic, vocal)
- Active segments shown as filled blocks, inactive as empty/dimmed
- User can toggle activity on/off by clicking segments
- Activity changes saved to backend

**Backend:**
- `PATCH /api/reference/{id}/role-activity` — User overrides for activity segments

---

### Phase 3: Call-and-Response / Interaction Labeling
**Goal**: Lightweight manual interaction labeling on the timeline.

#### 3A — Interaction Label UI
**New component**: `frontend/src/components/structureCanvas/InteractionLabeler.tsx`

**Capabilities:**
- User can draw labeled regions directly on the timeline (drag to create)
- Adjustable start/end boundaries (drag handles)
- Label selector dropdown: A, B, ABAB, call, response, fill, sustain, break, transition
- Color coding per label type
- Snap to bar/beat grid
- Duplicate pattern across sections (select pattern → apply to section X)
- Delete/resize existing labels

**Data model** (`backend/src/models/interaction_label.py`):
```python
class InteractionLabel:
    id: str
    section_id: str  # which section this belongs to
    start_bar: float
    end_bar: float
    label: str  # "A", "B", "call", "response", "fill", etc.
    color: Optional[str]
    notes: Optional[str]
```

**Backend endpoints:**
- `GET /api/reference/{id}/interactions` — Get all interaction labels
- `POST /api/reference/{id}/interactions` — Create/update interaction labels
- `DELETE /api/reference/{id}/interactions/{label_id}` — Delete label

#### 3B — Pattern Duplication
- Select a set of interaction labels within a section
- "Apply to section" action copies the pattern to another section
- Adjusts bar positions relative to target section start

---

### Phase 4: User Loop / Stem Ingestion
**Goal**: Accept user's own loop material for arrangement expansion.

#### 4A — Loop Upload Endpoint
**New files:**
- `backend/src/api/routes_user_loop.py` — User loop upload and management
- `backend/src/models/user_loop.py` — Data models
- `backend/src/models/store.py` — Add `USER_LOOPS` store

**Endpoint**: `POST /api/project/{id}/loops/upload`

**Behavior:**
- Accept one or more audio files (stems or grouped tracks)
- Detect loop length (8, 16, 32 bars based on BPM and duration)
- Allow user override of loop boundaries
- Store per-loop: audio data, detected length, role assignment

#### 4B — Role Assignment UI
**New component**: `frontend/src/pages/LoopIngestPage.tsx`

**Capabilities:**
- List uploaded loop stems
- Assign each stem to a role: drums, bass, chord/harmony, lead, vocal, FX/transition, percussion, texture
- Visual waveform preview per stem
- Loop length indicator and override control
- Simple playback for verification

**Data model** (`backend/src/models/user_loop.py`):
```python
class UserLoopStem:
    id: str
    filename: str
    role: str  # "drums", "bass", "chord", "lead", "vocal", "fx", "percussion", "texture"
    loop_length_bars: int
    start_bar: float  # trim start
    end_bar: float  # trim end
    audio_path: str

class UserLoopBundle:
    id: str
    project_id: str
    stems: List[UserLoopStem]
    bpm: float
```

#### 4C — Loop-to-Reference BPM Alignment
- If user loop BPM differs from reference BPM, compute time-stretch ratio
- Store ratio for export-time rendering (non-destructive)
- Display BPM mismatch warning in UI

---

### Phase 5: Loop Mapping Engine
**Goal**: Auto-arrange user material across the approved reference structure.

#### 5A — Mapping Engine Core
**New files:**
- `backend/src/arrangement/mapping_engine.py` — Core arrangement logic
- `backend/src/arrangement/models.py` — Arrangement output models

**Algorithm:**
1. For each section in the approved structure:
   a. Determine section length in bars
   b. For each role lane (drums, bass, melodic, vocal):
      - Check reference role activity: is this role active in this section?
      - If active: repeat user's corresponding loop stem to fill section length
      - If inactive: leave silent (or apply dropout)
   c. Apply interaction labels:
      - If section has A/B labels, alternate between user stems accordingly
      - If "call/response" labeled, map call-stem to call bars, response-stem to response bars
   d. Preserve contrast moments from reference energy curve:
      - Breakdowns → remove drums/bass
      - Drops → restore full activity
      - Builds → gradual layer addition

**Output model** (`backend/src/arrangement/models.py`):
```python
class ArrangementBlock:
    id: str
    stem_id: str  # reference to user loop stem
    role: str
    section_id: str
    start_bar: float
    end_bar: float
    active: bool
    variation_type: Optional[str]  # "mute", "dropout", "alternate", etc.
    source_loop_start: float  # where in the source loop to pull from
    source_loop_end: float

class Arrangement:
    id: str
    project_id: str
    sections: List[ArrangementSection]
    blocks: List[ArrangementBlock]
    total_bars: int
    bpm: float
```

**API endpoint:**
- `POST /api/project/{id}/arrange` — Generate arrangement from approved structure + user loops
- `GET /api/project/{id}/arrangement` — Retrieve current arrangement

#### 5B — Arrangement Preview UI
**New page**: `frontend/src/pages/ArrangementPage.tsx`

- Full-song timeline showing generated arrangement blocks
- Color-coded by role
- Blocks show which user stem is used and where
- Empty sections visible where roles are inactive
- Section labels from Structure Canvas carried over

---

### Phase 6: Variation Suggestions & Arrangement Guidance
**Goal**: Provide actionable arrangement improvement ideas.

#### 6A — Variation Suggestion Engine
**New file**: `backend/src/arrangement/variation_engine.py`

**Rules-based suggestions:**
1. **Mute on repetition**: If a role repeats identically for >2 sections, suggest muting it in one
2. **Pre-impact dropout**: Before high-energy sections, suggest 1–2 bar silence in drums/bass
3. **Half-section density**: Suggest lighter first half / fuller second half for long sections
4. **A/B alternation**: If user has multiple stems for same role, suggest ABAB patterning
5. **Transition gaps**: Suggest brief silence before section changes

**Output model:**
```python
class VariationSuggestion:
    id: str
    type: str  # "mute_layer", "dropout", "density_shift", "alternate", "gap"
    target_block_id: str
    section_id: str
    description: str  # Human-readable: "Mute bass for first 4 bars of Chorus 2"
    applied: bool  # Whether user accepted this
    parameters: dict  # Type-specific params (which bars, which layer, etc.)
```

**API endpoints:**
- `GET /api/project/{id}/suggestions` — Get variation suggestions
- `POST /api/project/{id}/suggestions/{suggestion_id}/apply` — Apply a suggestion
- `POST /api/project/{id}/suggestions/{suggestion_id}/dismiss` — Dismiss a suggestion

#### 6B — Arrangement Guidance Layer
**New file**: `backend/src/arrangement/guidance_engine.py`

**Analysis rules:**
1. **Similar density warning**: Compare RMS/energy between adjacent sections; warn if too similar
2. **Transition cue**: Suggest fills or silence before section changes without transitions
3. **Missing role warning**: If a section has very few active roles compared to neighbors
4. **Interaction coherence**: If call/response labels exist but only one layer is present, warn
5. **Section purpose hints**: Based on position and energy, suggest what each section "should do"

**Output model:**
```python
class GuidanceMessage:
    id: str
    type: str  # "density_warning", "transition_cue", "missing_role", "interaction", "purpose"
    section_id: str
    severity: str  # "info", "suggestion", "warning"
    message: str  # "This chorus and verse use very similar density"
    action_hint: Optional[str]  # "Consider adding drums in the second half"
```

#### 6C — Suggestions & Guidance UI
**New components:**
- `frontend/src/components/arrangement/SuggestionPanel.tsx` — Side panel showing suggestions
- `frontend/src/components/arrangement/GuidanceOverlay.tsx` — Inline indicators on timeline

**UX:**
- Suggestions shown as dismissible cards with "Apply" / "Dismiss" buttons
- Guidance shown as colored markers/badges on the timeline sections
- Click guidance marker to see detailed message and action hint

---

### Phase 7: Placeholder Guide Content
**Goal**: Lightweight structural event markers.

#### 7A — Guide Content System
**New file**: `backend/src/arrangement/guide_content.py`

**Types of guide content:**
- **Marker regions**: "Fill needed here", "Impact here", "Build starts"
- **Guide lanes**: Empty lanes suggesting where a response phrase or new element could go
- **Transition cue markers**: Visual indicators at section transitions
- **Call/response prompts**: Based on interaction labels, suggest where missing call/response should be

**Data model:**
```python
class GuideMarker:
    id: str
    type: str  # "fill", "impact", "build", "transition", "response_needed"
    bar_position: float
    section_id: str
    label: str
    description: str
```

#### 7B — Guide Content UI
**New component**: `frontend/src/components/arrangement/GuideMarkerLayer.tsx`
- Render guide markers as labeled flags/pins on the timeline
- Distinct visual style from actual arrangement blocks (dashed borders, lighter colors)
- Tooltip with description on hover

---

### Phase 8: Fine-Tuning Interface
**Goal**: Let users adjust the generated arrangement before export.

#### 8A — Arrangement Editing
**Extend**: `frontend/src/pages/ArrangementPage.tsx`

**Capabilities:**
- Move arrangement blocks (drag to different bar positions)
- Resize blocks (drag handles)
- Delete blocks
- Mute/unmute blocks per section (toggle button)
- Adjust role activity per section (toggle switches per lane per section)
- Quick apply/dismiss variation suggestions inline
- Edit interaction labels post-generation

#### 8B — Section Audition
**New component**: `frontend/src/components/arrangement/AuditionPlayer.tsx`

- Select a section to preview
- Render audio for that section on-the-fly (or use pre-cached preview)
- Simple transport: play, stop, loop section
- Solo/mute individual roles during preview

**Backend support:**
- `POST /api/project/{id}/audition` — Render a section's audio for preview
- Returns audio buffer (WAV) for the requested section range

---

### Phase 9: Export Module
**Goal**: Export DAW-ready arranged output.

#### 9A — Stem Export
**New file**: `backend/src/export/stem_exporter.py`

**Process:**
1. For each role in the arrangement:
   a. Concatenate the user's loop material according to arrangement blocks
   b. Apply time-stretch if BPM mismatch
   c. Apply mutes/dropouts as specified
   d. Render continuous WAV file for the full song length
2. All stems aligned to same length and bar grid

**Output:**
- One WAV file per role (e.g., `drums.wav`, `bass.wav`, `lead.wav`)
- All same duration, bar-aligned

#### 9B — Marker & Structure Export
**New file**: `backend/src/export/marker_exporter.py`

**Outputs:**
- **Arrangement JSON**: Full structure with sections, blocks, labels, suggestions, guide markers
- **MIDI markers**: Section boundaries as MIDI markers (importable by most DAWs)
- **CSV markers**: Fallback format for DAWs that prefer CSV import

**JSON schema:**
```json
{
  "bpm": 130,
  "totalBars": 128,
  "sections": [
    { "name": "Intro", "startBar": 0, "endBar": 8, "type": "intro" }
  ],
  "blocks": [
    { "role": "drums", "startBar": 0, "endBar": 8, "active": true, "stemFile": "drums.wav" }
  ],
  "interactionLabels": [...],
  "guideMarkers": [...],
  "suggestions": [...]
}
```

#### 9C — Export UI
**New component**: `frontend/src/components/export/ExportPanel.tsx`

**Capabilities:**
- Export button opens export dialog
- Checkboxes: stems (WAV), markers (MIDI), structure (JSON)
- Format selection for stems: WAV 16-bit, WAV 24-bit, AIFF
- Download as ZIP bundle

**API endpoint:**
- `POST /api/project/{id}/export` — Triggers export rendering
- `GET /api/project/{id}/export/download` — Download the rendered ZIP

---

## Phase Dependencies & Ordering

```
Phase 1 (Reference Analysis)
    ↓
Phase 2 (Structure Canvas)  ←── can start frontend work in parallel with Phase 1B/1C
    ↓
Phase 3 (Interaction Labeling)  ←── builds on Structure Canvas UI
    ↓
Phase 4 (User Loop Ingestion)  ←── independent of Phase 3, can parallel
    ↓
Phase 5 (Loop Mapping Engine)  ←── requires Phase 1-4 complete
    ↓
Phase 6 (Variations & Guidance)  ←── requires Phase 5
Phase 7 (Guide Content)         ←── requires Phase 5, can parallel with 6
    ↓
Phase 8 (Fine-Tuning)  ←── requires Phase 5-7
    ↓
Phase 9 (Export)  ←── requires Phase 5, can start in parallel with 6-8
```

**Parallelization opportunities:**
- Phase 1A (upload) + 1B (role detection) can develop concurrently
- Phase 2 frontend can start once Phase 1A API is stubbed
- Phase 4 (loop ingestion) is independent and can develop alongside Phases 2-3
- Phase 6 + 7 can develop in parallel
- Phase 9 backend can start as soon as Phase 5 models are defined

---

## Key Architectural Decisions

### 1. Preserve vs. Replace Current Stem-Based Flow
**Decision**: Keep the existing stem-based flow as an "advanced mode" but make single full-mix upload the default path. The new `ReferenceMix` model is simpler and doesn't require stems.

### 2. In-Memory Storage
**Decision**: Continue using in-memory stores for V1 (matching current pattern). Abstract behind repository interfaces for future database migration. Add file-based session persistence so projects survive server restarts.

### 3. Non-Destructive Audio
**Decision**: All arrangement operations store metadata only. Audio rendering happens only at export time and during section audition. This keeps the workflow fast and reversible.

### 4. Role Activity Detection Fidelity
**Decision**: Use spectral band analysis + HPSS (Harmonic-Percussive Source Separation) from librosa. This gives "good enough" broad role detection from a full mix without requiring actual source separation. Accept ~70-80% accuracy — the Structure Canvas lets users correct mistakes.

### 5. Frontend Architecture
**Decision**: Extend the existing React + ProjectContext pattern. Add a `useArrangement` hook and `ArrangementContext` for the new arrangement state. Keep the Visual Composer code as foundation for Structure Canvas rather than rewriting.

---

## New Dependencies

### Backend
- `soundfile` (already present) — for export rendering
- No new major dependencies — librosa already provides HPSS, onset detection, spectral analysis

### Frontend
- Consider adding a lightweight waveform rendering library if the existing approach is insufficient for full-song timeline
- No major new dependencies expected

---

## File Structure (New Files Summary)

```
backend/src/
├── analysis/
│   ├── role_activity/
│   │   ├── __init__.py
│   │   ├── role_detector.py         # Phase 1B
│   │   └── spectral_bands.py        # Phase 1B
│   └── energy/
│       ├── __init__.py
│       └── energy_curve.py           # Phase 1C
├── models/
│   ├── role_activity.py              # Phase 1B
│   ├── interaction_label.py          # Phase 3
│   ├── user_loop.py                  # Phase 4
│   └── arrangement.py               # Phase 5
├── api/
│   ├── routes_user_loop.py           # Phase 4
│   └── routes_arrangement.py        # Phase 5+
├── arrangement/
│   ├── __init__.py
│   ├── mapping_engine.py            # Phase 5
│   ├── models.py                     # Phase 5
│   ├── variation_engine.py          # Phase 6A
│   ├── guidance_engine.py           # Phase 6B
│   └── guide_content.py             # Phase 7
└── export/
    ├── __init__.py
    ├── stem_exporter.py              # Phase 9A
    └── marker_exporter.py            # Phase 9B

frontend/src/
├── pages/
│   ├── StructureCanvasPage.tsx       # Phase 2 (refactored from VisualComposerPage)
│   ├── LoopIngestPage.tsx            # Phase 4
│   └── ArrangementPage.tsx           # Phase 5+
├── components/
│   ├── structureCanvas/
│   │   ├── SectionEditor.tsx         # Phase 2B
│   │   ├── EnergyOverlay.tsx         # Phase 2C
│   │   ├── RoleActivityLanes.tsx     # Phase 2D
│   │   └── InteractionLabeler.tsx    # Phase 3
│   ├── arrangement/
│   │   ├── SuggestionPanel.tsx       # Phase 6C
│   │   ├── GuidanceOverlay.tsx       # Phase 6C
│   │   ├── GuideMarkerLayer.tsx      # Phase 7B
│   │   └── AuditionPlayer.tsx        # Phase 8B
│   └── export/
│       └── ExportPanel.tsx           # Phase 9C
├── context/
│   └── ArrangementContext.tsx        # Phase 5
└── api/
    ├── userLoop.ts                   # Phase 4
    └── arrangement.ts               # Phase 5+
```

---

## Testing Strategy

Each phase should include:
1. **Backend unit tests** for new analysis/engine modules
2. **API integration tests** for new endpoints
3. **Frontend component tests** for new UI components

Priority test areas:
- Role activity detection accuracy (compare against known reference tracks)
- Loop mapping engine correctness (verify blocks align to structure)
- Variation suggestion logic (verify rules produce valid suggestions)
- Export output integrity (verify WAV alignment and marker accuracy)

---

## V1 Definition Checklist (from PRD §13)

| Feature | Phase | Status |
|---------|-------|--------|
| Full-mix reference upload | 1A | New |
| BPM/grid detection | 1A | Exists (enhance) |
| Section segmentation | 1C/1D | Exists (enhance) |
| Broad role activity detection | 1B | New |
| Editable Structure Canvas | 2 | New (builds on Visual Composer) |
| Manual call-and-response / A-B labeling | 3 | New |
| User loop/stem upload | 4 | New |
| Reference-based auto-arrangement | 5 | New |
| Simple variation suggestions | 6A | New |
| Arrangement guidance prompts | 6B | New |
| Aligned stem export | 9A | New |
| Structure / marker export | 9B | New |
