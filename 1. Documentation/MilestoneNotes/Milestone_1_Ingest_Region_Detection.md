# Milestone 1: Ingest & Region Detection

## Overview

This milestone implements the complete vertical slice for uploading reference tracks, analyzing their structure, and visualizing detected regions. The implementation includes both backend analysis engine and frontend UI components.

## Implementation Summary

### Backend Implementation

#### 1. Project Scaffold (Prompt 1)
- **Files Created:**
  - `backend/src/main.py` - FastAPI application with CORS middleware
  - `backend/src/config.py` - Configuration with APP_NAME and LOG_LEVEL
  - `backend/src/utils/logger.py` - Logging utility with get_logger()
  - `backend/src/api/routes_reference.py` - Reference API router
  - `backend/requirements.txt` - Python dependencies

- **Features:**
  - FastAPI app with healthcheck endpoint (`GET /api/health`)
  - CORS middleware configured for localhost frontend
  - Basic logging infrastructure
  - Reference API router with ping endpoint

#### 2. Ingest Models & Service (Prompt 2)
- **Files Created:**
  - `backend/src/stem_ingest/audio_file.py` - AudioFile model and loading logic
  - `backend/src/models/reference_bundle.py` - ReferenceBundle container model
  - `backend/src/stem_ingest/ingest_service.py` - Reference bundle loading service
  - `backend/tests/test_ingest_validation.py` - Validation tests

- **Features:**
  - AudioFile dataclass with path, role, sr, duration, channels, samples
  - Format validation (WAV/AIFF only)
  - Automatic resampling to target sample rates (44100, 48000, 96000)
  - ReferenceBundle with 5 AudioFiles (drums, bass, vocals, instruments, full_mix)
  - Duration validation with tolerance checking
  - BPM estimation using librosa.beat.tempo
  - Key estimation stub (returns None for now)

#### 3. Feature Extraction (Prompt 3)
- **Files Created:**
  - `backend/src/analysis/region_detector/features.py` - Feature extraction utilities
  - `backend/tests/test_feature_extraction.py` - Feature extraction tests

- **Features:**
  - `compute_rms_envelope()` - Frame-wise RMS energy
  - `compute_spectral_centroid()` - Spectral brightness analysis
  - `compute_transient_density()` - Onset strength density
  - `compute_novelty_curve()` - Spectral flux for boundary detection
  - Automatic mono conversion for multi-channel audio
  - Normalized outputs for transient density and novelty curve

#### 4. Region Detection Pipeline (Prompt 4)
- **Files Created:**
  - `backend/src/models/region.py` - Region dataclass model
  - `backend/src/analysis/region_detector/priors.py` - Probabilistic boundary priors
  - `backend/src/analysis/region_detector/region_detector.py` - Main detection algorithm
  - `backend/tests/test_region_detection.py` - Region detection tests

- **Features:**
  - Region model with id, name, type, start, end, motifs, fills, callResponse
  - Probabilistic priors based on typical song structure (intro, chorus, breakdown, outro)
  - Novelty curve peak detection using scipy
  - Boundary snapping (priors to nearest peaks)
  - Region generation from boundaries
  - Energy-based type assignment (low_energy, build, high_energy, drop)

#### 5. API Endpoints (Prompt 5)
- **Files Created:**
  - `backend/src/models/store.py` - In-memory storage for bundles and regions
  - Updated `backend/src/api/routes_reference.py` - Full API implementation

- **Endpoints:**
  - `POST /api/reference/upload` - Upload 5 audio files, returns referenceId
  - `POST /api/reference/{id}/analyze` - Run region detection analysis
  - `GET /api/reference/{id}/regions` - Get detected regions as JSON

- **Features:**
  - File upload handling with temporary storage
  - Error handling with cleanup
  - JSON serialization of Region dataclasses
  - In-memory storage (suitable for M1)

#### 6. Region Detection Improvements (Prompt 9)
- **Files Updated:**
  - `backend/src/config.py` - Added MIN_BOUNDARY_GAP_SEC and MIN_REGION_DURATION_SEC
  - `backend/src/analysis/region_detector/region_detector.py` - Major improvements

- **Improvements:**
  - Minimum boundary gap enforcement (4.0s default)
  - Minimum region duration enforcement (8.0s default) with merge logic
  - Enhanced region statistics computation (energy z-scores, slopes)
  - Improved labeling heuristics:
    - Guaranteed Intro and Outro
    - Drop detection (highest energy, prefers middle position)
    - Build vs Breakdown vs Verse logic based on energy slope
  - Comprehensive diagnostic logging with region stats table

#### 7. BPM Estimation Improvements (Prompt 10)
- **Files Updated:**
  - `backend/src/stem_ingest/ingest_service.py` - BPM snapping logic

- **Improvements:**
  - `snap_bpm_to_grid()` helper function
  - Uses `librosa.beat.tempo` with median aggregate
  - Snaps to nearest integer BPM
  - Half-time/double-time correction (< 70 or > 180 BPM)
  - Detailed logging of raw vs snapped BPM

### Frontend Implementation

