# LoopExpander - Human QA Checklist

Use this checklist for manual QA testing before each release. Test in Chrome, Firefox, and Safari where applicable. Mark each item with `[x]` when verified.

---

## 1. Application Startup

- [ ] `run.sh` launches both backend (port 8000) and frontend (port 5173) without errors
- [ ] Frontend loads in the browser and displays the header with project title
- [ ] Tab navigation bar renders all tabs: Ingest, Region Map, Structure Canvas, Loop Material, Arrangement
- [ ] Visual Composer tab appears when `VISUAL_COMPOSER_ENABLED=true`
- [ ] Visual Composer tab is hidden when the feature flag is off
- [ ] Backend health endpoint responds (FastAPI docs at `/docs`)
- [ ] CORS allows requests from frontend origin (localhost:5173 and localhost:3000)

---

## 2. Reference Ingestion (Ingest Page)

### Single Full-Mix Upload
- [ ] File picker accepts WAV, MP3, FLAC, AIFF formats
- [ ] Upload progress/status message appears while uploading
- [ ] BPM is auto-detected and displayed after analysis
- [ ] Optional BPM override field accepts numeric input and overrides detection
- [ ] Duration validation rejects files that are too short
- [ ] Status transitions correctly: idle -> uploading -> analyzing -> complete
- [ ] Error message displays for invalid/corrupt files
- [ ] Uploading a new file replaces the previous reference

### Stems Upload
- [ ] Five file inputs render: Drums, Bass, Vocals, Instruments, Full Mix
- [ ] All five stems can be selected and uploaded together
- [ ] Analysis runs on the stem bundle after upload
- [ ] Partial uploads (missing stems) show appropriate error/warning

---

## 3. Region Map Page

- [ ] Regions list populates after reference analysis
- [ ] Each region displays label, start/end time, and type
- [ ] Region rename saves and persists on page refresh
- [ ] Region retype (e.g., Verse -> Chorus) updates the label correctly
- [ ] Region split creates two regions at the chosen boundary
- [ ] Region merge combines adjacent regions into one
- [ ] Region delete removes the region from the list
- [ ] Motif groups display per region with cluster visualization
- [ ] Motif sensitivity slider adjusts clustering granularity in real time
- [ ] Call-response lane shows detected pairs with offset markers
- [ ] Subregion analysis shows silence and intensity markers
- [ ] Scrolling/navigation works for tracks with many regions

---

## 4. Structure Canvas Page

### Timeline
- [ ] Timeline header renders bar markers (0, 10, 20, 30, ...)
- [ ] Section blocks render as color-coded rectangles
- [ ] Section colors are distinct for each type (Intro, Verse, Chorus, Bridge, Drop, Outro)
- [ ] Sections span correct proportional widths based on duration
- [ ] Horizontal scrolling works for long tracks
- [ ] Demo mode renders hardcoded data when backend is unavailable

### Energy Overlay
- [ ] Loudness (LUFS) curve renders in blue
- [ ] Brightness (spectral centroid) curve renders in orange
- [ ] Bass energy curve renders in red
- [ ] Transient rate/density curve renders in green
- [ ] Curves align correctly with the section timeline
- [ ] Transition markers appear at region boundaries
- [ ] Legend/labels identify each curve

### Role Activity Lanes
- [ ] Four lanes render: Drums, Bass, Melodic, Vocal
- [ ] On/off segments display correctly per lane per region
- [ ] Lane widths align with the timeline above

### Section Editor (Right Panel)
- [ ] Clicking a section highlights it and opens the editor
- [ ] Rename field updates the section label
- [ ] Retype dropdown offers all valid section types
- [ ] Edit and delete buttons function correctly
- [ ] Changes persist after navigating away and returning

---

## 5. Loop Material Page (User Loop Ingestion)

