LoopExpander Development plan 

Here’s a concrete development plan from a lead dev / architect POV, aligned to your PRD.   
 
0. Working Assumptions & Tech Stack 
 
You can adjust these, but I’ll anchor the plan to something concrete: 
 
Runtime & Core: 
Backend / analysis engine: Python 3.11+ 
Audio / DSP: librosa, soundfile, numpy, scipy, possibly essentia later 
CLI + simple HTTP API: FastAPI (or Flask) for local service mode 
 
Frontend: 
React + TypeScript SPA 
Component lib: minimal (e.g., MUI or Tailwind + headless components) 
Bundler: Vite 
 
Project structure (monorepo): 
song-structure-replicator/ 
  backend/ 
    src/ 
      stem_ingest/ 
      analysis/ 
        region_detector/ 
        motif_detector/ 
        call_response_detector/ 
        fill_detector/ 
      arrangement/ 
      exporter/ 
    tests/ 
  frontend/ 
    src/ 
      pages/ 
      components/ 
      hooks/ 
      api/ 
    tests/ 
  docs/ 
    nano-banana/ 
      ingest-view.md 
      region-map.md 
      timeline-arranger.md 
      export-view.md 
  scripts/ 
  README.md 
Governing principle: backend is a headless “analysis & arrangement engine”; frontend is just a client. 
 
1. Architecture Overview (Concrete) 
 
1.1 Core Backend Modules (matching PRD) 
stem_ingest 
File validation (formats, sample rates, length coherence)   
BPM detection / user override 
Simple key estimation (optional/heuristic) 
analysis.region_detector 
Compute per-stem envelopes, spectral features, novelty. 
Use probabilistic priors for typical structures; refine with novelty peaks.   
analysis.motif_detector 
Segment candidate motifs (short windows). 
Extract embeddings/features and cluster. 
Mark motif groups + variations, with sensitivity param. 
analysis.call_response_detector 
Look at lead-lag patterns between motif occurrences (inter- and intra-stem).   
analysis.fill_detector 
Detect high-transient-density windows at region boundaries; classify as fills. 
arrangement 
Map reference region map onto user timeline (bars). 
Apply on/off patterns, dropout, gap moments. 
exporter 
Slice user stems per region and write to disk. 
(Later) generate PDF/PNG region map + optional MIDI markers. 
api/http 
REST endpoints for: 
Upload reference 
Run analysis 
Get region map / motifs / call-response / fills 
Upload user stems 
Generate arrangement 
Export 
 
1.2 Frontend 
Pages 
IngestPage (reference ingest + state) 
StructureMapPage (Region Map + editing) 
ArrangementPage (user stems + arrangement timeline) 
ExportPage 
Shared State 
Global ProjectContext or RTK store: 
referenceTrack, referenceRegions, motifs, callResponse, fills 
userStems, userArrangement 
exportConfig 
API Clients 
api/reference.ts 
api/analysis.ts 
api/userStems.ts 
api/arrangement.ts 
api/export.ts 
Nano Banana Prompts 
/docs/nano-banana/ingest-view.md 
/docs/nano-banana/region-map.md 
/docs/nano-banana/timeline-arranger.md 
/docs/nano-banana/export-view.md 
 
2. Milestone-by-Milestone Development Plan 
 
I’ll expand the PRD milestones into concrete epics / tasks.   
 
Milestone 1 — Ingest & Region Detection 
 
Goal: Load 4 stems + full mix; detect regions; show a basic Region Map. 
 
