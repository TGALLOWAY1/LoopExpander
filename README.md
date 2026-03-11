# LoopExpander

A reference-driven arrangement tool that analyzes a full-mix reference track, maps user-provided loop material onto that structure, and produces an expanded, DAW-ready arrangement.

<img width="1210" height="702" alt="image" src="https://github.com/user-attachments/assets/9483f085-6fa0-45cb-a525-4384f70e024e" />

## Overview

LoopExpander takes a single reference track (or separated stems), analyzes its structure, energy profile, and role activity, then helps you arrange your own loops across that structure. The workflow:

1. **Ingest** - Upload a reference track (single full-mix or 4 stems + mix)
2. **Analyze** - Automatic detection of sections, BPM, energy curve, and role activity (drums, bass, melodic, vocal)
3. **Structure Canvas** - Full-song timeline showing all sections, energy overlay, and role activity lanes
4. **Edit** - Rename, split, merge, and retype sections; toggle role activity per segment
5. **Loop Upload** - Upload your loop stems and assign roles (drums, bass, chord, lead, vocal, fx, percussion, texture)
6. **Auto-Arrange** - Map loops onto the reference structure with interaction labels and energy-aware dropouts
7. **Fine-Tune** - Edit blocks (resize, mute, delete), apply variation suggestions, and audition sections
8. **Export** - Download per-role WAV stems, MIDI markers, structure JSON, and CSV markers as a ZIP bundle

## Architecture

```
frontend/          React + TypeScript + Vite
  src/
    pages/         IngestPage, RegionMapPage, StructureCanvasPage,
                   LoopIngestPage, ArrangementPage
    components/
      structureCanvas/   SectionTimeline, SectionBlock, SectionEditor,
                         EnergyOverlay, RoleActivityLanes, TimelineHeader
      arrangement/       SuggestionPanel, GuidanceOverlay, GuideMarkerLayer,
                         BlockToolbar, AuditionPlayer
      export/            ExportPanel
      visualComposer/    ComposerTimeline, LaneRow, Block, NotesPanel
    api/           reference.ts, referenceMix.ts, arrangement.ts,
                   suggestions.ts, userLoop.ts
    context/       ProjectContext.tsx

backend/           Python FastAPI
  src/
    api/           routes_reference.py, routes_reference_mix.py,
                   routes_arrangement.py, routes_user_loop.py,
                   routes_export.py
    analysis/
      region_detector/   Novelty-curve section segmentation
      role_activity/     Spectral band role detection (drums, bass, melodic, vocal)
      energy/            RMS energy curve + transition markers
      motif_detector/    Motif detection & clustering
      call_response_detector/  Call-response pair detection
      fill_detector/     Fill detection
    arrangement/
      mapping_engine.py      Loop-to-structure mapping
      variation_engine.py    Variation suggestion rules
      guidance_engine.py     Arrangement guidance analysis
      guide_content.py       Guide marker generation
      audition.py            Section audio preview renderer
    export/
      stem_exporter.py       Per-role WAV rendering
      marker_exporter.py     JSON, MIDI, CSV marker export
    models/        Region, ReferenceMix, ReferenceBundle, RoleActivityTimeline,
                   UserLoopBundle, Arrangement, InteractionLabel, etc.
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
| Phase 3 | Call-and-Response / Interaction Labeling | Complete |
| Phase 4 | User Loop / Stem Ingestion | Complete |
| Phase 5 | Loop Mapping Engine | Complete |
| Phase 6 | Variation Suggestions & Arrangement Guidance | Complete |
| Phase 7 | Placeholder Guide Content | Complete |
| Phase 8 | Fine-Tuning Interface | Complete |
| Phase 9 | Export Module | Complete |

### Phase 8 - Fine-Tuning Interface

Extends the Arrangement page with interactive editing and audio preview:

- **Block editing toolbar** - Click a block to select, then mute/unmute or delete it from the inline toolbar
- **Drag-to-resize** - Selected blocks show resize handles on left/right edges; drag to adjust bar boundaries
- **Section audition** - Select a section and play its rendered audio with play/stop/loop transport controls
- **Solo/Mute roles** - During audition, solo (S) or mute (M) individual roles for isolated listening
- **Variation suggestions** - Side panel with apply/dismiss actions for auto-generated arrangement improvements

#### API Endpoints (Phase 8)

| Method | Endpoint | Description |
|--------|----------|-------------|
| PATCH | `/api/project/{id}/arrangement/blocks/{blockId}` | Update block (mute, resize, move) |
| DELETE | `/api/project/{id}/arrangement/blocks/{blockId}` | Delete a block |
| POST | `/api/project/{id}/audition` | Render a section's audio for preview (returns WAV) |

### Phase 9 - Export Module

Full arrangement export with multiple output formats:

- **Stem export** - Renders one continuous WAV file per role for the full song length
- **Format options** - WAV 16-bit, WAV 24-bit, or AIFF
- **MIDI markers** - Section boundaries as MIDI marker events (importable by most DAWs)
- **Structure JSON** - Full arrangement data including sections, blocks, interaction labels, guide markers
- **CSV markers** - Section boundaries in CSV format with bar positions and timestamps
- **ZIP bundle** - All selected outputs packaged into a single downloadable ZIP file

#### API Endpoints (Phase 9)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/project/{id}/export` | Export arrangement as ZIP bundle |

## Key Design Decisions

- **Non-destructive** - All operations store metadata only; audio rendering happens at export time and during section audition
- **In-memory storage** - V1 uses in-memory stores for speed; abstracted for future DB migration
- **Spectral band analysis** - Role detection uses HPSS + spectral bands from librosa (~70-80% accuracy; users correct via Structure Canvas)
- **Demo mode** - Structure Canvas works without a backend using built-in demo data for development/preview
- **Rules-based suggestions** - Variation suggestions use deterministic rules (mute on repetition, pre-impact dropout, A/B alternation) rather than ML
- **Modular export** - Users choose which outputs to include; stems, markers, and structure data are independently toggleable
