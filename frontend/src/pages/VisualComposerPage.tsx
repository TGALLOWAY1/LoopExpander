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
import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useProject } from '../context/ProjectContext';
import { 
  RegionAnnotations, 
  AnnotationLane, 
  AnnotationBlock,
} from '../api/reference';
import {
  type VcAnnotations,
  type VcRegionAnnotations,
  type VcLane,
  type VcBlock,
} from '../api/visualComposerApi';
import { useVisualComposerAnnotations } from '../hooks/useVisualComposerAnnotations';
import { LaneList } from '../components/visualComposer/LaneList';
import { ComposerTimeline } from '../components/visualComposer/ComposerTimeline';
import { NotesPanel } from '../components/visualComposer/NotesPanel';
import './VisualComposerPage.css';

interface VisualComposerPageProps {
  onBack: () => void;
}

// Helper functions to convert between Vc types and Annotation types (for component compatibility)
function vcLaneToAnnotationLane(vcLane: VcLane): AnnotationLane {
  return {
    id: vcLane.id,
    name: vcLane.name,
    color: vcLane.color || undefined,
    collapsed: vcLane.collapsed,
    order: vcLane.order,
  };
}

function annotationLaneToVcLane(annotationLane: AnnotationLane): VcLane {
  return {
    id: annotationLane.id,
    name: annotationLane.name,
    color: annotationLane.color || null,
    collapsed: annotationLane.collapsed,
    order: annotationLane.order,
  };
}

function vcBlockToAnnotationBlock(vcBlock: VcBlock): AnnotationBlock {
  return {
    id: vcBlock.id,
    laneId: vcBlock.laneId,
    startBar: vcBlock.startBar,
    endBar: vcBlock.endBar,
    color: vcBlock.color || undefined,
    type: vcBlock.type,
    label: null, // VcBlock doesn't have label, use null
    notes: vcBlock.notes || undefined,
  };
}

function annotationBlockToVcBlock(annotationBlock: AnnotationBlock): VcBlock {
  return {
    id: annotationBlock.id,
    laneId: annotationBlock.laneId,
    startBar: annotationBlock.startBar,
    endBar: annotationBlock.endBar,
    color: annotationBlock.color || null,
    type: annotationBlock.type,
    notes: annotationBlock.notes || null,
  };
}

function vcRegionToRegionAnnotations(vcRegion: VcRegionAnnotations): RegionAnnotations {
  return {
    regionId: vcRegion.regionId,
    name: vcRegion.regionName || undefined,
    notes: vcRegion.notes || undefined,
    lanes: vcRegion.lanes.map(vcLaneToAnnotationLane),
    blocks: vcRegion.blocks.map(vcBlockToAnnotationBlock),
  };
}

function regionAnnotationsToVcRegion(
  regionAnnotations: RegionAnnotations,
  region?: { id: string; name: string; type: string; start: number; end: number } | null
): VcRegionAnnotations {
  // Calculate bars from region time if available (will need BPM, but for now use a default)
  // In a real implementation, we'd get BPM from the bundle, but for now we'll leave these as null
  // The backend will populate them when creating defaults
  const startBar = region ? null : null; // Will be populated by backend
  const endBar = region ? null : null; // Will be populated by backend
  
  return {
    regionId: regionAnnotations.regionId,
    regionName: region?.name || regionAnnotations.name || null,
    notes: regionAnnotations.notes || null,
    startBar: startBar,
    endBar: endBar,
    regionType: region?.type || null,
    displayOrder: null, // Will be set by backend based on region order
    lanes: regionAnnotations.lanes.map(annotationLaneToVcLane),
    blocks: regionAnnotations.blocks.map(annotationBlockToVcBlock),
  };
}

