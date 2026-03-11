# LoopExpander

A reference-driven arrangement tool that analyzes a full-mix reference track, maps user-provided loop material onto that structure, and produces an expanded, DAW-ready arrangement.

<img width="1210" height="702" alt="image" src="https://github.com/user-attachments/assets/9483f085-6fa0-45cb-a525-4384f70e024e" />

## Overview

LoopExpander takes a single reference track (or separated stems), analyzes its structure, energy profile, and role activity, then helps you arrange your own loops across that structure. The workflow:

1. **Ingest** - Upload a reference track (single full-mix or 4 stems + mix)
2. **Analyze** - Automatic detection of sections, BPM, energy curve, and role activity (drums, bass, melodic, vocal)
3. **Structure Canvas** - Full-song timeline showing all sections, energy overlay, and role activity lanes
4. **Edit** - Rename, split, merge, and retype sections; toggle role activity per segment
5. *(Coming)* Upload loops, auto-arrange, apply variations, and export

## Architecture

```
frontend/          React + TypeScript + Vite
  src/
    pages/         IngestPage, RegionMapPage, StructureCanvasPage, VisualComposerPage
    components/
      structureCanvas/   SectionTimeline, SectionBlock, SectionEditor,
                         EnergyOverlay, RoleActivityLanes, TimelineHeader
      visualComposer/    ComposerTimeline, LaneRow, Block, NotesPanel
    api/           reference.ts, referenceMix.ts, structureCanvas.ts
    context/       ProjectContext.tsx

backend/           Python FastAPI
  src/
    api/           routes_reference.py, routes_reference_mix.py, routes_visual_composer.py
    analysis/
      region_detector/   Novelty-curve section segmentation
      role_activity/     Spectral band role detection (drums, bass, melodic, vocal)
      energy/            RMS energy curve + transition markers
      motif_detector/    Motif detection & clustering
      call_response_detector/  Call-response pair detection
      fill_detector/     Fill detection
    models/        Region, ReferenceMix, ReferenceBundle, RoleActivityTimeline, etc.
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- librosa, soundfile, numpy (Python audio analysis)

### Backend

```bash
cd backend
pip install -r requirements.txt
cd src && uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and connects to the backend at `http://localhost:8000`.

## Implementation Progress

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Reference Ingestion & Full-Mix Analysis | Complete |
| Phase 2 | Structure Canvas (full-song timeline, section editing, energy overlay, role activity) | Complete |
| Phase 3 | Call-and-Response / Interaction Labeling | Planned |
| Phase 4 | User Loop / Stem Ingestion | Planned |
| Phase 5 | Loop Mapping Engine | Planned |
| Phase 6 | Variation Suggestions & Arrangement Guidance | Planned |
| Phase 7 | Placeholder Guide Content | Planned |
| Phase 8 | Fine-Tuning Interface | Planned |
| Phase 9 | Export Module | Planned |

### Phase 2 - Structure Canvas (Current)

The Structure Canvas transforms the per-region Visual Composer into a full-song timeline:

- **Full-song timeline** - All sections displayed simultaneously as color-coded blocks on a horizontal bar grid
- **Section editing** - Click any section to rename, change type, split at a bar position, or merge with the next section
- **Energy overlay** - RMS energy curve rendered as an area chart with transition markers (lift, drop, breakdown)
- **Role activity lanes** - Four lanes (drums, bass, melodic, vocal) showing active/inactive segments; click to toggle
- **Demo mode** - Works without uploaded audio using realistic demo data

#### API Endpoints (Phase 2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| PATCH | `/api/reference/{id}/regions` | Update region boundaries, labels, types |
| POST | `/api/reference/{id}/regions/split` | Split a region at a bar position |
| POST | `/api/reference/{id}/regions/merge` | Merge two adjacent regions |
| PATCH | `/api/reference/{id}/role-activity` | Apply user overrides to role activity |

## Key Design Decisions

- **Non-destructive** - All operations store metadata only; audio rendering happens at export time
- **In-memory storage** - V1 uses in-memory stores for speed; abstracted for future DB migration
- **Spectral band analysis** - Role detection uses HPSS + spectral bands from librosa (~70-80% accuracy; users correct via Structure Canvas)
- **Demo mode** - Structure Canvas works without a backend using built-in demo data for development/preview
