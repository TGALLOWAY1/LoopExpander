# CLAUDE.md — LoopExpander

## Project Overview

LoopExpander is a reference-driven arrangement tool. Users upload a reference track (full-mix or separated stems), the system analyzes its structure (sections, BPM, energy, roles), then maps user-provided loop material onto that structure to produce a DAW-ready arrangement with per-role WAV stems, MIDI markers, and structure metadata.

**Stack**: React + TypeScript + Vite frontend, Python FastAPI backend.

## Repository Structure

```
frontend/           React + TypeScript + Vite app
  src/
    api/            API client modules (reference.ts, arrangement.ts, etc.)
    components/     React components organized by feature
    pages/          Page-level components (Ingest, StructureCanvas, Arrangement, etc.)
    hooks/          Custom hooks (useAudioPlayback, useUndoRedo, etc.)
    types/          TypeScript type definitions
    context/        ProjectContext.tsx — shared state via React Context
    config.ts       Feature flags (Visual Composer)
    tests/          Frontend test files

backend/            Python FastAPI backend
  src/
    main.py         FastAPI entry point, router registration, CORS config
    config.py       All configuration constants and env var defaults
    api/            Route modules (reference, arrangement, user_loop, export, etc.)
    models/         Data models (Pydantic + dataclasses), in-memory stores
    analysis/       Audio analysis modules (region_detector, motif_detector, etc.)
    arrangement/    Mapping engine, variation engine, guidance, presets
    export/         Stem exporter (WAV), marker exporter (MIDI/JSON/CSV)
    stem_ingest/    Audio file loading and validation
    utils/          Logger, shared utilities
  tests/            Pytest test files (15+ modules)

docs/               Implementation summaries and design notes
```

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
cd src && uvicorn main:app --reload --port 8000
# OR: python dev.py
# OR: ./run.sh
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to :8000
```

### Both at once

```bash
./run.sh             # Starts backend + frontend with colored output
```

## Common Commands

| Task | Command |
|------|---------|
| Run backend tests | `cd backend && pytest` |
| Run frontend lint | `cd frontend && npm run lint` |
| Start backend dev | `cd backend/src && uvicorn main:app --reload --port 8000` |
| Start frontend dev | `cd frontend && npm run dev` |
| Type-check frontend | `cd frontend && npx tsc --noEmit` |

## Testing

- **Backend**: pytest discovers tests in `backend/tests/`. Run `cd backend && pytest`.
- **Frontend**: Test files exist in `frontend/src/tests/` but no test runner is configured in `package.json`. Lint is the primary frontend check (`npm run lint` with `--max-warnings 0`).

## Architecture & Data Flow

1. **Ingest** — Upload reference audio (full-mix or 4 stems + mix)
2. **Analyze** — Detect BPM, sections, energy curve, role activity, motifs, call-response patterns, fills
3. **Store** — In-memory dict-based stores in `backend/src/models/store.py`
4. **Structure Canvas** — User views/edits section timeline
5. **Loop Upload** — User uploads loop stems, assigns roles
6. **Mapping** — `mapping_engine.py` maps loops onto reference structure
7. **Fine-Tune** — Block editing, variation suggestions, section audition
8. **Export** — Per-role WAV stems + markers as ZIP bundle

**Storage**: All data is in-memory (dict stores). No database. Designed for future DB migration.

## Code Conventions

### Frontend (TypeScript/React)
- Functional components with hooks; no class components
- State management via React Context (`ProjectContext`)
- Plain CSS files alongside components (no CSS-in-JS)
- PascalCase for components/files, camelCase for functions/variables
- API clients centralized in `src/api/`
- TypeScript strict mode enabled

### Backend (Python/FastAPI)
- Type hints throughout; Pydantic for API models, dataclasses for internal models
- snake_case for files/functions, PascalCase for classes
- Routes organized by domain in `src/api/routes_*.py`
- Analysis modules are self-contained packages under `src/analysis/`
- HTTPException for error responses
- Custom logger in `src/utils/logger.py`

### General
- Atomic, focused commits with descriptive messages
- Feature branches merged via PRs to `main`
- No active git hooks or CI/CD pipeline

## Key Configuration

### Backend Environment Variables (with defaults in `config.py`)
- `LOG_LEVEL` (INFO)
- `MIN_BOUNDARY_GAP_SEC` (4.0), `MIN_REGION_DURATION_SEC` (8.0)
- `DEFAULT_MOTIF_SENSITIVITY` (0.5)
- `VISUAL_COMPOSER_ENABLED` (false)
- Various `DEFAULT_CALL_RESPONSE_*`, `DEFAULT_FILL_*`, `DEFAULT_SUBREGION_*` params

### Frontend Environment Variables
- `VITE_VISUAL_COMPOSER_ENABLED` — enables dev-only Visual Composer UI
- Vite proxy: `/api` routes → `http://localhost:8000`

### CORS
Backend allows origins: `localhost:3000`, `localhost:5173`, `127.0.0.1:3000`, `127.0.0.1:5173`

## Important Notes

- **No database** — all state is in-memory; restarting the backend clears data
- **Temp files** stored in `backend/src/tmp/reference/` (UUID subdirs), not auto-cleaned
- **Visual Composer** is a dev-only feature behind a feature flag
- **Audio analysis** uses librosa for feature extraction; role detection is ~70-80% accurate (spectral band heuristics, not ML)
- **Variation suggestions** are rules-based (deterministic), not neural
- **React StrictMode** is enabled — effects run twice in development
- Frontend ESLint enforces `--max-warnings 0` (all warnings are errors)
- Python 3.10+ required (type hint syntax)
- Node.js 18+ required
