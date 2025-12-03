/**
 * Visual Composer page for manual annotation of regions.
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import { useProject } from '../context/ProjectContext';
import { 
  ReferenceAnnotations, 
  RegionAnnotations, 
  AnnotationLane, 
  AnnotationBlock,
  StemCategory,
  getAnnotations,
  saveAnnotations
} from '../api/reference';
import './VisualComposerPage.css';

interface VisualComposerPageProps {
  onBack: () => void;
}

const STEM_CATEGORIES: StemCategory[] = ['drums', 'bass', 'vocals', 'instruments'];

function VisualComposerPage({ onBack }: VisualComposerPageProps): JSX.Element {
  const { 
    referenceId, 
    regions,
    annotations,
    setAnnotations
  } = useProject();

  const [currentRegionIndex, setCurrentRegionIndex] = useState(0);
  const [localAnnotations, setLocalAnnotations] = useState<ReferenceAnnotations | null>(null);
  const [collapsedLanes, setCollapsedLanes] = useState<Set<string>>(new Set());
  const [editingLaneId, setEditingLaneId] = useState<string | null>(null);
  const [laneName, setLaneName] = useState<string>('');
  const [regionNotes, setRegionNotes] = useState<string>('');
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragLaneId, setDragLaneId] = useState<string | null>(null);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Load annotations on mount
  useEffect(() => {
    if (!referenceId) return;

    const loadAnnotations = async () => {
      try {
        const data = await getAnnotations(referenceId);
        setLocalAnnotations(data);
        setAnnotations(data);
      } catch (err) {
        console.error('Error loading annotations:', err);
        // Initialize with empty structure
        const empty: ReferenceAnnotations = {
          referenceId,
          regions: [],
        };
        setLocalAnnotations(empty);
        setAnnotations(empty);
      }
    };

    loadAnnotations();
  }, [referenceId, setAnnotations]);

  // Sync region notes when region changes
  useEffect(() => {
    if (!localAnnotations || regions.length === 0) return;
    
    const currentRegion = regions[currentRegionIndex];
    if (!currentRegion) return;

    const regionAnnotation = localAnnotations.regions.find(
      r => r.regionId === currentRegion.id
    );
    
    setRegionNotes(regionAnnotation?.regionNotes || '');
  }, [currentRegionIndex, localAnnotations, regions]);

  // Debounced save function
  const debouncedSave = useCallback((data: ReferenceAnnotations) => {
    if (!referenceId) return;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(async () => {
      try {
        await saveAnnotations(referenceId, data);
        setAnnotations(data);
      } catch (err) {
        console.error('Error saving annotations:', err);
      }
    }, 1000); // 1 second debounce
  }, [referenceId, setAnnotations]);

  // Update local annotations and trigger save
  const updateLocalAnnotations = useCallback((updater: (prev: ReferenceAnnotations) => ReferenceAnnotations) => {
    setLocalAnnotations(prev => {
      if (!prev || !referenceId) return prev;
      const updated = updater(prev);
      debouncedSave(updated);
      return updated;
    });
  }, [referenceId, debouncedSave]);

  // Get or create region annotations for current region
  const getCurrentRegionAnnotations = (): RegionAnnotations => {
    if (!localAnnotations || regions.length === 0) {
      return { regionId: '', lanes: [] };
    }

    const currentRegion = regions[currentRegionIndex];
    if (!currentRegion) {
      return { regionId: '', lanes: [] };
    }

    let regionAnnotation = localAnnotations.regions.find(
      r => r.regionId === currentRegion.id
    );

    if (!regionAnnotation) {
      regionAnnotation = {
        regionId: currentRegion.id,
        lanes: [],
        regionNotes: null,
      };
      // Add to local annotations
      updateLocalAnnotations(prev => ({
        ...prev,
        regions: [...prev.regions, regionAnnotation!],
      }));
    }

    return regionAnnotation;
  };

  // Add a new lane
  const handleAddLane = () => {
    if (!localAnnotations || !referenceId || regions.length === 0) return;

    const currentRegion = regions[currentRegionIndex];
    if (!currentRegion) return;

    const regionAnnotation = getCurrentRegionAnnotations();
    const newLaneId = `lane_${Date.now()}`;
    const newLane: AnnotationLane = {
      stemCategory: 'drums', // Default
      blocks: [],
    };

    updateLocalAnnotations(prev => ({
      ...prev,
      regions: prev.regions.map(r =>
        r.regionId === currentRegion.id
          ? { ...r, lanes: [...r.lanes, newLane] }
          : r
      ),
    }));
  };

  // Toggle lane collapse
  const toggleLaneCollapse = (laneIndex: number) => {
    const key = `${regions[currentRegionIndex]?.id}_${laneIndex}`;
    setCollapsedLanes(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  // Start editing lane name
  const startEditingLane = (laneIndex: number) => {
    const regionAnnotation = getCurrentRegionAnnotations();
    const lane = regionAnnotation.lanes[laneIndex];
    if (lane) {
      setEditingLaneId(`${regions[currentRegionIndex]?.id}_${laneIndex}`);
      setLaneName(lane.stemCategory);
    }
  };

  // Save lane name edit
  const saveLaneEdit = () => {
    if (!editingLaneId || !localAnnotations || regions.length === 0) return;

    const [regionId, laneIndexStr] = editingLaneId.split('_');
    const laneIndex = parseInt(laneIndexStr, 10);
    const stemCategory = laneName.trim() as StemCategory;

    if (!STEM_CATEGORIES.includes(stemCategory)) {
      alert('Invalid stem category. Must be one of: drums, bass, vocals, instruments');
      return;
    }

    updateLocalAnnotations(prev => ({
      ...prev,
      regions: prev.regions.map(r =>
        r.regionId === regionId
          ? {
              ...r,
              lanes: r.lanes.map((lane, idx) =>
                idx === laneIndex ? { ...lane, stemCategory } : lane
              ),
            }
          : r
      ),
    }));

    setEditingLaneId(null);
    setLaneName('');
  };

  // Calculate bars for current region (simplified: assume 4/4 time, use duration)
  const getRegionBars = (): number => {
    const currentRegion = regions[currentRegionIndex];
    if (!currentRegion) return 0;
    // Rough estimate: 1 bar = 2 seconds at 120 BPM
    // For more accuracy, we'd need BPM from the bundle
    return Math.ceil(currentRegion.duration / 2);
  };

  // Handle bar grid click/drag
  const handleBarGridMouseDown = (laneIndex: number, bar: number) => {
    setIsDragging(true);
    setDragStart(bar);
    setDragLaneId(`${regions[currentRegionIndex]?.id}_${laneIndex}`);
  };

  const handleBarGridMouseMove = (bar: number) => {
    if (!isDragging || dragStart === null || !dragLaneId) return;

    const [regionId, laneIndexStr] = dragLaneId.split('_');
    const laneIndex = parseInt(laneIndexStr, 10);
    const startBar = Math.min(dragStart, bar);
    const endBar = Math.max(dragStart, bar) + 1; // Make end exclusive

    // Don't create blocks with zero or negative length
    if (endBar <= startBar) return;

    // Create or update block (will be finalized on mouse up)
    // For now, we'll just track the drag
  };

  const handleBarGridMouseUp = (finalBar?: number) => {
    if (isDragging && dragStart !== null && dragLaneId && finalBar !== undefined) {
      const [regionId, laneIndexStr] = dragLaneId.split('_');
      const laneIndex = parseInt(laneIndexStr, 10);
      const startBar = Math.min(dragStart, finalBar);
      const endBar = Math.max(dragStart, finalBar) + 1; // Make end exclusive

      // Don't create blocks with zero or negative length
      if (endBar > startBar) {
        const regionAnnotation = getCurrentRegionAnnotations();
        const lane = regionAnnotation.lanes[laneIndex];
        if (lane) {
          // Check if block overlaps with existing blocks
          const overlaps = lane.blocks.some(
            b => (startBar < b.endBar && endBar > b.startBar)
          );

          if (!overlaps) {
            // Create new block
            const newBlock: AnnotationBlock = {
              id: `block_${Date.now()}`,
              startBar,
              endBar,
              label: null,
            };

            updateLocalAnnotations(prev => ({
              ...prev,
              regions: prev.regions.map(r =>
                r.regionId === regionId
                  ? {
                      ...r,
                      lanes: r.lanes.map((l, idx) =>
                        idx === laneIndex
                          ? { ...l, blocks: [...l.blocks, newBlock] }
                          : l
                      ),
                    }
                  : r
              ),
            }));
          }
        }
      }
    }

    setIsDragging(false);
    setDragStart(null);
    setDragLaneId(null);
  };

  // Delete block
  const handleDeleteBlock = (laneIndex: number, blockId: string) => {
    if (!localAnnotations || regions.length === 0) return;

    const currentRegion = regions[currentRegionIndex];
    if (!currentRegion) return;

    updateLocalAnnotations(prev => ({
      ...prev,
      regions: prev.regions.map(r =>
        r.regionId === currentRegion.id
          ? {
              ...r,
              lanes: r.lanes.map((lane, idx) =>
                idx === laneIndex
                  ? {
                      ...lane,
                      blocks: lane.blocks.filter(b => b.id !== blockId),
                    }
                  : lane
              ),
            }
          : r
      ),
    }));
  };

  // Update region notes
  const handleRegionNotesChange = (notes: string) => {
    setRegionNotes(notes);
    
    if (!localAnnotations || regions.length === 0) return;
    const currentRegion = regions[currentRegionIndex];
    if (!currentRegion) return;

    updateLocalAnnotations(prev => ({
      ...prev,
      regions: prev.regions.map(r =>
        r.regionId === currentRegion.id
          ? { ...r, regionNotes: notes }
          : r
      ),
    }));
  };

  // Navigation
  const handlePrevRegion = () => {
    if (currentRegionIndex > 0) {
      setCurrentRegionIndex(currentRegionIndex - 1);
    }
  };

  const handleNextRegion = () => {
    if (currentRegionIndex < regions.length - 1) {
      setCurrentRegionIndex(currentRegionIndex + 1);
    }
  };

  // Validation
  if (!referenceId || regions.length === 0) {
    return (
      <div className="visual-composer-page">
        <div className="visual-composer-empty">
          <h2>No Reference Loaded</h2>
          <p>Please load a reference track and analyze it before using Visual Composer.</p>
          <button className="back-button" onClick={onBack}>
            Back to Region Map
          </button>
        </div>
      </div>
    );
  }

  const currentRegion = regions[currentRegionIndex];
  const regionAnnotation = getCurrentRegionAnnotations();
  const totalBars = getRegionBars();
  const regionKey = `${currentRegion.id}_${currentRegionIndex}`;

  return (
    <div className="visual-composer-page">
      <div className="visual-composer-header">
        <button className="back-button" onClick={onBack}>
          ← Back to Region Map
        </button>
        <div className="region-navigation">
          <button
            className="nav-button"
            onClick={handlePrevRegion}
            disabled={currentRegionIndex === 0}
          >
            ← Prev
          </button>
          <div className="region-info">
            <h2>{currentRegion.name}</h2>
            <span className="region-type">{currentRegion.type}</span>
            <span className="region-index">
              Region {currentRegionIndex + 1} of {regions.length}
            </span>
          </div>
          <button
            className="nav-button"
            onClick={handleNextRegion}
            disabled={currentRegionIndex === regions.length - 1}
          >
            Next →
          </button>
        </div>
      </div>

      <div className="visual-composer-content">
        <div className="lanes-section">
          <div className="lanes-header">
            <h3>Annotation Lanes</h3>
            <button className="add-lane-button" onClick={handleAddLane}>
              + Add Lane
            </button>
          </div>

          <div className="lanes-list">
            {regionAnnotation.lanes.map((lane, laneIndex) => {
              const laneKey = `${regionKey}_${laneIndex}`;
              const isCollapsed = collapsedLanes.has(laneKey);
              const isEditing = editingLaneId === laneKey;

              return (
                <div key={laneIndex} className="lane-item">
                  <div className="lane-header">
                    {isEditing ? (
                      <div className="lane-edit">
                        <input
                          type="text"
                          value={laneName}
                          onChange={(e) => setLaneName(e.target.value)}
                          onBlur={saveLaneEdit}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              saveLaneEdit();
                            } else if (e.key === 'Escape') {
                              setEditingLaneId(null);
                              setLaneName('');
                            }
                          }}
                          autoFocus
                        />
                      </div>
                    ) : (
                      <div className="lane-title">
                        <span onClick={() => startEditingLane(laneIndex)}>
                          {lane.stemCategory}
                        </span>
                        <button
                          className="collapse-button"
                          onClick={() => toggleLaneCollapse(laneIndex)}
                        >
                          {isCollapsed ? '▼' : '▲'}
                        </button>
                      </div>
                    )}
                  </div>

                  {!isCollapsed && (
                    <div className="lane-content">
                      <div className="bar-grid-container">
                        <div className="bar-grid">
                          {Array.from({ length: totalBars }, (_, i) => {
                            const bar = i;
                            const block = lane.blocks.find(
                              b => bar >= b.startBar && bar < b.endBar
                            );
                            const isStart = lane.blocks.some(b => b.startBar === bar);
                            const isEnd = lane.blocks.some(b => b.endBar === bar);

                            return (
                              <div
                                key={bar}
                                className={`bar-cell ${block ? 'has-block' : ''} ${isStart ? 'block-start' : ''} ${isEnd ? 'block-end' : ''}`}
                                onMouseDown={() => handleBarGridMouseDown(laneIndex, bar)}
                                onMouseMove={(e) => {
                                  if (isDragging) {
                                    handleBarGridMouseMove(bar);
                                  }
                                }}
                                onMouseUp={() => handleBarGridMouseUp(bar)}
                                onMouseLeave={() => {
                                  if (isDragging) {
                                    handleBarGridMouseUp(bar);
                                  }
                                }}
                              >
                                {bar % 4 === 0 && <span className="bar-label">{bar}</span>}
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      <div className="blocks-list">
                        {lane.blocks.map((block) => (
                          <div key={block.id} className="block-item">
                            <span>
                              Bar {block.startBar} - {block.endBar}
                              {block.label && `: ${block.label}`}
                            </span>
                            <button
                              className="delete-button"
                              onClick={() => handleDeleteBlock(laneIndex, block.id)}
                            >
                              ×
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="region-notes-section">
          <h3>Region Notes</h3>
          <textarea
            className="region-notes-input"
            value={regionNotes}
            onChange={(e) => handleRegionNotesChange(e.target.value)}
            placeholder="Add notes about this region..."
            rows={6}
          />
        </div>
      </div>
    </div>
  );
}

export default VisualComposerPage;