Backend Tasks 
Core project scaffold 
Set up backend with poetry or pip-tools, basic folder structure, and tests. 
Add logging config and .env handling. 
Ingest module (MVP) 
Implement AudioFile class with: 
path, sr, duration, channels, role 
Implement: 
load_reference_bundle(paths: dict[str, Path]) -> ReferenceBundle 
Validation: 
Same duration within tolerance for stems + mix. 
Supported formats (WAV/AIFF). 
Sample rates (44.1/48/96 kHz; resample others). 
BPM + key detection (simple first) 
estimate_bpm(full_mix) -> float 
Optionally estimate_key(full_mix) -> Optional[str] 
Allow overrides via API. 
Feature extraction 
Per-stem and full-mix: 
RMS / loudness envelope 
Spectral centroid 
Transient / onset counts 
Global novelty curve (e.g., self-similarity + spectral flux) 
Region detection v1 
Implement: 
detect_regions(features, priors) -> list[Region] 
Logic: 
Generate rough candidate boundaries from novelty peaks. 
Apply simple priors (expected positions of intro/chorus, etc.). 
Assign region labels + types + confidence. 
Region serialization 
Implement Region model per PRD (id, name, type, start, end, etc.).   
Basic JSON schema for API responses. 
API endpoints 
POST /reference/upload 
Accepts 4 stems + full mix; returns referenceId. 
POST /reference/{id}/analyze 
Triggers analysis -> region detection. 
GET /reference/{id}/regions 
Returns region list. 
Unit & integration tests 
Unit tests for ingest & validation. 
Use short fake audio (noise) for region detection sanity checks. 
Simple integration test: upload → analyze → get regions. 
 
Frontend Tasks 
Scaffold React app 
Vite, TS config, routing, basic layout. 
Ingest UI 
Drag-and-drop zone for stems + full mix. 
Role assignment for each file. 
Show BPM detected / editable. 
Call /reference/upload and /reference/{id}/analyze. 
Region Map UI (v1) 
Simple horizontal timeline with colored blocks per region. 
Show region name, start/end (in seconds for now). 
No editing yet — read-only. 
Nano Banana prompt: ingest-view.md & region-map.md 
Describe how the ingest and region map should look/behave. 
 
Exit Criteria 
Can load a real song’s stems + mix and view a Region Map with labeled sections. 
Processing time for 4-min track is within the rough 20–60s target on your machine. 
 
Milestone 2 — Motif & Call-Response 
 
Goal: Detect motifs, variations, call & response, and fills; visualize them on the Region Map.   
 
Backend Tasks 
Motif segmentation & features 
Segment stems into phrase-length windows (e.g., 1–4 bars). 
Extract MFCCs or melodic descriptors per segment. 
Implement Motif model + MotifGroup. 
Motif clustering 
Use distance metrics + clustering (e.g., agglomerative or DBSCAN). 
Mark: 
motif_id, group_id, is_variation. 
Add a “sensitivity” parameter to tune grouping. 
Call & response detection 
For each motif instance: 
Look for matching motif(s) within time window offset (e.g., 0.5–2 bars later) in other stems or same stem. 
Define: 
CallResponsePair: { fromMotifId, toMotifId, fromStem, toStem, timeOffset, confidence }. 
Fill detection 
Use transient density / high novelty near region boundaries to flag fills. 
Fill: { id, time, stems, associatedRegionId }. 
API expansions 
GET /reference/{id}/motifs 
GET /reference/{id}/call-response 
GET /reference/{id}/fills 
Tests 
Synthetic sequences to validate motif grouping (e.g., repeated patterns with small variations). 
Sanity tests: call-response offsets are in plausible ranges. 
 
Frontend Tasks 
Motif visualization on Region Map 
Option: motif markers within regions (icons or colored underlines). 
Hover / click to highlight all occurrences of same motif group. 
Call & response visualization 
Option A: arcs/lines overlay. 
Option B: side panel listing “conversations” (leaning toward this as in backlog suggestion). 
For v1.1: minimal arcs plus an inspector list. 
Fill markers 
Icons at bar positions near region transitions. 
Motif sensitivity control 
Slider in UI that calls API with different sensitivity / filters. 
Nano Banana update: region-map.md 
Update prompt to include motif & call-response visual. 
 
Exit Criteria 
Region Map shows motif groupings, call-response relationships, and fills. 
You can click a motif and see all locations; click a region and see its fills. 
 
