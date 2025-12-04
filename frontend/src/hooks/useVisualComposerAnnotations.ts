/**
 * Hook for loading and saving Visual Composer annotations.
 * 
 * Provides state management for Visual Composer annotations with automatic
 * loading on mount, debounced autosave, and manual save functionality.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  getVisualComposerAnnotations,
  saveVisualComposerAnnotations,
  type VcAnnotations,
  type VcRegionAnnotations,
} from '../api/visualComposerApi';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

/**
 * Region metadata for demo mode initialization.
 */
export interface RegionMeta {
  id: string;
  name: string;
  type: string;
  start: number;
  end: number;
  startBar?: number;
  endBar?: number;
  displayOrder?: number;
}

/**
 * Hook to load and save Visual Composer annotations for a project.
 * 
 * @param projectId - ID of the project (can be null/undefined to disable loading)
 * @param demoMode - If true, skip API calls and use initialRegions
 * @param initialRegions - Regions to use in demo mode (ignored if demoMode is false)
 * @returns Object with:
 *   - annotations: Current annotations data (null while loading or if error)
 *   - setAnnotations: Function to update annotations locally (marks as dirty)
 *   - isLoading: Whether data is being loaded
 *   - error: Any error that occurred during loading
 *   - saveAnnotations: Function to save annotations to the backend (manual save)
 *   - isSaving: Whether a save operation is in progress
 *   - saveStatus: Current save status ('idle' | 'saving' | 'saved' | 'error')
 *   - isDirty: Whether annotations have unsaved changes
 *   - forceSave: Function to force an immediate save (for region navigation)
 */
