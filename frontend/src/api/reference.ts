/**
 * API client for reference track endpoints.
 */

// Base URL for API (assumes same origin for now, can be configured via env)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Region type matching backend model.
 */
export interface Region {
  id: string;
  name: string;
  type: string; // e.g., "low_energy", "build", "high_energy", "drop"
  start: number; // seconds
  end: number; // seconds
  duration: number; // seconds
  motifs: string[];
  fills: string[];
  callResponse: Array<Record<string, unknown>>;
}

/**
 * Upload reference track stems and full mix.
 * 
 * @param files - Object containing 5 audio files
 * @returns Promise with referenceId
 */
export async function uploadReference(files: {
  drums: File;
  bass: File;
  vocals: File;
  instruments: File;
  full_mix: File;
}): Promise<{ referenceId: string; bpm: number; duration: number; key: string | null }> {
  const formData = new FormData();
  formData.append('drums', files.drums);
  formData.append('bass', files.bass);
  formData.append('vocals', files.vocals);
  formData.append('instruments', files.instruments);
  formData.append('full_mix', files.full_mix);

  const response = await fetch(`${API_BASE_URL}/api/reference/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || `Upload failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Analyze a reference bundle to detect regions.
 * 
 * @param referenceId - ID of the reference bundle to analyze
 * @returns Promise with analysis status and region count
 */
export async function analyzeReference(
  referenceId: string
): Promise<{ referenceId: string; regionCount: number; status: string }> {
  const response = await fetch(`${API_BASE_URL}/api/reference/${referenceId}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Analysis failed' }));
    throw new Error(error.detail || `Analysis failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch detected regions for a reference bundle.
 * 
 * @param referenceId - ID of the reference bundle
 * @returns Promise with array of regions
 */
export async function fetchRegions(referenceId: string): Promise<Region[]> {
  const response = await fetch(`${API_BASE_URL}/api/reference/${referenceId}/regions`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch regions' }));
    throw new Error(error.detail || `Failed to fetch regions with status ${response.status}`);
  }

  const data = await response.json();
  return data.regions || [];
}