Milestone 3 — User Stems 
 
Goal: Import user’s loop stems, detect loop length (bars), organize categories, validate.   
 
Backend Tasks 
User stem ingestion 
POST /user/{projectId}/stems 
Accept up to 16 stems, with category (drums/bass/vocals/instruments) + optional sub-track name. 
Loop length detection 
Using BPM (provided by user or estimated) + periodicity detection: 
Determine if the loop is 8/16/32 bars. 
Provide method for user override. 
Model for user stems 
UserStem: { id, path, category, name, barsLength, bpm, sampleRate, etc. }. 
Validation 
Ensure consistent BPM across user stems. 
Warn if stems drastically differ in length / alignment. 
Tests 
Unit tests for basic loop detection. 
Integration flow: create project → upload user stems → get metadata. 
 
Frontend Tasks 
User Stems Page/Section 
UI to upload stems and assign categories. 
Display detected loop length (bars) and allow override. 
Project glue 
Link reference analysis and user stems under one projectId. 
Show “Ready for Arrangement” status when both reference and user stems are in place. 
Nano Banana update 
Extend timeline-arranger.md description to reference user stems & categories. 
 
Exit Criteria 
You can import your loop stems, see their categories and loop length in bars, and have them associated with a reference project. 
 
Milestone 4 — Arrangement Engine 
 
Goal: Map user stems into a full arrangement based on the reference region map, density patterns, call & response, and gap moments.   
 
Backend Tasks 
Density & dropout patterns (from reference) 
For each region & stem category: 
Compute activity (e.g., energy / RMS threshold). 
Build a simple binary or graded on/off pattern. 
Arrangement mapping 
generate_arrangement(reference, userStems, options) -> ArrangementMap 
Steps: 
Translate reference region lengths to bars (initially via BPM/time; later refactor to true bars-based model per backlog). 
For each region: 
Clone user loops to fill region length. 
Apply stem on/off patterns to imitate reference density. 
Use call & response templates to alternate between stems when appropriate. 
Insert gaps where reference has full/partial dropouts. 
Data model 
ArrangementMap as per PRD (regions, motifs, fills, callResponsePairs, densityCurves).   
Plus explicit clip-blocks for user stems: 
clips: [ { stemId, regionId, barStart, barEnd, active } ] 
API 
POST /project/{id}/arrange 
Returns arrangement map + clip grid. 
Tests 
Synthetic test where reference has known gaps and dropouts – verify the generated arrangement respects them. 
 
Frontend Tasks 
Arrangement Timeline UI 
Multi-lane grid: 
X-axis: bars/regions. 
Y-axis: stems (grouped by category). 
Colored blocks where stems are active. 
Region headers on top (Intro, Build, Drop, etc.). 
Playback hooks 
For now, simple: highlight playhead but audio playback can be minimal or stubbed. 
Later: optionally integrate simple playback of reference/user stems via web audio. 
Inspector panel 
Click a clip or region to see: 
Stem, region name, role, call-response info, motif tags. 
Nano Banana 
Flesh out timeline-arranger.md to cover: multi-lane grid, clips, call-response overlays. 
 
Exit Criteria 
Given a reference and user stems, the app generates and displays a full arrangement timeline showing when each user stem is active across regions. 
 
Milestone 5 — Export 
 
Goal: Export region-sliced user stems and optional visual summaries (PDF/PNG), plus optional MIDI marker file.   
 
Backend Tasks 
Stem slicing 
Implement: 
slice_stems_by_regions(userStems, arrangementMap, bpm) -> list[ExportedStemRegion] 
Use sample-accurate slicing based on bar positions. 
Filesystem layout 
Folder-per-region: 
/01_Intro/01-Intro-Drums.wav, etc., as in PRD.   
Optional exports 
Simple region map PNG: 
Use matplotlib or PIL to render a basic time vs region block diagram. 
MIDI marker file: 
Create a .mid with markers at region starts and important motifs/fills. 
API 
POST /project/{id}/export 
Accepts options (stems-only, stems+PNG, stems+MIDI). 
Returns path or zipped archive for download. 
Tests 
Validate slice lengths & file names for synthetic cases. 
Round-trip: arrangement → export → re-import to check alignment. 
 