- [ ] Multi-file upload area accepts drag-and-drop
- [ ] Multi-file upload area accepts click-to-browse
- [ ] Uploaded stems appear in a list with file names
- [ ] Role selector dropdown offers all roles: drums, bass, chord, lead, vocal, fx, percussion, texture
- [ ] Changing a role assignment saves immediately
- [ ] BPM is auto-detected per stem and displayed
- [ ] Manual BPM override field works per stem
- [ ] BPM mismatch warning appears when stem BPM differs from reference
- [ ] Stem bounds adjustment handles are draggable
- [ ] Delete button removes a stem from the list
- [ ] Uploading additional stems appends (does not replace)
- [ ] Supported formats (WAV, MP3, FLAC, AIFF) are accepted
- [ ] Unsupported formats show an error message

---

## 6. Arrangement Page

### Arrangement Generation
- [ ] "Generate Arrangement" maps user loops onto reference structure
- [ ] Timeline view renders section headers with labels and boundaries
- [ ] Color-coded lanes render per role (drums=red, bass=blue, chord=green, lead=orange, vocal=purple, fx=cyan, percussion=pink, texture=gray)
- [ ] Blocks appear in the correct lanes and sections
- [ ] Empty lanes (no assigned loops) render but show no blocks

### Block Interaction
- [ ] Clicking a block selects it and shows the toolbar
- [ ] Mute button toggles block mute state (visual dimming)
- [ ] Delete button removes the block from the arrangement
- [ ] Blocks are draggable to new positions within the lane
- [ ] Blocks are resizable via drag handles
- [ ] Undo is possible after destructive actions (delete, move)

### Variation Suggestions Panel
- [ ] Suggestions auto-generate and appear in the right panel
- [ ] "Mute on repetition" suggestion applies correctly
- [ ] "Pre-impact dropout" suggestion applies correctly
- [ ] "A/B alternation" suggestion applies correctly
- [ ] Apply button modifies the arrangement as described
- [ ] Dismiss button removes the suggestion from the panel

### Genre Presets
- [ ] Preset selector dropdown lists all presets: Future Bass, Dubstep, Trap, Pop, House
- [ ] Selecting a preset modifies the arrangement mapping rules
- [ ] Preset changes are reflected in the timeline immediately

### Guidance Overlay
- [ ] Guide markers render at appropriate positions
- [ ] Call-response highlights appear when detected pairs exist
- [ ] Guidance overlay can be toggled on/off

---

## 7. Audition Player

- [ ] Play button starts audio playback of the arrangement
- [ ] Stop button halts playback immediately
- [ ] Loop toggle enables continuous section playback
- [ ] Section selector dropdown lists all sections
- [ ] Selecting a section jumps playback to that section
- [ ] Solo per role plays only the selected role
- [ ] Mute per role silences only the selected role
- [ ] Multiple roles can be muted simultaneously
- [ ] Playback position indicator moves along the timeline
- [ ] Audio stops cleanly when navigating away from the page

---

## 8. Export Module

### Format Options
- [ ] WAV 16-bit option is selectable
- [ ] WAV 24-bit option is selectable
- [ ] AIFF option is selectable
- [ ] Default format is pre-selected

### Content Selection
- [ ] "Per-role stems" checkbox includes/excludes stem WAVs
- [ ] "MIDI markers" checkbox includes/excludes MIDI marker file
- [ ] "Structure JSON" checkbox includes/excludes JSON structure file
- [ ] "CSV markers" checkbox includes/excludes CSV marker file
- [ ] At least one content type must be selected to enable export

### Export Execution
- [ ] Export button triggers download
- [ ] Downloaded file is a valid ZIP archive
- [ ] ZIP contains the selected content types only
- [ ] Per-role stem files are correctly named by role
- [ ] Stem audio files are in the selected format and bit depth
- [ ] MIDI markers file contains correct section boundaries
- [ ] Structure JSON matches the arrangement state
- [ ] CSV markers file is well-formed with headers and correct data
- [ ] Export works for arrangements with many sections (10+)
- [ ] Export works when only one content type is selected

---

## 9. Visual Composer (Feature-Flagged)

### Region Navigation
- [ ] Region carousel shows current region label
- [ ] Previous/Next buttons navigate between regions
- [ ] Navigation wraps or disables at boundaries

### Lane Management
- [ ] "Add Lane" button creates a new lane
- [ ] Lane list renders all created lanes
- [ ] Lanes are collapsible
- [ ] Lanes are reorderable via drag
- [ ] Lane deletion removes the lane and its blocks

