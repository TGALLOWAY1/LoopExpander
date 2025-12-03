/**
 * Visual Composer page for manual annotation of regions.
 * 
 * ANNOTATION MODEL AUDIT (P2-01):
 * 
 * TypeScript Types (from frontend/src/api/reference.ts):
 * - ReferenceAnnotations: { referenceId: string; regions: RegionAnnotations[]; }
 * - RegionAnnotations: { regionId: string; lanes: AnnotationLane[]; regionNotes?: string | null; }
 * - AnnotationLane: { stemCategory: StemCategory; blocks: AnnotationBlock[]; }
 * - AnnotationBlock: { id: string; startBar: number; endBar: number; label?: string | null; }
 * 
 * Backend Pydantic Models (from backend/src/models/annotations.py):
 * - ReferenceAnnotations: { reference_id: str; regions: List[RegionAnnotations] }
 * - RegionAnnotations: { region_id: str; lanes: List[AnnotationLane] }  [NOTE: NO regionNotes field!]
 * - AnnotationLane: { stem_category: str; blocks: List[AnnotationBlock] }
 * - AnnotationBlock: { id: str; start_bar: float; end_bar: float; label: Optional[str] }
 * 
 * Key Differences:
 * 1. Naming: Backend uses snake_case (reference_id, region_id, start_bar, end_bar, stem_category)
 *            Frontend uses camelCase (referenceId, regionId, startBar, endBar, stemCategory)
 * 2. Missing Field: Backend RegionAnnotations lacks 'regionNotes' field that frontend expects
 * 3. Type: Backend uses float for bars, frontend uses number (compatible but noted)
 * 
 * Data Flow:
 * - Loading: getAnnotations() fetches from GET /api/reference/{id}/annotations
 *            Backend returns snake_case via model_dump() (no aliases configured)
 *            Frontend expects camelCase - POTENTIAL MISMATCH
 * - Storage: Stored in ProjectContext.annotations (ReferenceAnnotations | null)
 * - Local State: VisualComposerPage maps to localRegionAnnotations (RegionAnnotations)
 *            via useEffect that finds existing RegionAnnotations by regionId
 * - Saving: saveAnnotations() sends POST /api/reference/{id}/annotations
 *            Frontend sends camelCase, backend expects snake_case - POTENTIAL MISMATCH
 * 
 * See docs/visual-composer-notes.md for full audit details.
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import { useProject } from '../context/ProjectContext';
import { 
  ReferenceAnnotations, 
  RegionAnnotations, 
  AnnotationLane, 
  AnnotationBlock,
  saveAnnotations
} from '../api/reference';
import './VisualComposerPage.css';

interface VisualComposerPageProps {
  onBack: () => void;
}

function VisualComposerPage({ onBack }: VisualComposerPageProps): JSX.Element {
  const { 
    referenceId, 
    regions,
    annotations,
    setAnnotations
  } = useProject();

  const [currentRegionIndex, setCurrentRegionIndex] = useState(0);
  const currentRegion = regions?.[currentRegionIndex];
  const regionId = currentRegion?.id;

  // Local state for current region's annotations
  const [localRegionAnnotations, setLocalRegionAnnotations] = useState<RegionAnnotations>({
    regionId: regionId || '',
    lanes: [],
    blocks: [],
    notes: '',
  });

  const [collapsedLanes, setCollapsedLanes] = useState<Set<string>>(new Set());
  const [editingLaneId, setEditingLaneId] = useState<string | null>(null);
  const [laneName, setLaneName] = useState<string>('');
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragLaneId, setDragLaneId] = useState<string | null>(null);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Color palette for lanes (rotates through these colors)
  const LANE_COLORS = [
    '#FF6B6B', // Red
    '#4ECDC4', // Teal
    '#FFE66D', // Yellow
    '#95E1D3', // Mint
    '#F38181', // Coral
    '#AA96DA', // Purple
    '#FCBAD3', // Pink
    '#A8E6CF', // Green
  ];

  // Helper to generate unique lane IDs
  const createLaneId = useCallback(() => {
    return `lane_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Update global annotations when local region annotations change
  const updateGlobalAnnotations = useCallback((updatedRegion: RegionAnnotations) => {
    if (!annotations) return;

    const others = annotations.regions.filter(r => r.regionId !== updatedRegion.regionId);
    const next = { ...annotations, regions: [...others, updatedRegion] };
    setAnnotations(next);
  }, [annotations, setAnnotations]);

  // Track if we're syncing from global to avoid circular updates
  const isSyncingFromGlobalRef = useRef(false);

  // Find or create RegionAnnotations when regionId or annotations change
  useEffect(() => {
    if (!regionId) {
      const emptyRegionAnnotations: RegionAnnotations = {
        regionId: '',
        lanes: [],
        blocks: [],
        notes: '',
      };
      isSyncingFromGlobalRef.current = true;
      setLocalRegionAnnotations(emptyRegionAnnotations);
      isSyncingFromGlobalRef.current = false;
      return;
    }

    // Find existing RegionAnnotations for current region
    const existingRegionAnnotations = annotations?.regions.find(
      r => r.regionId === regionId
    );

    if (existingRegionAnnotations) {
      isSyncingFromGlobalRef.current = true;
      setLocalRegionAnnotations(existingRegionAnnotations);
      isSyncingFromGlobalRef.current = false;
    } else {
      // Create empty RegionAnnotations
      const emptyRegionAnnotations: RegionAnnotations = {
        regionId,
        lanes: [],
        blocks: [],
        notes: '',
      };
      isSyncingFromGlobalRef.current = true;
      setLocalRegionAnnotations(emptyRegionAnnotations);
      isSyncingFromGlobalRef.current = false;
      // Also add to global annotations
      if (annotations) {
        updateGlobalAnnotations(emptyRegionAnnotations);
      }
    }
  }, [regionId, annotations, updateGlobalAnnotations]);

  // Update global annotations whenever localRegionAnnotations changes (but not when syncing from global)
  useEffect(() => {
    if (localRegionAnnotations.regionId && !isSyncingFromGlobalRef.current) {
      updateGlobalAnnotations(localRegionAnnotations);
    }
  }, [localRegionAnnotations, updateGlobalAnnotations]);

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

  // Save annotations when they change
  useEffect(() => {
    if (annotations && referenceId) {
      debouncedSave(annotations);
    }
  }, [annotations, referenceId, debouncedSave]);

  // ============================================================================
  // Lane CRUD Helper Functions
  // ============================================================================

  /**
   * Adds a new lane to localRegionAnnotations.
   * Creates a lane with generated ID, default name, rotating color, and proper order.
   * Automatically syncs to global annotations via useEffect.
   */
  const addLane = useCallback(() => {
    if (!localRegionAnnotations || !regionId) return;

    const lanes = localRegionAnnotations.lanes || [];
    const maxOrder = lanes.length > 0 
      ? Math.max(...lanes.map(l => l.order ?? 0))
      : -1;
    const nextOrder = maxOrder + 1;
    
    // Rotate through color palette
    const colorIndex = lanes.length % LANE_COLORS.length;
    const color = LANE_COLORS[colorIndex];
    
    const newLane: AnnotationLane = {
      id: createLaneId(),
      name: `Lane ${lanes.length + 1}`,
      color,
      collapsed: false,
      order: nextOrder,
    };

    setLocalRegionAnnotations(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        lanes: [...(prev.lanes || []), newLane],
      };
    });
  }, [localRegionAnnotations, regionId, createLaneId]);

  /**
   * Updates a lane by ID with a partial patch of properties.
   * Finds the lane and applies the patch, then syncs to global annotations via useEffect.
   */
  const updateLane = useCallback((id: string, patch: Partial<AnnotationLane>) => {
    if (!localRegionAnnotations || !id) return;

    setLocalRegionAnnotations(prev => {
      if (!prev || !prev.lanes) return prev;
      
      return {
        ...prev,
        lanes: prev.lanes.map(lane => 
          lane.id === id ? { ...lane, ...patch } : lane
        ),
      };
    });
  }, [localRegionAnnotations]);

  /**
   * Deletes a lane by ID and optionally removes all blocks that reference it.
   * Syncs to global annotations via useEffect.
   */
  const deleteLane = useCallback((id: string) => {
    if (!localRegionAnnotations || !id) return;

    setLocalRegionAnnotations(prev => {
      if (!prev || !prev.lanes) return prev;
      
      // Remove the lane
      const updatedLanes = prev.lanes.filter(lane => lane.id !== id);
      
      // Optionally remove blocks that reference this lane
      const updatedBlocks = prev.blocks?.filter(block => block.laneId !== id) || [];
      
      return {
        ...prev,
        lanes: updatedLanes,
        blocks: updatedBlocks,
      };
    });
  }, [localRegionAnnotations]);

  /**
   * Reorders lanes based on an ordered list of lane IDs.
   * Updates each lane's order property to match the new position.
   * Syncs to global annotations via useEffect.
   */
  const reorderLanes = useCallback((orderedIds: string[]) => {
    if (!localRegionAnnotations || !orderedIds || orderedIds.length === 0) return;

    setLocalRegionAnnotations(prev => {
      if (!prev || !prev.lanes) return prev;
      
      // Create a map of lane by ID for quick lookup
      const laneMap = new Map(prev.lanes.map(lane => [lane.id, lane]));
      
      // Reorder lanes based on orderedIds and update their order values
      const reorderedLanes = orderedIds
        .map((id, index) => {
          const lane = laneMap.get(id);
          if (!lane) return null;
          return { ...lane, order: index };
        })
        .filter((lane): lane is AnnotationLane => lane !== null);
      
      // Keep any lanes that weren't in orderedIds (shouldn't happen, but safe)
      const existingIds = new Set(orderedIds);
      const remainingLanes = prev.lanes
        .filter(lane => !existingIds.has(lane.id))
        .map((lane, index) => ({ ...lane, order: reorderedLanes.length + index }));
      
      return {
        ...prev,
        lanes: [...reorderedLanes, ...remainingLanes],
      };
    });
  }, [localRegionAnnotations]);

  // ============================================================================
  // Legacy Handlers (to be replaced with helpers above in future UI updates)
  // ============================================================================

  // Add a new lane
  const handleAddLane = () => {
    addLane();
  };

  // Toggle lane collapse
  const toggleLaneCollapse = (laneIndex: number) => {
    const key = `${regionId}_${laneIndex}`;
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
    const lane = localRegionAnnotations.lanes[laneIndex];
    if (lane) {
      setEditingLaneId(`${regionId}_${laneIndex}`);
      setLaneName(lane.name);
    }
  };

  // Save lane name edit
  const saveLaneEdit = () => {
    if (!editingLaneId || !regionId) return;

    const [, laneIndexStr] = editingLaneId.split('_');
    const laneIndex = parseInt(laneIndexStr, 10);
    const name = laneName.trim();

    if (!name) {
      alert('Lane name cannot be empty');
      return;
    }

    setLocalRegionAnnotations(prev => ({
      ...prev,
      lanes: prev.lanes.map((lane, idx) =>
        idx === laneIndex ? { ...lane, name } : lane
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
    setDragLaneId(`${regionId}_${laneIndex}`);
  };

  const handleBarGridMouseMove = (_bar: number) => {
    if (!isDragging || dragStart === null || !dragLaneId) return;

    // Create or update block (will be finalized on mouse up)
    // For now, we'll just track the drag
  };

  const handleBarGridMouseUp = (finalBar?: number) => {
    if (isDragging && dragStart !== null && dragLaneId && finalBar !== undefined) {
      const [, laneIndexStr] = dragLaneId.split('_');
      const laneIndex = parseInt(laneIndexStr, 10);
      const startBar = Math.min(dragStart, finalBar);
      const endBar = Math.max(dragStart, finalBar) + 1; // Make end exclusive

      // Don't create blocks with zero or negative length
      if (endBar > startBar) {
        const lane = localRegionAnnotations.lanes[laneIndex];
        if (lane) {
          // Check if block overlaps with existing blocks in this lane
          const laneBlocks = localRegionAnnotations.blocks.filter(b => b.laneId === lane.id);
          const overlaps = laneBlocks.some(
            (b: AnnotationBlock) => (startBar < b.endBar && endBar > b.startBar)
          );

          if (!overlaps) {
            // Create new block at region level
            const newBlock: AnnotationBlock = {
              id: `block_${Date.now()}`,
              laneId: lane.id,
              startBar,
              endBar,
              type: 'custom',
              label: null,
            };

            setLocalRegionAnnotations(prev => ({
              ...prev,
              blocks: [...prev.blocks, newBlock],
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
  const handleDeleteBlock = (blockId: string) => {
    if (!regionId) return;

    setLocalRegionAnnotations(prev => ({
      ...prev,
      blocks: prev.blocks.filter(b => b.id !== blockId),
    }));
  };

  // Update region notes
  const handleRegionNotesChange = (notes: string) => {
    if (!regionId) return;

    setLocalRegionAnnotations(prev => ({
      ...prev,
      notes: notes,
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

  const totalBars = getRegionBars();
  const regionKey = `${regionId}_${currentRegionIndex}`;

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
            {localRegionAnnotations.lanes.map((lane, laneIndex) => {
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
                          {lane.name}
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
                            const laneBlocks = localRegionAnnotations.blocks.filter(b => b.laneId === lane.id);
                            const block = laneBlocks.find(
                              (b: AnnotationBlock) => bar >= b.startBar && bar < b.endBar
                            );
                            const isStart = laneBlocks.some((b: AnnotationBlock) => b.startBar === bar);
                            const isEnd = laneBlocks.some((b: AnnotationBlock) => b.endBar === bar);

                            return (
                              <div
                                key={bar}
                                className={`bar-cell ${block ? 'has-block' : ''} ${isStart ? 'block-start' : ''} ${isEnd ? 'block-end' : ''}`}
                                onMouseDown={() => handleBarGridMouseDown(laneIndex, bar)}
                                onMouseMove={() => {
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
                        {localRegionAnnotations.blocks
                          .filter((b: AnnotationBlock) => b.laneId === lane.id)
                          .map((block: AnnotationBlock) => (
                            <div key={block.id} className="block-item">
                              <span>
                                Bar {block.startBar} - {block.endBar}
                                {block.label && `: ${block.label}`}
                              </span>
                              <button
                                className="delete-button"
                                onClick={() => handleDeleteBlock(block.id)}
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
            value={localRegionAnnotations.notes || ''}
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

