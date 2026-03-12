# Structural Patterns & Energy UI Improvement Plan

## Current State Summary

The codebase already has:
- **Energy**: Single RMS-based energy curve (`energy_curve.py`) with bar-level granularity and transition markers
- **Motifs**: MFCC-based motif detection with DBSCAN clustering (`motif_detector.py`), per-stem, with variation marking
- **Regions**: Novelty-based region detection with energy-driven labeling (`region_detector.py`)
- **Feature extraction**: `spectral_centroid`, `transient_density`, `compute_band_energy` already exist in `features.py` and `spectral_bands.py`
- **UI**: Single energy curve overlay (RMS only), section blocks, role lanes, arrangement timeline

## What's Missing (per the guidance)

1. **Multi-dimensional energy curves** — only RMS exists; no LUFS, spectral centroid curve, bass energy curve, or transient density curve exposed to frontend
2. **Loop repetition (exact match) detection** — motif detector groups by similarity but doesn't distinguish exact vs. near matches
3. **Call-response pattern detection** — backend has a `REFERENCE_CALL_RESPONSE` store slot but no detection algorithm
4. **Tonal balance display** — no 5-band spectral balance (Low/LowMid/Mid/HighMid/High) per region
5. **Song View vs Section View** — UI shows everything at once; no simplified "song overview" vs "section detail" split
6. **Arrangement presets** — no genre-based structure templates
7. **Structural pattern data model** — no unified model combining loops, motifGroups, callResponsePairs, regions, energyCurves, tonalBalance

---

## Implementation Plan

### Phase 1: Multi-Layer Energy Curves (Backend)

**Files to modify:**
- `backend/src/analysis/energy/energy_curve.py` — extend `EnergyCurveResult`
- `backend/src/analysis/region_detector/features.py` — already has `compute_spectral_centroid` and `compute_transient_density`; reuse
- `backend/src/models/store.py` — update energy curve storage shape
- `backend/src/api/routes_reference.py` or `routes_reference_mix.py` — update API response

**Changes:**
1. Add `compute_multi_energy_curves()` function that computes 4 parallel curves:
   - **LUFS (Short-Term)**: Use `librosa`'s RMS with LUFS-style weighting (or approximate via K-weighted RMS). Compute integrated and short-term.
   - **Spectral Centroid**: Reuse existing `compute_spectral_centroid()` from `features.py`, aggregate per-bar
   - **Bass Energy (20-80 Hz)**: Reuse existing `compute_band_energy()` from `spectral_bands.py` with `low_hz=20, high_hz=80`, aggregate per-bar
   - **Transient Density**: Reuse existing `compute_transient_density()` from `features.py`, aggregate per-bar
2. Extend `EnergyCurveResult` dataclass to include all 4 curve arrays
3. Update the API endpoint to return the full multi-curve payload

### Phase 2: Multi-Layer Energy Curves (Frontend)

**Files to modify:**
- `frontend/src/components/structureCanvas/EnergyOverlay.tsx` — replace single curve with stacked multi-curve display
- `frontend/src/api/referenceMix.ts` — update response type

**Changes:**
1. Update `EnergyCurveResponse` type to include `spectralCentroid`, `bassEnergy`, `transientDensity` arrays
2. Rewrite `EnergyOverlay` to render 4 stacked curves with distinct colors:
   - Loudness (blue), Brightness (orange), Bass Energy (red), Transient Rate (green)
3. Add toggle buttons to show/hide individual curves
4. Each curve rendered as a semi-transparent area chart on the same canvas (layered)

### Phase 3: Tonal Balance per Region (Backend + Frontend)

**Files to create:**
- `backend/src/analysis/energy/tonal_balance.py`

**Files to modify:**
- `backend/src/api/routes_reference.py` — add tonal balance endpoint or include in energy response
- Frontend: new `TonalBalanceDisplay` component

**Changes:**
1. Create `compute_tonal_balance()` that computes 5-band energy per region:
   - Low (20-250 Hz), Low-Mid (250-500 Hz), Mid (500-2000 Hz), High-Mid (2000-6000 Hz), High (6000-20000 Hz)
   - Use existing `compute_band_energy()` from `spectral_bands.py`
2. Return per-region tonal balance as part of the structure canvas data
3. Frontend: render as horizontal bar chart per section when section is selected/hovered

### Phase 4: Exact Loop Repetition Detection

**Files to modify:**
- `backend/src/analysis/motif_detector/motif_detector.py` — add similarity threshold classification

**Changes:**
1. In `_cluster_motifs`, after clustering, compute pairwise similarity within each group
2. Classify members as:
   - **Exact** if `similarity > 0.92` (chroma + MFCC + spectral envelope)
   - **Variation** if `rhythm_similarity > 0.9 AND timbre_similarity between 0.4-0.9`