### Block Drawing
- [ ] Clicking and dragging on a lane creates a colored block
- [ ] Blocks snap to bar grid
- [ ] Block color matches the lane color
- [ ] Blocks can be resized after creation
- [ ] Blocks can be deleted via right-click context menu or toolbar
- [ ] Multiple blocks can exist per lane without overlap

### Audio Player
- [ ] Stem selector offers: Mix, Drums, Bass, Vocals, Instruments
- [ ] Selecting a stem plays that audio source
- [ ] Playback aligns with the block timeline

### Notes Panel
- [ ] Text area accepts free-form notes per region
- [ ] Notes persist when navigating between regions
- [ ] Notes persist after page refresh

### Annotation Persistence
- [ ] Annotations save to backend via API
- [ ] Reloading the page restores all lanes, blocks, and notes
- [ ] Switching regions and returning preserves annotations

---

## 10. Cross-Cutting Concerns

### State Management
- [ ] ProjectContext maintains state across tab navigation
- [ ] Navigating between tabs does not lose in-progress work
- [ ] Reference ID displays correctly in the header after ingestion
- [ ] Region count updates in the header after analysis

### Error Handling
- [ ] Network errors show user-friendly messages (not raw stack traces)
- [ ] Backend 500 errors display a meaningful error in the UI
- [ ] File upload failures show specific error reasons
- [ ] Timeout on long analysis shows appropriate feedback

### Performance
- [ ] Reference analysis completes within reasonable time for a 5-minute track
- [ ] Structure Canvas renders smoothly for tracks with 20+ regions
- [ ] Arrangement page handles 8 roles x 15 sections without UI lag
- [ ] Export completes without timeout for typical arrangements
- [ ] No memory leaks when repeatedly uploading new references

### Browser Compatibility
- [ ] All pages render correctly in Chrome (latest)
- [ ] All pages render correctly in Firefox (latest)
- [ ] All pages render correctly in Safari (latest)
- [ ] No console errors in any browser during normal workflows

### Accessibility
- [ ] All buttons and inputs have visible labels or aria-labels
- [ ] Tab key navigation follows a logical order on each page
- [ ] Color-coded elements have non-color differentiation (text labels, patterns)
- [ ] Status messages are announced to screen readers

---

## 11. End-to-End Workflow Tests

### Workflow A: Full Pipeline
- [ ] Upload a reference full-mix (WAV, ~3-5 minutes)
- [ ] Verify BPM detection and region segmentation
- [ ] Review Structure Canvas: sections, energy, role activity all render
- [ ] Upload 3+ loop stems and assign roles
- [ ] Generate arrangement and verify blocks appear correctly
- [ ] Apply at least one variation suggestion
- [ ] Audition one section with solo/mute
- [ ] Export ZIP with all content types and verify contents

### Workflow B: Stems-Based Analysis
- [ ] Upload 4 separated stems + full mix
- [ ] Verify region detection matches single-mix approach
- [ ] Navigate Region Map and inspect motifs
- [ ] Check call-response detection across stems
- [ ] Proceed to arrangement and export

### Workflow C: Iterative Editing
- [ ] Generate an arrangement
- [ ] Mute 3 blocks, delete 2 blocks, resize 1 block
- [ ] Verify changes persist after navigating away and returning
- [ ] Export and verify muted blocks are excluded from stems
- [ ] Re-generate arrangement and verify it resets cleanly

### Workflow D: Visual Composer Standalone
- [ ] Enable Visual Composer feature flag
- [ ] Upload a reference and navigate to Visual Composer
- [ ] Create 3 lanes with different names
- [ ] Draw blocks across multiple lanes
- [ ] Add notes for 2 regions
- [ ] Navigate between regions and verify persistence
- [ ] Refresh the page and verify all data is restored

---

## Sign-Off

| Role | Name | Date | Pass/Fail |
|------|------|------|-----------|
| QA Tester | | | |
| Developer | | | |
| Product Owner | | | |

**Notes / Blockers:**

---
