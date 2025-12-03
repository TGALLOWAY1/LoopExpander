/**
 * Hook for loading and saving Visual Composer annotations.
 * 
 * Provides state management for Visual Composer annotations with automatic
 * loading on mount and manual save functionality.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  getVisualComposerAnnotations,
  saveVisualComposerAnnotations,
  type VcAnnotations,
} from '../api/visualComposerApi';

/**
 * Hook to load and save Visual Composer annotations for a project.
 * 
 * @param projectId - ID of the project (can be null/undefined to disable loading)
 * @returns Object with:
 *   - annotations: Current annotations data (null while loading or if error)
 *   - setAnnotations: Function to update annotations locally
 *   - isLoading: Whether data is being loaded
 *   - error: Any error that occurred during loading
 *   - saveAnnotations: Function to save annotations to the backend
 *   - isSaving: Whether a save operation is in progress
 */
export function useVisualComposerAnnotations(projectId: string | null | undefined) {
  const [annotations, setAnnotations] = useState<VcAnnotations | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Load annotations on mount or when projectId changes
  useEffect(() => {
    if (!projectId) {
      setAnnotations(null);
      setIsLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);
    
    getVisualComposerAnnotations(projectId)
      .then((data) => {
        if (!cancelled) {
          setAnnotations(data);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error(String(err)));
          // On error, initialize with empty structure
          setAnnotations({
            projectId,
            regions: [],
          });
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [projectId]);

  // Save annotations to backend
  const saveAnnotations = useCallback(async () => {
    if (!projectId || !annotations) {
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const saved = await saveVisualComposerAnnotations(projectId, annotations);
      setAnnotations(saved);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      throw error; // Re-throw so caller can handle it
    } finally {
      setIsSaving(false);
    }
  }, [projectId, annotations]);

  return {
    annotations,
    setAnnotations,
    isLoading,
    error,
    saveAnnotations,
    isSaving,
  };
}

