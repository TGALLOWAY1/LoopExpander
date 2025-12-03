/**
 * Hook for managing motif sensitivity configuration for a reference.
 * 
 * Provides state management for loading, editing, and saving motif sensitivity
 * settings per stem type (drums, bass, vocals, instruments).
 */

import React from "react";
import { getMotifSensitivity, updateMotifSensitivity } from "../api/motifSensitivity";
import { MotifSensitivityConfig, MotifSensitivityUpdate } from "../types/motifSensitivity";

/**
 * Hook to manage motif sensitivity configuration for a reference.
 * 
 * @param referenceId - ID of the reference bundle
 * @returns Object with:
 *   - config: Current sensitivity configuration (null while loading)
 *   - setConfig: Function to update config locally (optimistic update)
 *   - save: Function to save changes to backend
 *   - loading: Whether initial load is in progress
 *   - saving: Whether save operation is in progress
 *   - error: Any error that occurred during load or save
 */
export function useMotifSensitivity(referenceId: string) {
  const [config, setConfig] = React.useState<MotifSensitivityConfig | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<any>(null);

  // Load configuration when referenceId changes
  React.useEffect(() => {
    if (!referenceId) {
      setConfig(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    getMotifSensitivity(referenceId)
      .then(setConfig)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [referenceId]);

  /**
   * Save sensitivity configuration updates to the backend.
   * 
   * @param update - Partial update with sensitivity values to change
   * @returns Promise that resolves when save completes
   */
  async function save(update: MotifSensitivityUpdate) {
    if (!referenceId) {
      throw new Error("Cannot save: referenceId is required");
    }

    setSaving(true);
    setError(null);
    try {
      const updated = await updateMotifSensitivity(referenceId, update);
      setConfig(updated);
    } catch (err) {
      setError(err);
      throw err; // Re-throw so caller can handle if needed
    } finally {
      setSaving(false);
    }
  }

  return { config, setConfig, save, loading, saving, error };
}