3. Add `similarity_type` field to `MotifInstance`: `"exact"` | `"variation"` | `"unique"`
4. Frontend: render exact matches as identical-color blocks, variations as different shades

### Phase 5: Call-Response Pattern Detection

**Files to create:**
- `backend/src/analysis/call_response/detector.py`

**Files to modify:**
- `backend/src/models/store.py` — already has `REFERENCE_CALL_RESPONSE` slot
- `backend/src/api/routes_reference.py` — add endpoint

**Changes:**
1. Implement `detect_call_response_pairs()`:
   - For each pair of stems (e.g., lead + bass), find motifs that alternate with consistent time offset
   - Rule: `time_offset(call_i, response_i) ≈ constant` across >= 3 repetitions
   - Return `CallResponsePair` with call stem, response stem, instances, and average lag
2. Wire into the analysis pipeline
3. Frontend: render as paired blocks with arc connectors between call and response

### Phase 6: Arrangement Regions with Algorithmic Labeling

**Files to modify:**
- `backend/src/analysis/region_detector/region_detector.py` — enhance `assign_region_labels`

**Changes:**
1. Use multi-dimensional energy signals for boundary detection:
   - Δ LUFS, Δ spectral centroid, Δ transient density, Δ bass energy
   - Boundary when `energy_gradient > threshold` across multiple signals
2. Update semantic label assignment to use energy patterns:
   - Gradual rise → "Build"
   - Sudden peak → "Drop"
   - Low density → "Breakdown"
3. Make labels editable (already partially supported via `label` field on Region)

### Phase 7: Song View vs Section View (Frontend)

**Files to modify:**
- `frontend/src/pages/StructureCanvasPage.tsx` — add view mode toggle
- `frontend/src/components/structureCanvas/` — new or modified components

**Changes:**
1. **Song View (default)**: Simplified display showing:
   - Section blocks: `Intro | Build | Drop | Break | Drop | Outro`
   - Single composite energy curve underneath
   - Click a section to enter Section View
2. **Section View**: Existing detailed view showing:
   - Stem lanes with role activity
   - Motif blocks with exact/variation shading
   - Call-response arcs
   - Loop instances
   - Tonal balance for the selected section
3. Add smooth transition between views (zoom into section)

### Phase 8: Structural Pattern Data Model

**Files to create:**
- `backend/src/models/structural_patterns.py`

**Changes:**
1. Create unified `StructuralPatternBundle` dataclass:
   - `loops: List[LoopInstance]` — exact repetitions
   - `motif_groups: List[MotifGroup]` — near-similar patterns
   - `call_response_pairs: List[CallResponsePair]`
   - `regions: List[Region]`
   - `energy_curves: MultiEnergyCurves` — lufs, spectralCentroid, bassEnergy, transientDensity
   - `tonal_balance: List[RegionTonalBalance]`
2. Add API endpoint that returns the full bundle for a reference
3. Frontend: consume this unified model in the Structure Canvas

### Phase 9: Arrangement Presets

**Files to create:**
- `backend/src/arrangement/presets.py`

**Files to modify:**
- `backend/src/arrangement/mapping_engine.py` — accept preset as input
- `frontend/src/pages/ArrangementPage.tsx` — preset selector UI

**Changes:**
1. Define preset templates for genres:
   - Future Bass, Dubstep, Trap, Pop, House
   - Each specifies: region order, region lengths (in bars), density curves, call-response templates
2. Add preset selection step before arrangement generation
3. Reference songs refine the preset (override lengths/order from detected structure)
4. Frontend: genre selector dropdown/cards before "Generate Arrangement"

### Phase 10: Playback Priority

**Files to modify:**
- `frontend/src/pages/ArrangementPage.tsx` — auto-trigger playback after generation

**Changes:**
1. After arrangement generation completes, automatically scroll to and highlight the AuditionPlayer
2. Auto-start playback of the first section
3. Add a prominent "Play Full Arrangement" button at the top of the arrangement view

---

## Priority Order

1. **Phase 1+2** (Multi-Energy Curves) — Most impactful visual improvement, leverages existing backend code
2. **Phase 4** (Exact Loop Detection) — Extends existing motif detector, small change
3. **Phase 7** (Song View vs Section View) — Biggest UX improvement
4. **Phase 3** (Tonal Balance) — Useful for arrangement guidance
5. **Phase 6** (Algorithmic Region Labels) — Improves label accuracy
6. **Phase 5** (Call-Response Detection) — New detection capability
7. **Phase 8** (Unified Data Model) — Clean architecture, can be done incrementally
8. **Phase 9** (Arrangement Presets) — Feature addition, independent of other phases
9. **Phase 10** (Playback Priority) — Small UX polish
