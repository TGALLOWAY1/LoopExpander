import React from "react";

import { getMotifSensitivity, updateMotifSensitivity } from "../api/motifSensitivity";

import { MotifSensitivityConfig, MotifSensitivityUpdate } from "../types/motifSensitivity";

/**
 * Hook for managing motif sensitivity configuration for a reference bundle.
 * 
 * Automatically loads the configuration when the referenceId changes.
 * Provides methods to update and save the configuration.
 * 
 * @param referenceId - ID of the reference bundle
 * @returns Object with config state, loading/saving states, error, and save function
 */
export function useMotifSensitivity(referenceId: string) {
  const [config, setConfig] = React.useState<MotifSensitivityConfig | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<any>(null);

  React.useEffect(() => {
    setLoading(true);
    setError(null);
    getMotifSensitivity(referenceId)
      .then(setConfig)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [referenceId]);

  /**
   * Save updated sensitivity configuration.
   * Only provided keys in the update will be changed; omitted keys remain unchanged.
   * 
   * @param update - Partial update with sensitivity values to change
   * @returns Promise that resolves when the update is complete
   */
  async function save(update: MotifSensitivityUpdate) {
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

