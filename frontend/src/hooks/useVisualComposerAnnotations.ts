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
} from '../api/visualComposerApi';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

/**
 * Hook to load and save Visual Composer annotations for a project.
 * 
 * @param projectId - ID of the project (can be null/undefined to disable loading)
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
export function useVisualComposerAnnotations(projectId: string | null | undefined) {
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

  // Load annotations on mount or when projectId changes
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
  }, [projectId]);

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
  const performSave = useCallback(async (): Promise<void> => {
    if (!projectId || !annotations) {
      return;
    }

    setIsSaving(true);
    setSaveStatus('saving');
    setError(null);

    try {
      const saved = await saveVisualComposerAnnotations(projectId, annotations);
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
  }, [projectId, annotations]);

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
          
          // Set new autosave timeout (1.5 seconds)
          autosaveTimeoutRef.current = setTimeout(() => {
            if (projectId && next) {
              performSave().catch(err => {
                console.error('Autosave failed:', err);
              });
            }
            autosaveTimeoutRef.current = null;
          }, 1500);
        }
      } else if (next && !lastSavedAnnotationsRef.current) {
        // First time setting annotations (after load), mark as dirty if different from loaded
        setIsDirty(true);
      }
      
      return next;
    });
  }, [projectId, performSave]);

  // Cleanup autosave timeout on unmount
  useEffect(() => {
    return () => {
      if (autosaveTimeoutRef.current) {
        clearTimeout(autosaveTimeoutRef.current);
      }
    };
  }, []);

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
  };
}