function VisualComposerPage({ onBack }: VisualComposerPageProps): JSX.Element {
  const { 
    referenceId, 
    regions,
  } = useProject();

  // Use the new Visual Composer annotations hook
  // Use referenceId as projectId (they're the same in this context)
  const {
    annotations: vcAnnotations,
    setAnnotations: setVcAnnotations,
    isLoading: isLoadingAnnotations,
    error: annotationsError,
    saveAnnotations: saveVcAnnotations,
    isSaving,
  } = useVisualComposerAnnotations(referenceId || null);

  const [currentRegionIndex, setCurrentRegionIndex] = useState(0);
  const currentRegion = regions?.[currentRegionIndex];
  const regionId = currentRegion?.id;

  // Save status for UI feedback
  const [saveStatus, setSaveStatus] = useState<{ type: 'success' | 'error' | null; message: string }>({
    type: null,
    message: '',
  });

  // Local state for current region's annotations (using Annotation types for component compatibility)
  const [localRegionAnnotations, setLocalRegionAnnotations] = useState<RegionAnnotations>({
    regionId: regionId || '',
    lanes: [],
    blocks: [],
    notes: '',
  });

  // Block selection state
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  
  // Audition state (for future audio playback)
  const [lastAuditionRequest, setLastAuditionRequest] = useState<{
    laneId: string;
    startBar: number;
    endBar: number;
  } | null>(null);

  // Legacy state (will be used for bar grid/block functionality in future prompts)
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragLaneId, setDragLaneId] = useState<string | null>(null);

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

  // Helper to generate unique block IDs
  const createBlockId = useCallback(() => {
    return `block_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Update Vc annotations when local region annotations change
  const updateVcAnnotations = useCallback((updatedRegion: RegionAnnotations) => {
    if (!vcAnnotations || !referenceId) return;

    const updatedVcRegion = regionAnnotationsToVcRegion(updatedRegion, currentRegion || null);
    const otherRegions = vcAnnotations.regions.filter(r => r.regionId !== updatedRegion.regionId);
    const next: VcAnnotations = {
      ...vcAnnotations,
      regions: [...otherRegions, updatedVcRegion],
    };
    setVcAnnotations(next);
  }, [vcAnnotations, setVcAnnotations, referenceId, currentRegion]);

  // Track if we're syncing from global to avoid circular updates
  const isSyncingFromGlobalRef = useRef(false);

  // Find or create RegionAnnotations when regionId or vcAnnotations change
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

    // Find existing VcRegionAnnotations for current region
    // The backend should have created defaults for all known regions, so this should always find one
    const existingVcRegion = vcAnnotations?.regions.find(
      r => r.regionId === regionId
    );

    if (existingVcRegion) {
      isSyncingFromGlobalRef.current = true;
      setLocalRegionAnnotations(vcRegionToRegionAnnotations(existingVcRegion));
      isSyncingFromGlobalRef.current = false;
    } else {
      // Create empty RegionAnnotations if not found (shouldn't happen if backend creates defaults)
      // This is a fallback for edge cases
      const emptyRegionAnnotations: RegionAnnotations = {
        regionId,
        lanes: [],
        blocks: [],
        notes: '',
      };
      isSyncingFromGlobalRef.current = true;
      setLocalRegionAnnotations(emptyRegionAnnotations);
      isSyncingFromGlobalRef.current = false;
      
      // Also ensure it's added to Vc annotations with region metadata
      if (vcAnnotations && currentRegion) {
        const newVcRegion = regionAnnotationsToVcRegion(emptyRegionAnnotations, currentRegion);
        setVcAnnotations({
          ...vcAnnotations,
          regions: [...vcAnnotations.regions, newVcRegion],
        });
      }
    }
  }, [regionId, vcAnnotations]);

  // Update Vc annotations whenever localRegionAnnotations changes (but not when syncing from global)
  useEffect(() => {
    if (localRegionAnnotations.regionId && !isSyncingFromGlobalRef.current && vcAnnotations) {
      updateVcAnnotations(localRegionAnnotations);
    }
  }, [localRegionAnnotations, updateVcAnnotations, vcAnnotations]);

  // Handle manual save button click
  const handleSave = useCallback(async () => {
    if (!vcAnnotations || !referenceId) return;

    try {
      await saveVcAnnotations();
      setSaveStatus({ type: 'success', message: 'Annotations saved successfully!' });
      setTimeout(() => setSaveStatus({ type: null, message: '' }), 3000);
    } catch (err) {
      console.error('Error saving annotations:', err);
      setSaveStatus({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to save annotations',
      });
      setTimeout(() => setSaveStatus({ type: null, message: '' }), 5000);
    }
  }, [vcAnnotations, referenceId, saveVcAnnotations]);

  // ============================================================================
  // Lane CRUD Helper Functions
  // ============================================================================

  /**
   * Adds a new lane to localRegionAnnotations.
   * Creates a lane with generated ID, default name, rotating color, and proper order.
   * Automatically syncs to Vc annotations via useEffect.
   * Also ensures the region exists in Vc annotations if it doesn't already.
   */
  const addLane = useCallback(() => {
    if (!localRegionAnnotations || !regionId || !referenceId) return;

    // Ensure region exists in Vc annotations (create on demand)
    if (!vcAnnotations) {
      const newVcAnnotations: VcAnnotations = {
        projectId: referenceId,
        regions: [regionAnnotationsToVcRegion(localRegionAnnotations, currentRegion || null)],
      };
      setVcAnnotations(newVcAnnotations);
    } else {
      const regionExists = vcAnnotations.regions.some(r => r.regionId === regionId);
      if (!regionExists) {
        const newRegion = regionAnnotationsToVcRegion(localRegionAnnotations, currentRegion || null);
        setVcAnnotations({
          ...vcAnnotations,
          regions: [...vcAnnotations.regions, newRegion],
        });
      }
    }

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
  }, [localRegionAnnotations, regionId, referenceId, vcAnnotations, setVcAnnotations, currentRegion, createLaneId]);

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
  // Block CRUD Helper Functions
  // ============================================================================

  /**
   * Adds a new block to localRegionAnnotations.
   * Generates a unique ID and adds the block to the blocks array.
   * Automatically syncs to global annotations via useEffect.
   */
  const addBlock = useCallback((partial: Omit<AnnotationBlock, 'id'>) => {
    if (!localRegionAnnotations || !regionId) return;

    const newBlock: AnnotationBlock = {
      id: createBlockId(),
      ...partial,
    };

    setLocalRegionAnnotations(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        blocks: [...(prev.blocks || []), newBlock],
      };
    });
  }, [localRegionAnnotations, regionId, createBlockId]);

  /**
   * Updates a block by ID with a partial patch of properties.
   * Finds the block and applies the patch, then syncs to global annotations via useEffect.
   */
  const updateBlock = useCallback((id: string, patch: Partial<AnnotationBlock>) => {
    if (!localRegionAnnotations || !id) return;

    setLocalRegionAnnotations(prev => {
      if (!prev || !prev.blocks) return prev;
      
      return {
        ...prev,
        blocks: prev.blocks.map(block => 
          block.id === id ? { ...block, ...patch } : block
        ),
      };
    });
  }, [localRegionAnnotations]);

  /**
   * Deletes a block by ID from localRegionAnnotations.
   * Removes the block from the blocks array and syncs to global annotations via useEffect.
   */
  const deleteBlock = useCallback((id: string) => {
    if (!localRegionAnnotations || !id) return;

    setLocalRegionAnnotations(prev => {
      if (!prev || !prev.blocks) return prev;
      
      return {
        ...prev,
        blocks: prev.blocks.filter(block => block.id !== id),
      };
    });
  }, [localRegionAnnotations]);

  // ============================================================================
  // Legacy Handlers (for bar grid/block functionality - to be used in future prompts)
  // ============================================================================

  // Calculate bars for current region (simplified: assume 4/4 time, use duration)
  const getRegionBars = (): number => {
    const currentRegion = regions[currentRegionIndex];
    if (!currentRegion) return 0;
    // Rough estimate: 1 bar = 2 seconds at 120 BPM
    // For more accuracy, we'd need BPM from the bundle
    return Math.ceil(currentRegion.duration / 2);
  };

  // Handle block creation from timeline
  const handleCreateBlock = useCallback((laneId: string, startBar: number) => {
    if (!localRegionAnnotations || !regionId) return;

    // Find the lane to get its color
    const lane = localRegionAnnotations.lanes.find(l => l.id === laneId);
    const laneColor = lane?.color || null;

    // Create a 1-bar block
    addBlock({
      laneId,
      startBar,
      endBar: startBar + 1,
      type: 'call',
      color: laneColor,
      label: null,
      notes: null,
    });
  }, [localRegionAnnotations, regionId, addBlock]);

  // Derive selected block from selectedBlockId
  const selectedBlock = useMemo(() => {
    if (!selectedBlockId || !localRegionAnnotations) return undefined;
    return localRegionAnnotations.blocks.find(b => b.id === selectedBlockId);
  }, [selectedBlockId, localRegionAnnotations]);

  // Audition hook (stub implementation)
  const handleAuditionBlock = useCallback((laneId: string, startBar: number, endBar: number) => {
    console.log('[Audition] Block requested:', {
      laneId,
      startBar,
      endBar,
      duration: endBar - startBar,
    });
    
    setLastAuditionRequest({
      laneId,
      startBar,
      endBar,
    });
    
    // TODO: Implement actual audio playback in future phase
  }, []);

  // Handle block selection and audition
  const handleSelectBlock = useCallback((blockId: string) => {
    setSelectedBlockId(blockId);
    
    // Find the block for audition
    const block = localRegionAnnotations?.blocks.find(b => b.id === blockId);
    if (block) {
      // Find the lane to get laneId
      const lane = localRegionAnnotations?.lanes.find(l => l.id === block.laneId);
      if (lane) {
        handleAuditionBlock(lane.id, block.startBar, block.endBar);
      }
    }
  }, [localRegionAnnotations, handleAuditionBlock]);

  // Handle block notes change
  const handleBlockNotesChange = useCallback((blockId: string, notes: string) => {
    updateBlock(blockId, { notes: notes.trim() || null });
  }, [updateBlock]);

  // Handle block update from timeline
  const handleUpdateBlock = useCallback((blockId: string, patch: Partial<AnnotationBlock>) => {
    if (!localRegionAnnotations || !blockId) return;

    // Validate constraints
    const block = localRegionAnnotations.blocks.find(b => b.id === blockId);
    if (!block) return;

    const barCount = getRegionBars();
    const updatedPatch: Partial<AnnotationBlock> = { ...patch };

    // Ensure startBar < endBar
    if ('startBar' in updatedPatch || 'endBar' in updatedPatch) {
      const newStartBar = updatedPatch.startBar ?? block.startBar;
      const newEndBar = updatedPatch.endBar ?? block.endBar;
      
      if (newEndBar <= newStartBar) {
        // Don't allow invalid ranges
        return;
      }

      // Clamp to valid range [0, barCount]
      updatedPatch.startBar = Math.max(0, Math.min(newStartBar, barCount));
      updatedPatch.endBar = Math.max(updatedPatch.startBar! + 1, Math.min(newEndBar, barCount));
    }

    updateBlock(blockId, updatedPatch);
  }, [localRegionAnnotations, updateBlock]);

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

  // Update region notes (with debouncing)
  const handleRegionNotesChange = useCallback((notes: string) => {
    if (!regionId) return;

    // Update local state immediately for responsive UI
    setLocalRegionAnnotations(prev => ({
      ...prev,
      notes: notes,
    }));

    // Debounce is handled by the existing useEffect that syncs localRegionAnnotations to global
    // The debounced save to backend is already handled by debouncedSave
  }, [regionId]);

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
        <div className="save-section">
          <button
            className="save-button"
            onClick={handleSave}
            disabled={isSaving || isLoadingAnnotations || !vcAnnotations}
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
          {saveStatus.type && (
            <span className={`save-status ${saveStatus.type}`}>
              {saveStatus.message}
            </span>
          )}
          {annotationsError && (
            <span className="save-status error">
              Error: {annotationsError.message}
            </span>
          )}
        </div>
      </div>

      <div className="visual-composer-content">
        <div className="lanes-section">
          {!localRegionAnnotations ? (
            <div className="lanes-empty-state">
              <p>No region annotations available. Please select a region.</p>
            </div>
          ) : (
            <LaneList
              lanes={localRegionAnnotations.lanes ?? []}
              onChangeLane={updateLane}
              onDeleteLane={deleteLane}
              onReorderLanes={reorderLanes}
              onAddLane={addLane}
            />
          )}
        </div>

        {/* Timeline area */}
        {localRegionAnnotations && localRegionAnnotations.lanes.length > 0 && (
          <div className="timeline-section">
            <ComposerTimeline
              regionAnnotations={localRegionAnnotations}
              barCount={getRegionBars()}
              onCreateBlock={handleCreateBlock}
              onSelectBlock={handleSelectBlock}
              onUpdateBlock={handleUpdateBlock}
            />
          </div>
        )}

        <div className="visual-composer-sidebar">
          <div className="region-notes-section">
            <h3>Region Notes</h3>
            <textarea
              className="region-notes-input"
              value={localRegionAnnotations?.notes || ''}
              onChange={(e) => handleRegionNotesChange(e.target.value)}
              placeholder="Add notes about this region..."
              rows={6}
              disabled={!localRegionAnnotations}
            />
          </div>

          <div className="block-notes-section">
            <NotesPanel
              selectedBlock={selectedBlock}
              onChangeNotes={handleBlockNotesChange}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default VisualComposerPage;

