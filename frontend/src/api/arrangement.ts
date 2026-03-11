/**
 * API client for arrangement endpoints (Phase 5).
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * A single block in the arrangement timeline.
 */
export interface ArrangementBlock {
  id: string;
  stemId: string;
  role: string;
  sectionId: string;
  startBar: number;
  endBar: number;
  active: boolean;
  variationType: string | null;
  sourceLoopStart: number;
  sourceLoopEnd: number;
}

/**
 * A section within the arrangement, mirroring the reference structure.
 */
export interface ArrangementSection {
  id: string;
  name: string;
  label: string;
  startBar: number;
  endBar: number;
  type: string;
}

/**
 * The full arrangement response.
 */
export interface Arrangement {
  id: string;
  projectId: string;
  sections: ArrangementSection[];
  blocks: ArrangementBlock[];
  totalBars: number;
  bpm: number;
}

/**
 * Generate an arrangement from the approved structure and user loops.
 */
export async function generateArrangement(
  projectId: string,
): Promise<Arrangement> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/arrange`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    },
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to generate arrangement' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Retrieve the current arrangement for a project.
 */
export async function getArrangement(
  projectId: string,
): Promise<Arrangement> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/arrangement`,
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch arrangement' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Update a single arrangement block (mute/unmute, move, resize).
 */
export async function updateArrangementBlock(
  projectId: string,
  blockId: string,
  updates: {
    active?: boolean;
    variationType?: string;
    startBar?: number;
    endBar?: number;
  },
): Promise<{ blockId: string; block: ArrangementBlock }> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/arrangement/blocks/${blockId}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    },
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update block' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Delete a block from the arrangement.
 */
export async function deleteArrangementBlock(
  projectId: string,
  blockId: string,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/arrangement/blocks/${blockId}`,
    { method: 'DELETE' },
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete block' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }
}
