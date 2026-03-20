/**
 * StructureCanvasPage - Full-song timeline view for structure analysis.
 *
 * Displays all sections simultaneously on a horizontal bar-based timeline,
 * with role activity lanes, energy overlay, and section editing tools.
 */
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useProject } from '../context/ProjectContext';
import {
  CanvasSection,
  StructureCanvasData,
  loadStructureCanvasData,
  patchRegions,
  splitRegion,
  mergeRegions,
} from '../api/structureCanvas';
import {
  RoleActivityTimeline,
  ActivitySegment,
  EnergyCurveResponse,
} from '../api/referenceMix';
import {
  InteractionLabel,
  InteractionLabelCreate,
  InteractionLabelType,
  INTERACTION_LABEL_TYPES,
  getInteractionLabels,
  createInteractionLabels,
  deleteInteractionLabel,
  updateInteractionLabel,
} from '../api/interactions';
import { SectionTimeline } from '../components/structureCanvas/SectionTimeline';
import { SectionEditor } from '../components/structureCanvas/SectionEditor';
import { EnergyOverlay } from '../components/structureCanvas/EnergyOverlay';
import { RoleActivityLanes } from '../components/structureCanvas/RoleActivityLanes';
import { ComposerWaveform } from '../components/visualComposer/ComposerWaveform';
import '../components/structureCanvas/StructureCanvas.css';
import './StructureCanvasPage.css';

interface StructureCanvasPageProps {
  onBack?: () => void;
  demoMode?: boolean;
}

const DEMO_SECTIONS: CanvasSection[] = [
  { id: 'demo-1', name: 'Intro', type: 'intro', label: 'Intro', provisionalLabel: 'Intro', start: 0, end: 14.77, duration: 14.77, startBar: 0, endBar: 8, color: '#4CAF50' },
  { id: 'demo-2', name: 'Verse 1', type: 'verse', label: 'Verse 1', provisionalLabel: 'Verse', start: 14.77, end: 44.31, duration: 29.54, startBar: 8, endBar: 24, color: '#2196F3' },
  { id: 'demo-3', name: 'Chorus 1', type: 'chorus', label: 'Chorus 1', provisionalLabel: 'Chorus', start: 44.31, end: 73.85, duration: 29.54, startBar: 24, endBar: 40, color: '#FF9800' },
  { id: 'demo-4', name: 'Verse 2', type: 'verse', label: 'Verse 2', provisionalLabel: 'Verse', start: 73.85, end: 103.38, duration: 29.54, startBar: 40, endBar: 56, color: '#2196F3' },
  { id: 'demo-5', name: 'Chorus 2', type: 'chorus', label: 'Chorus 2', provisionalLabel: 'Chorus', start: 103.38, end: 132.92, duration: 29.54, startBar: 56, endBar: 72, color: '#FF9800' },
  { id: 'demo-6', name: 'Bridge', type: 'bridge', label: 'Bridge', provisionalLabel: 'Bridge', start: 132.92, end: 147.69, duration: 14.77, startBar: 72, endBar: 80, color: '#9C27B0' },
  { id: 'demo-7', name: 'Drop', type: 'drop', label: 'Drop', provisionalLabel: 'Drop', start: 147.69, end: 177.23, duration: 29.54, startBar: 80, endBar: 96, color: '#F44336' },
  { id: 'demo-8', name: 'Outro', type: 'outro', label: 'Outro', provisionalLabel: 'Outro', start: 177.23, end: 206.77, duration: 29.54, startBar: 96, endBar: 112, color: '#795548' },
];

