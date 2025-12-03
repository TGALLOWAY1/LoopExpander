/**
 * API client for motif sensitivity endpoints.
 */

import { MotifSensitivityConfig, MotifSensitivityUpdate } from "../types/motifSensitivity";

// Base URL for API (assumes same origin for now, can be configured via env)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Get motif sensitivity configuration for a reference bundle.
 * 
 * @param referenceId - ID of the reference bundle
 * @returns Promise with motif sensitivity configuration
 * @throws Error if the request fails or reference is not found
 */
export async function getMotifSensitivity(referenceId: string): Promise<MotifSensitivityConfig> {
  const url = `${API_BASE_URL}/api/reference/${referenceId}/motif-sensitivity`;
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch motif sensitivity' }));
    throw new Error(error.detail || `Failed to fetch motif sensitivity with status ${response.status}`);
  }

  const data = await response.json();
  
  // Extract the config from the response (backend returns { referenceId, motifSensitivityConfig })
  return data.motifSensitivityConfig;
}

/**
 * Update motif sensitivity configuration for a reference bundle.
 * 
 * Only provided keys will be updated; omitted keys remain unchanged.
 * All values must be in the range [0.0, 1.0].
 * 
 * @param referenceId - ID of the reference bundle
 * @param update - Partial update with sensitivity values to change
 * @returns Promise with updated motif sensitivity configuration
 * @throws Error if the request fails, reference is not found, or values are invalid
 */
export async function updateMotifSensitivity(
  referenceId: string,
  update: MotifSensitivityUpdate
): Promise<MotifSensitivityConfig> {
  // Validate values are in range [0.0, 1.0]
  for (const [key, value] of Object.entries(update)) {
    if (value !== undefined && (value < 0.0 || value > 1.0)) {
      throw new Error(`Invalid sensitivity value for ${key}: ${value}. Must be between 0.0 and 1.0`);
    }
  }

  const url = `${API_BASE_URL}/api/reference/${referenceId}/motif-sensitivity`;
  
  const response = await fetch(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(update),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update motif sensitivity' }));
    throw new Error(error.detail || `Failed to update motif sensitivity with status ${response.status}`);
  }

  const data = await response.json();
  
  // Extract the config from the response (backend returns { referenceId, motifSensitivityConfig })
  return data.motifSensitivityConfig;
}