#### 8. API Client & Project Context (Prompt 6)
- **Files Created:**
  - `frontend/src/api/reference.ts` - TypeScript API client
  - `frontend/src/context/ProjectContext.tsx` - React context for project state
  - `frontend/src/main.tsx` - App entry with ProjectProvider
  - `frontend/package.json` - React + TypeScript + Vite setup
  - `frontend/tsconfig.json` - TypeScript configuration
  - `frontend/vite.config.ts` - Vite config with API proxy

- **Features:**
  - TypeScript API client with uploadReference, analyzeReference, fetchRegions
  - ProjectContext with referenceId and regions state
  - useProject() hook for accessing context
  - Configurable API base URL via environment variables

#### 9. Ingest Page UI (Prompt 7)
- **Files Created:**
  - `frontend/src/pages/IngestPage.tsx` - Upload and analysis UI
  - `frontend/src/pages/IngestPage.css` - Styling

- **Features:**
  - File inputs for 5 audio files (drums, bass, vocals, instruments, full_mix)
  - "Analyze Reference" button with validation
  - Status messages (Uploading, Analyzing, Complete)
  - Error handling with inline messages
  - Automatic navigation to Region Map after analysis
  - Integration with ProjectContext

#### 10. Region Map Page UI (Prompt 8)
- **Files Created:**
  - `frontend/src/pages/RegionMapPage.tsx` - Timeline visualization
  - `frontend/src/pages/RegionMapPage.css` - Styling
  - `frontend/src/components/RegionBlock.tsx` - Individual region component
  - `frontend/src/components/RegionBlock.css` - Component styling
  - `frontend/src/App.tsx` - Updated with routing
  - `frontend/src/App.css` - Navigation styles

- **Features:**
  - Horizontal timeline with color-coded region blocks
  - Proportional width based on region duration
  - Color coding by region type (low_energy, build, high_energy, drop)
  - Time scale markers
  - Region list with details below timeline
  - Empty states for no reference/no regions
  - Read-only view (no editing in M1)

### Documentation

#### 11. Nano Banana Prompts (Prompt 9)
- **Files Created:**
  - `docs/nano-banana/ingest-view.md` - Design prompt for ingest UI
  - `docs/nano-banana/region-map.md` - Design prompt for region map UI

- **Features:**
  - Detailed UI specifications for visual mockup generation
  - Strict 2D screen-only rendering rules
  - Color schemes, layouts, and interaction states
  - Updated to enforce no physical objects or 3D elements

## Technical Details

### Dependencies Added
- FastAPI, uvicorn, python-multipart
- librosa, soundfile, numpy, scipy
- pydantic, typing-extensions
- pytest (for testing)

### Configuration
- `MIN_BOUNDARY_GAP_SEC = 4.0` - Minimum gap between region boundaries
- `MIN_REGION_DURATION_SEC = 8.0` - Minimum region duration before merging
- Configurable via environment variables

### Key Algorithms
1. **Novelty Detection**: Spectral flux for structural boundary detection
2. **Boundary Generation**: Combination of novelty peaks and probabilistic priors
3. **Region Merging**: Merges regions below minimum duration threshold
4. **Label Assignment**: Energy-based heuristics with z-score normalization
5. **BPM Snapping**: Round to integer with half-time/double-time correction

## Testing

### Test Coverage
- Ingest validation tests (duration matching)
- Feature extraction tests (RMS, spectral centroid, transient density, novelty)
- Region detection tests (boundary generation, labeling, merging)

### Test Files
- `backend/tests/test_ingest_validation.py`
- `backend/tests/test_feature_extraction.py`
- `backend/tests/test_region_detection.py`

## Git Commits

1. `feat: scaffold backend with FastAPI app and basic logger`
2. `feat: implement AudioFile, ReferenceBundle, and reference ingest service`
3. `feat: add feature extraction utilities for region detection`
4. `feat: implement region model, priors, and region detection pipeline`
5. `feat: expose reference upload, analyze, and regions API endpoints`
6. `feat: add reference API client and project context on frontend`
7. `feat: implement ingest page UI to upload and analyze reference stems`
8. `feat: add region map page with read-only timeline of detected regions`
9. `docs: add Nano Banana prompts for ingest and region map views`
10. `docs: refine Nano Banana prompts to enforce strict 2D screen-only UI rendering`
11. `fix: stabilize region segmentation and improve heuristic labels with min duration and energy-based rules`
12. `fix: snap BPM estimates to musically sensible values and log raw vs snapped tempo`

## Exit Criteria Met

✅ Can load a real song's stems + mix  
✅ View a Region Map with labeled sections  
✅ Processing time for 4-min track is within 20-60s target  
✅ Region count is reasonable (5-10 for 2.5 min track)  
✅ Regions have meaningful labels (Intro, Build, Drop, Outro, etc.)  
✅ BPM is human-readable (integer values)  
✅ Full vertical slice: upload → analyze → view regions  

## Next Steps (Future Milestones)

- Milestone 2: Motif & Call-Response detection
- Milestone 3: User Stems ingestion
- Milestone 4: Arrangement Engine
- Milestone 5: Export functionality
- Milestone 6: Region Editing Tools

