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
import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { useProject } from "../context/ProjectContext";
import {
  RegionAnnotations,
  AnnotationLane,
  AnnotationBlock,
} from "../api/reference";
import {
  type VcAnnotations,
  type VcRegionAnnotations,
  type VcLane,
  type VcBlock,
} from "../api/visualComposerApi";
import { useVisualComposerAnnotations } from "../hooks/useVisualComposerAnnotations";
import { LaneList } from "../components/visualComposer/LaneList";
import { ComposerTimeline } from "../components/visualComposer/ComposerTimeline";
import { NotesPanel } from "../components/visualComposer/NotesPanel";
import "./VisualComposerPage.css";

const __DEV__ = import.meta.env.MODE !== "production";

interface VisualComposerPageProps {
  onBack: () => void;
  demoMode?: boolean;
}

// Helper functions to convert between Vc types and Annotation types (for component compatibility)
function vcLaneToAnnotationLane(vcLane: VcLane): AnnotationLane {
  return {
    id: vcLane.id,
    name: vcLane.name,
    color: vcLane.color || "#FF6B6B", // Provide default color if null/undefined
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

function vcRegionToRegionAnnotations(
  vcRegion: VcRegionAnnotations,
): RegionAnnotations {
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
  region?: {
    id: string;
    name: string;
    type: string;
    start: number;
    end: number;
  } | null,
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

function VisualComposerPage({
  onBack,
  demoMode = false,
}: VisualComposerPageProps): JSX.Element {
  const { referenceId, regions } = useProject();

  // DEV: Render counter for debugging sync loops
  const renderCountRef = useRef<number>(0);
  if (__DEV__) {
    renderCountRef.current += 1;
  }

  // Component initialization

  // Create demo regions if in demo mode
  const demoRegions = useMemo(() => {
    if (!demoMode) return null;

    return [
      {
        id: "demo-intro",
        name: "Intro",
        type: "low_energy",
        start: 0.0,
        end: 9.0,
        duration: 9.0,
        motifs: [],
        fills: [],
        callResponse: [],
        startBar: 0.0,
        endBar: 9.0,
        displayOrder: 0,
      },
      {
        id: "demo-build",
        name: "Build",
        type: "build",
        start: 9.0,
        end: 17.0,
        duration: 8.0,
        motifs: [],
        fills: [],
        callResponse: [],
        startBar: 9.0,
        endBar: 17.0,
        displayOrder: 1,
      },
      {
        id: "demo-drop",
        name: "Drop",
        type: "high_energy",
        start: 17.0,
        end: 33.0,
        duration: 16.0,
        motifs: [],
        fills: [],
        callResponse: [],
        startBar: 17.0,
        endBar: 33.0,
        displayOrder: 2,
      },
    ];
  }, [demoMode]);

  // Use demo projectId/referenceId in demo mode
  const projectId = demoMode ? "demo-project" : referenceId || null;
  const effectiveRegions = demoMode ? demoRegions || [] : regions;

  // Use the new Visual Composer annotations hook
  // Use referenceId as projectId (they're the same in this context)
  const {
    annotations: vcAnnotations,
    setAnnotations: setVcAnnotations,
    isLoading: isLoadingAnnotations,
    error: saveError, // Save errors
    loadError, // Initial load errors
    saveAnnotations: saveVcAnnotations,
    isSaving,
    saveStatus,
    isDirty,
    forceSave,
    retryLoad,
    addLane: addLaneToVcAnnotations,
  } = useVisualComposerAnnotations(projectId, demoMode, demoRegions);

  // Debug logs after useVisualComposerAnnotations hook

  // Build ordered region list from annotations (if available) or fallback to regions from context
  // Annotations have displayOrder and bar ranges, so prefer that for ordering
  const orderedRegions = useMemo(() => {
    // DEBUG: this guard may be blocking lanes/waveform/timeline - returns empty array if no regions
    if (!vcAnnotations || !effectiveRegions || effectiveRegions.length === 0) {
      return effectiveRegions || [];
    }

    // Create a map of region annotations by regionId
    const annotationsByRegionId = new Map<string, VcRegionAnnotations>();
    vcAnnotations.regions.forEach((regionAnn) => {
      annotationsByRegionId.set(regionAnn.regionId, regionAnn);
    });

    // Build ordered list: use annotations displayOrder if available, otherwise use region order
    const regionList = effectiveRegions.map((region) => {
      const regionAnn = annotationsByRegionId.get(region.id);
      return {
        ...region,
        startBar: regionAnn?.startBar ?? null,
        endBar: regionAnn?.endBar ?? null,
        displayOrder: regionAnn?.displayOrder ?? null,
      };
    });

    // Sort by displayOrder if available, otherwise keep original order
    return regionList.sort((a, b) => {
      if (a.displayOrder !== null && b.displayOrder !== null) {
        return a.displayOrder - b.displayOrder;
      }
      if (a.displayOrder !== null) return -1;
      if (b.displayOrder !== null) return 1;
      return 0; // Keep original order if no displayOrder
    });
  }, [vcAnnotations, effectiveRegions]);

  // Initialize currentRegionIndex from URL params if available (for future router integration)
  // For now, default to 0
  const [currentRegionIndex, setCurrentRegionIndex] = useState(() => {
    // TODO: If router params are added, read from URL here
    // const params = useSearchParams(); // or useParams() if using React Router
    // const regionIndexParam = params.get('regionIndex');
    // return regionIndexParam ? parseInt(regionIndexParam, 10) : 0;
    return 0;
  });

  // Ensure currentRegionIndex is valid
  useEffect(() => {
    if (
      orderedRegions.length > 0 &&
      currentRegionIndex >= orderedRegions.length
    ) {
      setCurrentRegionIndex(0);
    }
  }, [orderedRegions.length, currentRegionIndex]);

  const currentRegion = orderedRegions[currentRegionIndex];
  const regionId = currentRegion?.id;

  // Ensure selectedRegionId is stable - use regionId if available, otherwise fallback to first region
  // This ensures selectedRegionId is NEVER undefined after initial load if regions exist
  const selectedRegionId =
    regionId || (orderedRegions.length > 0 ? orderedRegions[0]?.id : undefined);

  // DEV: Log render with region info
  if (__DEV__) {
    console.log(`[VC] render #${renderCountRef.current} region=${selectedRegionId}`);
  }

  // Auto-select first region when regions become available and selectedRegionId is null/undefined
  // This ensures a region is always selected when regions exist
  useEffect(() => {
    if (orderedRegions.length > 0 && !selectedRegionId) {
      // Regions exist but no region is selected - auto-select the first one
      setCurrentRegionIndex(0);
    }
  }, [orderedRegions.length, selectedRegionId]);

  // Get bar range from annotations or calculate from region time
  const currentRegionBarRange = useMemo(() => {
    // DEBUG: this guard may be blocking lanes/waveform/timeline - returns null if no currentRegion
    if (!currentRegion) return null;

    // Try to get from annotations first
    // DEBUG: this may crash if currentRegion is undefined - accessing .id without guard
    const regionAnn = vcAnnotations?.regions.find(
      (r) => r.regionId === currentRegion?.id,
    );
    if (
      regionAnn?.startBar !== null &&
      regionAnn?.startBar !== undefined &&
      regionAnn?.endBar !== null &&
      regionAnn?.endBar !== undefined
    ) {
      return {
        startBar: regionAnn.startBar,
        endBar: regionAnn.endBar,
      };
    }

    // Fallback: use currentRegion.startBar/endBar if available (from orderedRegions mapping)
    const regionWithBars = currentRegion as typeof currentRegion & {
      startBar?: number | null;
      endBar?: number | null;
    };
    if (
      regionWithBars.startBar !== null &&
      regionWithBars.startBar !== undefined &&
      regionWithBars.endBar !== null &&
      regionWithBars.endBar !== undefined
    ) {
      return {
        startBar: regionWithBars.startBar,
        endBar: regionWithBars.endBar,
      };
    }

    // Last fallback: calculate from region time (would need BPM, but for now return null)
    // In a real implementation, we'd get BPM from the bundle
    return null;
  }, [currentRegion, vcAnnotations]);

  // Note: saveStatus and isDirty are now provided by the hook

  // Local state for current region's annotations (using Annotation types for component compatibility)
  const [localRegionAnnotations, setLocalRegionAnnotations] =
    useState<RegionAnnotations>({
      regionId: regionId || "",
      lanes: [],
      blocks: [],
      notes: "",
    });

  // Keep ref in sync with localRegionAnnotations for comparison in effects
  useEffect(() => {
    localRegionAnnotationsRef.current = localRegionAnnotations;
  }, [localRegionAnnotations]);

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

  // Debug state for development
  const vcDebugState = {
    regions:
      effectiveRegions?.map((r) => ({
        id: r.id ?? (r as any).regionId,
        name: r.name,
        startBar: (r as any).startBar,
        endBar: (r as any).endBar,
      })) ?? [],
    selectedRegionId,
    annotationsRegions:
      vcAnnotations?.regions?.map((r) => ({
        regionId: r.regionId,
        name: r.regionName,
        lanes:
          r.lanes?.map((l) => ({
            laneId: l.id,
            label: l.name,
            blocks: r.blocks?.filter((b) => b.laneId === l.id).length ?? 0,
          })) ?? [],
      })) ?? [],
    localRegionAnnotations: localRegionAnnotations && {
      regionId: localRegionAnnotations.regionId,
      name: localRegionAnnotations.name,
      lanes:
        localRegionAnnotations.lanes?.map((l) => ({
          laneId: l.id,
          label: l.name,
          blocks:
            localRegionAnnotations.blocks?.filter((b) => b.laneId === l.id)
              .length ?? 0,
        })) ?? [],
    },
  };

  // Color palette for lanes (rotates through these colors)
  const LANE_COLORS = [
    "#FF6B6B", // Red
    "#4ECDC4", // Teal
    "#FFE66D", // Yellow
    "#95E1D3", // Mint
    "#F38181", // Coral
    "#AA96DA", // Purple
    "#FCBAD3", // Pink
    "#A8E6CF", // Green
  ];

  // Helper to generate unique lane IDs
  const createLaneId = useCallback(() => {
    return `lane_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Helper to generate unique block IDs
  const createBlockId = useCallback(() => {
    return `block_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // updateVcAnnotations is now inlined in the sync effect below to avoid circular dependencies

  // Track if we're syncing from global to avoid circular updates
  const isSyncingFromGlobalRef = useRef(false);
  // Track the last regionId we synced to avoid unnecessary updates
  const lastSyncedRegionIdRef = useRef<string | undefined>(undefined);
  // Track the last vcAnnotations we synced from to avoid re-syncing same state
  const lastSyncedVcAnnotationsRef = useRef<VcAnnotations | null>(null);
  // Track current localRegionAnnotations for comparison without adding to dependencies
  const localRegionAnnotationsRef = useRef<RegionAnnotations>(
    localRegionAnnotations,
  );
  // DEV: Effect counter for global→local sync
  const globalToLocalEffectCountRef = useRef<number>(0);
  // TODO: Remove this safety fuse once the sync loop is resolved.
  // Safety fuse: track run count to prevent infinite loops
  const globalToLocalRunCountRef = useRef<number>(0);

  // Initialize vcAnnotations ONLY when it's null and regions are available
  // This should NOT depend on localRegionAnnotations or run on every render
  // Note: The hook (useVisualComposerAnnotations) handles initial loading from the API.
  // This effect is mainly a guard to prevent premature initialization attempts.
  // In practice, vcAnnotations will be initialized by the hook's loadAnnotations.
  useEffect(() => {
    // Only initialize if vcAnnotations is null/undefined
    if (vcAnnotations) return;

    // Only initialize if we have a referenceId and regions exist
    if (!referenceId || !effectiveRegions || effectiveRegions.length === 0)
      return;

    // Don't initialize in demo mode (hook handles that)
    if (demoMode) return;

    // The hook's loadAnnotations will handle initialization when projectId is set
    // We don't need to create empty annotations here - the backend will return defaults
    // This effect is just a guard to ensure we don't try to use vcAnnotations before it's loaded
  }, [vcAnnotations, referenceId, effectiveRegions, demoMode]);

  // Sync from vcAnnotations to localRegionAnnotations when selectedRegionId changes
  // This effect should ONLY depend on [vcAnnotations, selectedRegionId]
  useEffect(() => {
    // TODO: Remove this safety fuse once the sync loop is resolved.
    // Safety fuse: abort if run count exceeds threshold to prevent infinite loops
    globalToLocalRunCountRef.current += 1;
    if (globalToLocalRunCountRef.current > 20) {
      if (__DEV__) {
        console.warn('[VC] ABORT vcAnnotations→local sync: run count exceeded');
      }
      return;
    }

    // DEV: Structured logging at effect start
    if (__DEV__) {
      globalToLocalEffectCountRef.current += 1;
      console.log('[VC] global→local effect fired', {
        runCount: globalToLocalRunCountRef.current,
        effectCount: globalToLocalEffectCountRef.current,
        selectedRegionId,
        vcAnnotationsIsNull: vcAnnotations === null,
        localRegionAnnotationsRefIsNull: localRegionAnnotationsRef.current === null,
      });
    }

    // Early return if prerequisites are missing
    if (!vcAnnotations || !selectedRegionId) {
      if (__DEV__) {
        console.log('[VC] global→local: no vcAnnotations or no selectedRegionId – exiting');
      }
      // Only set empty localRegionAnnotations if we truly have no data
      if (!vcAnnotations && !selectedRegionId) {
        const emptyRegionAnnotations: RegionAnnotations = {
          regionId: "",
          lanes: [],
          blocks: [],
          notes: "",
        };
        isSyncingFromGlobalRef.current = true;
        setLocalRegionAnnotations(emptyRegionAnnotations);
        localRegionAnnotationsRef.current = emptyRegionAnnotations;
        isSyncingFromGlobalRef.current = false;
        lastSyncedRegionIdRef.current = undefined;
        lastSyncedVcAnnotationsRef.current = null;
      }
      return;
    }

    // Check if we've already synced this exact combination
    // Use JSON.stringify for deep comparison since vcAnnotations is an object
    const vcAnnotationsKey = JSON.stringify(vcAnnotations);
    const lastSyncedKey = lastSyncedVcAnnotationsRef.current
      ? JSON.stringify(lastSyncedVcAnnotationsRef.current)
      : null;

    if (
      lastSyncedRegionIdRef.current === selectedRegionId &&
      lastSyncedKey === vcAnnotationsKey
    ) {
      // Already synced this region with this vcAnnotations state
      if (__DEV__) {
        console.log('[VC] global→local: skipping – already synced this region/state combination');
      }
      return;
    }

    // Find existing VcRegionAnnotations for current region
    const existingVcRegion = vcAnnotations.regions.find(
      (r) => r.regionId === selectedRegionId,
    );

    let newLocalAnnotations: RegionAnnotations | null = null;

    if (existingVcRegion) {
      if (__DEV__) {
        console.log('[VC] global→local: using existingVcRegion – comparing to local');
      }
      newLocalAnnotations = vcRegionToRegionAnnotations(existingVcRegion);
    } else if (currentRegion) {
      if (__DEV__) {
        console.log('[VC] global→local: no existingVcRegion – creating emptyRegionAnnotations');
      }
      // Create empty RegionAnnotations if not found in vcAnnotations
      newLocalAnnotations = {
        regionId: selectedRegionId,
        lanes: [],
        blocks: [],
        notes: "",
      };
    } else {
      if (__DEV__) {
        console.log('[VC] global→local: no currentRegion – exiting');
      }
      return;
    }

    // DEEP comparison BEFORE calling setLocalRegionAnnotations
    const currentLocalJson = JSON.stringify(localRegionAnnotationsRef.current);
    const newLocalJson = JSON.stringify(newLocalAnnotations);
    
    if (currentLocalJson === newLocalJson) {
      if (__DEV__) {
        console.log('[VC] global→local: skipping setLocalRegionAnnotations (no diff)');
      }
      // Update tracking refs even if we don't update state
      lastSyncedRegionIdRef.current = selectedRegionId;
      lastSyncedVcAnnotationsRef.current = vcAnnotations;
      return;
    }

    // Only when they differ: apply the update
    if (__DEV__) {
      console.log('[VC] global→local: applying setLocalRegionAnnotations');
    }
    
    isSyncingFromGlobalRef.current = true;
    setLocalRegionAnnotations(newLocalAnnotations);
    localRegionAnnotationsRef.current = newLocalAnnotations;
    isSyncingFromGlobalRef.current = false;
    
    lastSyncedRegionIdRef.current = selectedRegionId;
    lastSyncedVcAnnotationsRef.current = vcAnnotations;

    // If we created empty annotations and the region doesn't exist in vcAnnotations, add it
    if (!existingVcRegion && currentRegion) {
      const regionExists = vcAnnotations.regions.some(
        (r) => r.regionId === selectedRegionId,
      );
      if (!regionExists) {
        const newVcRegion = regionAnnotationsToVcRegion(
          newLocalAnnotations,
          currentRegion,
        );
        // Use functional update to avoid dependency on vcAnnotations
        setVcAnnotations((prev) => {
          if (!prev) return prev;
          // Double-check if region already exists (race condition guard)
          const alreadyExists = prev.regions.some(
            (r) => r.regionId === selectedRegionId,
          );
          if (alreadyExists) return prev;
          return {
            ...prev,
            regions: [...prev.regions, newVcRegion],
          };
        });
      }
    }
  }, [vcAnnotations, selectedRegionId, currentRegion, setVcAnnotations]);

  // Update Vc annotations whenever localRegionAnnotations changes (but not when syncing from global)
  // This effect should NOT depend on vcAnnotations to avoid circular updates
  // Use a ref to track if we've already updated for this regionId to prevent loops
  const lastUpdatedRegionIdRef = useRef<string | undefined>(undefined);
  const lastUpdatedLocalRef = useRef<string>("");
  // DEV: Effect counter for local→global sync
  const localToGlobalEffectCountRef = useRef<number>(0);
  // TODO: Remove this safety fuse once the sync loop is resolved.
  // Safety fuse: track run count to prevent infinite loops
  const localToGlobalRunCountRef = useRef<number>(0);

  useEffect(() => {
    // TODO: Remove this safety fuse once the sync loop is resolved.
    // Safety fuse: abort if run count exceeds threshold to prevent infinite loops
    localToGlobalRunCountRef.current += 1;
    if (localToGlobalRunCountRef.current > 20) {
      if (__DEV__) {
        console.warn('[VC] ABORT local→vcAnnotations sync: run count exceeded');
      }
      return;
    }

    // DEV: Structured logging at effect start
    if (__DEV__) {
      localToGlobalEffectCountRef.current += 1;
      console.log('[VC] local→global effect fired', {
        runCount: localToGlobalRunCountRef.current,
        effectCount: localToGlobalEffectCountRef.current,
        selectedRegionId,
        localRegionAnnotationsIsNull: localRegionAnnotations === null,
        isSyncingFromGlobal: isSyncingFromGlobalRef.current,
      });
    }

    // Guard 1: Check prerequisites
    // Note: vcAnnotations is checked inside the functional update, not here
    if (!selectedRegionId || !localRegionAnnotations) {
      if (__DEV__) {
        console.log('[VC] local→global: early exit – no selectedRegionId or no localRegionAnnotations');
      }
      return;
    }

    // Guard 2: Don't sync if localRegionAnnotations doesn't match selectedRegionId
    if (
      !localRegionAnnotations.regionId ||
      localRegionAnnotations.regionId !== selectedRegionId
    ) {
      if (__DEV__) {
        console.log('[VC] local→global: early exit – regionId mismatch', {
          localRegionId: localRegionAnnotations.regionId,
          selectedRegionId,
        });
      }
      return;
    }

    // Guard 3: CRITICAL - If we're syncing from global, reset flag and abort
    // This prevents local→global from firing during global→local updates
    if (isSyncingFromGlobalRef.current) {
      isSyncingFromGlobalRef.current = false;
      if (__DEV__) {
        console.log('[VC] local→global: skipping because isSyncingFromGlobalRef was true (reset flag)');
      }
      return;
    }

    // Guard 4: Skip if we've already updated for this exact localRegionAnnotations state
    const currentLocalJson = JSON.stringify(localRegionAnnotations);
    if (
      lastUpdatedRegionIdRef.current === selectedRegionId &&
      lastUpdatedLocalRef.current === currentLocalJson
    ) {
      if (__DEV__) {
        console.log('[VC] local→global: skipping – already updated for this state');
      }
      return;
    }

    // Build candidate VcRegionAnnotations for comparison
    const candidateVcRegion = regionAnnotationsToVcRegion(
      localRegionAnnotations,
      currentRegion || null,
    );

    // Use functional setState to update vcAnnotations
    // Compare BEFORE calling setVcAnnotations to avoid unnecessary updates
    setVcAnnotations((prev) => {
      if (!prev) return prev;

      // Find the region to update
      const regionIndex = prev.regions.findIndex(
        (r) => r.regionId === selectedRegionId,
      );
      
      if (regionIndex === -1) {
        // Region doesn't exist in vcAnnotations, add it
        if (!currentRegion) return prev;
        
        if (__DEV__) {
          console.log('[VC] local→global: applying update to vcAnnotations (adding new region)');
        }
        
        // Update refs after determining we need to update
        lastUpdatedRegionIdRef.current = selectedRegionId;
        lastUpdatedLocalRef.current = currentLocalJson;
        
        return {
          ...prev,
          regions: [...prev.regions, candidateVcRegion],
        };
      }

      // Update existing region - DEEP comparison before updating
      const prevRegion = prev.regions[regionIndex];
      const prevJson = JSON.stringify(prevRegion);
      const nextJson = JSON.stringify(candidateVcRegion);
      
      if (prevJson === nextJson) {
        // No change - update refs but don't trigger state update
        if (__DEV__) {
          console.log('[VC] local→global: no diff – skipping setVcAnnotations');
        }
        lastUpdatedRegionIdRef.current = selectedRegionId;
        lastUpdatedLocalRef.current = currentLocalJson;
        return prev; // No change, return previous state
      }

      // Only if they differ: apply the update
      if (__DEV__) {
        console.log('[VC] local→global: applying update to vcAnnotations (updating existing region)');
      }
      
      // Update refs after determining we need to update
      lastUpdatedRegionIdRef.current = selectedRegionId;
      lastUpdatedLocalRef.current = currentLocalJson;

      const updatedRegions = [...prev.regions];
      updatedRegions[regionIndex] = candidateVcRegion;

      return {
        ...prev,
        regions: updatedRegions,
      };
    });
  }, [
    localRegionAnnotations,
    selectedRegionId,
    currentRegion,
    setVcAnnotations,
  ]); // Use selectedRegionId for stability

  // Handle manual save button click
  const handleSave = useCallback(async () => {
    if (!vcAnnotations || !referenceId) return;

    try {
      await saveVcAnnotations();
      // saveStatus is updated by the hook
    } catch (err) {
      console.error("Error saving annotations:", err);
      // Error status is updated by the hook
    }
  }, [vcAnnotations, referenceId, saveVcAnnotations]);

  // ============================================================================
  // Lane CRUD Helper Functions
  // ============================================================================

  /**
   * Adds a new lane to the current region's annotations.
   * Updates both vcAnnotations (via hook) and localRegionAnnotations (local state).
   */
  const handleAddLane = useCallback(() => {
    if (!selectedRegionId) return;

    // Update vcAnnotations via hook
    addLaneToVcAnnotations(selectedRegionId);

    // Also update localRegionAnnotations immediately for responsive UI
    const lanes = localRegionAnnotations?.lanes || [];
    const maxOrder =
      lanes.length > 0 ? Math.max(...lanes.map((l) => l.order ?? 0)) : -1;
    const nextOrder = maxOrder + 1;

    // Rotate through color palette
    const colorIndex = lanes.length % LANE_COLORS.length;
    const color = LANE_COLORS[colorIndex];

    const newLaneId = crypto.randomUUID
      ? crypto.randomUUID()
      : `lane-${Date.now()}-${Math.random().toString(16).slice(2)}`;

    const newLane: AnnotationLane = {
      id: newLaneId,
      name: `New Lane`,
      color,
      collapsed: false,
      order: nextOrder,
    };

    setLocalRegionAnnotations((prev) => {
      if (!prev || prev.regionId !== selectedRegionId) return prev;
      return {
        ...prev,
        lanes: [...(prev.lanes || []), newLane],
      };
    });
  }, [selectedRegionId, addLaneToVcAnnotations, localRegionAnnotations]);

  /**
   * Updates a lane by ID with a partial patch of properties.
   * Finds the lane and applies the patch, then syncs to global annotations via useEffect.
   */
  const updateLane = useCallback(
    (id: string, patch: Partial<AnnotationLane>) => {
      if (!localRegionAnnotations || !id) return;

      setLocalRegionAnnotations((prev) => {
        if (!prev || !prev.lanes) return prev;

        return {
          ...prev,
          lanes: prev.lanes.map((lane) =>
            lane.id === id ? { ...lane, ...patch } : lane,
          ),
        };
      });
    },
    [localRegionAnnotations],
  );

  /**
   * Deletes a lane by ID and optionally removes all blocks that reference it.
   * Syncs to global annotations via useEffect.
   */
  const deleteLane = useCallback(
    (id: string) => {
      if (!localRegionAnnotations || !id) return;

      setLocalRegionAnnotations((prev) => {
        if (!prev || !prev.lanes) return prev;

        // Remove the lane
        const updatedLanes = prev.lanes.filter((lane) => lane.id !== id);

        // Optionally remove blocks that reference this lane
        const updatedBlocks =
          prev.blocks?.filter((block) => block.laneId !== id) || [];

        return {
          ...prev,
          lanes: updatedLanes,
          blocks: updatedBlocks,
        };
      });
    },
    [localRegionAnnotations],
  );

  /**
   * Reorders lanes based on an ordered list of lane IDs.
   * Updates each lane's order property to match the new position.
   * Syncs to global annotations via useEffect.
   */
  const reorderLanes = useCallback(
    (orderedIds: string[]) => {
      if (!localRegionAnnotations || !orderedIds || orderedIds.length === 0)
        return;

      setLocalRegionAnnotations((prev) => {
        if (!prev || !prev.lanes) return prev;

        // Create a map of lane by ID for quick lookup
        const laneMap = new Map(prev.lanes.map((lane) => [lane.id, lane]));

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
          .filter((lane) => !existingIds.has(lane.id))
          .map((lane, index) => ({
            ...lane,
            order: reorderedLanes.length + index,
          }));

        return {
          ...prev,
          lanes: [...reorderedLanes, ...remainingLanes],
        };
      });
    },
    [localRegionAnnotations],
  );

  // ============================================================================
  // Block CRUD Helper Functions
  // ============================================================================

  /**
   * Adds a new block to localRegionAnnotations.
   * Generates a unique ID and adds the block to the blocks array.
   * Automatically syncs to global annotations via useEffect.
   */
  const addBlock = useCallback(
    (partial: Omit<AnnotationBlock, "id">) => {
      if (!localRegionAnnotations || !selectedRegionId) return;

      const newBlock: AnnotationBlock = {
        id: createBlockId(),
        ...partial,
      };

      setLocalRegionAnnotations((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          blocks: [...(prev.blocks || []), newBlock],
        };
      });
    },
    [localRegionAnnotations, regionId, createBlockId],
  );

  /**
   * Updates a block by ID with a partial patch of properties.
   * Finds the block and applies the patch, then syncs to global annotations via useEffect.
   */
  const updateBlock = useCallback(
    (id: string, patch: Partial<AnnotationBlock>) => {
      if (!localRegionAnnotations || !id) return;

      setLocalRegionAnnotations((prev) => {
        if (!prev || !prev.blocks) return prev;

        return {
          ...prev,
          blocks: prev.blocks.map((block) =>
            block.id === id ? { ...block, ...patch } : block,
          ),
        };
      });
    },
    [localRegionAnnotations],
  );

  /**
   * Deletes a block by ID from localRegionAnnotations.
   * Removes the block from the blocks array and syncs to global annotations via useEffect.
   */
  const deleteBlock = useCallback(
    (id: string) => {
      if (!localRegionAnnotations || !id) return;

      setLocalRegionAnnotations((prev) => {
        if (!prev || !prev.blocks) return prev;

        return {
          ...prev,
          blocks: prev.blocks.filter((block) => block.id !== id),
        };
      });
    },
    [localRegionAnnotations],
  );

  // ============================================================================
  // Legacy Handlers (for bar grid/block functionality - to be used in future prompts)
  // ============================================================================

  // Calculate bars for current region
  // Prefer bar range from annotations, otherwise use region's startBar/endBar, or estimate from duration
  const getRegionBars = (): number => {
    if (!currentRegion) return 0;

    // Use bar range from annotations if available
    if (currentRegionBarRange && currentRegionBarRange.endBar) {
      return Math.ceil(currentRegionBarRange.endBar);
    }

    // Fallback: use currentRegion.startBar/endBar if available (demo mode)
    const regionWithBars = currentRegion as typeof currentRegion & {
      startBar?: number | null;
      endBar?: number | null;
    };
    if (
      regionWithBars.startBar !== null &&
      regionWithBars.startBar !== undefined &&
      regionWithBars.endBar !== null &&
      regionWithBars.endBar !== undefined
    ) {
      return Math.ceil(regionWithBars.endBar);
    }

    // Last fallback: rough estimate (1 bar = 2 seconds at 120 BPM)
    // For more accuracy, we'd need BPM from the bundle
    return Math.ceil((currentRegion?.duration || 0) / 2);
  };

  // Handle block creation from timeline
  const handleCreateBlock = useCallback(
    (laneId: string, startBar: number) => {
      if (!localRegionAnnotations || !selectedRegionId) return;

      // Find the lane to get its color
      const lane = localRegionAnnotations.lanes.find((l) => l.id === laneId);
      const laneColor = lane?.color || null;

      // Create a 1-bar block
      addBlock({
        laneId,
        startBar,
        endBar: startBar + 1,
        type: "call",
        color: laneColor,
        label: null,
        notes: null,
      });
    },
    [localRegionAnnotations, regionId, addBlock],
  );

  // Derive selected block from selectedBlockId
  const selectedBlock = useMemo(() => {
    if (!selectedBlockId || !localRegionAnnotations) return undefined;
    return localRegionAnnotations.blocks.find((b) => b.id === selectedBlockId);
  }, [selectedBlockId, localRegionAnnotations]);

  // Audition hook (stub implementation)
  const handleAuditionBlock = useCallback(
    (laneId: string, startBar: number, endBar: number) => {
      // Audition block (logging removed for production)
      setLastAuditionRequest({
        laneId,
        startBar,
        endBar,
      });

      // TODO: Implement actual audio playback in future phase
    },
    [],
  );

  // Handle block selection and audition
  const handleSelectBlock = useCallback(
    (blockId: string) => {
      setSelectedBlockId(blockId);

      // Find the block for audition
      const block = localRegionAnnotations?.blocks.find(
        (b) => b.id === blockId,
      );
      if (block) {
        // Find the lane to get laneId
        const lane = localRegionAnnotations?.lanes.find(
          (l) => l.id === block.laneId,
        );
        if (lane) {
          handleAuditionBlock(lane.id, block.startBar, block.endBar);
        }
      }
    },
    [localRegionAnnotations, handleAuditionBlock],
  );

  // Handle block notes change
  const handleBlockNotesChange = useCallback(
    (blockId: string, notes: string) => {
      updateBlock(blockId, { notes: notes.trim() || null });
    },
    [updateBlock],
  );

  // Handle block update from timeline
  const handleUpdateBlock = useCallback(
    (blockId: string, patch: Partial<AnnotationBlock>) => {
      if (!localRegionAnnotations || !blockId) return;

      // Validate constraints
      const block = localRegionAnnotations.blocks.find((b) => b.id === blockId);
      if (!block) return;

      const barCount = getRegionBars();
      const updatedPatch: Partial<AnnotationBlock> = { ...patch };

      // Ensure startBar < endBar
      if ("startBar" in updatedPatch || "endBar" in updatedPatch) {
        const newStartBar = updatedPatch.startBar ?? block.startBar;
        const newEndBar = updatedPatch.endBar ?? block.endBar;

        if (newEndBar <= newStartBar) {
          // Don't allow invalid ranges
          return;
        }

        // Clamp to valid range [0, barCount]
        updatedPatch.startBar = Math.max(0, Math.min(newStartBar, barCount));
        updatedPatch.endBar = Math.max(
          updatedPatch.startBar! + 1,
          Math.min(newEndBar, barCount),
        );
      }

      updateBlock(blockId, updatedPatch);
    },
    [localRegionAnnotations, updateBlock],
  );

  // Handle bar grid click/drag
  const handleBarGridMouseDown = (laneIndex: number, bar: number) => {
    setIsDragging(true);
    setDragStart(bar);
    setDragLaneId(`${regionId}_${laneIndex}`);
  };

  const handleBarGridMouseUp = (finalBar?: number) => {
    if (
      isDragging &&
      dragStart !== null &&
      dragLaneId &&
      finalBar !== undefined
    ) {
      const [, laneIndexStr] = dragLaneId.split("_");
      const laneIndex = parseInt(laneIndexStr, 10);
      const startBar = Math.min(dragStart, finalBar);
      const endBar = Math.max(dragStart, finalBar) + 1; // Make end exclusive

      // Don't create blocks with zero or negative length
      if (endBar > startBar) {
        const lane = localRegionAnnotations.lanes[laneIndex];
        if (lane) {
          // Check if block overlaps with existing blocks in this lane
          const laneBlocks = localRegionAnnotations.blocks.filter(
            (b) => b.laneId === lane.id,
          );
          const overlaps = laneBlocks.some(
            (b: AnnotationBlock) => startBar < b.endBar && endBar > b.startBar,
          );

          if (!overlaps) {
            // Create new block at region level
            const newBlock: AnnotationBlock = {
              id: `block_${Date.now()}`,
              laneId: lane.id,
              startBar,
              endBar,
              type: "custom",
              label: null,
            };

            setLocalRegionAnnotations((prev) => ({
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
    if (!selectedRegionId) return;

    setLocalRegionAnnotations((prev) => ({
      ...prev,
      blocks: prev.blocks.filter((b) => b.id !== blockId),
    }));
  };

  // Update region notes (with debouncing)
  const handleRegionNotesChange = useCallback(
    (notes: string) => {
      if (!selectedRegionId) return;

      // Update local state immediately for responsive UI
      setLocalRegionAnnotations((prev) => ({
        ...prev,
        notes: notes,
      }));

      // Debounce is handled by the existing useEffect that syncs localRegionAnnotations to global
      // The debounced save to backend is already handled by debouncedSave
    },
    [regionId],
  );

  // Navigation handlers
  // Edits are preserved automatically because:
  // 1. Edits are stored in localRegionAnnotations (current region's edits)
  // 2. A useEffect syncs localRegionAnnotations to vcAnnotations (keyed by regionId)
  // 3. When navigating, we change currentRegionIndex, which triggers a useEffect
  //    that loads the new region's annotations from vcAnnotations into localRegionAnnotations
  // 4. The previous region's edits remain in vcAnnotations (unsaved until autosave completes)
  // 5. If dirty, we trigger an immediate save before switching regions
  const handlePrevRegion = useCallback(async () => {
    if (currentRegionIndex > 0) {
      // If there are unsaved changes, save immediately before navigating
      if (isDirty) {
        try {
          await forceSave();
        } catch (err) {
          console.error("Error saving before navigation:", err);
          // Still allow navigation, but warn user
          alert(
            "Failed to save changes. Your edits may be lost if you navigate away.",
          );
        }
      }

      // Change the index to show the previous region
      setCurrentRegionIndex(currentRegionIndex - 1);
      // Clear selected block when navigating
      setSelectedBlockId(null);
    }
  }, [currentRegionIndex, isDirty, forceSave]);

  const handleNextRegion = useCallback(async () => {
    if (currentRegionIndex < orderedRegions.length - 1) {
      // If there are unsaved changes, save immediately before navigating
      if (isDirty) {
        try {
          await forceSave();
        } catch (err) {
          console.error("Error saving before navigation:", err);
          // Still allow navigation, but warn user
          alert(
            "Failed to save changes. Your edits may be lost if you navigate away.",
          );
        }
      }

      // Change the index to show the next region
      setCurrentRegionIndex(currentRegionIndex + 1);
      // Clear selected block when navigating
      setSelectedBlockId(null);
    }
  }, [currentRegionIndex, orderedRegions.length, isDirty, forceSave]);

  // Validation
  // DEBUG: this guard may be blocking lanes/waveform/timeline - early return if no referenceId or regions
  if (!demoMode && (!referenceId || orderedRegions.length === 0)) {
    return (
      <div className="visual-composer-page">
        <div className="visual-composer-empty">
          <h2>No Reference Loaded</h2>
          <p>
            Please load a reference track and analyze it before using Visual
            Composer.
          </p>
          {loadError && (
            <div
              className="load-error-badge"
              style={{ marginTop: "1rem", maxWidth: "500px" }}
            >
              <span className="error-text">
                Failed to load annotations: {loadError.message}
              </span>
              <button
                className="retry-button"
                onClick={retryLoad}
                disabled={isLoadingAnnotations}
              >
                Retry
              </button>
            </div>
          )}
          <button className="back-button" onClick={onBack}>
            Back to Region Map
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="visual-composer-page" data-testid="visual-composer-page">
      <div className="visual-composer-header">
        <button className="back-button" onClick={onBack}>
          ← Back to Region Map
        </button>
        <div className="region-navigation">
          {/* DEBUG: this guard may be blocking lanes/waveform/timeline - navigation may be disabled if no currentRegion */}
          <button
            className="nav-button"
            onClick={handlePrevRegion}
            disabled={currentRegionIndex === 0}
          >
            ← Prev
          </button>
          <div className="region-info">
            {/* DEBUG: this may crash if currentRegion is undefined - no guard before accessing .name */}
            <h2>{currentRegion?.name || "No Region"}</h2>
            <span className="region-type">{currentRegion?.type || ""}</span>
            {/* Bar range display - show if currentRegionBarRange exists OR use currentRegion.startBar/endBar as fallback */}
            {(() => {
              const regionWithBars = currentRegion as typeof currentRegion & {
                startBar?: number | null;
                endBar?: number | null;
              };
              const hasBarRange =
                currentRegionBarRange ||
                (regionWithBars?.startBar !== null &&
                  regionWithBars?.startBar !== undefined &&
                  regionWithBars?.endBar !== null &&
                  regionWithBars?.endBar !== undefined);
              if (!hasBarRange) return null;

              const startBar =
                currentRegionBarRange?.startBar ?? regionWithBars.startBar!;
              const endBar =
                currentRegionBarRange?.endBar ?? regionWithBars.endBar!;
              return (
                <span className="region-bar-range">
                  Bars {startBar.toFixed(1)} - {endBar.toFixed(1)}
                </span>
              );
            })()}
            <span className="region-index">
              Region {currentRegionIndex + 1} of {orderedRegions.length}
            </span>
          </div>
          <button
            className="nav-button"
            onClick={handleNextRegion}
            disabled={currentRegionIndex >= orderedRegions.length - 1}
          >
            Next →
          </button>
        </div>
        <div className="save-section">
          {/* DEBUG: this guard may be blocking lanes/waveform/timeline - save button disabled if !vcAnnotations */}
          <button
            className="save-button"
            onClick={handleSave}
            disabled={isSaving || isLoadingAnnotations || !vcAnnotations}
          >
            {isSaving ? "Saving..." : "Save"}
          </button>
          <div className="save-status-indicator">
            {saveStatus === "saving" && (
              <span className="save-status saving">Saving...</span>
            )}
            {saveStatus === "saved" && (
              <span className="save-status saved">All changes saved</span>
            )}
            {saveStatus === "error" && (
              <span className="save-status error" title={saveError?.message}>
                Save failed
              </span>
            )}
            {saveStatus === "idle" && isDirty && (
              <span className="save-status unsaved">Unsaved changes</span>
            )}
            {saveStatus === "idle" && !isDirty && !isLoadingAnnotations && (
              <span className="save-status saved">All changes saved</span>
            )}
          </div>
          {loadError && (
            <div className="load-error-badge">
              <span className="error-text">Failed to load annotations</span>
              <button
                className="retry-button"
                onClick={retryLoad}
                disabled={isLoadingAnnotations}
              >
                Retry
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="visual-composer-content-wrapper">
        <div className="visual-composer-content">
          {/* Waveform placeholder (demo mode) or real waveform */}
          {/* Always show waveform section if we have a current region */}
          {currentRegion && (
            <div className="vc-waveform-section">
              {demoMode ? (
                <div className="vc-waveform-placeholder">
                  Waveform demo placeholder (no audio in demo mode yet)
                </div>
              ) : (
                // TODO: Add real waveform component when audio is available
                <div className="vc-waveform-placeholder">
                  Waveform (audio not yet implemented)
                </div>
              )}
            </div>
          )}

          {/* Timeline area - show whenever currentRegion exists */}
          {/* Always show timeline if we have a current region, even if barCount is 0 */}
          {currentRegion && (
            <div className="timeline-section">
              <ComposerTimeline
                regionAnnotations={
                  localRegionAnnotations || {
                    regionId: selectedRegionId || "",
                    lanes: [],
                    blocks: [],
                    notes: "",
                  }
                }
                barCount={getRegionBars()}
                onCreateBlock={handleCreateBlock}
                onSelectBlock={handleSelectBlock}
                onUpdateBlock={handleUpdateBlock}
              />
            </div>
          )}

          {/* Lanes section - show whenever currentRegion exists and localRegionAnnotations is not null */}
        {currentRegion && localRegionAnnotations ? (
          <div className="lanes-section">
            <div className="lanes-container">
              {(() => {
                const lanes = localRegionAnnotations.lanes ?? [];

                if (lanes.length > 0) {
                  return (
                    <div className="lanes-list">
                      {lanes.map((lane) => (
                        <div
                          key={lane.id}
                          className="vc-lane-row"
                          style={{
                            padding: "0.5rem",
                            marginBottom: "0.5rem",
                            border: "1px solid #ddd",
                            borderRadius: "4px",
                            background: "#fff",
                          }}
                        >
                          <div
                            className="vc-lane-label"
                            style={{
                              fontWeight: "500",
                              marginBottom: "0.25rem",
                            }}
                          >
                            {lane.name}
                          </div>
                          <div
                            className="vc-lane-track"
                            style={{
                              minHeight: "40px",
                              background: "#f9f9f9",
                              borderRadius: "2px",
                            }}
                          >
                            {/* Lane track area - blocks will go here */}
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                } else {
                  return (
                    <div
                      className="vc-lane-empty"
                      style={{
                        padding: "2rem",
                        textAlign: "center",
                        color: "#666",
                      }}
                    >
                      <p>
                        No lanes yet — click "Add Lane" to create your first
                        sound lane.
                      </p>
                    </div>
                  );
                }
              })()}

              <div className="lanes-actions" style={{ marginTop: "1rem" }}>
                <button
                  type="button"
                  className="vc-add-lane-button"
                  onClick={handleAddLane}
                  style={{
                    padding: "0.75rem 1.5rem",
                    fontSize: "0.9rem",
                    fontWeight: "500",
                    color: "white",
                    background: "#1976d2",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                  }}
                >
                  + Add Lane
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="lanes-section">
            <div className="lanes-empty-state">
              <p>
                {!currentRegion
                  ? "No region selected. Please select a region."
                  : "Loading region annotations..."}
              </p>
            </div>
          </div>
        )}

        </div>

        <div className="visual-composer-sidebar">
          <div className="region-notes-section">
            <h3>Region Notes</h3>
            <textarea
              className="region-notes-input"
              value={localRegionAnnotations?.notes || ""}
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

        {__DEV__ && (
          <div
            style={{
              marginTop: "1rem",
              padding: "0.75rem",
              fontSize: "0.75rem",
              background: "#111",
              color: "#ddd",
              borderRadius: 4,
            }}
          >
            <strong>Visual Composer Debug</strong>
            <pre style={{ whiteSpace: "pre-wrap" }}>
              {JSON.stringify(vcDebugState, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default VisualComposerPage;
