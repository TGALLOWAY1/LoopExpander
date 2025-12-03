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
 * Motif instance type matching backend model.
 */
export interface MotifInstance {
  id: string;
  stemRole: string; // "drums", "bass", "vocals", "instruments", "full_mix"
  startTime: number; // seconds
  endTime: number; // seconds
  duration: number; // seconds
  groupId: string | null;
  isVariation: boolean;
  regionIds: string[];
}

/**
 * Motif group type matching backend model.
 */
export interface MotifGroup {
  id: string;
  label: string | null;
  memberIds: string[];
  memberCount: number;
  variationCount: number;
}

/**
 * Motifs response type.
 */
export interface MotifsResponse {
  referenceId: string;
  instances: MotifInstance[];
  groups: MotifGroup[];
  instanceCount: number;
  groupCount: number;
}

/**
 * Call-response pair type matching backend model.
 */
export interface CallResponsePair {
  id: string;
  fromMotifId: string;
  toMotifId: string;
  fromStemRole: string;
  toStemRole: string;
  fromTime: number; // seconds
  toTime: number; // seconds
  timeOffset: number; // seconds
  confidence: number; // 0.0 to 1.0
  regionId: string | null;
  isInterStem: boolean;
  isIntraStem: boolean;
}

/**
 * Call-response response type.
 */
export interface CallResponseResponse {
  referenceId: string;
  pairs: CallResponsePair[];
  count: number;
}

/**
 * Fill type matching backend model.
 */
export interface Fill {
  id: string;
  time: number; // seconds
  stemRoles: string[];
  regionId: string;
  confidence: number; // 0.0 to 1.0
  fillType: string | null; // e.g., "drum_fill", "bass_slide", "vocal_adlib"
}

/**
 * Fills response type.
 */
export interface FillsResponse {
  referenceId: string;
  fills: Fill[];
  count: number;
}

/**
 * Stem category type for subregions.
 */
export type StemCategory = 'drums' | 'bass' | 'vocals' | 'instruments';

/**
 * Subregion pattern type matching backend model.
 */
export interface SubRegionPattern {
  id: string;
  regionId: string;
  stemCategory: StemCategory;
  startBar: number;
  endBar: number;
  label?: string | null;
  motifGroupId?: string | null;
  isVariation?: boolean;
  isSilence?: boolean;
  intensity?: number; // 0–1
  metadata?: Record<string, unknown> | null;
}

/**
 * Region subregions type containing lanes per stem category.
 */
export interface RegionSubRegions {
  regionId: string;
  lanes: Record<StemCategory, SubRegionPattern[]>;
}

/**
 * Reference subregions response type.
 */
export interface ReferenceSubRegionsResponse {
  referenceId: string;
  regions: RegionSubRegions[];
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
 * Dev-only: Create a reference from Gallium test stems on disk.
 * 
 * @returns Promise with referenceId, bpm, duration, and key (same format as uploadReference)
 */
export async function createGalliumDevReference(): Promise<{ referenceId: string; bpm: number; duration: number; key: string | null }> {
  const response = await fetch(`${API_BASE_URL}/api/reference/dev/gallium`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to create Gallium dev reference' }));
    throw new Error(error.detail || `Failed to create Gallium dev reference with status ${response.status}`);
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

/**
 * Fetch detected motifs for a reference bundle.
 * 
 * @param referenceId - ID of the reference bundle
 * @param sensitivity - Optional sensitivity parameter (0.0 = strict, 1.0 = loose)
 * @returns Promise with motifs response
 */
export async function getMotifs(
  referenceId: string,
  sensitivity?: number
): Promise<MotifsResponse> {
  // Log before request
  console.log('[getMotifs] Fetching motifs:', { referenceId, sensitivity });
  
  const url = new URL(`${API_BASE_URL}/api/reference/${referenceId}/motifs`);
  if (sensitivity !== undefined) {
    url.searchParams.set('sensitivity', sensitivity.toString());
  }

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch motifs' }));
    throw new Error(error.detail || `Failed to fetch motifs with status ${response.status}`);
  }

  const data = await response.json();
  
  // Log after success
  console.log('[getMotifs] Motifs fetched successfully:', {
    referenceId,
    instanceCount: data.instanceCount || data.instances?.length || 0,
    groupCount: data.groupCount || data.groups?.length || 0,
  });
  
  return data;
}

/**
 * Re-analyze motifs for a reference bundle using stored sensitivity configuration.
 * 
 * @param referenceId - ID of the reference bundle
 * @returns Promise with analysis status and motif counts
 * @throws Error if the request fails or reference is not found
 */
export async function reanalyzeMotifs(referenceId: string): Promise<{
  referenceId: string;
  motifInstanceCount: number;
  motifGroupCount: number;
  status: string;
}> {
  const url = `${API_BASE_URL}/api/reference/${referenceId}/reanalyze-motifs`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to reanalyze motifs' }));
    throw new Error(error.detail || `Failed to reanalyze motifs with status ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch detected call-response pairs for a reference bundle.
 * 
 * @param referenceId - ID of the reference bundle
 * @returns Promise with call-response response
 */
export async function getCallResponse(referenceId: string): Promise<CallResponseResponse> {
  const response = await fetch(`${API_BASE_URL}/api/reference/${referenceId}/call-response`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch call-response pairs' }));
    throw new Error(error.detail || `Failed to fetch call-response pairs with status ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch detected fills for a reference bundle.
 * 
 * @param referenceId - ID of the reference bundle
 * @returns Promise with fills response
 */
export async function getFills(referenceId: string): Promise<FillsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/reference/${referenceId}/fills`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch fills' }));
    throw new Error(error.detail || `Failed to fetch fills with status ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch computed subregions for a reference bundle.
 * 
 * @param referenceId - ID of the reference bundle
 * @returns Promise with subregions response containing per-region lane data
 */
export async function fetchReferenceSubregions(
  referenceId: string
): Promise<ReferenceSubRegionsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/reference/${referenceId}/subregions`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch subregions' }));
    throw new Error(error.detail || `Failed to fetch subregions with status ${response.status}`);
  }

  const data = await response.json();
  
  // Validate and normalize the response structure
  if (!data.referenceId || !Array.isArray(data.regions)) {
    throw new Error('Invalid subregions response format');
  }

  // Ensure all regions have all 4 stem categories in lanes
  const normalizedRegions: RegionSubRegions[] = data.regions.map((region: RegionSubRegions) => {
    const lanes: Record<StemCategory, SubRegionPattern[]> = {
      drums: region.lanes?.drums || [],
      bass: region.lanes?.bass || [],
      vocals: region.lanes?.vocals || [],
      instruments: region.lanes?.instruments || [],
    };
    return {
      regionId: region.regionId,
      lanes,
    };
  });

  return {
    referenceId: data.referenceId,
    regions: normalizedRegions,
  };
}

