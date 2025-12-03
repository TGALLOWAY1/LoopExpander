# **Product Requirements Document (PRD)**

## **Feature: Visual Composer (Manual Per-Region Annotation Tool)**

### Version: 1.0

### Status: Draft

### Related Document: *Song Structure Replicator PRD v1.1* (Not modified)

---

# **1. Feature Overview**

**Visual Composer** is a new page/feature that enables users to manually analyze a song—region by region—using a fast, block-based visual system for identifying motifs, call-and-response relationships, variations, and sound characteristics.

The tool is **manual-first** and **region-focused**. It is intended for:

* Users analyzing a new song (reference track)
* Users who prefer human-guided structural annotation
* Producers learning arrangement, motif development, and sound identity
* Future ML training from user-generated annotation data

This feature is **fully independent** of the existing automatic analysis pipeline. Automatic analysis remains available on a separate page labeled “In Development,” but the Visual Composer provides a workflow where users build arrangements and motif maps manually.

---

# **2. Goals & Non-Goals**

## **2.1 Goals**

* Provide a **quick and intuitive manual annotation workspace** for analyzing song regions.
* Allow users to add **colored blocks** to represent motifs, calls, responses, variations, fills, or sound events across time.
* Support **user-created lanes** for labeling recurring sounds or musical ideas.
* Support **per-block notes** to capture qualitative sound details (“grit,” “formant sweep,” etc.).
* Allow users to **audition audio slices** of blocks within regions.
* Enable **region-by-region navigation** (carousel) for incremental deep-dive analysis.
* Capture all annotations as structured data for **future ML training**.

## **2.2 Non-Goals**

* Does not modify audio, time-stretch, or synthesize new audio.
* Does not replace the existing automatic analysis pipeline.
* Does not attempt to export full arrangements from manual annotations.
* Does not attempt to detect or generate motifs automatically in this feature.

---

# **3. User Stories**

### **Primary User: Producer / Music Creator**

**As a producer**,
I want to analyze one song region at a time and visually map out motifs, calls, responses, and variations
**so I can better understand and learn from the structure of professional tracks.**

### **Secondary User: Sound Designer or Mix Engineer**

**As a sound designer**,
I want to create labeled lanes for specific sound identities and annotate characteristics
**so I can identify recurring sound signatures across a drop or build.**

### **Future User: ML Pipeline**

**As the system**,
I want to store annotated blocks, variations, and motifs in structured form
**so the automatic region, motif, and call-response models can learn from user preferences.**

---

# **4. User Workflow Summary**

1. User imports a **full mix** or **stems** for a reference song.
2. User navigates to **Visual Composer**.
3. The interface loads **Region 1** (e.g., Intro) and displays audio + empty lanes.
4. User creates lanes for different sound identities.
5. User drags colored blocks into timelines under lanes to mark events.
6. User adjusts duration, color shade (variation), notes, and labels.
7. User can audition any block by clicking it.
8. User moves to the next region (carousel navigation).
9. System saves all data per region and per block.
10. Export is available as **annotation JSON** for ML/further processing.

---

# **5. Functional Requirements**

## **5.1 Region Navigation**

* Provide **carousel navigation**:

  * Next Region →
  * ← Previous Region
* Display region name, start bar, end bar, and duration.
* Allow basic region rename.
* Only **one region** is visible at a time.

---

## **5.2 Audio Playback**

* Playback modes:

  * Full mix
  * Drums stem
  * Bass stem
  * Vocals stem
  * Instruments stem
* User can loop playback within the region.
* Clicking a block plays that section of audio:

  * If stems exist, isolate the appropriate stem.
  * If stems do not exist, play full mix slice.

---

## **5.3 Lanes (Sound Identity Tracks)**

Users can:

* Add new lanes
* Rename lanes
* Assign a lane color (base motif color)
* Collapse/expand lanes
* Drag lanes to reorder
* Solo lane (isolates the corresponding stem if available)
* Delete lane (with confirmation)

Lane data model:

```json
{
  "laneId": "lane_01",
  "name": "Growl Bass",
  "color": "#FF4A4A",
  "collapsed": false,
  "order": 1
}
```

---

## **5.4 Blocks (Events / Motifs / Calls / Responses)**

Users can:

* Drag blocks onto lanes
* Stretch or shrink blocks in bar increments
* Set block variation (lighter/darker version of lane color)
* Add notes (plain text)
* Label block as:

  * Call
  * Response
  * Variation
  * Fill
  * Custom label

