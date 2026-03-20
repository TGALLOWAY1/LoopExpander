/**
 * API client for interaction label endpoints (Phase 3).
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface InteractionLabel {
  id: string;
  sectionId: string;
  startBar: number;
  endBar: number;
  label: string;
  role?: string | null;
  color: string | null;
  notes: string | null;
}

export interface InteractionLabelsResponse {
  referenceId: string;
  labels: InteractionLabel[];
  count: number;
}

export interface InteractionLabelCreate {
  sectionId: string;
  startBar: number;
  endBar: number;
  label: string;
  role?: string | null;
  color?: string | null;
  notes?: string | null;
}

/**
 * Valid interaction label types.
 */
export const INTERACTION_LABEL_TYPES = [
  'A', 'B', 'ABAB', 'call', 'response', 'fill', 'sustain', 'break', 'transition',
] as const;

export type InteractionLabelType = typeof INTERACTION_LABEL_TYPES[number];

/**
 * Color mapping for interaction label types.
 */
export const LABEL_COLORS: Record<string, string> = {
  A: '#4FC3F7',
  B: '#FFB74D',
  ABAB: '#81C784',
  call: '#7986CB',
  response: '#F06292',
  fill: '#FFD54F',
  sustain: '#A1887F',
  break: '#90A4AE',
  transition: '#CE93D8',
};

/**
 * Fetch all interaction labels for a reference.
 */
export async function getInteractionLabels(
  referenceId: string,
): Promise<InteractionLabelsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/reference/${referenceId}/interactions`,
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch labels' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }
  return response.json();
}

/**
 * Create interaction labels in batch.
 */
export async function createInteractionLabels(
  referenceId: string,
  labels: InteractionLabelCreate[],
): Promise<InteractionLabelsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/reference/${referenceId}/interactions`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ labels }),
    },
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to create labels' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }
  return response.json();
}

/**
 * Update a single interaction label.
 */
export async function updateInteractionLabel(
  referenceId: string,
  labelId: string,
  updates: Partial<InteractionLabel>,
): Promise<{ referenceId: string; label: InteractionLabel }> {
  const response = await fetch(
    `${API_BASE_URL}/api/reference/${referenceId}/interactions/${labelId}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    },
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update label' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }
  return response.json();
}

/**
 * Delete an interaction label.
 */
export async function deleteInteractionLabel(
  referenceId: string,
  labelId: string,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/reference/${referenceId}/interactions/${labelId}`,
    { method: 'DELETE' },
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete label' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }
}

/**
 * Duplicate interaction labels from one section to another.
 */
export async function duplicatePattern(
  referenceId: string,
  sourceSectionId: string,
  targetSectionId: string,
): Promise<InteractionLabelsResponse & { duplicated: number }> {
  const response = await fetch(
    `${API_BASE_URL}/api/reference/${referenceId}/interactions/duplicate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sourceSectionId, targetSectionId }),
    },
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to duplicate pattern' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }
  return response.json();
}
