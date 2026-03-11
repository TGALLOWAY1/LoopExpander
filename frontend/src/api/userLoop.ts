/**
 * API client for user loop/stem endpoints (Phase 4).
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Valid role assignments for user loop stems.
 */
export const VALID_ROLES = [
  'drums', 'bass', 'chord', 'lead', 'vocal',
  'fx', 'percussion', 'texture',
] as const;

export type StemRole = typeof VALID_ROLES[number];

/**
 * Display labels for roles.
 */
export const ROLE_LABELS: Record<StemRole, string> = {
  drums: 'Drums',
  bass: 'Bass',
  chord: 'Chord / Harmony',
  lead: 'Lead / Melody',
  vocal: 'Vocal',
  fx: 'FX / Transition',
  percussion: 'Percussion',
  texture: 'Texture / Pad',
};

/**
 * Color mapping for roles.
 */
export const ROLE_COLORS: Record<StemRole, string> = {
  drums: '#EF5350',
  bass: '#42A5F5',
  chord: '#66BB6A',
  lead: '#FFA726',
  vocal: '#AB47BC',
  fx: '#26C6DA',
  percussion: '#EC407A',
  texture: '#78909C',
};

export interface UserLoopStem {
  id: string;
  filename: string;
  role: StemRole;
  loopLengthBars: number;
  startBar: number;
  endBar: number;
  audioPath: string;
  durationSeconds: number;
}

export interface UserLoopBundle {
  id: string;
  projectId: string;
  stems: UserLoopStem[];
  bpm: number;
  detectedBpm: number;
  bpmRatio: number;
}

export interface UploadLoopsResponse {
  projectId: string;
  bundleId: string;
  bpm: number;
  detectedBpm: number;
  bpmRatio: number;
  stemCount: number;
  newStems: UserLoopStem[];
  allStems: UserLoopStem[];
}

export interface GetLoopsResponse {
  projectId: string;
  bundle: UserLoopBundle | null;
  stemCount: number;
}

/**
 * Upload one or more loop stems for a project.
 */
export async function uploadUserLoops(
  projectId: string,
  files: File[],
  bpmOverride?: number,
): Promise<UploadLoopsResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  let url = `${API_BASE_URL}/api/project/${projectId}/loops/upload`;
  if (bpmOverride !== undefined) {
    url += `?bpm_override=${bpmOverride}`;
  }

  const response = await fetch(url, {
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
 * Fetch all user loop stems for a project.
 */
export async function getUserLoops(projectId: string): Promise<GetLoopsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/project/${projectId}/loops`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch loops' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }
  return response.json();
}

/**
 * Update the role assignment for a stem.
 */
export async function updateStemRole(
  projectId: string,
  stemId: string,
  role: StemRole,
): Promise<{ stemId: string; role: string; stem: UserLoopStem }> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/loops/${stemId}/role`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    },
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update role' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }
  return response.json();
}

/**
 * Update loop length and trim boundaries for a stem.
 */
export async function updateStemBounds(
  projectId: string,
  stemId: string,
  bounds: { loopLengthBars?: number; startBar?: number; endBar?: number },
): Promise<{ stemId: string; stem: UserLoopStem }> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/loops/${stemId}/bounds`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bounds),
    },
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update bounds' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }
  return response.json();
}

/**
 * Delete a user loop stem.
 */
export async function deleteUserStem(
  projectId: string,
  stemId: string,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/loops/${stemId}`,
    { method: 'DELETE' },
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete stem' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }
}

/**
 * Update the BPM for the user's loop bundle.
 */
export async function updateLoopBpm(
  projectId: string,
  bpm: number,
): Promise<{ projectId: string; bpm: number; bpmRatio: number; bundle: UserLoopBundle }> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/loops/bpm`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bpm }),
    },
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update BPM' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }
  return response.json();
}