const DEMO_ROLE_TIMELINES: RoleActivityTimeline[] = [
  { role: 'drums', segments: [
    { startBar: 0, endBar: 8, active: false, confidence: 0.2 },
    { startBar: 8, endBar: 72, active: true, confidence: 0.85 },
    { startBar: 72, endBar: 80, active: false, confidence: 0.3 },
    { startBar: 80, endBar: 96, active: true, confidence: 0.95 },
    { startBar: 96, endBar: 112, active: false, confidence: 0.15 },
  ]},
  { role: 'bass', segments: [
    { startBar: 0, endBar: 8, active: false, confidence: 0.1 },
    { startBar: 8, endBar: 24, active: true, confidence: 0.7 },
    { startBar: 24, endBar: 72, active: true, confidence: 0.9 },
    { startBar: 72, endBar: 80, active: false, confidence: 0.2 },
    { startBar: 80, endBar: 96, active: true, confidence: 0.95 },
    { startBar: 96, endBar: 112, active: false, confidence: 0.1 },
  ]},
  { role: 'melodic', segments: [
    { startBar: 0, endBar: 8, active: true, confidence: 0.5 },
    { startBar: 8, endBar: 40, active: true, confidence: 0.8 },
    { startBar: 40, endBar: 56, active: true, confidence: 0.75 },
    { startBar: 56, endBar: 80, active: true, confidence: 0.85 },
    { startBar: 80, endBar: 96, active: true, confidence: 0.9 },
    { startBar: 96, endBar: 112, active: true, confidence: 0.4 },
  ]},
  { role: 'vocal', segments: [
    { startBar: 0, endBar: 8, active: false, confidence: 0.1 },
    { startBar: 8, endBar: 24, active: true, confidence: 0.8 },
    { startBar: 24, endBar: 40, active: true, confidence: 0.85 },
    { startBar: 40, endBar: 56, active: true, confidence: 0.75 },
    { startBar: 56, endBar: 72, active: true, confidence: 0.8 },
    { startBar: 72, endBar: 80, active: false, confidence: 0.15 },
    { startBar: 80, endBar: 96, active: false, confidence: 0.1 },
    { startBar: 96, endBar: 112, active: false, confidence: 0.2 },
  ]},
];

// Helper to generate demo energy values per section
function demoEnergy(length: number, ranges: Array<[number, number, number, number]>) {
  return Array.from({ length }, (_, i) => {
    for (const [start, end, base, variance] of ranges) {
      if (i >= start && i < end) return base + Math.random() * variance;
    }
    return 0.1;
  });
}

const DEMO_ENERGY: EnergyCurveResponse = {
  referenceId: 'demo',
  barEnergies: demoEnergy(112, [
    [0, 8, 0.2, 0.1], [8, 24, 0.4, 0.15], [24, 40, 0.7, 0.15],
    [40, 56, 0.45, 0.1], [56, 72, 0.75, 0.1], [72, 80, 0.25, 0.1],
    [80, 96, 0.85, 0.1], [96, 112, 0.15, 0.1],
  ]),
  sectionDensities: [],
  transitionMarkers: [
    { bar: 8, timeSeconds: 14.77, energyDelta: 0.3, type: 'lift' },
    { bar: 24, timeSeconds: 44.31, energyDelta: 0.35, type: 'lift' },
    { bar: 40, timeSeconds: 73.85, energyDelta: -0.25, type: 'drop' },
    { bar: 72, timeSeconds: 132.92, energyDelta: -0.4, type: 'breakdown' },
    { bar: 80, timeSeconds: 147.69, energyDelta: 0.6, type: 'lift' },
    { bar: 96, timeSeconds: 177.23, energyDelta: -0.7, type: 'drop' },
  ],
  multiCurves: {
    lufs: demoEnergy(112, [
      [0, 8, 0.2, 0.1], [8, 24, 0.4, 0.15], [24, 40, 0.7, 0.15],
      [40, 56, 0.45, 0.1], [56, 72, 0.75, 0.1], [72, 80, 0.25, 0.1],
      [80, 96, 0.85, 0.1], [96, 112, 0.15, 0.1],
    ]),
    spectralCentroid: demoEnergy(112, [
      [0, 8, 0.3, 0.1], [8, 24, 0.5, 0.1], [24, 40, 0.65, 0.15],
      [40, 56, 0.45, 0.1], [56, 72, 0.7, 0.1], [72, 80, 0.35, 0.1],
      [80, 96, 0.8, 0.15], [96, 112, 0.2, 0.1],
    ]),
    bassEnergy: demoEnergy(112, [
      [0, 8, 0.1, 0.05], [8, 24, 0.35, 0.1], [24, 40, 0.6, 0.15],
      [40, 56, 0.3, 0.1], [56, 72, 0.65, 0.1], [72, 80, 0.15, 0.05],
      [80, 96, 0.9, 0.1], [96, 112, 0.1, 0.05],
    ]),
    transientDensity: demoEnergy(112, [
      [0, 8, 0.15, 0.1], [8, 24, 0.55, 0.15], [24, 40, 0.7, 0.1],
      [40, 56, 0.5, 0.1], [56, 72, 0.65, 0.1], [72, 80, 0.2, 0.1],
      [80, 96, 0.85, 0.1], [96, 112, 0.1, 0.05],
    ]),
  },
};

