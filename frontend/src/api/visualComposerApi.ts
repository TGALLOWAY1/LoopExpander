/**
 * API client for Visual Composer annotations endpoints.
 */

// Base URL for API (assumes same origin for now, can be configured via env)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Visual Composer lane type (aligned with backend VisualComposerLane model).
 */
export interface VcLane {
  id: string;
  name: string;
  color?: string | null;
  collapsed: boolean;
  order: number;
}

/**
 * Visual Composer block type (aligned with backend VisualComposerBlock model).
 */
export interface VcBlock {
  id: string;
  laneId: string;
  startBar: number;
  endBar: number;
  color?: string | null;
  type: 'call' | 'response' | 'variation' | 'fill' | 'custom';
  notes?: string | null;
}

/**
 * Visual Composer region annotations type (aligned with backend VisualComposerRegionAnnotations model).
 */
export interface VcRegionAnnotations {
  regionId: string;
  regionName?: string | null;
  notes?: string | null;
  startBar?: number | null;
  endBar?: number | null;
  regionType?: string | null;
  displayOrder?: number | null;
  lanes: VcLane[];
  blocks: VcBlock[];
}

/**
 * Visual Composer annotations type (aligned with backend VisualComposerAnnotations model).
 */
export interface VcAnnotations {
  projectId: string;
  regions: VcRegionAnnotations[];
}

/**
 * Get Visual Composer annotations for a project.
 * 
 * @param projectId - ID of the project
 * @returns Promise with annotations data, or empty structure if none exist
 */
export async function getVisualComposerAnnotations(projectId: string): Promise<VcAnnotations> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/visual-composer/${projectId}/annotations`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Handle 404 or other errors by returning empty structure instead of throwing
    if (!response.ok) {
      if (response.status === 404) {
        // 404 is expected for new projects - return empty structure
        return {
          projectId,
          regions: [],
        };
      }
      // For other errors, log and return empty structure
      console.warn(`Failed to fetch Visual Composer annotations for project ${projectId}: ${response.status}`);
      return {
        projectId,
        regions: [],
      };
    }

    const data = await response.json();
    
    // Normalize data with safe defaults
    return {
      projectId: data.projectId || projectId,
      regions: (data.regions || []).map((region: any) => ({
        regionId: region.regionId || '',
        regionName: region.regionName ?? null,
        notes: region.notes ?? null,
        startBar: region.startBar ?? null,
        endBar: region.endBar ?? null,
        regionType: region.regionType ?? null,
        displayOrder: region.displayOrder ?? null,
        lanes: region.lanes || [],
        blocks: region.blocks || [],
      })),
    };
  } catch (error) {
    // Network errors or JSON parsing errors - return empty structure
    console.warn(`Error fetching Visual Composer annotations for project ${projectId}:`, error);
    return {
      projectId,
      regions: [],
    };
  }
}

/**
 * Save Visual Composer annotations for a project.
 * 
 * @param projectId - ID of the project
 * @param payload - Annotations data to save
 * @returns Promise with saved annotations data
 */
export async function saveVisualComposerAnnotations(
  projectId: string,
  payload: VcAnnotations
): Promise<VcAnnotations> {
  // Ensure projectId in payload matches parameter
  const normalizedPayload: VcAnnotations = {
    ...payload,
    projectId,
  };

  const response = await fetch(`${API_BASE_URL}/api/visual-composer/${projectId}/annotations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(normalizedPayload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to save annotations' }));
    throw new Error(error.detail || `Failed to save annotations with status ${response.status}`);
  }

  const data = await response.json();
  
  // Normalize response with safe defaults
  return {
    projectId: data.projectId || projectId,
    regions: (data.regions || []).map((region: any) => ({
      regionId: region.regionId || '',
      regionName: region.regionName ?? null,
      notes: region.notes ?? null,
      lanes: region.lanes || [],
      blocks: region.blocks || [],
    })),
  };
}