export function useVisualComposerAnnotations(
  projectId: string | null | undefined,
  demoMode: boolean = false,
  initialRegions?: RegionMeta[] | null
) {
  const [annotations, setAnnotations] = useState<VcAnnotations | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [isDirty, setIsDirty] = useState(false);
  const [loadError, setLoadError] = useState<Error | null>(null); // Separate error for initial load
  
  // Ref to track autosave timeout
  const autosaveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Ref to track the last saved annotations (for dirty detection)
  const lastSavedAnnotationsRef = useRef<VcAnnotations | null>(null);

  // Load annotations on mount or when projectId/demoMode/initialRegions change
  useEffect(() => {
    if (!projectId) {
      setAnnotations(null);
      setIsLoading(false);
      setError(null);
      setLoadError(null);
      setIsDirty(false);
      lastSavedAnnotationsRef.current = null;
      return;
    }

    // In demo mode, construct annotations from initialRegions without calling API
    if (demoMode && initialRegions && initialRegions.length > 0) {
      const demoAnnotations: VcAnnotations = {
        projectId,
        regions: initialRegions.map((region): VcRegionAnnotations => ({
          regionId: region.id,
          regionName: region.name,
          notes: null,
          startBar: region.startBar ?? null,
          endBar: region.endBar ?? null,
          regionType: region.type,
          displayOrder: region.displayOrder ?? null,
          lanes: [],
          blocks: [],
        })),
      };
      
      setAnnotations(demoAnnotations);
      setError(null);
      setLoadError(null);
      setIsLoading(false);
      setIsDirty(false);
      lastSavedAnnotationsRef.current = JSON.parse(JSON.stringify(demoAnnotations));
      setSaveStatus('idle');
      return;
    }

    // Use a cancellation flag to prevent setState on unmounted component
    let cancelled = false;

    setIsLoading(true);
    setLoadError(null);
    setError(null);
    setIsDirty(false);
    
    const loadAnnotations = async () => {
      try {
        const data = await getVisualComposerAnnotations(projectId);
        
        // Check if component was unmounted before updating state
        if (!cancelled) {
          setAnnotations(data);
          setError(null);
          setLoadError(null);
          lastSavedAnnotationsRef.current = JSON.parse(JSON.stringify(data)); // Deep copy for comparison
          setSaveStatus('idle');
        }
      } catch (err) {
        // getVisualComposerAnnotations should never throw (returns empty structure on error)
        // But handle it just in case
        if (!cancelled) {
          const error = err instanceof Error ? err : new Error(String(err));
          setLoadError(error);
          // On error, initialize with empty structure but DON'T wipe existing annotations
          // This preserves in-memory state if user has unsaved edits
          setAnnotations(prev => {
            if (!prev) {
              const emptyAnnotations = {
                projectId,
                regions: [],
              };
              lastSavedAnnotationsRef.current = JSON.parse(JSON.stringify(emptyAnnotations));
              return emptyAnnotations;
            }
            return prev; // Keep existing annotations
          });
          setSaveStatus('idle');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    loadAnnotations();

    // Cleanup function to cancel any pending operations
    return () => {
      cancelled = true;
    };
  }, [projectId, demoMode, initialRegions]); // Include demoMode and initialRegions in deps

  // Expose loadAnnotations for retry functionality
  const loadAnnotations = useCallback(async () => {
    if (!projectId) {
      setAnnotations(null);
      setIsLoading(false);
      setError(null);
      setLoadError(null);
      setIsDirty(false);
      lastSavedAnnotationsRef.current = null;
      return;
    }

    let cancelled = false;

    setIsLoading(true);
    setLoadError(null);
    setError(null);
    setIsDirty(false);
    
    try {
      const data = await getVisualComposerAnnotations(projectId);
      
      if (!cancelled) {
        setAnnotations(data);
        setError(null);
        setLoadError(null);
        lastSavedAnnotationsRef.current = JSON.parse(JSON.stringify(data));
        setSaveStatus('idle');
      }
    } catch (err) {
      if (!cancelled) {
        const error = err instanceof Error ? err : new Error(String(err));
        setLoadError(error);
        setAnnotations(prev => {
          if (!prev) {
            const emptyAnnotations = {
              projectId,
              regions: [],
            };
            lastSavedAnnotationsRef.current = JSON.parse(JSON.stringify(emptyAnnotations));
            return emptyAnnotations;
          }
          return prev;
        });
        setSaveStatus('idle');
      }
    } finally {
      if (!cancelled) {
        setIsLoading(false);
      }
    }
  }, [projectId]);

  // Internal save function (shared by autosave and manual save)
  // Use functional setState to avoid dependency on annotations
  const performSave = useCallback(async (): Promise<void> => {
    if (!projectId || demoMode) {
      // Skip save in demo mode
      return;
    }

    setIsSaving(true);
    setSaveStatus('saving');
    setError(null);

    try {
      // Use functional update to get latest annotations
      let currentAnnotations: VcAnnotations | null = null;
      setAnnotations(prev => {
        currentAnnotations = prev;
        return prev;
      });

      if (!currentAnnotations) {
        throw new Error('No annotations to save');
      }

      const saved = await saveVisualComposerAnnotations(projectId, currentAnnotations);
      setAnnotations(saved);
      lastSavedAnnotationsRef.current = JSON.parse(JSON.stringify(saved)); // Deep copy
      setIsDirty(false);
      setSaveStatus('saved');
      
      // Clear saved status after 2 seconds
      setTimeout(() => {
        setSaveStatus(prev => prev === 'saved' ? 'idle' : prev);
      }, 2000);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      setSaveStatus('error');
      throw error; // Re-throw so caller can handle it
    } finally {
      setIsSaving(false);
    }
  }, [projectId, demoMode]); // Removed annotations dependency, use functional update instead

  // Manual save function (explicit save button)
  const saveAnnotations = useCallback(async () => {
    await performSave();
  }, [performSave]);

  // Force immediate save (for region navigation)
  const forceSave = useCallback(async (): Promise<void> => {
    // Clear any pending autosave
    if (autosaveTimeoutRef.current) {
      clearTimeout(autosaveTimeoutRef.current);
      autosaveTimeoutRef.current = null;
    }
    
    if (isDirty) {
      await performSave();
    }
  }, [isDirty, performSave]);

  // Wrapper for setAnnotations that marks as dirty and triggers autosave
  // Use functional setState to avoid dependency on annotations
  const setAnnotationsWithAutosave = useCallback((newAnnotations: VcAnnotations | null | ((prev: VcAnnotations | null) => VcAnnotations | null)) => {
    setAnnotations(prev => {
      const next = typeof newAnnotations === 'function' ? newAnnotations(prev) : newAnnotations;
      
      // Check if annotations actually changed
      if (next && lastSavedAnnotationsRef.current) {
        const prevJson = JSON.stringify(lastSavedAnnotationsRef.current);
        const nextJson = JSON.stringify(next);
        if (prevJson !== nextJson) {
          setIsDirty(true);
          
          // Clear existing autosave timeout
          if (autosaveTimeoutRef.current) {
            clearTimeout(autosaveTimeoutRef.current);
          }
          
          // Set new autosave timeout (1.5 seconds) - skip autosave in demo mode
          if (!demoMode && projectId && next) {
            autosaveTimeoutRef.current = setTimeout(() => {
              // Use functional update to get latest annotations
              setAnnotations(current => {
                if (current && projectId) {
                  performSave().catch(err => {
                    console.error('Autosave failed:', err);
                  });
                }
                return current;
              });
              autosaveTimeoutRef.current = null;
            }, 1500);
          }
        }
      } else if (next && !lastSavedAnnotationsRef.current) {
        // First time setting annotations (after load), mark as dirty if different from loaded
        setIsDirty(true);
      }
      
      return next;
    });
  }, [projectId, demoMode]); // Removed performSave dependency, use functional update instead

  // Cleanup autosave timeout on unmount
  useEffect(() => {
    return () => {
      if (autosaveTimeoutRef.current) {
        clearTimeout(autosaveTimeoutRef.current);
      }
    };
  }, []);

  // Add lane function - updates vcAnnotations for a specific region
  const addLane = useCallback((regionId: string) => {
    setAnnotationsWithAutosave(prev => {
      if (!prev) return prev;

      const regions = prev.regions ?? [];
      const idx = regions.findIndex(r => r.regionId === regionId);
      if (idx === -1) return prev;

      const target = regions[idx];

      const newLaneId = crypto.randomUUID
        ? crypto.randomUUID()
        : `lane-${Date.now()}-${Math.random().toString(16).slice(2)}`;

      // Pick a color from a simple palette
      const laneColors = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3', '#F38181', '#AA96DA', '#FCBAD3', '#A8E6CF'];
      const colorIndex = (target.lanes?.length ?? 0) % laneColors.length;
      const color = laneColors[colorIndex];

      const newLane = {
        id: newLaneId,
        name: `New Lane`,
        color: color,
        collapsed: false,
        order: target.lanes?.length ?? 0,
      };

      const updatedRegion = {
        ...target,
        lanes: [...(target.lanes ?? []), newLane],
      };

      const updatedRegions = [...regions];
      updatedRegions[idx] = updatedRegion;

      return {
        ...prev,
        regions: updatedRegions,
      };
    });
  }, [setAnnotationsWithAutosave]);

  return {
    annotations,
    setAnnotations: setAnnotationsWithAutosave,
    isLoading,
    error, // Save errors
    loadError, // Initial load errors (for retry)
    saveAnnotations,
    isSaving,
    saveStatus,
    isDirty,
    forceSave,
    retryLoad: loadAnnotations, // Retry function for initial load failures
    addLane, // Add lane function
  };
}