Block data model:

```json
{
  "blockId": "block_01",
  "laneId": "lane_01",
  "startBar": 17,
  "endBar": 19,
  "color": "#FF7A7A",
  "type": "response",
  "notes": "formant sweep / gritty tail"
}
```

---

## **5.5 Block Audio Audition**

* Clicking a block must:

  * Move playhead
  * Loop audio within block boundaries
  * Solo stem if available
* Hotkeys:

  * **Space:** play/pause
  * **Shift+Click:** audition block instantly

---

## **5.6 Annotations**

Per-block notes:

* Free-text, inline editor
* Persistent on save
* Displayed as icon on block

Per-region notes:

* Text box at top of region
* Saved with region data

---

## **5.7 Data Persistence**

The system must store:

### Per project:

* Project ID
* File references (mix or stems)

### Per region:

* Lanes
* Blocks
* Notes

Data must persist:

* Automatically on edit
* Across sessions
* In structured JSON format

---

## **5.8 Integration with Automatic Analysis (Later)**

* Visual Composer must **not depend** on automatic analysis.
* The existing automatic analysis page remains unchanged.
* Visual Composer data must be usable to improve:

  * motif clustering sensitivity
  * repetition detection
  * fill classification
  * call-response relationships

This will be added in a future ML milestone.

---

# **6. UX/UI Requirements**

## **6.1 Layout Structure**

### Top Section

* Region name / type
* Audio mode selector (Mix, Drums, Bass, etc.)
* Mini playback waveform
* Play, pause, loop, audition controls

### Middle Section

* Timeline ruler (bars)
* Lanes (expandable/collapsible)
* Colored blocks placed on lanes
* Blocks snap to bar grid

### Bottom Section

* Navigation: Previous Region / Next Region
* Export annotations (JSON)
* “Add Lane” CTA

---

## **6.2 Design Principles**

* **Speed-first:** Users must be able to annotate regions rapidly.
* **Visual clarity:** Blocks must communicate identity, variation, and role.
* **Region isolation:** No multi-region distractions.
* **Low cognitive load:** Similar to “clip launching” or “pattern drafting” metaphors.

---

# **7. Technical Requirements**

## **7.1 Frontend**

* Built within existing React + TypeScript architecture.
* New page route: `/visual-composer/:projectId/:regionIndex`
* Components:

  * RegionHeader
  * ComposerTimeline
  * Lane
  * Block
  * AudioPlayer (shared)
  * RegionNavigation
  * NotesPanel

---

## **7.2 Backend**

Minimal backend needs for v1:

### GET /project/:id/regions

Return region metadata (bars, timecodes).

### GET /project/:id/annotations

Return stored lanes and blocks for all regions.

### POST /project/:id/annotations

Save updated annotation mapping.

### Audio slicing endpoint

Only if CPU-segment auditioning is needed (optional; can be client-side with Web Audio API).

---

# **8. Data Model Overview**

Top-level project annotation:

```json
{
  "projectId": "p123",
  "regions": [
    {
      "regionId": "r1",
      "name": "Drop 1",
      "lanes": [...],
      "blocks": [...],
      "notes": "Very dense main growl + wobble response"
    }
  ]
}
```

---

# **9. Success Metrics**

### Qualitative:

* Users can annotate a region within 2–8 minutes.
* Users report that the tool helps them understand the structure of a drop or build.

### Quantitative:

* 80% of lane/block operations under 100ms update time.
* 90% of audio audition triggers within 200ms latency.
* 70% of users annotate at least 2 regions per project (stickiness).

---

# **10. Future Enhancements (Not in Scope for v1)**

* Auto-suggest blocks based on detected motifs.
* Show algorithm predictions side-by-side with user blocks.
* Auto-create lanes from stem spectral clusters.
* Export visual composer layout as PDF/PNG.
* Integrate the annotations directly into the arrangement generator.
* “Compare Regions” mode.
* Machine-learning feedback loop (RLHF).

---

# **11. Release Plan**

### **Milestone VC-1: Core Composer**

* Region view
* Lanes
* Blocks
* Notes
* Audition

### **Milestone VC-2: Data Persistence**

* Full save/load
* Region carousel

### **Milestone VC-3: Stem-Aware Playback**

* Audition by stem
* Loop playback

### **Milestone VC-4: Export & ML Integration Prep**

* Export JSON
* Begin data schema for ML training


