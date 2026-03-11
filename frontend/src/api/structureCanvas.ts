/**
 * API client for Structure Canvas endpoints.
 *
 * Provides functions for managing sections (regions), role activity,
 * and energy data for the full-song Structure Canvas view.
 */

import {
  MixRegion,
  RoleActivityTimeline,
  EnergyCurveResponse,
  getMixRegions,
  getRoleActivity,
  getEnergyCurve,
} from './referenceMix';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Section type used in the Structure Canvas.
 * Extends MixRegion with editable fields.
 */
export interface CanvasSection extends MixRegion {
  color: string;
}

/**
 * Patch payload for updating region boundaries or labels.
 */
export interface RegionPatch {
  id: string;
  name?: string;
  label?: string;
  type?: string;
  startBar?: number;
  endBar?: number;
}

/**
 * Split region request.
 */
export interface SplitRegionRequest {
  regionId: string;
  splitBar: number;
}

/**
 * Merge region request.
 */
export interface MergeRegionRequest {
  regionId1: string;
  regionId2: string;
}

/**
 * Role activity override payload.
 */
export interface RoleActivityOverride {
  role: string;
  startBar: number;
  endBar: number;
  active: boolean;
}

/**
 * Full Structure Canvas state bundling all analysis data.
 */
export interface StructureCanvasData {
  sections: CanvasSection[];
  roleTimelines: RoleActivityTimeline[];
  energyCurve: EnergyCurveResponse | null;
  totalBars: number;
}

// Section type color mapping
const SECTION_COLORS: Record<string, string> = {
  intro: '#4CAF50',
  verse: '#2196F3',
  chorus: '#FF9800',
  bridge: '#9C27B0',
  drop: '#F44336',
  breakdown: '#607D8B',
  build: '#FF5722',
  outro: '#795548',
  low_energy: '#78909C',
  medium_energy: '#42A5F5',
  high_energy: '#EF5350',
};

function getSectionColor(type: string): string {
  return SECTION_COLORS[type] || '#9E9E9E';
}

/**
 * Load all data needed for the Structure Canvas.
 */
export async function loadStructureCanvasData(
  referenceId: string,
): Promise<StructureCanvasData> {
  const [regionsRes, roleRes, energyRes] = await Promise.allSettled([
    getMixRegions(referenceId),
    getRoleActivity(referenceId),
    getEnergyCurve(referenceId),
  ]);

  const regions =
    regionsRes.status === 'fulfilled' ? regionsRes.value.regions : [];
  const roleTimelines =
    roleRes.status === 'fulfilled' ? roleRes.value.timelines : [];
  const energyCurve =
    energyRes.status === 'fulfilled' ? energyRes.value : null;

  const sections: CanvasSection[] = regions.map((r) => ({
    ...r,
    color: getSectionColor(r.type),
  }));

  const totalBars = Math.max(
    ...sections.map((s) => s.endBar),
    energyCurve?.barEnergies?.length ?? 0,
    0,
  );

  return {
    sections,
    roleTimelines,
    energyCurve,
    totalBars: Math.ceil(totalBars),
  };
}

/**
 * Update region boundaries and labels.
 */
export async function patchRegions(
  referenceId: string,
  patches: RegionPatch[],
): Promise<MixRegion[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/reference/${referenceId}/regions`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patches }),
    },
  );

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: 'Failed to update regions' }));
    throw new Error(
      error.detail || `Failed to update regions with status ${response.status}`,
    );
  }

  const data = await response.json();
  return data.regions;
}

/**
 * Split a region at a given bar position.
 */
export async function splitRegion(
  referenceId: string,
  regionId: string,
  splitBar: number,
): Promise<MixRegion[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/reference/${referenceId}/regions/split`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ regionId, splitBar }),
    },
  );

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: 'Failed to split region' }));
    throw new Error(
      error.detail || `Failed to split region with status ${response.status}`,
    );
  }

  const data = await response.json();
  return data.regions;
}

/**
 * Merge two adjacent regions.
 */
export async function mergeRegions(
  referenceId: string,
  regionId1: string,
  regionId2: string,
): Promise<MixRegion[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/reference/${referenceId}/regions/merge`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ regionId1, regionId2 }),
    },
  );

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: 'Failed to merge regions' }));
    throw new Error(
      error.detail || `Failed to merge regions with status ${response.status}`,
    );
  }

  const data = await response.json();
  return data.regions;
}

/**
 * Update role activity overrides.
 */
export async function patchRoleActivity(
  referenceId: string,
  overrides: RoleActivityOverride[],
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/reference/${referenceId}/role-activity`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ overrides }),
    },
  );

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: 'Failed to update role activity' }));
    throw new Error(
      error.detail ||
        `Failed to update role activity with status ${response.status}`,
    );
  }
}