const BASE_BAR_WIDTH = 24;

type ViewMode = 'song' | 'section';

const StructureCanvasPage: React.FC<StructureCanvasPageProps> = ({
  onBack,
  demoMode = false,
}) => {
  const { referenceId } = useProject();
  const [sections, setSections] = useState<CanvasSection[]>([]);
  const [roleTimelines, setRoleTimelines] = useState<RoleActivityTimeline[]>([]);
  const [energyCurve, setEnergyCurve] = useState<EnergyCurveResponse | null>(null);
  const [totalBars, setTotalBars] = useState(0);
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [interactionLabels, setInteractionLabels] = useState<InteractionLabel[]>([]);
  const [activeLabelType, setActiveLabelType] = useState<InteractionLabelType>('call');
  const scrollRef = useRef<HTMLDivElement>(null);

  // View mode state: song overview vs section detail
  const [viewMode, setViewMode] = useState<ViewMode>('song');
  const [focusedSectionId, setFocusedSectionId] = useState<string | null>(null);



  const [containerWidth, setContainerWidth] = useState(1000);
  useEffect(() => {
    const updateWidth = () => {
      if (scrollRef.current) {
        setContainerWidth(scrollRef.current.clientWidth);
      }
    };
    // use setTimeout to ensure ref is mounted and layout is complete before measuring
    const timer = setTimeout(updateWidth, 50);
    window.addEventListener('resize', updateWidth);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', updateWidth);
    };
  }, []);

  // Compute section-filtered data for Section View
  const focusedSection = sections.find((s) => s.id === focusedSectionId) ?? null;

  const barWidth = React.useMemo(() => {
    if (viewMode === 'song' || !focusedSection) return BASE_BAR_WIDTH;
    const sectionBars = focusedSection.endBar - focusedSection.startBar;
    if (sectionBars <= 0) return BASE_BAR_WIDTH;
    // Aim to fit the section into 80% of the container width to leave context around it
    return Math.max(BASE_BAR_WIDTH, Math.floor((containerWidth * 0.8) / sectionBars));
  }, [viewMode, focusedSection, containerWidth]);

  // Handle auto-scrolling when focusing a section
  useEffect(() => {
    if (viewMode === 'section' && focusedSection && scrollRef.current) {
      // Put the start of the section 10% from the left edge
      const targetScroll = (focusedSection.startBar * barWidth) - (containerWidth * 0.1);
      scrollRef.current.scrollTo({ left: Math.max(0, targetScroll), behavior: 'smooth' });
    }
  }, [viewMode, focusedSectionId, barWidth, containerWidth]);

  // Handle clicking a section in Song View to enter Section View
  const handleSectionClick = useCallback((sectionId: string | null) => {
    if (!sectionId) return;
    if (viewMode === 'song') {
      setFocusedSectionId(sectionId);
      setSelectedSectionId(sectionId);
      setViewMode('section');
    } else {
      setSelectedSectionId(sectionId);
    }
  }, [viewMode]);

  // Return to Song View
  const handleBackToSongView = useCallback(() => {
    setViewMode('song');
    setFocusedSectionId(null);
    setSelectedSectionId(null);
  }, []);


  // Load data from API or use demo data
  useEffect(() => {
    if (demoMode || !referenceId) {
      setSections(DEMO_SECTIONS);
      setRoleTimelines(DEMO_ROLE_TIMELINES);
      setEnergyCurve(DEMO_ENERGY);
      setTotalBars(112);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      loadStructureCanvasData(referenceId),
      getInteractionLabels(referenceId).catch(() => ({ labels: [] })),
    ])
      .then(([data, labelsData]) => {
        if (cancelled) return;
        setSections((data as StructureCanvasData).sections);
        setRoleTimelines((data as StructureCanvasData).roleTimelines);
        setEnergyCurve((data as StructureCanvasData).energyCurve);
        setTotalBars((data as StructureCanvasData).totalBars);
        setInteractionLabels(labelsData.labels);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [referenceId, demoMode]);

  const selectedSection = sections.find((s) => s.id === selectedSectionId) ?? null;

  const handleSectionUpdate = useCallback(
    async (sectionId: string, patch: Partial<CanvasSection>) => {
      // Optimistic local update
      setSections((prev) =>
        prev.map((s) => (s.id === sectionId ? { ...s, ...patch } : s)),
      );

      if (!demoMode && referenceId) {
        try {
          await patchRegions(referenceId, [
            {
              id: sectionId,
              name: patch.name ?? patch.label,
              label: patch.label,
              type: patch.type,
              startBar: patch.startBar,
              endBar: patch.endBar,
            },
          ]);
        } catch (err) {
          console.error('Failed to save section update:', err);
        }
      }
    },
    [demoMode, referenceId],
  );

  const handleSplit = useCallback(
    async (sectionId: string, splitBar: number) => {
      if (demoMode) {
        // Demo mode: locally split
        setSections((prev) => {
          const section = prev.find((s) => s.id === sectionId);
          if (!section || splitBar <= section.startBar || splitBar >= section.endBar) return prev;
          const bpm = 130;
          const secPerBar = (60 / bpm) * 4;
          const splitTime = splitBar * secPerBar;
          const first: CanvasSection = {
            ...section,
            id: `${section.id}-a`,
            endBar: splitBar,
            end: splitTime,
            duration: splitTime - section.start,
            name: `${section.name} (A)`,
            label: `${section.label} (A)`,
          };
          const second: CanvasSection = {
            ...section,
            id: `${section.id}-b`,
            startBar: splitBar,
            start: splitTime,
            duration: section.end - splitTime,
            name: `${section.name} (B)`,
            label: `${section.label} (B)`,
          };
          return prev.flatMap((s) => (s.id === sectionId ? [first, second] : [s]));
        });
        setSelectedSectionId(null);
        return;
      }

      if (!referenceId) return;
      try {
        await splitRegion(referenceId, sectionId, splitBar);
        // Reload full data after structural change
        const data = await loadStructureCanvasData(referenceId);
        setSections(data.sections);
        setTotalBars(data.totalBars);
        setSelectedSectionId(null);
      } catch (err) {
        console.error('Failed to split section:', err);
      }
    },
    [demoMode, referenceId],
  );

  const handleMerge = useCallback(
    async (sectionId: string) => {
      const idx = sections.findIndex((s) => s.id === sectionId);
      if (idx < 0 || idx >= sections.length - 1) return;
      const nextSection = sections[idx + 1];

      if (demoMode) {
        setSections((prev) => {
          const current = prev[idx];
          const next = prev[idx + 1];
          if (!current || !next) return prev;
          const merged: CanvasSection = {
            ...current,
            endBar: next.endBar,
            end: next.end,
            duration: next.end - current.start,
          };
          return [...prev.slice(0, idx), merged, ...prev.slice(idx + 2)];
        });
        setSelectedSectionId(null);
        return;
      }

      if (!referenceId) return;
      try {
        await mergeRegions(referenceId, sectionId, nextSection.id);
        const data = await loadStructureCanvasData(referenceId);
        setSections(data.sections);
        setTotalBars(data.totalBars);
        setSelectedSectionId(null);
      } catch (err) {
        console.error('Failed to merge sections:', err);
      }
    },
    [setSections, demoMode, referenceId, sections],
  );

  const handleCreateLabel = useCallback(
    async (labelData: InteractionLabelCreate) => {
      // Optimistic update
      const tempId = `temp-${Date.now()}`;
      setInteractionLabels((prev) => [
        ...prev,
        {
          id: tempId,
          sectionId: labelData.sectionId,
          startBar: labelData.startBar,
          endBar: labelData.endBar,
          label: labelData.label,
          role: labelData.role,
          color: labelData.color || null,
          notes: labelData.notes || null,
        },
      ]);

      if (!demoMode && referenceId) {
        try {
          await createInteractionLabels(referenceId, [labelData]);
          // Re-fetch all to ensure sync
          const newData = await getInteractionLabels(referenceId);
          setInteractionLabels(newData.labels);
        } catch (err) {
          console.error('Failed to create label:', err);
          // Rollback
          setInteractionLabels((prev) => prev.filter((l) => l.id !== tempId));
        }
      }
    },
    [demoMode, referenceId]
  );

  const handleUpdateLabel = useCallback(
    async (labelId: string, updates: Partial<InteractionLabel>) => {
      // Optimistic upate
      setInteractionLabels((prev) =>
        prev.map((l) => (l.id === labelId ? { ...l, ...updates } : l))
      );
      if (!demoMode && referenceId && !labelId.startsWith('temp-')) {
        try {
          await updateInteractionLabel(referenceId, labelId, updates);
        } catch (err) {
          console.error('Failed to update label:', err);
        }
      }
    },
    [demoMode, referenceId]
  );

  const handleDeleteLabel = useCallback(
    async (labelId: string) => {
      setInteractionLabels((prev) => prev.filter((l) => l.id !== labelId));
      if (!demoMode && referenceId && !labelId.startsWith('temp-')) {
        try {
          await deleteInteractionLabel(referenceId, labelId);
        } catch (err) {
          console.error('Failed to delete label:', err);
        }
      }
    },
    [demoMode, referenceId]
  );

  const handleRoleSegmentUpdate = useCallback(
    (role: string, index: number, patch: Partial<ActivitySegment>) => {
      setRoleTimelines((prev) =>
        prev.map((timeline) => {
          if (timeline.role !== role) return timeline;
          const newSegments = [...timeline.segments];
          newSegments[index] = { ...newSegments[index], ...patch };
          return { ...timeline, segments: newSegments };
        }),
      );
    },
    [],
  );

  const handleRoleSegmentSplit = useCallback(
    (role: string, index: number, splitBar: number) => {
      setRoleTimelines((prev) =>
        prev.map((timeline) => {
          if (timeline.role !== role) return timeline;
          const newSegments = [...timeline.segments];
          const segToSplit = newSegments[index];
          if (splitBar <= segToSplit.startBar || splitBar >= segToSplit.endBar) return timeline;
          
          const leftSeg = { ...segToSplit, endBar: splitBar };
          const rightSeg = { ...segToSplit, startBar: splitBar };
          newSegments.splice(index, 1, leftSeg, rightSeg);
          
          return { ...timeline, segments: newSegments };
        }),
      );
    },
    [],
  );

  if (loading) {
    return (
      <div className="structure-canvas-page">
        <div className="sc-loading">Loading structure analysis...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="structure-canvas-page">
        <div className="sc-error">
          <h3>Error loading structure data</h3>
          <p>{error}</p>
          {onBack && (
            <button className="sc-editor-btn" onClick={onBack}>
              Go Back
            </button>
          )}
        </div>
      </div>
    );
  }

  const filteredTimelines = useMemo(() => {
    if (!focusedSection) return [];
    return roleTimelines.map(timeline => ({
      ...timeline,
      segments: timeline.segments.filter(
        s => s.startBar < focusedSection.endBar && s.endBar > focusedSection.startBar
      ).map(s => ({
        ...s,
        startBar: Math.max(s.startBar, focusedSection.startBar),
        endBar: Math.min(s.endBar, focusedSection.endBar),
      }))
    }));
  }, [roleTimelines, focusedSection]);

  return (
    <div className="structure-canvas-page">
      <div className="sc-header">
        <div className="sc-header-left">
          {onBack && (
            <button className="sc-editor-btn" onClick={onBack}>
              Back
            </button>
          )}
          <h2>Structure Canvas</h2>
          {demoMode && <span className="sc-demo-badge">Demo</span>}
          <div className="sc-view-mode-toggle">
            <button
              className={`sc-view-mode-btn ${viewMode === 'song' ? 'active' : ''}`}
              onClick={handleBackToSongView}
            >
              Song View
            </button>
            <button
              className={`sc-view-mode-btn ${viewMode === 'section' ? 'active' : ''}`}
              onClick={() => {
                if (sections.length > 0 && !focusedSectionId) {
                  setFocusedSectionId(sections[0].id);
                  setSelectedSectionId(sections[0].id);
                }
                setViewMode('section');
              }}
            >
              Section View
            </button>
          </div>
        </div>
        <div className="sc-header-right">
          {viewMode === 'section' && focusedSection && (
            <span className="sc-focused-section-badge" style={{ background: focusedSection.color }}>
              {focusedSection.label}
            </span>
          )}
          <span className="sc-meta">
            {sections.length} sections &middot; {totalBars} bars
          </span>
        </div>
      </div>

      <div className={`sc-content-layout ${viewMode === 'song' ? 'sc-song-view' : 'sc-section-view'}`}>
        <div className="sc-timeline-panel" ref={scrollRef}>
          {/* Section timeline — always visible */}
          <SectionTimeline
            sections={sections}
            totalBars={totalBars}
            barWidth={barWidth}
            selectedSectionId={viewMode === 'song' ? focusedSectionId : selectedSectionId}
            onSelectSection={handleSectionClick}
          />

          {/* Actual Audio Waveform Component placed between segments and energy */}
          <ComposerWaveform
            audioUrl="/demo.wav"
            pixelsPerBar={barWidth}
            totalBars={totalBars}
            height={64}
            bpm={130}
          />

          {/* Energy overlay — always visible */}
          {energyCurve && (
            <EnergyOverlay
              energyCurve={energyCurve}
              totalBars={totalBars}
              barWidth={barWidth}
            />
          )}

          {/* Section View: detailed layers (role lanes, interactions) */}
          {viewMode === 'section' && (
            <div className="sc-module" style={{ flexShrink: 0, paddingLeft: 0, paddingRight: 0 }}>
              <div style={{ padding: '0 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 className="sc-module-title" style={{ margin: 0 }}>Role Activity & Interactions</h3>
                <div className="sc-interaction-type-selector" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: '#666', marginRight: '4px' }}>Active Label:</span>
                  {INTERACTION_LABEL_TYPES.map((type) => (
                    <button
                      key={type}
                      className={`sc-label-type-btn ${activeLabelType === type ? 'active' : ''}`}
                      style={{
                        padding: '4px 8px',
                        fontSize: '0.75rem',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        border: '1px solid',
                        borderColor: activeLabelType === type ? '#1976d2' : '#ddd',
                        background: activeLabelType === type ? '#1976d2' : '#fff',
                        color: activeLabelType === type ? '#fff' : '#555',
                        boxShadow: activeLabelType === type ? '0 2px 4px rgba(0,0,0,0.1)' : 'none'
                      }}
                      onClick={() => setActiveLabelType(type as InteractionLabelType)}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>
              <RoleActivityLanes
                timelines={filteredTimelines}
                totalBars={totalBars}
                barWidth={barWidth}
                onUpdateSegment={handleRoleSegmentUpdate}
                interactionLabels={interactionLabels}
                activeLabelType={activeLabelType}
                onCreateLabel={handleCreateLabel}
                onUpdateLabel={handleUpdateLabel}
                onDeleteLabel={handleDeleteLabel}
              />
            </div>
          )}

          {/* Song View: hint to click a section */}
          {viewMode === 'song' && (
            <div className="sc-song-view-hint">
              Click a section to view details
            </div>
          )}
        </div>

        {/* Section editor sidebar — only in section view */}
        {viewMode === 'section' && (
          <div className="sc-sidebar">
            {selectedSection ? (
              <SectionEditor
                section={selectedSection}
                sections={sections}
                onUpdate={handleSectionUpdate}
                onSplit={handleSplit}
                onMerge={handleMerge}
                onDeselect={() => setSelectedSectionId(null)}
              />
            ) : (
              <div className="sc-sidebar-empty">
                <p>Click a section on the timeline to edit it.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default StructureCanvasPage;