Frontend Tasks 
Export UI 
Options for: 
Stems only 
Region map PNG / “PDF” 
MIDI markers 
Show project summary (reference track, length, BPM, etc.). 
Download handling 
Show progress / success states; allow user to open export folder. 
Nano Banana 
export-view.md prompt describing export summary screen. 
 
Exit Criteria 
User can click export and get a structured folder with region-sliced stems that line up in their DAW. 
 
Milestone 6 — Region Editing Tools 
 
Goal: Human-in-the-loop editing of regions, motifs, and call-response, feeding back into arrangement & templates.   
 
Backend Tasks 
Editable region model 
API endpoints: 
PATCH /reference/{id}/regions (bulk update: split, merge, rename, retype). 
Implement logic for: 
Splitting region at a specific bar/second. 
Merging adjacent regions. 
Recalculating derived data (e.g., which motifs/fills fall into which region). 
Editable motif & call-response groups 
PATCH /reference/{id}/motifs (reassign motif group). 
PATCH /reference/{id}/call-response (update relationships). 
Recompute arrangement 
On changes to region map or motif/call-response groups, mark arrangement as stale. 
Allow “Re-generate arrangement” using updated structure. 
Template saving 
(Optional, but powerful and in scope) 
POST /templates to save cleaned-up region + interaction map as reusable template. 
 
Frontend Tasks 
Region editing UI 
Drag handles on Region Map to move boundaries. 
Context menu / buttons: 
Split at playhead / bar. 
Merge with previous/next. 
Rename / change type. 
Motif & call-response editing 
Side “Conversation” panel: 
List call-response pairs. 
Allow reassigning roles (call ↔ response). 
Simple motif group reassign UI. 
Re-generation flow 
“Apply Changes & Rebuild Arrangement” button with confirmation dialog. 
Nano Banana 
Update region-map & timeline-arranger prompts to reflect editing tools. 
 
Exit Criteria 
You can adjust the detected structure, re-run the arrangement engine, and export updated stems. 
 
3. Cross-Cutting Concerns 
 
3.1 Testing Strategy 
Unit Tests 
For all analysis submodules (ingest, features, detection). 
Golden Sample Tests 
Keep 1–3 known songs + your own loops as “golden references”. 
Track expected region counts, approximate positions, and some high-level metrics. 
End-to-End Smoke Test 
Script: load reference → analyze → load user loops → arrange → export → validate exported lengths. 
 
3.2 Config & Experimentation 
Central config.yaml: 
Motif sensitivity defaults. 
Call-response time windows. 
Fill detection thresholds. 
Region prior profiles (e.g., “Pop Song”, “EDM Banger”). 
Ability to override configs via CLI or .env. 
 
3.3 Performance 
Profile Milestone 1 / 2 pipelines on typical track. 
Optimize: 
Use downsampled audio for analysis (e.g., mono 22.05 kHz) while keeping original for export slicing. 
Cache intermediate features (novelty curves, envelopes, embeddings). 
 
4. Backlog & Future Architecture Hooks 
 
You already have a good backlog in the PRD. From an architecture POV, ensure: 
Bars/Beats model 
Introduce a TimeGrid abstraction early (even if Milestone 1 uses seconds internally). 
Then moving to bar-based arrangement (per backlog) is a refactor inside TimeGrid, not everywhere.   
Spectral mismatch warnings 
Keep per-region spectral summaries for both reference and user arrangement to support these later. 
Reference vs User toggle 
Design timeline components so they can render either reference or user arrangement data with the same structure. 
Separation model integration 
Wrap future Demucs/Spleeter integration behind a SeparationService interface; don’t hardwire it into ingest. 
 